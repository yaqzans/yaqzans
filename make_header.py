"""Draw the profile header: my public repos as a graph, edges = what they share.

GitHub shows SVGs as plain images, so links inside them do nothing. To make
every node clickable, the drawing is cut into vertical strips, one per node,
and each strip is wrapped in a link to that repo. Strips sit flush, so it
still reads as one picture. The script writes the strips to header/ and the
HTML for them into README.md between the GRAPH markers.

The colouring is computed and chi(G) is checked by brute force.
"""
import os
import re
from itertools import product

W, H = 920, 350
NAME = "shamvi md abdullah"
GH = "https://github.com/yaqzans/"

# id: (label, x, y). x must be strictly increasing; each node gets its own strip.
NODES = {
    "WT_Fall-25-26_Project":              ("WT project",            55, 105),
    "WT_Fall-25-26":                      ("WT fall 25",           140, 225),
    "HTML-CSS-JS-Practise":               ("html/css/js",          225, 95),
    "TicTacToeInfinity":                  ("tictactoe ∞",          320, 215),
    "2D-Parking-Game":                    ("2D parking",           410, 90),
    "who-should-count-more":              ("who should count more", 485, 265),
    "cvpr-two-stage-vehicle-recognition": ("vehicle recognition",  590, 120),
    "ids-sarcasm-detection":              ("sarcasm detection",    675, 250),
    "oshudbot":                           ("oshudbot",             765, 100),
    "markdown-converter-app":             ("markdown converter",   845, 215),
}

# (a, b, what they actually share)
EDGES = [
    ("WT_Fall-25-26_Project", "WT_Fall-25-26", "same course"),
    ("WT_Fall-25-26", "HTML-CSS-JS-Practise", "web basics"),
    ("HTML-CSS-JS-Practise", "TicTacToeInfinity", "vanilla JS"),
    ("TicTacToeInfinity", "who-should-count-more", "runs in browser"),
    ("TicTacToeInfinity", "2D-Parking-Game", "games"),
    ("2D-Parking-Game", "cvpr-two-stage-vehicle-recognition", "cars"),
    ("cvpr-two-stage-vehicle-recognition", "ids-sarcasm-detection", "classifiers"),
    ("cvpr-two-stage-vehicle-recognition", "oshudbot", "for Bangladesh"),
    ("oshudbot", "ids-sarcasm-detection", "text"),
    ("oshudbot", "markdown-converter-app", "zero setup"),
]

THEMES = {
    "dark":  dict(bg="#0d1117", fg="#e6edf3", dim="#7d8590", edge="#30363d",
                  pal=["#ff7b72", "#79c0ff", "#d2a8ff", "#7ee787"]),
    "light": dict(bg="#ffffff", fg="#1f2328", dim="#656d76", edge="#d0d7de",
                  pal=["#cf222e", "#0969da", "#8250df", "#1a7f37"]),
}


def chromatic_number():
    ids = list(NODES)
    adj = [(a, b) for a, b, _ in EDGES]
    for k in range(1, 5):
        for cols in product(range(k), repeat=len(ids)):
            c = dict(zip(ids, cols))
            if all(c[a] != c[b] for a, b in adj):
                return k, c
    raise RuntimeError("needs more than 4 colours")


def drawing(theme, chi, colour):
    """Everything inside the <svg>, in full-canvas coordinates."""
    t = THEMES[theme]
    out = ["<style>",
           ".e{stroke-dasharray:400;stroke-dashoffset:400;animation:draw 1.2s ease-out forwards}",
           "@keyframes draw{to{stroke-dashoffset:0}}",
           ".n{opacity:0;animation:pop .5s ease-out forwards}",
           "@keyframes pop{to{opacity:1}}",
           ".p{fill:none;stroke-width:1.5;animation:pulse 3.5s ease-out infinite}",
           "@keyframes pulse{0%{r:8;opacity:.9}70%,100%{r:22;opacity:0}}",
           "</style>",
           f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>']
    for i, (a, b, idea) in enumerate(EDGES):
        (_, x1, y1), (_, x2, y2) = NODES[a], NODES[b]
        out.append(f'<line class="e" style="animation-delay:{i*0.1:.1f}s" x1="{x1}" y1="{y1}" '
                   f'x2="{x2}" y2="{y2}" stroke="{t["edge"]}" stroke-width="1.5"/>')
        out.append(f'<text class="n" style="animation-delay:1.4s" x="{(x1+x2)/2:.0f}" y="{(y1+y2)/2 + 4:.0f}" '
                   f'text-anchor="middle" font-size="9" font-style="italic" fill="{t["dim"]}" '
                   f'paint-order="stroke" stroke="{t["bg"]}" stroke-width="4">{idea}</text>')
    for i, (nid, (label, x, y)) in enumerate(NODES.items()):
        c = t["pal"][colour[nid]]
        ty = y - 16 if y < 200 else y + 26
        out.append(f'<g class="n" style="animation-delay:{0.3 + i*0.08:.2f}s">'
                   f'<circle class="p" cx="{x}" cy="{y}" r="8" stroke="{c}" style="animation-delay:{1.5 + i*0.35:.2f}s"/>'
                   f'<circle cx="{x}" cy="{y}" r="8" fill="{c}"/>'
                   f'<text x="{x}" y="{ty}" text-anchor="middle" font-size="12" font-weight="700" '
                   f'fill="{t["fg"]}">{label}</text></g>')
    out.append(f'<text x="24" y="{H-22}" font-size="22" font-weight="700" fill="{t["fg"]}">{NAME}</text>')
    out.append(f'<text x="{W-20}" y="26" text-anchor="end" font-size="11" fill="{t["dim"]}">'
               f'click any node   |V| = {len(NODES)}   |E| = {len(EDGES)}   χ(G) = {chi}</text>')
    return "\n".join(out)


def strips():
    """(repo, x0, width) per node; boundaries halfway between neighbours."""
    xs = [x for _, x, _ in NODES.values()]
    cuts = [0] + [(a + b) / 2 for a, b in zip(xs, xs[1:])] + [W]
    return [(nid, cuts[i], cuts[i + 1] - cuts[i]) for i, nid in enumerate(NODES)]


def main():
    chi, colour = chromatic_number()
    print(f"chi(G) = {chi}, |V| = {len(NODES)}, |E| = {len(EDGES)}")
    os.makedirs("header", exist_ok=True)
    font = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
    html = []
    for k, (nid, x0, w) in enumerate(strips()):
        for theme in THEMES:
            with open(f"header/{k}-{theme}.svg", "w", encoding="utf-8") as f:
                f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:g}" height="{H}" '
                        f'viewBox="{x0:g} 0 {w:g} {H}" font-family="{font}">\n'
                        f'{drawing(theme, chi, colour)}\n</svg>\n')
        pct = int(w / W * 100000) / 1000  # floor, so the row never adds up past 100%
        html.append(f'<a href="{GH}{nid}"><picture>'
                    f'<source media="(prefers-color-scheme: dark)" srcset="header/{k}-dark.svg">'
                    f'<img src="header/{k}-light.svg" width="{pct}%" alt="{NODES[nid][0]}"></picture></a>')
    # one line, no whitespace between strips, or GitHub renders gaps
    block = "<!-- GRAPH -->\n<p>" + "".join(html) + "</p>\n<!-- /GRAPH -->"
    readme = open("README.md", encoding="utf-8").read()
    readme = re.sub(r"<!-- GRAPH -->.*?<!-- /GRAPH -->", lambda _: block, readme, flags=re.S)
    open("README.md", "w", encoding="utf-8").write(readme)


if __name__ == "__main__":
    main()
