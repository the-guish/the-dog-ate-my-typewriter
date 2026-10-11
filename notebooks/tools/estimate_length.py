#!/usr/bin/env python3
"""Estimate typewritten pages and reading time for Markdown posts.

Pages: the text is typed on US Letter in pica, double-spaced, with 1-inch
margins. Reading time: prose words at the adult silent-reading rate for
non-fiction. The README gives the sources for each number.

Usage: python3 estimate_length.py FILE [FILE ...] [--single-spaced]
"""

import argparse
import math
import re
import textwrap
from pathlib import Path

PAGE_WIDTH_IN, PAGE_HEIGHT_IN = 8.5, 11  # US Letter
MARGIN_IN = 1
CHARS_PER_INCH = 10  # pica
LINES_PER_INCH = 6
PARAGRAPH_INDENT = 5  # half an inch in pica

CHARS_PER_LINE = int((PAGE_WIDTH_IN - 2 * MARGIN_IN) * CHARS_PER_INCH)  # 65
LINES_PER_PAGE = int((PAGE_HEIGHT_IN - 2 * MARGIN_IN) * LINES_PER_INCH)  # 54

WORDS_PER_MINUTE = 238  # non-fiction mean
WORDS_PER_MINUTE_RANGE = (175, 300)  # most adults

FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
LIQUID = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)
IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
INLINE_MARKS = re.compile(r"[*_`]+")
LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+\.)\s+")


def typed_lines(markdown: str) -> tuple[list[str], list[str], int]:
    """Return the typed prose lines, the typed code lines and the image count."""
    text = FRONT_MATTER.sub("", markdown)
    images = len(IMAGE.findall(text))
    text = LIQUID.sub("", IMAGE.sub("", text))

    prose: list[str] = []
    code: list[str] = []
    paragraph: list[str] = []
    in_code = False

    def flush() -> None:
        if not paragraph:
            return
        first = paragraph[0]
        item = LIST_ITEM.match(first)
        body = " ".join(line.strip() for line in paragraph)
        body = INLINE_MARKS.sub("", LINK.sub(r"\1", body))
        if item:
            prose.extend(textwrap.wrap(body, CHARS_PER_LINE, subsequent_indent="  "))
        else:
            prose.extend(textwrap.wrap(" " * PARAGRAPH_INDENT + body, CHARS_PER_LINE))
        paragraph.clear()

    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            flush()
            in_code = not in_code
            continue
        if in_code:
            code.extend(textwrap.wrap(line, CHARS_PER_LINE) or [""])
            continue
        line = re.sub(r"^\s*>\s?", "", line)
        if not line.strip() or line.strip() == "---":
            flush()
        elif line.startswith("#"):
            flush()
            prose.append("")
            prose.extend(textwrap.wrap(line.lstrip("#").strip(), CHARS_PER_LINE))
        elif LIST_ITEM.match(line):
            flush()
            paragraph.append(line)
        else:
            paragraph.append(line)
    flush()
    return prose, code, images


def estimate(path: Path, single_spaced: bool) -> str:
    prose, code, images = typed_lines(path.read_text(encoding="utf-8"))
    lines_per_page = LINES_PER_PAGE if single_spaced else LINES_PER_PAGE // 2
    pages = (len(prose) + len(code)) / lines_per_page
    words = sum(len(line.split()) for line in prose)
    minutes = words / WORDS_PER_MINUTE
    slow, fast = (words / wpm for wpm in reversed(WORDS_PER_MINUTE_RANGE))
    spacing = "single-spaced" if single_spaced else "double-spaced"
    return "\n".join([
        f"{path}",
        f"  prose words      {words:,}",
        f"  typed lines      {len(prose):,} prose + {len(code):,} code",
        f"  pages            {pages:.1f} ({math.ceil(pages)} sheets), US Letter, pica, {spacing}",
        f"  reading time     {minutes:.0f} min at {WORDS_PER_MINUTE} wpm"
        f" ({fast:.0f} to {slow:.0f} min), code not counted",
        f"  images           {images}, not counted",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--single-spaced", action="store_true",
                        help="54 lines a page instead of the manuscript's 27")
    args = parser.parse_args()
    print("\n\n".join(estimate(path, args.single_spaced) for path in args.files))


if __name__ == "__main__":
    main()
