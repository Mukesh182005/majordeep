"""Screenshot / screen-recapture detection and letterbox removal.

A screenshot of an image is not the image. The capture is resampled to the
display scale, framed by viewer chrome (black or grey bars, toolbars), and
re-encoded — which strips EXIF / C2PA provenance and blurs away the
high-frequency traces AI-image detectors rely on. The uniform bars also skew
every whole-frame statistic (noise level, "zero-noise matte" ratio, the 224 px
classifier input), so they are removed before analysis.

Only borders that look like a frame are cropped: each side must be a run of
near-uniform lines whose inner edge meets content along most of its length. A
subject cut out onto a black background fails that test (its first content
line is mostly background), so genuine composites keep their matte.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from PIL import Image

# A line is part of a bar when this share of its pixels matches its median colour.
_BAR_PIXEL_SHARE = 0.95
_BAR_COLOUR_TOL = 10
# Inner edge of a frame: share of pixels that must differ from the bar colour.
_EDGE_COVERAGE = 0.5
_EDGE_DIFF = 12
# Window chrome (hairlines, scrollbars, editor gutters) may sit outside a bar.
_MAX_CHROME_FRAC = 0.03
# Ignore hairline borders; refuse crops that would leave too little content.
_MIN_BORDER_FRAC = 0.005
_MIN_BORDER_PX = 2
_MIN_CONTENT_FRAC = 0.3
_MIN_SIDE_PX = 64
# Bars are found on a reduced copy; NEAREST keeps flat bars exactly flat.
_DETECT_MAX_SIDE = 1024


def _bar_lines(lines: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per line (axis 0): is it a flat bar, and what is its median colour?"""
    median = np.median(lines, axis=1, keepdims=True)
    close = np.abs(lines - median).max(axis=2) <= _BAR_COLOUR_TOL
    return close.mean(axis=1) >= _BAR_PIXEL_SHARE, median[:, 0, :]


def _bar_depth(is_bar: np.ndarray, colour: np.ndarray, limit: int, min_run: int, max_chrome: int) -> int:
    """Depth of the one-colour bar at the edge, allowing a thin chrome strip outside it.

    The run stops where the colour changes, so a flat region at the edge of the
    picture itself is never mistaken for part of a differently coloured bar.
    Anything thinner than a bar at the very edge (a 1 px window outline, an
    editor gutter) is treated as chrome, provided a real bar follows it.
    """
    start = 0
    while start < min(max_chrome, limit):
        if not is_bar[start]:
            start += 1
            continue
        end = start
        while end < limit and is_bar[end] and np.abs(colour[end] - colour[start]).max() <= _BAR_COLOUR_TOL:
            end += 1
        if end - start >= max(min_run, 2 * start):
            return end
        start = end
    return 0


def _edge_is_frame(bar: np.ndarray, edge_line: np.ndarray) -> bool:
    """True when the content line next to a bar differs from the bar along most of its length."""
    if bar.size == 0 or edge_line.size == 0:
        return False
    bar_colour = np.median(bar.reshape(-1, 3), axis=0)
    differs = np.abs(edge_line.reshape(-1, 3) - bar_colour).max(axis=1) > _EDGE_DIFF
    return float(differs.mean()) >= _EDGE_COVERAGE


def _peel_once(sub: np.ndarray) -> tuple[int, int, int, int]:
    """Bar depths ``(top, bottom, left, right)`` on the outermost layer of ``sub``."""
    h, w, _ = sub.shape
    min_h = max(_MIN_BORDER_PX, math.ceil(h * _MIN_BORDER_FRAC))
    min_w = max(_MIN_BORDER_PX, math.ceil(w * _MIN_BORDER_FRAC))
    chrome_h = max(1, int(h * _MAX_CHROME_FRAC))
    chrome_w = max(1, int(w * _MAX_CHROME_FRAC))

    rows, row_colour = _bar_lines(sub)
    top = _bar_depth(rows, row_colour, h // 2, min_h, chrome_h)
    bottom = _bar_depth(rows[::-1], row_colour[::-1], h // 2, min_h, chrome_h)
    if h - top - bottom < 4:
        return 0, 0, 0, 0  # a flat image has nothing inside to frame
    # Columns are measured between the row bars, so a toolbar spanning the
    # full width does not hide the side bars beneath it.
    cols, col_colour = _bar_lines(sub[top : h - bottom].transpose(1, 0, 2))
    left = _bar_depth(cols, col_colour, w // 2, min_w, chrome_w)
    right = _bar_depth(cols[::-1], col_colour[::-1], w // 2, min_w, chrome_w)

    top = top if top >= min_h else 0
    bottom = bottom if bottom >= min_h else 0
    left = left if left >= min_w else 0
    right = right if right >= min_w else 0

    # Keep a side only if its inner edge meets content along most of its
    # length; probe a pixel in, past any resampling ringing.
    x0, x1, y0, y1 = left, w - right, top, h - bottom
    if x1 - x0 < 4 or y1 - y0 < 4:
        return 0, 0, 0, 0
    if top and not _edge_is_frame(sub[top - 1, x0:x1], sub[top + 1, x0:x1]):
        top = 0
    if bottom and not _edge_is_frame(sub[h - bottom, x0:x1], sub[h - bottom - 2, x0:x1]):
        bottom = 0
    if left and not _edge_is_frame(sub[y0:y1, left - 1], sub[y0:y1, left + 1]):
        left = 0
    if right and not _edge_is_frame(sub[y0:y1, w - right], sub[y0:y1, w - right - 2]):
        right = 0
    return top, bottom, left, right


def _content_box_small(arr: np.ndarray) -> tuple[int, int, int, int] | None:
    h, w, _ = arr.shape
    x0, y0, x1, y1 = 0, 0, w, h
    # Viewer frames are often nested (toolbar strip above a black letterbox),
    # each a different colour: peel one layer per pass until nothing is left.
    for _ in range(3):
        top, bottom, left, right = _peel_once(arr[y0:y1, x0:x1])
        if not (top or bottom or left or right):
            break
        x0, y0, x1, y1 = x0 + left, y0 + top, x1 - right, y1 - bottom
    if (x0, y0, x1, y1) == (0, 0, w, h):
        return None
    return x0, y0, x1, y1


def find_content_box(image: Image.Image) -> tuple[int, int, int, int] | None:
    """Return ``(left, top, right, bottom)`` of framed content, or ``None`` if unframed."""
    w, h = image.size
    if w < _MIN_SIDE_PX or h < _MIN_SIDE_PX:
        return None
    scale = min(1.0, _DETECT_MAX_SIDE / max(w, h))
    small = image.convert("RGB")
    if scale < 1.0:
        small = small.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.Resampling.NEAREST)
    box = _content_box_small(np.asarray(small, dtype=np.int16))
    if box is None:
        return None

    left, top, right, bottom = box
    if scale < 1.0:
        # Round inward by a reduced pixel so no sliver of bar survives the upscale.
        sw, sh = w / small.width, h / small.height
        left = min(w, math.ceil((left + (1 if left else 0)) * sw))
        top = min(h, math.ceil((top + (1 if top else 0)) * sh))
        right = max(0, math.floor((right - (1 if right < small.width else 0)) * sw))
        bottom = max(0, math.floor((bottom - (1 if bottom < small.height else 0)) * sh))

    content_w, content_h = right - left, bottom - top
    if content_w < max(_MIN_SIDE_PX, w * _MIN_CONTENT_FRAC) or content_h < max(_MIN_SIDE_PX, h * _MIN_CONTENT_FRAC):
        return None
    return left, top, right, bottom


def crop_recapture_borders(image: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    """Crop viewer/letterbox bars from a screenshot; report what was removed.

    Returns the image to analyse and a summary for the evidence payload. An
    unframed image is returned unchanged. ``framed`` is deliberately stricter
    than "something was cropped": a flat strip on one edge (a blown-out sky, a
    rendered status bar) is safe to trim but is not evidence of a screenshot.
    """
    box = find_content_box(image)
    if box is None:
        return image, {"letterbox_detected": False, "framed": False, "content_box": None,
                       "framed_sides": 0, "border_area_ratio": 0.0}
    w, h = image.size
    left, top, right, bottom = box
    removed = 1.0 - ((right - left) * (bottom - top)) / float(w * h)
    sides = int(left > 0) + int(top > 0) + int(right < w) + int(bottom < h)
    return image.crop(box), {
        "letterbox_detected": True,
        "framed": sides >= 2 or removed >= 0.10,
        "content_box": [left, top, right, bottom],
        "framed_sides": sides,
        "border_area_ratio": round(removed, 4),
    }
