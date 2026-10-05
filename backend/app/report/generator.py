"""Forensic PDF report generation (ReportLab).

The report follows the seven sections the project guide specifies for an
evidentiary document:

  1. Header — title, case/report reference, generation timestamp, platform name
  2. Submitted file details — filename, type, size, SHA-256, upload timestamp
  3. Analysis summary — media type, models + versions, verdict, confidence
  4. Detailed findings — heatmap / spectrogram, per-frame or per-segment chart
  5. Methodology note — plain language, written for a non-technical reader
  6. Limitations disclaimer
  7. Report integrity hash — the SHA-256 of the finished PDF

A document cannot contain its own hash, so section 7 does not try to print one.
The PDF is rendered once and then hashed; that hash is stored in the platform's
report register (the ``reports`` table) and served by the verification endpoint.
Anyone holding the PDF can therefore run ``shasum -a 256`` on it and compare the
result against the registered value — a check that actually reproduces, which a
self-referential hash printed inside the file never could.
"""

from __future__ import annotations

import contextlib
import hashlib
import platform
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app import __version__ as app_version
from app.config import settings
from app.models import Job, Verdict
from app.report.charts import confidence_gauge, confidence_timeline

PAGE_WIDTH, PAGE_HEIGHT = A4
CONTENT_WIDTH = PAGE_WIDTH - 40 * mm

ACCENT = colors.HexColor("#1f4e79")
MUTED = colors.HexColor("#5b6670")
LIGHT = colors.HexColor("#eef2f6")

VERDICT_STYLING: dict[Verdict, tuple[str, colors.Color]] = {
    Verdict.AUTHENTIC: ("LIKELY AUTHENTIC", colors.HexColor("#2e7d32")),
    Verdict.MANIPULATED: ("LIKELY MANIPULATED", colors.HexColor("#c62828")),
    Verdict.INCONCLUSIVE: ("INCONCLUSIVE", colors.HexColor("#f9a825")),
}

DISCLAIMER = (
    "This report is an automated technical assessment produced by a machine-learning "
    "system. It is <b>not</b> a certified forensic or legal determination, and it has not "
    "been reviewed by a qualified forensic examiner. Automated deepfake detectors produce "
    "both false positives (authentic media flagged as manipulated) and false negatives "
    "(manipulated media reported as authentic), and their accuracy degrades on "
    "compression, low resolution, and manipulation techniques not represented in their "
    "training data. For legal proceedings, verification by a certified forensic expert or "
    "an accredited government forensic laboratory is recommended. The findings here "
    "should be treated as an investigative lead, not as conclusive proof."
)

METHODOLOGY: dict[str, str] = {
    "image": (
        "The submitted image was scanned for human faces. Each detected face was cropped, "
        "resized, and passed through a convolutional neural network trained to tell apart "
        "authentic photographs from images produced or altered by face-swap, GAN, and "
        "diffusion-based generators. The network outputs a probability between 0 and 1 that "
        "the region is manipulated. The accompanying heatmap highlights, in warmer colours, "
        "the areas of the image that most influenced that decision — commonly the blending "
        "boundary of a swapped face, or inconsistent skin and eye texture."
    ),
    "video": (
        "Frames were sampled from the submitted video at regular intervals rather than "
        "analysing every frame, which keeps processing time practical. In each sampled "
        "frame the largest face was located and cropped, then scored by the same neural "
        "network used for still images. The per-frame scores are plotted over time, so a "
        "manipulation affecting only part of the clip remains visible instead of being "
        "averaged away. The overall video score is the mean of the highest-scoring quarter "
        "of frames."
    ),
    "audio": (
        "The submitted audio was converted to a standard 16 kHz mono signal, silence was "
        "trimmed, and the clip was divided into short consecutive windows. Each window was "
        "transformed into a log-Mel spectrogram — a visual representation of how the sound's "
        "frequency content changes over time — and scored by a neural network trained on "
        "the ASVspoof anti-spoofing benchmark to distinguish genuine human speech from "
        "text-to-speech and voice-cloned speech. Synthetic speech typically leaves "
        "artefacts in the higher frequency bands that are hard to hear but measurable. "
        "The spectrogram in this report marks the flagged windows in red."
    ),
}


@dataclass
class ReportArtifacts:
    path: Path
    sha256: str
    report_reference: str
    generated_at: datetime


def generate_report(
    job: Job,
    output_dir: str | Path | None = None,
    *,
    evidence_dir: str | Path | None = None,
    requester: str | None = None,
) -> ReportArtifacts:
    """Render the forensic PDF for a completed job.

    Returns the file path, the SHA-256 printed inside the document, and the
    unique report reference.
    """
    output_dir = Path(output_dir or settings.report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = Path(evidence_dir or settings.evidence_dir)

    generated_at = datetime.now(UTC)
    report_reference = _build_report_reference(job)
    output_path = output_dir / f"{report_reference}.pdf"

    charts = _render_charts(job, evidence_dir, report_reference)

    _build_pdf(job, output_path, report_reference, generated_at, charts, requester)
    document_hash = _sha256_file(output_path)

    return ReportArtifacts(
        path=output_path,
        sha256=document_hash,
        report_reference=report_reference,
        generated_at=generated_at,
    )


def verify_report_hash(pdf_path: str | Path, expected_hash: str) -> bool:
    """True when the PDF on disk still hashes to the registered value.

    This is the same comparison a recipient performs by hand with
    ``shasum -a 256``, so a report that verifies here verifies for them too.
    """
    try:
        return _sha256_file(pdf_path) == expected_hash
    except OSError:
        return False


# --------------------------------------------------------------------------- internals
def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_report_reference(job: Job) -> str:
    """One canonical report reference per case, e.g. ``DFR-DF-20260831-8A3C21``.

    Regenerating a report for the same case reuses this reference and replaces
    the stored PDF, so the register always names exactly one current document
    per case rather than accumulating near-identical references.
    """
    return f"DFR-{job.case_reference}"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontSize=19, leading=23, textColor=ACCENT, spaceAfter=2
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontSize=9.5,
            leading=13,
            textColor=MUTED,
            alignment=1,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontSize=12.5,
            leading=15,
            textColor=ACCENT,
            spaceBefore=12,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "body", parent=base["BodyText"], fontSize=9.5, leading=13.5, alignment=TA_JUSTIFY
        ),
        "small": ParagraphStyle(
            "small", parent=base["BodyText"], fontSize=8, leading=11, textColor=MUTED
        ),
        "mono": ParagraphStyle(
            "mono", parent=base["BodyText"], fontName="Courier", fontSize=8, leading=11
        ),
        "cell": ParagraphStyle("cell", parent=base["BodyText"], fontSize=8.5, leading=11),
        "cellmono": ParagraphStyle(
            "cellmono", parent=base["BodyText"], fontName="Courier", fontSize=8, leading=10.5
        ),
    }


def _build_pdf(
    job: Job,
    output_path: Path,
    report_reference: str,
    generated_at: datetime,
    charts: dict[str, Path],
    requester: str | None,
) -> None:
    styles = _styles()
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title=f"Forensic Analysis Report {report_reference}",
        author=settings.app_name,
        subject="Automated media authenticity analysis",
    )

    story: list[Any] = []
    story += _section_header(job, report_reference, generated_at, requester, styles)
    story += _section_file_details(job, styles)
    story += _section_analysis_summary(job, charts, styles)
    story += _section_findings(job, charts, styles)
    forensics_story = _section_forensics(job, charts, styles)
    story += forensics_story
    has_forensics = bool(forensics_story)
    story += _section_methodology(job, styles, has_forensics=has_forensics)
    story += _section_disclaimer(styles, has_forensics=has_forensics)
    story += _section_integrity(job, report_reference, generated_at, styles, has_forensics=has_forensics)

    document.build(
        story,
        onFirstPage=lambda canvas, doc: _draw_page_furniture(canvas, doc, report_reference),
        onLaterPages=lambda canvas, doc: _draw_page_furniture(canvas, doc, report_reference),
    )


def _draw_page_furniture(canvas, document, report_reference: str) -> None:
    """Footer with the case reference and page number on every page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 12 * mm, f"{settings.app_name} · Report {report_reference}")
    canvas.drawRightString(PAGE_WIDTH - 20 * mm, 12 * mm, f"Page {document.page}")
    canvas.setStrokeColor(colors.HexColor("#d4dae0"))
    canvas.setLineWidth(0.4)
    canvas.line(20 * mm, 15 * mm, PAGE_WIDTH - 20 * mm, 15 * mm)
    canvas.restoreState()


def _kv_table(
    rows: list[tuple[str, Any]],
    styles: dict[str, ParagraphStyle],
    mono_keys: set[str] | None = None,
) -> Table:
    mono_keys = mono_keys or set()
    data = [
        [
            Paragraph(f"<b>{label}</b>", styles["cell"]),
            Paragraph(str(value), styles["cellmono"] if label in mono_keys else styles["cell"]),
        ]
        for label, value in rows
    ]
    table = Table(data, colWidths=[52 * mm, CONTENT_WIDTH - 52 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d4dae0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


# --------------------------------------------------------------------- section 1
def _section_header(job, report_reference, generated_at, requester, styles) -> list[Any]:
    return [
        Paragraph("FORENSIC MEDIA AUTHENTICITY REPORT", styles["title"]),
        Paragraph(
            f"{settings.app_name} — automated deepfake analysis<br/>"
            f"Report reference <b>{report_reference}</b> · Case reference "
            f"<b>{job.case_reference}</b>",
            styles["subtitle"],
        ),
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=1.1, color=ACCENT, spaceAfter=8),
        _kv_table(
            [
                ("Report reference", report_reference),
                ("Case reference", job.case_reference),
                ("Generated at (UTC)", generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")),
                ("Requested by", requester or "Anonymous / guest submission"),
                ("Platform version", f"{settings.app_name} v{app_version}"),
                ("Runtime", f"Python {platform.python_version()} on {platform.system()}"),
            ],
            styles,
        ),
    ]


# --------------------------------------------------------------------- section 2
def _section_file_details(job, styles) -> list[Any]:
    uploaded = job.uploaded_at.strftime("%Y-%m-%d %H:%M:%S UTC") if job.uploaded_at else "—"
    return [
        Paragraph("1. Submitted File Details", styles["h2"]),
        Paragraph(
            "The file described below was received and stored without modification. Its "
            "SHA-256 cryptographic hash was computed at the moment of upload; recomputing "
            "that hash on the original file will yield the same value if, and only if, the "
            "file has not been altered since submission.",
            styles["body"],
        ),
        Spacer(1, 5),
        _kv_table(
            [
                ("Original filename", job.original_filename),
                ("Media type", job.media_type.value.capitalize()),
                ("Declared content type", job.content_type),
                (
                    "File size",
                    f"{job.file_size_bytes:,} bytes ({job.file_size_bytes / (1024 * 1024):.2f} MB)",
                ),
                ("SHA-256 of submitted file", job.sha256),
                ("Received at (UTC)", uploaded),
            ],
            styles,
            mono_keys={"SHA-256 of submitted file"},
        ),
    ]


# --------------------------------------------------------------------- section 3
def _section_analysis_summary(job, charts, styles) -> list[Any]:
    label, colour = VERDICT_STYLING.get(job.verdict, ("NOT ANALYSED", MUTED))
    probability = job.fake_probability if job.fake_probability is not None else 0.0
    confidence = job.confidence if job.confidence is not None else 0.0

    verdict_table = Table(
        [
            [
                Paragraph(
                    f'<font color="white"><b>{label}</b></font>',
                    ParagraphStyle(
                        "v", fontSize=13, leading=16, alignment=1, textColor=colors.white
                    ),
                ),
                Paragraph(
                    f"<b>P(manipulated) = {probability * 100:.1f}%</b><br/>"
                    f"<font size=8>Decision confidence {confidence * 100:.1f}% · "
                    f"threshold {settings.fake_threshold:.2f} "
                    f"± {settings.uncertain_band:.2f} uncertain band</font>",
                    ParagraphStyle("vd", fontSize=10, leading=13, alignment=1),
                ),
            ]
        ],
        colWidths=[CONTENT_WIDTH * 0.42, CONTENT_WIDTH * 0.58],
    )
    verdict_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colour),
                ("BACKGROUND", (1, 0), (1, 0), LIGHT),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#d4dae0")),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )

    evidence = job.evidence or {}
    rows: list[tuple[str, Any]] = [
        ("Media analysed", job.media_type.value.capitalize()),
        ("Model", job.model_name or "—"),
        ("Model version", job.model_version or "—"),
        ("Weights status", _weights_label(job.weights_status)),
        (
            "Decision threshold",
            f"{settings.fake_threshold:.2f} (± {settings.uncertain_band:.2f} inconclusive band)",
        ),
        ("Processing time", f"{job.processing_ms} ms" if job.processing_ms else "—"),
    ]
    if job.media_type.value == "video":
        rows.append(("Frames analysed", evidence.get("frames_analysed", "—")))
        rows.append(("Frames above threshold", evidence.get("flagged_frames", "—")))
    elif job.media_type.value == "audio":
        rows.append(("Duration", f"{evidence.get('duration_seconds', '—')} s"))
        rows.append(
            (
                "Windows above threshold",
                f"{evidence.get('flagged_segments', '—')} of "
                f"{evidence.get('segments_analysed', '—')}",
            )
        )
    else:
        rows.append(("Faces detected", evidence.get("faces_detected", 0)))

    story: list[Any] = [
        Paragraph("2. Analysis Summary", styles["h2"]),
        verdict_table,
        Spacer(1, 7),
    ]
    gauge = charts.get("gauge")
    if gauge and gauge.exists():
        story += [
            Image(str(gauge), width=CONTENT_WIDTH, height=CONTENT_WIDTH * 1.15 / 7.2),
            Spacer(1, 6),
        ]
    story.append(_kv_table(rows, styles))

    if job.weights_status and job.weights_status != "trained":
        story += [
            Spacer(1, 6),
            _callout(
                "MODEL NOT TRAINED — RESULT IS NOT EVIDENCE",
                "This analysis ran on a network with no trained checkpoint loaded. The score "
                "above is the output of an untrained model and carries no evidentiary value "
                "whatsoever. Do not submit this report in support of a complaint.",
                colors.HexColor("#c62828"),
                styles,
            ),
        ]
    return story


def _weights_label(status: str | None) -> str:
    if status == "trained":
        return "Trained checkpoint loaded"
    if status == "untrained-backbone":
        return "<b>UNTRAINED — demonstration only, not evidential</b>"
    return status or "—"


def _callout(title: str, body: str, colour: colors.Color, styles) -> Table:
    table = Table(
        [
            [
                Paragraph(
                    f'<font color="white"><b>{title}</b></font><br/>'
                    f'<font color="white" size=8.5>{body}</font>',
                    ParagraphStyle("callout", fontSize=9, leading=12),
                )
            ]
        ],
        colWidths=[CONTENT_WIDTH],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colour),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


# --------------------------------------------------------------------- section 4
def _section_findings(job, charts, styles) -> list[Any]:
    evidence = job.evidence or {}
    story: list[Any] = [PageBreak(), Paragraph("3. Detailed Findings", styles["h2"])]

    heatmap = charts.get("heatmap")
    if heatmap and heatmap.exists():
        story += [
            Paragraph(
                "<b>3.1 Manipulation heatmap (Grad-CAM)</b><br/>Warmer regions contributed most "
                "strongly to the model's decision. On a face-swap these commonly appear along "
                "the jawline, hairline, or the boundary where a synthetic face was blended "
                "into the original frame.",
                styles["body"],
            ),
            Spacer(1, 5),
            _fitted_image(heatmap, max_width=110 * mm, max_height=95 * mm),
            Spacer(1, 9),
        ]

    spectrogram = charts.get("spectrogram")
    if spectrogram and spectrogram.exists():
        story += [
            Paragraph(
                "<b>3.1 Spectrogram evidence</b><br/>The log-Mel spectrogram of the submitted "
                "audio. Windows the model flagged as synthetic are outlined in red.",
                styles["body"],
            ),
            Spacer(1, 5),
            _fitted_image(spectrogram, max_width=CONTENT_WIDTH, max_height=60 * mm),
            Spacer(1, 9),
        ]

    timeline = charts.get("timeline")
    if timeline and timeline.exists():
        unit = "frame" if job.media_type.value == "video" else "window"
        story += [
            Paragraph(
                f"<b>3.2 Per-{unit} confidence</b><br/>Manipulation probability for each "
                f"analysed {unit}. Points above the dashed threshold line were flagged. A "
                f"manipulation confined to part of the media shows here as a localised peak "
                f"rather than a uniformly raised curve.",
                styles["body"],
            ),
            Spacer(1, 5),
            _fitted_image(timeline, max_width=CONTENT_WIDTH, max_height=52 * mm),
            Spacer(1, 9),
        ]

    optical_flow = charts.get("optical_flow")
    if optical_flow and optical_flow.exists():
        story += [
            Paragraph(
                "<b>3.3 Optical Flow & Motion Vector Discontinuities</b><br/>Spatiotemporal velocity "
                "vector field and inter-frame flicker residual plate. Velocity divergences highlight "
                "synthetic face boundary warps and temporal motion inconsistencies.",
                styles["body"],
            ),
            Spacer(1, 5),
            _fitted_image(optical_flow, max_width=CONTENT_WIDTH, max_height=58 * mm),
            Spacer(1, 9),
        ]

    detail_table = _findings_table(job, evidence, styles)
    if detail_table is not None:
        table_idx = "3.4" if optical_flow and optical_flow.exists() else "3.3"
        story += [
            Paragraph(f"<b>{table_idx} Highest-scoring segments</b>", styles["body"]),
            Spacer(1, 4),
            detail_table,
            Spacer(1, 8),
        ]

    notes = evidence.get("notes") or []
    if notes:
        bullets = "".join(f"<br/>• {note}" for note in notes)
        notes_idx = "3.5" if optical_flow and optical_flow.exists() else "3.4"
        story.append(Paragraph(f"<b>{notes_idx} Analysis notes</b>{bullets}", styles["body"]))

    return story


def _findings_table(job, evidence: dict, styles) -> Table | None:
    """Table of the highest-scoring frames/windows/faces."""
    media = job.media_type.value
    if media == "video":
        rows = sorted(
            evidence.get("frame_scores", []),
            key=lambda item: float(item.get("fake_probability", 0.0)),
            reverse=True,
        )[:10]
        header = ["Frame", "Timestamp (s)", "Face found", "P(manipulated)"]
        body = [
            [
                str(row.get("frame_index", row.get("index", idx))),
                f"{float(row.get('timestamp_s', row.get('timestamp', 0.0))):.2f}",
                "yes" if row.get("face_detected") else "no",
                f"{float(row.get('fake_probability', 0.0)) * 100:.1f}%",
            ]
            for idx, row in enumerate(rows)
        ]
    elif media == "audio":
        rows = sorted(
            evidence.get("segment_scores", []),
            key=lambda item: float(item.get("fake_probability", 0.0)),
            reverse=True,
        )[:10]
        header = ["Window", "Start (s)", "End (s)", "P(manipulated)"]
        body = [
            [
                str(row.get("segment_index", row.get("index", idx))),
                f"{float(row.get('start_s', row.get('start', 0.0))):.2f}",
                f"{float(row.get('end_s', row.get('end', 0.0))):.2f}",
                f"{float(row.get('fake_probability', 0.0)) * 100:.1f}%",
            ]
            for idx, row in enumerate(rows)
        ]
    else:
        rows = sorted(
            evidence.get("face_scores", []), key=lambda item: float(item.get("fake_probability", 0.0)), reverse=True
        )[:10]
        if not rows:
            return None
        header = ["Region", "Bounding box (x1,y1,x2,y2)", "Detection conf.", "P(manipulated)"]
        body = [
            [
                f"Face {row.get('index', idx) + 1}",
                ",".join(str(v) for v in row["box"]) if row.get("box") else "whole image",
                f"{float(row['detection_confidence']) * 100:.1f}%"
                if row.get("detection_confidence")
                else "—",
                f"{float(row.get('fake_probability', 0.0)) * 100:.1f}%",
            ]
            for idx, row in enumerate(rows)
        ]

    if not body:
        return None

    data = [[Paragraph(f"<b>{cell}</b>", styles["cell"]) for cell in header]]
    data += [[Paragraph(cell, styles["cell"]) for cell in row] for row in body]
    table = Table(
        data, colWidths=[CONTENT_WIDTH * w for w in (0.18, 0.34, 0.24, 0.24)], repeatRows=1
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d4dae0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ]
        )
    )
    return table


def _fitted_image(path: Path, max_width: float, max_height: float) -> Image:
    """Scale an image to fit a box while preserving its aspect ratio."""
    from PIL import Image as PILImage

    with PILImage.open(path) as opened:
        width, height = opened.size
    scale = min(max_width / width, max_height / height)
    return Image(str(path), width=width * scale, height=height * scale)


# --------------------------------------------------------------------- section 5 (or 4)
def _section_methodology(job, styles, has_forensics: bool = True) -> list[Any]:
    num = 5 if has_forensics else 4
    return [
        Paragraph(f"{num}. Methodology", styles["h2"]),
        Paragraph(METHODOLOGY.get(job.media_type.value, ""), styles["body"]),
        Spacer(1, 5),
        Paragraph(
            "The probability reported in section 2 is the model's own confidence, not a "
            "measured error rate. It should be read together with the detection accuracy "
            "figures published for the model version named above.",
            styles["small"],
        ),
    ]


# --------------------------------------------------------------------- section 6 (or 5)
def _section_disclaimer(styles, has_forensics: bool = True) -> list[Any]:
    num = 6 if has_forensics else 5
    return [
        Paragraph(f"{num}. Limitations and Disclaimer", styles["h2"]),
        _callout(
            "AUTOMATED ASSESSMENT — NOT A CERTIFIED FORENSIC OPINION",
            DISCLAIMER,
            colors.HexColor("#455a64"),
            styles,
        ),
        Spacer(1, 6),
        Paragraph(
            "This platform produces a technical evidence report only. It does not file, "
            "register, or transmit any complaint to a police service or cybercrime authority, "
            "and it holds no investigative or legal authority. Complaint procedures differ by "
            "jurisdiction; the recipient should confirm the current process with their local "
            "cybercrime unit or national reporting portal before submission.",
            styles["body"],
        ),
    ]


# --------------------------------------------------------------------- section 7 (or 6)
def _section_integrity(job, report_reference, generated_at, styles, has_forensics: bool = True) -> list[Any]:
    num = 7 if has_forensics else 6
    return [
        Paragraph(f"{num}. Report Integrity and Chain of Custody", styles["h2"]),
        Paragraph(
            "Two hashes secure this report. The first covers the media that was analysed and "
            "is printed below. The second covers this PDF itself: a document cannot contain "
            "its own hash, so that value is held in the platform's report register against "
            "the reference below and is published by the verification endpoint. Either hash "
            "changes completely if a single byte of the corresponding file is altered.",
            styles["body"],
        ),
        Spacer(1, 5),
        KeepTogether(
            _kv_table(
                [
                    ("SHA-256 of analysed file", job.sha256),
                    ("Report reference", report_reference),
                    ("Generated at (UTC)", generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")),
                    ("Report hash register", f"GET /api/reports/{report_reference}/verify"),
                ],
                styles,
                mono_keys={"SHA-256 of analysed file", "Report hash register"},
            )
        ),
        Spacer(1, 6),
        Paragraph(
            "<b>How to verify.</b> Compute the SHA-256 of a file with "
            "<font face='Courier'>shasum -a 256 &lt;file&gt;</font> on Linux or macOS, or "
            "<font face='Courier'>certutil -hashfile &lt;file&gt; SHA256</font> on Windows. "
            "Run it on the original media and confirm the result equals the value printed "
            "above. Run it on this PDF and confirm the result equals the hash the register "
            f"endpoint returns for report <b>{report_reference}</b>. Both checks must pass "
            "for the report and the media it describes to be considered unaltered.",
            styles["small"],
        ),
        Spacer(1, 4),
        Paragraph(
            "This report is not cryptographically signed. Hashes detect accidental or casual "
            "alteration; they are not a substitute for a digital signature issued by a "
            "recognised certifying authority, and the register value is only as trustworthy "
            "as the platform that publishes it.",
            styles["small"],
        ),
    ]


# --------------------------------------------------------------------- charts
def _render_charts(job: Job, evidence_dir: Path, report_reference: str) -> dict[str, Path]:
    """Render/collect every image the report embeds."""
    evidence = job.evidence or {}
    charts: dict[str, Path] = {}
    chart_dir = evidence_dir / "report_charts"

    if job.fake_probability is not None:
        # Charts are supporting evidence: a rendering failure must not block
        # the report, which still carries the score, hashes and disclaimers.
        with contextlib.suppress(Exception):
            charts["gauge"] = confidence_gauge(
                job.fake_probability, chart_dir / f"{report_reference}_gauge.png"
            )

    for key, filename in (
        ("heatmap", evidence.get("heatmap_file")),
        ("spectrogram", evidence.get("spectrogram_file")),
        ("timeline", evidence.get("timeline_file")),
        ("optical_flow", evidence.get("optical_flow_file")),
        ("ela", evidence.get("ela_file")),
        ("noise", evidence.get("noise_file")),
        ("tampering", evidence.get("tampering_file")),
        ("watermark", evidence.get("watermark_file")),
        ("combined", evidence.get("combined_file")),
        ("lfcc", evidence.get("lfcc_scalogram_file")),
        ("cqt", evidence.get("cqt_scalogram_file")),
        ("waveform", evidence.get("waveform_file")),
        ("multi", evidence.get("multi_resolution_plate_file")),
    ):
        if filename:
            candidate = evidence_dir / filename
            if candidate.exists():
                charts[key] = candidate

    if "timeline" not in charts:
        points = evidence.get("frame_scores") or evidence.get("segment_scores")
        if points and len(points) > 1:
            is_video = bool(evidence.get("frame_scores"))
            first = points[0] if isinstance(points[0], dict) else {}
            if is_video:
                x_k = "timestamp_s" if "timestamp_s" in first else "timestamp"
            else:
                x_k = "start_s" if "start_s" in first else "start"
            with contextlib.suppress(Exception):
                charts["timeline"] = confidence_timeline(
                    points,
                    chart_dir / f"{report_reference}_timeline.png",
                    x_key=x_k,
                    x_label="Time (seconds)",
                    title="Per-frame manipulation probability"
                    if is_video
                    else "Per-window synthetic-speech probability",
                )

    return charts


# --------------------------------------------------------------------- section 4 (forensics)
def _section_forensics(job, charts, styles) -> list[Any]:
    evidence = job.evidence or {}
    forensics = evidence.get("forensics") or {}

    # ------------------------------------------------ VIDEO FORENSICS REPORT SECTION
    if job.media_type.value == "video":
        container = evidence.get("container_forensics") or {}
        temporal = evidence.get("temporal_metrics") or {}
        facial = evidence.get("facial_dynamics") or {}
        lipsync = evidence.get("crossmodal_lipsync") or {}
        rppg = evidence.get("rppg_biometrics") or {}
        attribution = evidence.get("generator_attribution") or {}
        spatiotemporal = evidence.get("spatiotemporal_forensics") or {}
        scenes = evidence.get("scenes") or []

        has_video_data = any([container, temporal, facial, lipsync, rppg, attribution, spatiotemporal, scenes])
        if not has_video_data and not forensics:
            return []

        story: list[Any] = [
            PageBreak(),
            Paragraph("4. Video Spatiotemporal & Biometric Forensics Matrix", styles["h2"]),
            Paragraph(
                "Multi-dimensional spatiotemporal forensic evaluation across 8 temporal and biometric engines, "
                "incorporating video container bitstream DNA, optical flow velocity consistency, "
                "3D facial landmark dynamics, SyncNet crossmodal lip-sync, and remote photoplethysmography (rPPG).",
                styles["body"],
            ),
            Spacer(1, 6),
        ]

        # 4.1 Video Container, GOP Architecture & Cryptographic Hashes
        f_info = container.get("file_info") or {}
        s_info = container.get("stream_info") or {}
        c_audit = container.get("container_audit") or {}

        ext = str(f_info.get("extension") or "mp4").upper().lstrip(".")
        codec = str(s_info.get("video_codec") or "H.264")
        container_rows = [
            ("Video Container Format", f"{ext} / Codec: {codec}"),
            ("Resolution / Dimensions", f"{s_info.get('resolution', 'N/A')} ({s_info.get('width', 'N/A')}x{s_info.get('height', 'N/A')})"),
            ("Frame Rate / Frame Count", f"{evidence.get('source_fps', s_info.get('fps', 'N/A'))} FPS / {evidence.get('total_frames', 'N/A')} total frames ({evidence.get('sampled_frames', len(evidence.get('frame_scores', [])))} sampled)"),
            ("Duration / Bitrate", f"{float(evidence.get('duration_seconds') or 0.0):.2f}s / {s_info.get('bitrate_kbps', 'N/A')} kbps"),
            ("Moov Atom / FastStart", f"{'PRESENT (Valid Header)' if c_audit.get('moov_atom_present') else 'ANOMALY'} (FastStart: {'ENABLED' if c_audit.get('fast_start_enabled') else 'STANDARD'})"),
            ("Audio Stream Multiplexed", "YES (Audio track present)" if s_info.get("has_audio") else "NO (Mute container)"),
            ("Video SHA-256 (Primary)", str(f_info.get("sha256") or job.sha256)),
            ("Dominant Forensic Threat", f"<b>{evidence.get('dominant_threat', 'CLEAN')}</b> (Code: {evidence.get('threat_code', 'CLEAN')})"),
            ("Corroborating Signals", ", ".join(evidence.get("corroborating_signals", [])) or "None (Clean Signals)"),
        ]
        story += [
            Paragraph("<b>4.1 Video Container & Bitstream Architecture</b>", styles["body"]),
            Spacer(1, 3),
            _kv_table(container_rows, styles, mono_keys={"Video SHA-256 (Primary)"}),
            Spacer(1, 7),
        ]

        # 4.2 Spatiotemporal Motion & Optical Flow Analysis
        opt_flow = temporal.get("optical_flow") or {}
        mean_motion = float(temporal.get("motion_anomaly") or opt_flow.get("mean_motion_anomaly") or 0.0)
        max_motion = float(opt_flow.get("max_motion_anomaly") or 0.0)
        face_bg_div = float(temporal.get("face_bg_divergence") or opt_flow.get("face_background_divergence") or 0.0)
        jitter = float(temporal.get("jitter_score") or 0.0)

        motion_rows = [
            ("Optical Flow Mean Anomaly", f"{mean_motion:.4f} ({'SUSPICIOUS DISCONTINUITY' if mean_motion > 0.6 else 'NORMAL CONTINUOUS FLOW'})"),
            ("Max Velocity Discontinuity", f"{max_motion:.4f}"),
            ("Face-to-Background Divergence", f"{face_bg_div:.4f} ({'BOUNDARY WARPING DETECTED' if face_bg_div > 0.4 else 'COHERENT MOTION'})"),
            ("Temporal Jitter Residual", f"{jitter:.4f} ({'HIGH JITTER' if jitter > 0.3 else 'STABLE'})"),
            ("Scene Cuts / Transitions", f"{len(scenes)} distinct scene(s) segmented"),
            ("Spatiotemporal Artifact Score", f"{spatiotemporal.get('artifact_score', 'N/A')} ({spatiotemporal.get('status', 'ANALYZED')})"),
        ]
        story += [
            Paragraph("<b>4.2 Spatiotemporal Motion & Optical Flow Telemetry</b>", styles["body"]),
            Spacer(1, 3),
            _kv_table(motion_rows, styles),
            Spacer(1, 7),
        ]

        # 4.3 3D Facial Dynamics & SyncNet Crossmodal Lip-Sync
        blink = facial.get("blink_analysis") or {}
        blink_rate = float(blink.get("blink_rate_per_min") or 0.0)
        blink_reg = str(blink.get("blink_regularity") or "N/A")
        landmark_jitter = float(facial.get("landmark_jitter_score") or 0.0)
        corneal = float(facial.get("corneal_reflection_consistency") if facial.get("corneal_reflection_consistency") is not None else 1.0)
        mouth_stab = float(facial.get("mouth_interior_stability") if facial.get("mouth_interior_stability") is not None else 1.0)

        av_corr = float(lipsync.get("audiovisual_correlation") or 0.0)
        sync_anomaly = bool(lipsync.get("lip_sync_anomaly_detected"))

        face_rows = [
            ("Tracked Face Keyframes", f"{facial.get('faces_tracked', evidence.get('faces_detected_in_frames', 0))} face detections"),
            ("3D Landmark Trajectory Jitter", f"{landmark_jitter:.4f} ({'UNNATURAL FACIAL JITTER' if landmark_jitter > 0.25 else 'NATURAL DYNAMICS'})"),
            ("Spontaneous Blink Frequency", f"{blink_rate:.1f} blinks/min ({blink_reg})"),
            ("Corneal Specular Reflection", f"{corneal * 100:.1f}% bilateral consistency"),
            ("Mouth Cavity / Teeth Stability", f"{mouth_stab * 100:.1f}% anatomical cohesion"),
            ("SyncNet Audio-Visual Lip Sync", f"{'SYNC ANOMALY DETECTED' if sync_anomaly else 'LIP-AUDIO SYNCHRONIZED'} (Correlation: {av_corr:.3f})"),
            ("Viseme Alignment Verdict", str(lipsync.get("verdict_reason") or "Normal phonemic articulation")),
        ]
        story += [
            Paragraph("<b>4.3 3D Facial Dynamics & SyncNet Lip-Sync Correlation</b>", styles["body"]),
            Spacer(1, 3),
            _kv_table(face_rows, styles),
            Spacer(1, 7),
        ]

        # 4.4 Remote Photoplethysmography (rPPG Pulse) & Model Attribution
        pulse_detected = bool(rppg.get("biometric_pulse_detected"))
        hr_bpm = float(rppg.get("estimated_heart_rate_bpm") or 0.0)
        snr_db = float(rppg.get("cardiac_snr_db") or 0.0)
        bio_plaus = float(rppg.get("biological_plausibility_score") if rppg.get("biological_plausibility_score") is not None else 0.5)
        rppg_status = str(rppg.get("status") or "N/A")

        attrib_plat = str(attribution.get("predicted_platform") or "Unknown / Natural Source")
        attrib_conf = float(attribution.get("attribution_confidence") or 0.0)
        vit_prob = float(evidence.get("vit_genai_prob") or 0.0)
        risk_score_val = evidence.get("risk_score", int((job.fake_probability or 0.0) * 100))

        bio_rows = [
            ("Capillary Pulse (rPPG)", f"{'PHYSIOLOGICAL PULSE CONFIRMED' if pulse_detected else 'ABSENT / UNVERIFIED'} ({rppg_status})"),
            ("Estimated Cardiac Rate (HR)", f"{hr_bpm:.1f} BPM (Cardiac SNR: {snr_db:.1f} dB)"),
            ("Biological Plausibility Index", f"{bio_plaus * 100:.1f}%"),
            ("Generator Architecture Attribution", f"<b>{attrib_plat}</b> ({attrib_conf * 100:.1f}% confidence)"),
            ("ViT Generative Probe Probability", f"<b>{vit_prob * 100:.1f}%</b>"),
            ("Composite Forensic Risk Score", f"<b>{risk_score_val} / 100</b> ({evidence.get('risk_tier', 'LOW_RISK')})"),
        ]
        story += [
            Paragraph("<b>4.4 Physiological rPPG Biometrics & Generative Attribution</b>", styles["body"]),
            Spacer(1, 3),
            _kv_table(bio_rows, styles),
            Spacer(1, 7),
        ]

        # 4.5 Auxiliary Visual Evidence Plates
        optical_flow_img = charts.get("optical_flow")
        heatmap_img = charts.get("heatmap")
        if (optical_flow_img and optical_flow_img.exists()) or (heatmap_img and heatmap_img.exists()):
            story += [
                Paragraph("<b>4.5 Multi-Frame Forensic Visual Plates</b>", styles["body"]),
                Spacer(1, 3),
            ]
            if optical_flow_img and optical_flow_img.exists():
                story += [
                    Paragraph("<i>Dense Optical Flow Motion Residual Plate:</i>", styles["small"]),
                    _fitted_image(optical_flow_img, max_width=CONTENT_WIDTH, max_height=65 * mm),
                    Spacer(1, 4),
                ]
            if heatmap_img and heatmap_img.exists():
                story += [
                    Paragraph("<i>Worst-Frame Activation Heatmap (Grad-CAM):</i>", styles["small"]),
                    _fitted_image(heatmap_img, max_width=100 * mm, max_height=80 * mm),
                    Spacer(1, 4),
                ]

        # 4.6 SWGDE & ISO/IEC 27037 Chain of Custody
        custody_rows = [
            ("Evidence ID", f"EVID-{job.case_reference}"),
            ("Primary Subject Asset", job.original_filename),
            ("Cryptographic SHA-256 Digest", job.sha256),
            ("Analysis Platform Version", f"{settings.app_name} Video Forensics Suite v2.6"),
            ("Judicial Standard Compliance", "ISO/IEC 27037:2012 & SWGDE Digital Video Guidelines"),
        ]
        story += [
            Paragraph("<b>4.6 SWGDE Chain of Custody Register</b>", styles["body"]),
            Spacer(1, 3),
            _kv_table(custody_rows, styles, mono_keys={"Evidence ID", "Cryptographic SHA-256 Digest"}),
            Spacer(1, 7),
        ]
        return story

    # ------------------------------------------------ AUDIO FORENSICS REPORT SECTION
    if job.media_type.value == "audio":
        if not forensics:
            return []

        story: list[Any] = [
            PageBreak(),
            Paragraph("4. Audio Intelligence, Authenticity & Cyber Forensics Matrix", styles["h2"]),
            Paragraph(
                "Exhaustive forensic evaluation across 10 analytical engines, incorporating "
                "cryptographic chain of custody, Audio File DNA, 120+ deterministic signal descriptors, "
                "IAIF glottal flow aerodynamics, VoiceRadar physical propagation, and ENF power grid continuity.",
                styles["body"],
            ),
            Spacer(1, 6),
        ]

        fusion = forensics.get("fusion_decision") or {}
        verdict = str(fusion.get("final_verdict") or "N/A")
        r_synth = float(fusion.get("generative_ai_risk_score") or 0.0)
        r_tamper = float(fusion.get("structural_tampering_risk_score") or 0.0)
        conf_set = ", ".join(fusion.get("conformal_prediction_set") or []) or "N/A"
        lr = float(fusion.get("forensic_likelihood_ratio") if fusion.get("forensic_likelihood_ratio") is not None else 1.0)
        verbal = str(fusion.get("verbal_scale_interpretation") or "Inconclusive")

        fusion_rows = [
            ("Forensic Verdict", f"<b>{verdict}</b>"),
            ("Generative AI Risk (R_synth)", f"<b>{r_synth * 100:.1f}%</b> (TTS / Neural Vocoder / Cloning)"),
            ("Structural Tampering Risk (R_tamper)", f"<b>{r_tamper * 100:.1f}%</b> (Splicing / Container Edits)"),
            ("Conformal Prediction Set (alpha <= 0.01)", f"<b>{conf_set}</b>"),
            ("Forensic Likelihood Ratio (LR)", f"<b>{lr:,.1f}</b> ({verbal})"),
        ]
        story += [
            Paragraph("<b>4.1 Evidence Fusion & Conformal Dual-Risk Engine</b>", styles["body"]),
            Spacer(1, 3),
            _kv_table(fusion_rows, styles),
            Spacer(1, 7),
        ]

        # Audio File DNA
        dna = forensics.get("file_dna") or {}
        inferred_history = []
        for s in (dna.get("inferred_transcoding_history") or []):
            if isinstance(s, dict) and "description" in s:
                inferred_history.append(str(s["description"])[:45])
            elif isinstance(s, str):
                inferred_history.append(s[:45])
        inferred_str = " -> ".join(inferred_history) or "Direct Capture"

        dna_rows = [
            ("Container Architecture", str(dna.get("container_format") or "N/A")),
            ("Audio Codec", str(dna.get("codec") or "N/A")),
            ("Sample Rate / Channels", f"{dna.get('sample_rate_hz', 'N/A')} Hz / {dna.get('channels', 'N/A')} ch"),
            ("Bit Depth / Bitrate", f"{dna.get('bit_depth', 'N/A')}-bit / {dna.get('bitrate_kbps', 'N/A')} kbps"),
            ("Encoder Signature", str(dna.get("encoder_signature") or "N/A")),
            ("Trailing Bytes after EOF", f"{dna.get('trailing_bytes_count', 0)} bytes detected" if dna.get("trailing_data_detected") else "None (Clean Container)"),
            ("Inferred Transcoding History", inferred_str),
        ]
        story += [
            Paragraph("<b>4.2 Audio File DNA & Inferred Transcoding History</b>", styles["body"]),
            Spacer(1, 3),
            _kv_table(dna_rows, styles),
            Spacer(1, 7),
        ]

        # Signal Intelligence & Glottal Flow
        intel = forensics.get("signal_intel") or {}
        td = intel.get("time_domain") or {}
        clip = intel.get("clipping_analysis") or {}
        clip_pct = float(clip.get("clipping_percentage") or 0.0)
        dyn = intel.get("dynamics_and_loudness") or {}
        phys = forensics.get("glottal_physics") or {}
        glottal = phys.get("glottal_flow") or {}
        vr = phys.get("physical_propagation") or {}

        sig_rows = [
            ("Signal Quality Score", f"<b>{intel.get('quality_score', 85)} / 100</b>"),
            ("Estimated SNR / Noise Floor", f"{dyn.get('estimated_snr_db', 'N/A')} dB / {dyn.get('estimated_noise_floor_dbfs', 'N/A')} dBFS"),
            ("Loudness (LUFS) / Dynamic Range", f"{dyn.get('integrated_loudness_lufs', 'N/A')} LUFS / {td.get('dynamic_range_db', 'N/A')} dB"),
            ("Crest Factor / Digital Clipping", f"{td.get('crest_factor_db', 'N/A')} dB / {clip_pct:.3f}% ({clip.get('severity', 'NONE')})"),
            ("IAIF Glottal Open / Closing Quotient", f"Qo: {glottal.get('open_quotient', 'N/A')} / Qc: {glottal.get('closing_quotient', 'N/A')} (MFDR: {glottal.get('mfdr_index', 'N/A')})"),
            ("Biological Vocal Turbulence Index", str(glottal.get("biological_turbulence_index") or "N/A")),
            ("VoiceRadar Doppler Micro-Dispersion", f"{vr.get('doppler_micro_dispersion_hz', 'N/A')} Hz (Acoustic 3D Adherence: {vr.get('acoustic_propagation_adherence', 'N/A')})"),
        ]
        story += [
            Paragraph("<b>4.3 Deterministic Signal Intelligence & Physiological Physics</b>", styles["body"]),
            Spacer(1, 3),
            _kv_table(sig_rows, styles),
            Spacer(1, 7),
        ]

        # Environmental ENF & Cybersecurity
        enf = forensics.get("enf_environment") or {}
        enf_data = enf.get("enf_forensics") or {}
        room = enf.get("room_acoustics") or {}
        sec = forensics.get("security_provenance") or {}
        wm = sec.get("watermark_analysis") or {}
        stego = sec.get("steganography_forensics") or {}
        c2pa = sec.get("provenance_c2pa") or {}

        env_rows = [
            ("ENF Power Grid Carrier", f"{enf_data.get('nominal_grid_frequency_hz', 'N/A')} Hz (Mean: {enf_data.get('estimated_mean_frequency_hz', 'N/A')} Hz)"),
            ("ENF Phase Continuity Splicing Check", f"Max Phase Slip: {enf_data.get('max_phase_slip_degrees', 0.0)}° — {'SPLICING CONFIRMED' if enf.get('environmental_splicing_confirmed') else 'CONTINUOUS COHERENT PHASE'}"),
            ("Room Acoustic Reverb (RT60)", f"{room.get('mean_reverberation_time_rt60_s', 'N/A')}s ({room.get('acoustic_space_type', 'N/A')})"),
            ("C2PA Cryptographic Provenance", f"{c2pa.get('cryptographic_signature_status', 'NOT_PRESENT')} (AI Disclosed: {'YES' if c2pa.get('ai_generation_disclosed') else 'NO'})"),
            ("Imperceptible Latent Watermark", f"{wm.get('watermark_scheme', 'NONE')} (Overwriting Attack: {'SUSPECTED' if wm.get('overwriting_attack_suspected') else 'NO'})"),
            ("Steganography / Covert Channel", f"{stego.get('covert_channel_status', 'CLEAN')} (LSB Entropy: {stego.get('lsb_bitplane_entropy', 'N/A')})"),
        ]
        story += [
            Paragraph("<b>4.4 Environmental ENF, Provenance & Cybersecurity</b>", styles["body"]),
            Spacer(1, 3),
            _kv_table(env_rows, styles),
            Spacer(1, 7),
        ]

        # Visual Evidence for Audio
        lfcc_img = charts.get("lfcc")
        multi_img = charts.get("multi")
        if (lfcc_img and lfcc_img.exists()) or (multi_img and multi_img.exists()):
            story += [
                Paragraph("<b>4.5 Multi-Resolution Diagnostic Scalograms</b>", styles["body"]),
                Spacer(1, 3),
            ]
            if lfcc_img and lfcc_img.exists():
                story += [
                    Paragraph("<i>Linear Frequency Cepstral Coefficients (LFCC) Scalogram:</i>", styles["small"]),
                    _fitted_image(lfcc_img, max_width=CONTENT_WIDTH, max_height=60 * mm),
                    Spacer(1, 4),
                ]
            if multi_img and multi_img.exists():
                story += [
                    Paragraph("<i>Multi-Panel Forensic Diagnostic Dossier Plate:</i>", styles["small"]),
                    _fitted_image(multi_img, max_width=CONTENT_WIDTH, max_height=85 * mm),
                    Spacer(1, 4),
                ]

        # Chain of custody
        vault = forensics.get("vault_record") or {}
        vault_hashes = vault.get("hashes") or {}
        custody_rows = [
            ("Evidence ID", str(vault.get("evidence_id") or "N/A")),
            ("Acquisition Timestamp", str(vault.get("acquisition_timestamp") or "N/A")),
            ("SHA-256 Digest", str(vault_hashes.get("sha256") or job.sha256)),
            ("SHA-512 Digest", str(vault_hashes.get("sha512") or "N/A")[:32] + "..."),
            ("Legal Compliance Standards", ", ".join(vault.get("compliance", ["SWGDE 08-A-001", "ISO/IEC 27042"]))),
        ]
        story += [
            Paragraph("<b>4.6 SWGDE Chain of Custody Register</b>", styles["body"]),
            Spacer(1, 3),
            _kv_table(custody_rows, styles, mono_keys={"Evidence ID", "SHA-256 Digest", "SHA-512 Digest"}),
            Spacer(1, 7),
        ]

        return story

    # ------------------------------------------------ IMAGE FORENSICS REPORT SECTION
    if not forensics:
        return []

    story: list[Any] = [
        PageBreak(),
        Paragraph("4. Cybersecurity & Digital Image Forensics Matrix", styles["h2"]),
        Paragraph(
            "Multi-dimensional forensic evaluation across 28 analytical axes, incorporating file "
            "container validation, perceptual hashing, signal residuals, and evidence fusion.",
            styles["body"],
        ),
        Spacer(1, 6),
    ]

    # Risk Engine & Fusion
    risk = forensics.get("risk_engine") or {}
    fusion = risk.get("evidence_fusion") or {}
    risk_score = risk.get("overall_risk_score", "N/A")
    risk_tier = risk.get("risk_tier", "N/A")
    corroborating = ", ".join(fusion.get("corroborating_signals", [])) or "None (Clean Signals)"

    risk_rows = [
        ("Image Security Risk Score", f"<b>{risk_score} / 100</b> ({risk_tier})"),
        ("Evidence Fusion Consensus", fusion.get("fusion_verdict", "N/A")),
        ("Fusion Confidence", fusion.get("fusion_confidence", "N/A")),
        ("Corroborating Signals", corroborating),
    ]
    story += [
        Paragraph("<b>4.1 Evidence Fusion & Risk Scoring Engine</b>", styles["body"]),
        Spacer(1, 3),
        _kv_table(risk_rows, styles),
        Spacer(1, 7),
    ]

    # File Security & Hashes
    fsec = forensics.get("file_security") or {}
    hashes = forensics.get("hashes") or {}
    sec_rows = [
        ("File Structure", fsec.get("file_status", "VALID")),
        ("Detected Magic Bytes", fsec.get("format", "N/A")),
        ("MIME Type", fsec.get("mime_type", "N/A")),
        ("Extension Mismatch", "DETECTED (Warning)" if fsec.get("extension_mismatch") else "None (Matches Signature)"),
        ("Trailing Data after EOF", f"{fsec.get('trailing_bytes_count', 0)} bytes detected" if fsec.get("trailing_data_detected") else "None"),
        ("SHA-256 (Primary Evidence)", hashes.get("sha256", job.sha256)),
        ("MD5 Hash", hashes.get("md5", "N/A")),
        ("Perceptual Hash (pHash)", hashes.get("phash", "N/A")),
        ("Difference Hash (dHash)", hashes.get("dhash", "N/A")),
    ]
    story += [
        Paragraph("<b>4.2 File Container Security & Cryptographic Hashing</b>", styles["body"]),
        Spacer(1, 3),
        _kv_table(sec_rows, styles, mono_keys={"SHA-256 (Primary Evidence)", "MD5 Hash", "Perceptual Hash (pHash)", "Difference Hash (dHash)"}),
        Spacer(1, 7),
    ]

    # Image Signal Forensics
    tamp = forensics.get("tampering") or {}
    ela = forensics.get("ela") or {}
    cam = forensics.get("camera_stats") or {}
    stego = forensics.get("steganography") or {}
    meta = forensics.get("metadata_forensics") or {}

    watermark = forensics.get("watermark") or {}
    wm_label = f"DETECTED: {watermark.get('subtype', 'Watermark')} ({watermark.get('location', 'image')})" if watermark.get("watermark_detected") else "None detected"
    sig_rows = [
        ("Watermark Detection", wm_label),
        ("Copy-Move Tampering", "DETECTED" if tamp.get("copy_move_detected") else "Not detected"),
        ("Splicing Discontinuity", "DETECTED" if tamp.get("splicing_detected") else "Not detected"),
        ("Error Level Analysis (ELA)", f"Score: {ela.get('ela_score', 'N/A')} (Anomaly: {ela.get('compression_anomaly_detected', False)})"),
        ("Sensor Noise Pattern (PRNU)", cam.get("estimated_camera_family", "N/A")),
        ("CFA / Demosaicing", "Periodic Bayer Pattern Detected" if cam.get("cfa_artifacts_detected") else "Missing Periodic Demosaicing (Synthetic Footprint)"),
        ("Steganography Suspicion", f"{stego.get('payload_likelihood', 'LOW')} ({stego.get('suspicion_percentage', 0)}%)"),
        ("Camera Hardware Tag", f"{meta.get('camera_make', 'Unknown')} {meta.get('camera_model', '')}"),
        ("Lens Specification", f"{meta.get('lens_make', '')} {meta.get('lens_model', 'Not specified')}"),
        ("Capture Shutter / Aperture / ISO", f"{meta.get('exposure_time', 'N/A')} | {meta.get('f_number', 'N/A')} | {meta.get('iso', 'N/A')}"),
        ("Dimensions & Megapixels", f"{meta.get('dimensions', 'N/A')} ({meta.get('megapixels', 'N/A')})"),
        ("Color Space & Profile", f"{meta.get('color_space', 'sRGB')} | {meta.get('icc_profile_name', 'None')}"),
        ("Software Footprint", meta.get("software", "None recorded")),
        ("Timeline Consistency", meta.get("timeline_consistency", "CONSISTENT")),
        ("Metadata Integrity Audit", meta.get("metadata_status", "N/A")),
    ]
    story += [
        Paragraph("<b>4.3 Signal Forensics & Steganography</b>", styles["body"]),
        Spacer(1, 3),
        _kv_table(sig_rows, styles),
        Spacer(1, 7),
    ]

    # Visual Evidence: ELA and Combined Heatmaps if present
    ela_img = charts.get("ela")
    combined_img = charts.get("combined")
    if ela_img or combined_img:
        story += [
            Paragraph("<b>4.4 Auxiliary Forensic Visualizations</b>", styles["body"]),
            Spacer(1, 3),
        ]
        if ela_img and ela_img.exists():
            story += [
                Paragraph("<i>Calibrated Error Level Analysis (ELA) Map:</i>", styles["small"]),
                _fitted_image(ela_img, max_width=85 * mm, max_height=70 * mm),
                Spacer(1, 4),
            ]
        if combined_img and combined_img.exists():
            story += [
                Paragraph("<i>Multi-Layer Combined Forensic Heatmap:</i>", styles["small"]),
                _fitted_image(combined_img, max_width=85 * mm, max_height=70 * mm),
                Spacer(1, 4),
            ]
        watermark_img = charts.get("watermark")
        if watermark_img and watermark_img.exists():
            story += [
                Paragraph("<i>Watermark Localization Overlay:</i>", styles["small"]),
                _fitted_image(watermark_img, max_width=85 * mm, max_height=70 * mm),
                Spacer(1, 4),
            ]

    # Chain of Custody & Audit
    custody = forensics.get("chain_of_custody") or {}
    custody_rows = [
        ("Evidence ID", str(custody.get("evidence_id") or "N/A")),
        ("Custody Seal", str(custody.get("custody_verification_seal") or "N/A")[:32] + "..."),
        ("Acquired At", str(custody.get("acquired_at") or "N/A")),
        ("Forensic Suite Version", str(custody.get("analyzer_platform") or "N/A")),
    ]
    story += [
        Paragraph("<b>4.5 Chain of Custody Register</b>", styles["body"]),
        Spacer(1, 3),
        _kv_table(custody_rows, styles, mono_keys={"Evidence ID", "Custody Seal"}),
        Spacer(1, 7),
    ]

    return story
