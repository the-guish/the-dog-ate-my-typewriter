#!/usr/bin/env python3
"""Count lines of code per file or per directory.

Written for comparing test suites across projects. Code lines are total lines
minus blank lines minus full-line comments. Docstrings are not recognised, so
they count as code. Needs only Python 3.

Usage:
  count_lines.py ROOT [--by-file] [--depth N] [--ext .py,.ts,...]
                      [--include PREFIX ...] [--exclude GLOB ...]

  ROOT        directory to scan; paths in the output are relative to it
  --by-file   one CSV row per file (default: aggregate by directory)
  --depth N   aggregate at this directory depth below ROOT (default 2)
  --ext       comma-separated extensions to count (default: common code files)
  --include   only paths starting with one of these prefixes (relative to ROOT)
  --exclude   skip paths matching any of these fnmatch globs (added to defaults)

Output is CSV on stdout: path,files,lines,blank,comment,code
"""

import argparse
import fnmatch
import os
import sys
from collections import defaultdict

DEFAULT_EXT = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue",
    ".svelte", ".rb", ".erb", ".go", ".java", ".kt", ".kts", ".scala",
    ".php", ".clj", ".cljs", ".cljc", ".ex", ".exs", ".rs", ".cs", ".swift",
    ".sql", ".sh", ".bash", ".lua", ".hs", ".feature",
}

DEFAULT_EXCLUDE = [
    "*/.git/*", ".git/*", "*/node_modules/*", "node_modules/*",
    "*/__pycache__/*", "*/.venv/*", "*/venv/*", "*/vendor/*", "vendor/*",
    "*/dist/*", "*/build/*", "*/.tox/*", "*/.mypy_cache/*",
    "*/.pytest_cache/*", "*.min.js", "*/coverage/*",
]

HASH = {".py", ".pyi", ".rb", ".erb", ".sh", ".bash", ".feature"}
SLASH = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte",
         ".go", ".java", ".kt", ".kts", ".scala", ".php", ".rs", ".cs",
         ".swift"}
SEMI = {".clj", ".cljs", ".cljc"}
DASH = {".sql", ".lua", ".hs", ".ex", ".exs"}


def count_file(path, ext):
    lines = blank = comment = 0
    in_block = False
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                lines += 1
                s = raw.strip()
                if not s:
                    blank += 1
                    continue
                if ext in SLASH:
                    if in_block:
                        comment += 1
                        if "*/" in s:
                            in_block = False
                        continue
                    if s.startswith("//"):
                        comment += 1
                        continue
                    if s.startswith("/*"):
                        comment += 1
                        if "*/" not in s[2:]:
                            in_block = True
                        continue
                    if s.startswith("<!--") and ext in (".vue", ".svelte"):
                        comment += 1
                        continue
                elif ext in HASH:
                    if s.startswith("#"):
                        comment += 1
                        continue
                elif ext in SEMI:
                    if s.startswith(";"):
                        comment += 1
                        continue
                elif ext in DASH:
                    if s.startswith("--") or (ext in (".ex", ".exs") and s.startswith("#")):
                        comment += 1
                        continue
    except OSError as exc:
        print(f"skip {path}: {exc}", file=sys.stderr)
        return None
    return lines, blank, comment, lines - blank - comment


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--by-file", action="store_true")
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--ext", default=None)
    ap.add_argument("--include", nargs="*", default=[])
    ap.add_argument("--exclude", nargs="*", default=[])
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    exts = set(e if e.startswith(".") else "." + e
               for e in args.ext.split(",")) if args.ext else DEFAULT_EXT
    excludes = DEFAULT_EXCLUDE + args.exclude
    includes = [p.strip("/") for p in args.include]

    agg = defaultdict(lambda: [0, 0, 0, 0, 0])  # files, lines, blank, comment, code
    rows = []

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        rel_dir = "" if rel_dir == "." else rel_dir
        dirnames[:] = [d for d in dirnames
                       if not any(fnmatch.fnmatch(os.path.join(rel_dir, d) + "/x", g)
                                  for g in excludes)]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext not in exts:
                continue
            rel = os.path.join(rel_dir, name) if rel_dir else name
            if any(fnmatch.fnmatch(rel, g) for g in excludes):
                continue
            if includes and not any(rel == p or rel.startswith(p + "/") for p in includes):
                continue
            counted = count_file(os.path.join(dirpath, name), ext)
            if counted is None:
                continue
            lines, blank, comment, code = counted
            if args.by_file:
                rows.append((rel, 1, lines, blank, comment, code))
            else:
                parts = rel.split(os.sep)
                key = os.sep.join(parts[:args.depth]) if len(parts) > args.depth \
                    else os.sep.join(parts[:-1]) or "."
                a = agg[key]
                a[0] += 1
                a[1] += lines
                a[2] += blank
                a[3] += comment
                a[4] += code

    print("path,files,lines,blank,comment,code")
    if args.by_file:
        for r in sorted(rows):
            print(",".join(str(x) for x in r))
    else:
        for key in sorted(agg):
            a = agg[key]
            print(f"{key},{a[0]},{a[1]},{a[2]},{a[3]},{a[4]}")


if __name__ == "__main__":
    main()
