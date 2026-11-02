"""Draw assets/images/agent-clusters.svg with boxes sized by lines of code.

Usage: python3 -I -B agent_clusters_svg.py <out.svg>
Same layout, colours and edges as the hand-drawn version: the main line runs down the middle, the tool side
branches left from Turn control, the prompt side right. Each box is drawn at 1x to 4x area by the module's median
Python-equivalent lines of code across the ten products: 1x under 500, 2x 500 to 3k, 3x 3k to 10k, 4x 10k and over.
"""
import sys

MEDIAN = {  # median Python-equivalent lines across the ten products
    "Front end": 106360, "Built-in tools": 9522, "Gateway": 6997, "Configuration and trust": 6772,
    "Plugins, skills and hooks": 6668, "Provider adapter": 5599, "Session store": 5576, "Session runtime": 5258,
    "Execution backend and egress": 4946, "Logging and audit": 4604, "Approval policy": 4208, "Turn control": 4109,
    "Tool dispatch": 4102, "MCP client": 3642, "Model transport": 3600, "Process executor": 3470,
    "Sub-agents": 2446, "Agent definitions": 2324, "Long-term memory": 1893, "Prompt assembly": 1540,
    "Model choice": 1484, "Context size management": 1240, "Access control": 1231, "Files and attachments": 1040,
    "Usage and cost": 810, "Attachments into model input": 578, "Skills index": 259,
    "Oversized tool results": 168, "Modes": 88,
}
def tier(name):
    n = MEDIAN[name]
    return 4 if n >= 10000 else 3 if n >= 3000 else 2 if n >= 500 else 1

# key: (label lines, column, row, style)
N = {
    "U": (["User"], 2, 0, "end"), "FE": (["Front end"], 2, 1, "mid"), "GW": (["Gateway"], 2, 2, "mid"),
    "AC": (["Access control"], 2, 3, "mid"), "SS": (["Session store"], 2, 4, "mid"),
    "SR": (["Session runtime"], 2, 5, "mid"), "TC": (["Turn control"], 2, 6, "main"),
    "MS": (["Model choice"], 2, 7, "mid"), "UC": (["Usage and cost"], 2, 8, "mid"),
    "MT": (["Model transport"], 2, 9, "mid"), "PV": (["Provider adapter"], 2, 10, "mid"), "L": (["LLM"], 2, 11, "end"),
    "FI": (["Files and", "attachments"], 1, 2, "light"), "CF": (["Configuration", "and trust"], 1, 4, "light"),
    "LG": (["Logging and audit"], 1, 5, "light"), "TD": (["Tool dispatch"], 1, 6, "light"),
    "OR": (["Oversized tool", "results"], 0, 6, "light"), "AP": (["Approval policy"], 1, 7, "light"),
    "SA": (["Sub-agents"], 0, 7, "light"), "BT": (["Built-in tools"], 0, 8, "light"),
    "MC": (["MCP client"], 1, 8, "light"), "PE": (["Process executor"], 0, 9, "light"),
    "EB": (["Execution backend", "and egress"], 0, 10, "light"),
    "AD": (["Agent definitions"], 3, 4, "light"), "MO": (["Modes"], 3, 5, "light"),
    "PA": (["Prompt assembly"], 3, 6, "light"), "CM": (["Context size", "management"], 3, 7, "light"),
    "PL": (["Plugins, skills", "and hooks"], 3, 8, "light"), "ME": (["Long-term memory"], 4, 5, "light"),
    "SK": (["Skills index"], 4, 6, "light"), "AT": (["Attachments into", "model input"], 4, 7, "light"),
}
NAME = {"FI": "Files and attachments", "CF": "Configuration and trust", "OR": "Oversized tool results",
        "EB": "Execution backend and egress", "CM": "Context size management", "PL": "Plugins, skills and hooks",
        "AT": "Attachments into model input"}

W1, H1 = 96, 28          # a 1x box; an nx box has n times its area (2x is the old 136 x 40 box)
COLS = [96, 306, 516, 726, 936]
ROW0, ROWP = 34, 70
def center(k): _, c, r, _ = N[k]; return COLS[c], ROW0 + r * ROWP
def size(k):
    if N[k][3] == "end": return 136, 40
    f = tier(NAME.get(k, " ".join(N[k][0]))) ** 0.5
    return round(W1 * f), round(H1 * f)
def top(k): x, y = center(k); return x, y - size(k)[1] / 2
def bottom(k): x, y = center(k); return x, y + size(k)[1] / 2
def left(k): x, y = center(k); return x - size(k)[0] / 2, y
def right(k): x, y = center(k); return x + size(k)[0] / 2, y

out = []
def line(x1, y1, x2, y2, arrow=True):
    out.append(f'  <line class="edge" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"'
               + (' marker-end="url(#arrow)"/>' if arrow else '/>'))
def poly(pts):
    out.append('  <polyline class="edge" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
               + '" marker-end="url(#arrow)"/>')
def down(a, b): (x1, y1), (_, y2) = bottom(a), top(b); line(x1, y1, x1, y2 - 2)
def leftward(a, b): (x1, y1), (x2, _) = left(a), right(b); line(x1, y1, x2 + 2, y1)

main = ["U", "FE", "GW", "AC", "SS", "SR", "TC", "MS", "UC", "MT", "PV", "L"]
for a, b in zip(main, main[1:]): down(a, b)
for a, b in [("GW", "FI"), ("SR", "LG"), ("TC", "TD"), ("TD", "OR"), ("AP", "SA")]: leftward(a, b)
for a, b in [("TD", "AP"), ("AP", "MC"), ("BT", "PE"), ("PE", "EB")]: down(a, b)
# Session runtime -> Configuration and trust: branches off the line to Logging and audit
jx = (left("SR")[0] + right("LG")[0]) / 2
poly([(jx, center("SR")[1]), (jx, center("CF")[1]), (right("CF")[0] + 2, center("CF")[1])])
# Approval policy -> Built-in tools
ax, ay = center("AP")[0] - 44, bottom("AP")[1]
my = (bottom("AP")[1] + top("MC")[1]) / 2
poly([(ax, ay), (ax, my), (center("BT")[0], my), (center("BT")[0], top("BT")[1] - 2)])
# Turn control -> the prompt side, Prompt assembly -> its sources: a bus line each
def bus(src, dsts):
    bx = (right(src)[0] + min(left(d)[0] for d in dsts)) / 2
    line(right(src)[0], center(src)[1], bx, center(src)[1], False)
    ys = [center(d)[1] for d in dsts]
    line(bx, min(ys), bx, max(ys), False)
    for d in dsts: line(bx, center(d)[1], left(d)[0] - 2, center(d)[1])
bus("TC", ["AD", "MO", "PA", "CM", "PL"])
bus("PA", ["ME", "SK", "AT"])

for k, (lines, c, r, style) in N.items():
    x, y = center(k); w, h = size(k)
    cls = {"end": "light", "mid": "mid", "main": "main", "light": "light"}[style]
    rx = h / 2 if style == "end" else 4
    out.append(f'  <rect class="shape {cls}" x="{x - w/2:.1f}" y="{y - h/2:.1f}" width="{w}" height="{h}" rx="{rx}"/>')
    fs = ' style="font-size:10px"' if w < 100 else ""
    step = 11 if w < 100 else 14
    for i, t in enumerate(lines):
        ty = y + (i - (len(lines) - 1) / 2) * step + 1
        tc = ' class="on-main"' if style == "main" else ""
        out.append(f'  <text x="{x}" y="{ty:.1f}"{tc}{fs}>{t}</text>')

# legend
ly = ROW0 + 12 * ROWP + 8
out.append(f'  <text class="note" x="516" y="{ly:.1f}">Box area by median lines of code across the ten products, in Python-equivalent lines:</text>')
lx = 150
for t, label in [(1, "under 500"), (2, "500 to 3k"), (3, "3k to 10k"), (4, "10k and over")]:
    w, h = round(W1 * t ** 0.5 * 0.5), round(H1 * t ** 0.5 * 0.5)
    yy = ly + 34
    out.append(f'  <rect class="shape light" x="{lx:.1f}" y="{yy - h/2:.1f}" width="{w}" height="{h}" rx="3"/>')
    out.append(f'  <text class="note" x="{lx + w + 8:.1f}" y="{yy:.1f}" style="text-anchor:start">{t}x {label}</text>')
    lx += w + 130
out.append(f'  <text class="note" x="516" y="{ly + 68:.1f}">Arrows mean “calls” or “uses”. Results and events travel back the same way.</text>')

W, H = COLS[-1] + 96, ly + 86
title = ("The twenty-nine clusters of responsibilities, sized by lines of code: the main line from the user to the "
         "model runs down the middle, the tool side branches left from Turn control, the prompt side right")
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H:.0f}" width="{W}" height="{H:.0f}" '
       "font-family=\"ui-monospace, Menlo, Consolas, 'Liberation Mono', monospace\" role=\"img\" aria-labelledby=\"t\">",
       f'  <title id="t">{title}</title>',
       '''  <style>
    .shape { stroke: #222; stroke-width: 1.5; stroke-linejoin: round; }
    .light { fill: #eeeeea; } .mid { fill: #c8c8c4; } .main { fill: #555; }
    .edge { stroke: #222; stroke-width: 1.2; fill: none; }
    text { fill: #222; text-anchor: middle; dominant-baseline: middle; font-size: 12px; }
    text.on-main { fill: #fff; font-weight: bold; }
    text.note { font-size: 12px; fill: #666; }
  </style>''',
       '  <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#222"/></marker></defs>']
open(sys.argv[1], "w").write("\n".join(svg + out + ["</svg>"]) + "\n")
