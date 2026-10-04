"""Draw the profile header: my projects as a graph, edges = shared ideas.

Writes header-dark.svg and header-light.svg. The colouring is computed and
chi(G) is checked by brute force, so the number printed on it is real.
"""
from itertools import product

W, H = 880, 340

# id: (label, x, y, link or None). Private work appears as a topic, no link.
NODES = {
    "audit":   ("audit harness",        440, 175, None),
    "colo":    ("colorectal grading",   330, 100, None),
    "cerv":    ("cervical triage",      550, 100, None),
    "oral":    ("oral dysplasia",       575, 245, None),
    "gi":      ("GI endoscopy",         440, 285, None),
    "gleason": ("gleason raters",       310, 250, None),
    "gland":   ("gland graphs",         200, 168, None),
    "frac":    ("fractional χ GNN",     95, 235, None),
    "gfw":     ("fishing gear / AIS",   690, 170, None),
    "epist":   ("epistocracy sim",      790, 90,  "https://github.com/yaqzans/who-should-count-more"),
    "cvpr":    ("vehicle recognition",  700, 285, "https://github.com/yaqzans/cvpr-two-stage-vehicle-recognition"),
    "oshud":   ("oshudbot",             90,  85,  "https://github.com/yaqzans/oshudbot"),
    "sarc":    ("sarcasm NLP",          200, 50,  "https://github.com/yaqzans/ids-sarcasm-detection"),
    "ttt":     ("tictactoe ∞",          800, 230, "https://github.com/yaqzans/TicTacToeInfinity"),
}

# (a, b, shared idea)
EDGES = [
    ("audit", "colo", "conformal"), ("audit", "cerv", "conformal"),
    ("audit", "oral", "conformal"), ("audit", "gi", "conformal"),
    ("audit", "gleason", "grading"),
    ("colo", "cerv", "per-class coverage"), ("oral", "gi", "shift"),
    ("gland", "colo", "histopathology"), ("gland", "frac", "GNNs"),
    ("gleason", "gland", "histopathology"),
    ("gfw", "audit", "leakage control"), ("gfw", "epist", "simulation"),
    ("cvpr", "gi", "CNN backbones"), ("cvpr", "gfw", "two-stage"),
    ("oshud", "sarc", "NLP"), ("oshud", "gland", "python"),
    ("epist", "ttt", "web toys"), ("ttt", "cvpr", "javascript"),
]

THEMES = {
    "dark":  dict(bg="#0d1117", fg="#e6edf3", dim="#7d8590", edge="#30363d",
                  pal=["#ff7b72", "#79c0ff", "#d2a8ff", "#7ee787"]),
    "light": dict(bg="#ffffff", fg="#1f2328", dim="#656d76", edge="#d0d7de",
                  pal=["#cf222e", "#0969da", "#8250df", "#1a7f37"]),
}


def chromatic_number():
    ids = list(NODES)
    adj = {(a, b) for a, b, _ in EDGES} | {(b, a) for a, b, _ in EDGES}
    for k in range(1, 5):
        for cols in product(range(k), repeat=len(ids)):
            c = dict(zip(ids, cols))
            if all(c[a] != c[b] for a, b in adj):
                return k, c
    raise RuntimeError("needs more than 4 colours")


def svg(theme, chi, colour):
    t = THEMES[theme]
    font = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="{font}">',
           "<style>",
           ".e{stroke-dasharray:400;stroke-dashoffset:400;animation:draw 1.2s ease-out forwards}",
           "@keyframes draw{to{stroke-dashoffset:0}}",
           ".n{opacity:0;animation:pop .5s ease-out forwards}",
           "@keyframes pop{to{opacity:1}}",
           ".p{fill:none;stroke-width:1.5;animation:pulse 3.5s ease-out infinite}",
           "@keyframes pulse{0%{r:7;opacity:.9}70%,100%{r:20;opacity:0}}",
           "</style>",
           f'<rect width="{W}" height="{H}" rx="12" fill="{t["bg"]}"/>']

    # edges, drawn in BFS order from the hub so the graph grows outward
    order, seen, q = [], {"audit"}, ["audit"]
    while q:
        u = q.pop(0)
        for i, (a, b, _) in enumerate(EDGES):
            if u in (a, b) and i not in order:
                order.append(i)
                v = b if u == a else a
                if v not in seen:
                    seen.add(v)
                    q.append(v)
    for rank, i in enumerate(order):
        a, b, _ = EDGES[i]
        (_, x1, y1, _), (_, x2, y2, _) = NODES[a], NODES[b]
        out.append(f'<line class="e" style="animation-delay:{rank*0.08:.2f}s" '
                   f'x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{t["edge"]}" stroke-width="1.5"/>')

    # name each shared idea once, at the midpoint of its first edge
    named = set()
    for i in order:
        a, b, idea = EDGES[i]
        if idea in named:
            continue
        named.add(idea)
        (_, x1, y1, _), (_, x2, y2, _) = NODES[a], NODES[b]
        out.append(f'<text class="n" style="animation-delay:1.6s" x="{(x1+x2)/2:.0f}" y="{(y1+y2)/2 + 4:.0f}" '
                   f'text-anchor="middle" font-size="9" font-style="italic" fill="{t["dim"]}" '
                   f'paint-order="stroke" stroke="{t["bg"]}" stroke-width="4">{idea}</text>')

    # nodes
    for i, (nid, (label, x, y, link)) in enumerate(NODES.items()):
        c = t["pal"][colour[nid]]
        delay = 0.3 + i * 0.07
        g = [f'<g class="n" style="animation-delay:{delay:.2f}s">']
        if nid == "audit" or link:
            g.append(f'<circle class="p" cx="{x}" cy="{y}" r="7" stroke="{c}" '
                     f'style="animation-delay:{1.5 + i*0.25:.2f}s"/>')
        g.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{c}"/>')
        ty = y - 14 if y > 40 else y + 22
        weight = "700" if link else "400"
        g.append(f'<text x="{x}" y="{ty}" text-anchor="middle" font-size="12" '
                 f'font-weight="{weight}" fill="{t["fg"] if link else t["dim"]}">{label}</text>')
        g.append("</g>")
        out.append("".join(g))

    # title block
    out.append(f'<text x="24" y="{H-46}" font-size="22" font-weight="700" fill="{t["fg"]}">yaqzan m. a</text>')
    out.append(f'<text x="24" y="{H-24}" font-size="12" fill="{t["dim"]}">'
               f'G = (things I built, ideas they share)   χ(G) = {chi}</text>')
    out.append(f'<text x="{W-24}" y="24" text-anchor="end" font-size="11" fill="{t["dim"]}">'
               f'bold = public repo   |V| = {len(NODES)}   |E| = {len(EDGES)}</text>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    chi, colour = chromatic_number()
    print(f"chi(G) = {chi}, |V| = {len(NODES)}, |E| = {len(EDGES)}")
    for theme in THEMES:
        with open(f"header-{theme}.svg", "w", encoding="utf-8") as f:
            f.write(svg(theme, chi, colour))
