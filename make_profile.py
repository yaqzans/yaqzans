"""Build the whole profile: README.md plus every SVG it shows.

Header: my public repos as a graph, edges = what two repos actually share.
GitHub shows SVGs as plain images, so links inside them do nothing. To make
every node clickable the drawing is cut into vertical strips, one per node,
each wrapped in a link to that repo. Strips sit flush, so it reads as one
picture. That is why every node needs its own x.

Node list is checked against GitHub: anything not public stops the build.
chi(G) is checked by brute force. Run: python make_profile.py
"""
import json
import math
import os
import subprocess
from functools import cache
from itertools import product

USER = "yaqzans"
GH = f"https://github.com/{USER}/"
W, H = 980, 495
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

# repo: (label, tag, x, y). x must be distinct, each node owns a strip.
NODES = {
    "Bus-Management-System":              ("bus management",        "java, oop final",      60, 190),
    "WT_Fall-25-26_Project":              ("WT project",            "php course project",  131, 400),
    "Pink-Calculator":                    ("pink calculator",       "c# gui + sql",        202, 225),
    "HTML-CSS-JS-Practise":               ("html/css/js",           "practice tasks",      273, 330),
    "WT_Fall-25-26":                      ("WT fall 25",            "web tech course",     344, 420),
    "Productivity-Manager":               ("productivity manager",  "notes, tasks, timer", 415, 165),
    "TicTacToeInfinity":                  ("tictactoe ∞",          "move-to-win variant", 486, 290),
    "who-should-count-more":              ("who should count more", "voting experiment",   557, 400),
    "2D-Parking-Game":                    ("2D parking",            "opengl game",         628, 190),
    "cvpr-two-stage-vehicle-recognition": ("vehicle recognition",   "yolo + convnext",     699, 300),
    "ids-sarcasm-detection":              ("sarcasm detection",     "bow vs tf-idf",       770, 410),
    "markdown-converter-app":             ("markdown converter",    "anything to markdown", 841, 230),
    "oshudbot":                           ("oshudbot",              "bangla medicine lookup", 912, 340),
}

# (a, b, what they actually share)
EDGES = [
    ("Bus-Management-System", "Productivity-Manager", "oop course"),
    ("Bus-Management-System", "WT_Fall-25-26_Project", "course project"),
    ("Pink-Calculator", "Productivity-Manager", "c# + ms sql"),
    ("Pink-Calculator", "HTML-CSS-JS-Practise", "class tasks"),
    ("Productivity-Manager", "markdown-converter-app", "desktop app"),
    ("WT_Fall-25-26_Project", "WT_Fall-25-26", "same course"),
    ("WT_Fall-25-26_Project", "HTML-CSS-JS-Practise", "css"),
    ("WT_Fall-25-26", "HTML-CSS-JS-Practise", "web basics"),
    ("HTML-CSS-JS-Practise", "TicTacToeInfinity", "vanilla js"),
    ("HTML-CSS-JS-Practise", "who-should-count-more", "html + js"),
    ("TicTacToeInfinity", "who-should-count-more", "runs in browser"),
    ("TicTacToeInfinity", "2D-Parking-Game", "games"),
    ("2D-Parking-Game", "cvpr-two-stage-vehicle-recognition", "cars"),
    ("cvpr-two-stage-vehicle-recognition", "ids-sarcasm-detection", "classifiers"),
    ("cvpr-two-stage-vehicle-recognition", "oshudbot", "for bangladesh"),
    ("oshudbot", "ids-sarcasm-detection", "text"),
    ("oshudbot", "markdown-converter-app", "zero setup"),
]

LINKS = [  # (label, url, icon)
    ("LinkedIn", "https://www.linkedin.com/in/shamvi-md-abdullah-b42a321a6/", "in"),
    ("Google Scholar", "https://scholar.google.com/citations?user=DwskOfEAAAAJ&hl=en", "gs"),
    ("ORCID", "https://orcid.org/0009-0005-9717-9426", "id"),
    ("Email", "mailto:shamvi.abdullah@gmail.com", "@"),
]

ABOUT = [  # rendered as a highlighted code card
    ("k", "yaqzan"), ("p", " = {"), ("\n", ""),
    ("f", "  studies"), ("p", ":     "), ("s", '"CSE at AIUB, computational theory"'), ("p", ","), ("\n", ""),
    ("f", "  works_on"), ("p", ":    ["), ("s", '"medical imaging"'), ("p", ", "), ("s", '"graph theory"'),
    ("p", ", "), ("s", '"vision"'), ("p", ", "), ("s", '"nlp"'), ("p", "],"), ("\n", ""),
    ("f", "  cares_about"), ("p", ": "), ("s", '"whether a result survives its own controls"'), ("p", ","), ("\n", ""),
    ("f", "  tools"), ("p", ":       ["), ("s", '"pytorch"'), ("p", ", "), ("s", '"sklearn"'), ("p", ", "),
    ("s", '"r"'), ("p", ", "), ("s", '"c++"'), ("p", ", "), ("s", '"latex"'), ("p", ", "), ("s", '"esp32"'), ("p", "],"), ("\n", ""),
    ("p", "}"),
]

PAPERS = [  # (title, venue, role, doi or None)
    ("Gesture Controlled Robotic Hand Designed for Enhancing Industrial Automation and Innovation",
     "IEEE QPAIN 2026", "second + corresponding author", "10.1109/QPAIN69676.2026.11545528"),
    ("Development of a Simulated Blood-Like Solution for Medical Experiments",
     "Analytical Chemistry Letters, 2025", "fifth author", "10.1080/22297928.2025.2533331"),
    ("Evaluating the Performance of Agile-Waterfall Integrated Approaches in Large Scale Engineering Projects in Bangladesh",
     "IEOM Bangladesh 2025", "fifth author", "10.46254/BA08.20250467"),
    ("A Hybrid Human-AI Model for Sustainable Innovation in Media and Animation",
     "ICCTASS 2025", "third author", None),
]

THEMES = {
    "dark":  dict(bg="#0d1117", card="#161b22", fg="#e6edf3", dim="#7d8590", line="#30363d",
                  pal=["#ff7b72", "#58a6ff", "#d2a8ff"], k="#ff7b72", f="#79c0ff", s="#a5d6ff", p="#e6edf3"),
    "light": dict(bg="#ffffff", card="#f6f8fa", fg="#1f2328", dim="#656d76", line="#d0d7de",
                  pal=["#cf222e", "#0969da", "#8250df"], k="#cf222e", f="#0550ae", s="#0a3069", p="#1f2328"),
}


def check_public():
    out = subprocess.run(["gh", "repo", "list", USER, "--visibility", "public", "--limit", "200",
                          "--json", "name"], capture_output=True, text=True, check=True).stdout
    public = {r["name"] for r in json.loads(out)}
    bad = [n for n in NODES if n not in public]
    if bad:
        raise SystemExit(f"not public, refusing to draw: {bad}")
    missing = sorted(public - set(NODES) - {USER})
    if missing:
        print("public repos not in the graph yet:", missing)


def colouring():
    ids = list(NODES)
    for k in range(1, 5):
        for cols in product(range(k), repeat=len(ids)):
            c = dict(zip(ids, cols))
            if all(c[a] != c[b] for a, b, _ in EDGES):
                return k, c


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def degree(n):
    return sum(n in (a, b) for a, b, _ in EDGES)


def curve(a, b, i):
    """Quadratic edge; returns the path and a function giving the point at t."""
    (_, _, x1, y1), (_, _, x2, y2) = NODES[a], NODES[b]
    dx, dy = x2 - x1, y2 - y1
    bend = 0.14 * (1 if i % 2 else -1)
    cx, cy = (x1 + x2) / 2 - dy * bend, (y1 + y2) / 2 + dx * bend
    at = lambda t: ((1-t)**2 * x1 + 2*(1-t)*t * cx + t*t * x2, (1-t)**2 * y1 + 2*(1-t)*t * cy + t*t * y2)
    return f"M{x1},{y1} Q{cx:.0f},{cy:.0f} {x2},{y2}", at


def radius(n):
    return 7 + 2.2 * degree(n)


def boxes():
    """Rough bounding boxes of everything fixed: node, name, tag."""
    out = []
    for n, (label, tag, x, y) in NODES.items():
        r = radius(n)
        out.append((x - r - 6, y - r - 6, x + r + 6, y + r + 6))
        out.append((x - len(label) * 3.9, y + r + 7, x + len(label) * 3.9, y + r + 22))
        out.append((x - len(tag) * 3.1, y + r + 25, x + len(tag) * 3.1, y + r + 37))
    return out


def hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


@cache
def edge_labels():
    """Put each edge label at the first point along its curve that collides with nothing."""
    taken, pos = boxes(), []
    for i, (a, b, idea) in enumerate(EDGES):
        _, at = curve(a, b, i)
        hw = len(idea) * 2.9 + 3
        for t in (.5, .42, .58, .34, .66, .27, .73, .2, .8):
            px, py = at(t)
            box = (px - hw, py - 6, px + hw, py + 6)
            if not any(hit(box, o) for o in taken):
                break
        else:
            print(f"edge label '{idea}' collides wherever it goes")
        taken.append(box)
        pos.append((px, py))
    return pos


def graph(theme, chi, col):
    t = THEMES[theme]
    o = ['<defs>',
         '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%">'
         '<feGaussianBlur stdDeviation="5"/></filter>',
         f'<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">'
         f'<circle cx="1" cy="1" r="1" fill="{t["line"]}" opacity=".6"/></pattern>',
         f'<radialGradient id="vig" cx="60%" cy="55%" r="65%"><stop offset="0" stop-color="{t["bg"]}" stop-opacity="0"/>'
         f'<stop offset="1" stop-color="{t["bg"]}" stop-opacity="1"/></radialGradient>']
    for i, (a, b, _) in enumerate(EDGES):
        (_, _, x1, y1), (_, _, x2, y2) = NODES[a], NODES[b]
        o.append(f'<linearGradient id="g{i}" gradientUnits="userSpaceOnUse" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
                 f'<stop offset="0" stop-color="{t["pal"][col[a]]}"/><stop offset="1" stop-color="{t["pal"][col[b]]}"/></linearGradient>')
    o += ['</defs>', '<style>',
          '.e{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 1.4s ease-out forwards}',
          '@keyframes draw{to{stroke-dashoffset:0}}',
          '.f{opacity:0;animation:in .6s ease-out forwards}@keyframes in{to{opacity:1}}',
          '.r{fill:none;stroke-width:1.5;animation:ring 4s ease-out infinite;opacity:0}',
          '@keyframes ring{0%{r:12;opacity:.7}60%,100%{r:34;opacity:0}}',
          '</style>',
          f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>',
          f'<rect width="{W}" height="{H}" fill="url(#dots)"/>',
          f'<rect width="{W}" height="{H}" fill="url(#vig)"/>',
          f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="none" stroke="{t["line"]}"/>']

    # title
    o.append(f'<text class="f" x="34" y="66" font-family="{SANS}" font-size="38" font-weight="800" '
             f'fill="{t["fg"]}" letter-spacing="-1">yaqzan&#39;s</text>')
    o.append(f'<text class="f" style="animation-delay:.2s" x="36" y="94" font-family="{MONO}" font-size="12.5" '
             f'fill="{t["dim"]}">G = (public repos, things they share)</text>')
    o.append(f'<text class="f" style="animation-delay:.3s" x="{W-30}" y="44" text-anchor="end" font-family="{MONO}" '
             f'font-size="11.5" fill="{t["dim"]}">|V| = {len(NODES)}   |E| = {len(EDGES)}   '
             f'<tspan fill="{t["fg"]}" font-weight="700">χ(G) = {chi}</tspan></text>')
    sw = "".join(f'<circle cx="{W-82+i*16}" cy="66" r="5" fill="{c}"/>' for i, c in enumerate(t["pal"][:chi]))
    o.append(f'<g class="f" style="animation-delay:.4s">{sw}'
             f'<text x="{W-30}" y="88" text-anchor="end" font-family="{MONO}" font-size="10.5" fill="{t["dim"]}">'
             f'no edge joins two of a colour</text></g>')
    o.append(f'<text class="f" style="animation-delay:2.4s" x="{W-30}" y="110" text-anchor="end" '
             f'font-family="{MONO}" font-size="10.5" fill="{t["dim"]}">click a node to open the repo ↗</text>')

    # edges, then a particle travelling along each one
    for i, ((a, b, idea), (mx, my)) in enumerate(zip(EDGES, edge_labels())):
        d, _ = curve(a, b, i)
        o.append(f'<path class="e" pathLength="1" style="animation-delay:{.3 + i*.09:.2f}s" d="{d}" fill="none" '
                 f'stroke="url(#g{i})" stroke-width="1.8" stroke-opacity=".55"/>')
        o.append(f'<circle r="2.4" fill="{t["fg"]}" opacity="0"><animateMotion path="{d}" dur="{2.6 + (i % 4)*.5}s" '
                 f'begin="{2 + i*.37:.2f}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="opacity" values="0;.9;.9;0" dur="{2.6 + (i % 4)*.5}s" '
                 f'begin="{2 + i*.37:.2f}s" repeatCount="indefinite"/></circle>')
        o.append(f'<text class="f" style="animation-delay:1.8s" x="{mx:.0f}" y="{my + 3:.0f}" text-anchor="middle" '
                 f'font-family="{MONO}" font-size="9.5" font-style="italic" fill="{t["dim"]}" paint-order="stroke" '
                 f'stroke="{t["bg"]}" stroke-width="5" stroke-linejoin="round">{idea}</text>')

    # nodes: glow, ring, core, label
    for i, (n, (label, tag, x, y)) in enumerate(NODES.items()):
        c, r = t["pal"][col[n]], radius(n)
        o.append(f'<g class="f" style="animation-delay:{.5 + i*.08:.2f}s">'
                 f'<circle cx="{x}" cy="{y}" r="{r + 4:.1f}" fill="{c}" opacity=".35" filter="url(#glow)"/>'
                 f'<circle class="r" cx="{x}" cy="{y}" r="12" stroke="{c}" style="animation-delay:{2 + i*.6:.1f}s"/>'
                 f'<circle cx="{x}" cy="{y}" r="{r:.1f}" fill="{t["bg"]}" stroke="{c}" stroke-width="2.5"/>'
                 f'<circle cx="{x}" cy="{y}" r="{r*.42:.1f}" fill="{c}"/>'
                 f'<text x="{x}" y="{y + r + 19:.0f}" text-anchor="middle" font-family="{SANS}" font-size="13.5" '
                 f'font-weight="700" fill="{t["fg"]}" paint-order="stroke" stroke="{t["bg"]}" stroke-width="4">{esc(label)}</text>'
                 f'<text x="{x}" y="{y + r + 34:.0f}" text-anchor="middle" font-family="{MONO}" font-size="10" '
                 f'fill="{t["dim"]}" paint-order="stroke" stroke="{t["bg"]}" stroke-width="4">{esc(tag)}</text></g>')
    return "\n".join(o)


def chip(theme, label, icon):
    t = THEMES[theme]
    w = 46 + int(len(label) * 7.6)
    ic = {
        "in": f'<rect x="12" y="9" width="18" height="18" rx="3" fill="#0A66C2"/>'
              f'<text x="21" y="23" text-anchor="middle" font-family="{SANS}" font-size="12" font-weight="800" fill="#fff">in</text>',
        "gs": f'<circle cx="21" cy="18" r="9" fill="#4285F4"/>'
              f'<path d="M14 16.5 L21 12.5 L28 16.5 L21 20.5 Z M17 18.5 v3 q4 2.5 8 0 v-3 L21 20.5 Z" fill="#fff"/>',
        "id": f'<circle cx="21" cy="18" r="9" fill="#A6CE39"/>'
              f'<text x="21" y="22" text-anchor="middle" font-family="{SANS}" font-size="9.5" font-weight="800" fill="#fff">iD</text>',
        "@":  f'<rect x="12" y="11.5" width="18" height="13" rx="2" fill="none" stroke="{t["pal"][0]}" stroke-width="1.8"/>'
              f'<path d="M12.5 12.5 L21 19 L29.5 12.5" fill="none" stroke="{t["pal"][0]}" stroke-width="1.8"/>',
    }[icon]
    return (w, f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="36" viewBox="0 0 {w} 36">'
               f'<rect x=".5" y=".5" width="{w-1}" height="35" rx="9" fill="{t["card"]}" stroke="{t["line"]}"/>{ic}'
               f'<text x="38" y="22.5" font-family="{SANS}" font-size="13" font-weight="600" fill="{t["fg"]}">{label}</text></svg>')


def about(theme):
    t = THEMES[theme]
    lines, cur = [], []
    for kind, s in ABOUT:
        if kind == "\n":
            lines.append(cur)
            cur = []
        else:
            cur.append(f'<tspan fill="{t[kind]}">{esc(s)}</tspan>')
    lines.append(cur)
    h = 58 + 22 * len(lines)
    rows = "".join(f'<text x="58" y="{70 + 22*i}" xml:space="preserve">{"".join(l)}</text>'
                   f'<text x="34" y="{70 + 22*i}" text-anchor="end" fill="{t["dim"]}" opacity=".6">{i + 1}</text>'
                   for i, l in enumerate(lines))
    dots = "".join(f'<circle cx="{24 + 16*i}" cy="22" r="5" fill="{c}"/>' for i, c in enumerate(t["pal"]))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" '
            f'font-family="{MONO}" font-size="13.5">'
            f'<rect x=".5" y=".5" width="{W-1}" height="{h-1}" rx="12" fill="{t["card"]}" stroke="{t["line"]}"/>'
            f'{dots}<text x="{W/2}" y="26" text-anchor="middle" font-size="11.5" fill="{t["dim"]}">about.py</text>'
            f'<line x1="0" y1="40" x2="{W}" y2="40" stroke="{t["line"]}"/>{rows}</svg>')


def wrap(s, n):
    out, cur = [], ""
    for w in s.split():
        if len(cur) + len(w) + 1 > n:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return out + [cur]


def paper(theme, i, title, venue, role, doi):
    t = THEMES[theme]
    lines = wrap(title, 120)
    h = 48 + 20 * len(lines)
    c = t["pal"][i % len(t["pal"])]
    tl = "".join(f'<text x="34" y="{30 + 20*j}" font-family="{SANS}" font-size="15" font-weight="700" '
                 f'fill="{t["fg"]}">{esc(l)}</text>' for j, l in enumerate(lines))
    right = (f'<text x="{W-24}" y="{h/2 + 4:.0f}" text-anchor="end" font-family="{MONO}" font-size="11.5" '
             f'fill="{c}">doi ↗</text>') if doi else ""
    return h, (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}">'
               f'<rect x=".5" y=".5" width="{W-1}" height="{h-1}" rx="10" fill="{t["card"]}" stroke="{t["line"]}"/>'
               f'<rect x="12" y="14" width="4" height="{h-28}" rx="2" fill="{c}"/>{tl}'
               f'<text x="34" y="{30 + 20*len(lines) + 4}" font-family="{MONO}" font-size="11.5" fill="{t["dim"]}">'
               f'{esc(venue)}  ·  {esc(role)}</text>{right}</svg>')


def picture(base, width, alt):
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{base}-dark.svg">'
            f'<img src="{base}-light.svg" width="{width}" alt="{esc(alt)}"></picture>')


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    check_public()
    chi, col = colouring()
    print(f"chi(G) = {chi}, |V| = {len(NODES)}, |E| = {len(EDGES)}")
    b = boxes()
    for i in range(len(b)):
        for j in range(i + 1, len(b)):
            if i // 3 != j // 3 and hit(b[i], b[j]):
                print("node overlap:", list(NODES)[i // 3], list(NODES)[j // 3])
    os.makedirs("assets", exist_ok=True)
    for old in os.listdir("assets"):
        os.remove(os.path.join("assets", old))

    # header strips, cut at whole pixels halfway between neighbouring nodes
    xs = [v[2] for v in NODES.values()]
    assert xs == sorted(xs) and len(set(xs)) == len(xs), "node x must be distinct and increasing"
    cuts = [0] + [round((a + b) / 2) for a, b in zip(xs, xs[1:])] + [W]
    strips = []
    for k, n in enumerate(NODES):
        x0, w = cuts[k], cuts[k + 1] - cuts[k]
        for th in THEMES:
            write(f"assets/g{k}-{th}.svg", f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{H}" '
                                           f'viewBox="{x0} 0 {w} {H}">\n{graph(th, chi, col)}\n</svg>\n')
        pct = math.floor(w / W * 100000) / 1000
        strips.append(f'<a href="{GH}{n}">{picture(f"assets/g{k}", f"{pct}%", NODES[n][0])}</a>')

    chips = []
    for k, (label, url, icon) in enumerate(LINKS):
        for th in THEMES:
            w, svg = chip(th, label, icon)
            write(f"assets/link{k}-{th}.svg", svg)
        chips.append(f'<a href="{url}">{picture(f"assets/link{k}", w, label)}</a>')

    for th in THEMES:
        write(f"assets/about-{th}.svg", about(th))

    papers = []
    for k, (title, venue, role, doi) in enumerate(PAPERS):
        for th in THEMES:
            _, svg = paper(th, k, title, venue, role, doi)
            write(f"assets/paper{k}-{th}.svg", svg)
        pic = picture(f"assets/paper{k}", "100%", title)
        papers.append(f'<a href="https://doi.org/{doi}">{pic}</a>' if doi else pic)

    write("README.md", "\n".join([
        "<!-- generated by make_profile.py, edit that and rerun -->",
        # one line, no whitespace between strips, or GitHub renders gaps
        "<p>" + "".join(strips) + "</p>",
        "",
        '<p align="center">' + " &nbsp;".join(chips) + "</p>",
        "",
        "<p>" + picture("assets/about", "100%", "about") + "</p>",
        "",
        "### papers",
        "",
        "\n".join(f"<p>{p}</p>" for p in papers),
        "",
        "<sub>the graph is drawn by <a href=\"make_profile.py\">make_profile.py</a> from my public repos. "
        "each edge is something the two repos actually share, and χ(G) is checked by brute force.</sub>",
        "",
    ]))


if __name__ == "__main__":
    main()
