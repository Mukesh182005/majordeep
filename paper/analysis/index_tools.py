"""Write script-generated rows into ``paper_results/INDEX.md``.

Each experiment owns one section, delimited by HTML comments, and rewrites
only that section, so numbers in the index always come from the script that
computed them.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX = REPO_ROOT / "paper_results/INDEX.md"


def update_index_section(section: str, rows: list[tuple[str, str, str, str, str]], index: Path = INDEX) -> None:
    """Replace the rows of ``section`` (paper item, value, file, key, phase)."""
    begin, end = f"<!-- begin:{section} -->", f"<!-- end:{section} -->"
    body = "\n".join(f"| {item} | {value} | `{file}` | `{key}` | {phase} |" for item, value, file, key, phase in rows)
    block = f"{begin}\n{body}\n{end}"
    text = index.read_text(encoding="utf-8")
    if begin in text and end in text:
        head, rest = text.split(begin, 1)
        _, tail = rest.split(end, 1)
        text = head + block + tail
    else:
        text = text.rstrip("\n") + "\n" + block + "\n"
    index.write_text(text, encoding="utf-8")
