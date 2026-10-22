# SPDX-FileCopyrightText: 2026 The weft authors
# SPDX-License-Identifier: MIT
"""Generate the weft brand set into public/brand (and the favicon into public/).

Run inside `nix develop`: needs fontTools (wordmark outlines from Inter) and resvg (PNG export).
Usage: python3 brand/generate.py <path to InterVariable.ttf>
"""

import subprocess
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public" / "brand"

# Colours. Warp = vertical threads, weft = horizontal threads, ink = wordmark.
PALETTES = {
    "light": {"warp": "#1f3bad", "weft": "#c18215", "ink": "#1d2333"},  # on light backgrounds
    "dark": {"warp": "#3355db", "weft": "#f6bb55", "ink": "#e6e8ee"},  # on dark backgrounds
    "black": {"warp": "#111111", "weft": "#111111", "ink": "#111111"},  # one colour
    "white": {"warp": "#ffffff", "weft": "#ffffff", "ink": "#ffffff"},  # one colour, reversed
}
LIGHT_BG, DARK_BG = "#f7f6f2", "#11151f"
MUTED = "#4a5163"  # secondary text on the light background

# Repository icons: the mark with a badge. Pictograms on a 24-unit grid, drawn as white strokes.
PICTOGRAMS = {
    "weft-design": '<path d="M7 7.5H17M7 12H17M7 16.5H13"/>',  # text lines: documents
    "weft-verifier": '<path d="M6.5 12.5L10.5 16.5L17.5 8.5"/>',  # check mark
    "weft-parts": '<rect x="7.5" y="7.5" width="9" height="9" rx="1"/><path d="M12 4.5V7.5M12 16.5V19.5M4.5 12H7.5M16.5 12H19.5"/>',  # chip
    "weft-boardchecker": '<circle cx="10.5" cy="10.5" r="4.5"/><path d="M14 14L18.5 18.5"/>',  # magnifier: inspect
    "weft-sim": '<path d="M9.5 7V17L17 12Z" fill="#fff"/>',  # play
    "weft-website": '<rect x="5" y="6" width="14" height="12" rx="1.5"/><path d="M5 10H19"/>',  # browser window
    "weft-agent": '<path d="M6.5 9H17M14 6L17 9L14 12M17.5 15H7M10 12L7 15L10 18"/>',  # two arrows: exchange, sync
    "weft-cli": '<path d="M6.5 8L10.5 12L6.5 16M12.5 16.5H17.5"/>',  # terminal prompt
}
# Badge: centre and radius on the 48-unit grid, plus the background ring that separates it.
BADGE_C, BADGE_R, BADGE_RING = 36.5, 11, 1.5
ICON_MARK_SCALE = 0.72

# Repositories with a social preview card: name and the description shown on GitHub.
REPOS = [
    ("weft-design", "Design documents: decisions, prior art, contracts and facts"),
    ("weft-verifier", "Trusted core: verifies signed documents and delegations and decides desired state, offline and deterministically"),
    ("weft-parts", "Chip data (pinouts, address straps, device tree facts) and behavioural chip models"),
    ("weft-boardchecker", "Checks a PCB netlist (IPC-2581) against a Linux device tree overlay"),
    ("weft-sim", "Board simulation: real Linux drivers in a small VM against weft-parts chip models"),
    ("weft-website", "theweft.org: static site served by Cloudflare"),
    ("weft-agent", "Linux device and gateway agent: transport, decider and executor around weft-verifier"),
    ("weft-cli", "Operator tool: keys, signed documents and dry runs for weft"),
]

# Mark geometry on a 48-unit grid: 2x2 plain weave, square ends, real gaps.
SIZE, W, GAP, PITCH, LO, HI = 48, 6, 2.6, 16, 5, 43
WORD_WEIGHT = 600  # Inter weight for the wordmark
# Extra space between letter pairs, in font units: Inter's f and t crossbars almost touch.
KERN = {("f", "t"): 100}


def mark_paths():
    """(thread kind, path data) for the weave; under-threads are cut where they cross."""
    pos = [SIZE / 2 - PITCH / 2, SIZE / 2 + PITCH / 2]
    out = []

    def rect(vertical, c, a, b):
        h = W / 2
        if vertical:
            return f"M{c - h:g},{a:g}H{c + h:g}V{b:g}H{c - h:g}Z"
        return f"M{a:g},{c - h:g}V{c + h:g}H{b:g}V{c - h:g}Z"

    for vertical, kind in ((False, "weft"), (True, "warp")):
        for k in range(2):
            cuts = [pos[j] for j in range(2) if ((k + j) % 2 == 0) == vertical]
            start = LO
            for x in sorted(cuts):
                a, b = round(x - W / 2 - GAP, 2), round(x + W / 2 + GAP, 2)
                if a > start:
                    out.append((kind, rect(vertical, pos[k], start, a)))
                start = b
            if HI > start:
                out.append((kind, rect(vertical, pos[k], start, HI)))
    return out


def mark_group(p, dx=0.0, dy=0.0, scale=1.0):
    body = "".join(
        f'<path fill="{p[kind]}" d="{d}"/>' for kind, d in mark_paths()
    )
    return f'<g transform="translate({dx:g} {dy:g}) scale({scale:g})">{body}</g>'


def load_font(path, weight=WORD_WEIGHT):
    font = TTFont(path)
    return instancer.instantiateVariableFont(font, {"wght": weight, "opsz": 32}, inplace=False) if "fvar" in font else font


def word_outline(font, text):
    """Path data for `text` in font units (y up), plus advance width and x-height."""
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    x, parts = 0, []
    for i, ch in enumerate(text):
        x += KERN.get((text[i - 1], ch), 0) if i else 0
        name = cmap[ord(ch)]
        pen = SVGPathPen(glyphs)
        glyphs[name].draw(TransformPen(pen, (1, 0, 0, 1, x, 0)))
        parts.append(pen.getCommands())
        x += glyphs[name].width
    return " ".join(parts), x, font["OS/2"].sxHeight


def svg(width, height, body, bg=None):
    rect = f'<rect width="{width:g}" height="{height:g}" fill="{bg}"/>' if bg else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:g} {height:g}" '
        f'width="{width:g}" height="{height:g}">{rect}{body}</svg>\n'
    )


def word_group(word, p, x, baseline, scale):
    d, _, _ = word
    return f'<path fill="{p["ink"]}" transform="translate({x:g} {baseline:g}) scale({scale:g} {-scale:g})" d="{d}"/>'


def text_path(font, text, x, baseline, x_height, fill):
    """`text` as outlines with the given x-height; returns (svg path, width)."""
    d, advance, xh = word_outline(font, text)
    s = x_height / xh
    path = f'<path fill="{fill}" transform="translate({x:g} {baseline:g}) scale({s:g} {-s:g})" d="{d}"/>'
    return path, advance * s


def wrap(font, text, x_height, width):
    """Greedy line breaks so that no line is wider than `width`."""
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and text_path(font, candidate, 0, 0, x_height, "")[1] > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    return lines + [line]


def repo_icons():
    p = PALETTES["light"]
    (OUT / "repos").mkdir(exist_ok=True)
    for name, picto in PICTOGRAMS.items():
        s = BADGE_R * 2 / 24 * 0.82  # pictogram fills 82 % of the badge
        o = BADGE_C - 12 * s
        body = (
            mark_group(p, 1, 1, ICON_MARK_SCALE)
            + f'<circle cx="{BADGE_C:g}" cy="{BADGE_C:g}" r="{BADGE_R + BADGE_RING:g}" fill="{LIGHT_BG}"/>'
            + f'<circle cx="{BADGE_C:g}" cy="{BADGE_C:g}" r="{BADGE_R:g}" fill="{p["warp"]}"/>'
            + f'<g transform="translate({o:g} {o:g}) scale({s:g})" fill="none" stroke="#fff" stroke-width="2.6" '
            + f'stroke-linecap="round" stroke-linejoin="round">{picto}</g>'
        )
        write(f"repos/{name}.svg", svg(SIZE, SIZE, body, bg=LIGHT_BG))
        png(OUT / "repos" / f"{name}.svg", OUT / "repos" / f"{name}-512.png", 512)


def social(bold, regular):
    W, H, M = 1280, 640, 96
    p = PALETTES["light"]
    (OUT / "social").mkdir(exist_ok=True)
    for name, description in REPOS:
        body = mark_group(p, M - 5 * 2.5, M - 5 * 2.5, 2.5)  # 120 px mark, threads aligned to the margin
        # Name: "weft-" in ink, the rest in warp; as large as fits, at most x-height 64.
        prefix, rest = "weft-", name.removeprefix("weft-")
        _, full = text_path(bold, name, 0, 0, 64, "")
        xh = min(64, 64 * (W - 2 * M) / full)
        baseline = 380
        part, w = text_path(bold, prefix, M, baseline, xh, p["ink"])
        body += part + text_path(bold, rest, M + w, baseline, xh, p["warp"])[0]
        for i, line in enumerate(wrap(regular, description, 22, W - 2 * M)):
            body += text_path(regular, line, M, baseline + 80 + i * 50, 22, MUTED)[0]
        write(f"social/{name}.svg", svg(W, H, body, bg=LIGHT_BG))
        png(OUT / "social" / f"{name}.svg", OUT / "social" / f"{name}.png", W)


def write(name, text):
    (OUT / name).write_text(text)


def png(src, dst, width):
    subprocess.run(["resvg", "-w", str(width), str(src), str(dst)], check=True)


def main(font_path):
    OUT.mkdir(parents=True, exist_ok=True)
    font = load_font(font_path)
    word = word_outline(font, "weft")
    _, advance, x_height = word
    upm = font["head"].unitsPerEm

    for tag, p in PALETTES.items():
        write(f"mark-{tag}.svg", svg(SIZE, SIZE, mark_group(p)))

        # Wordmark alone: x-height 24 units.
        s = 24 / x_height
        ascent = font["OS/2"].sTypoAscender * s
        write(f"wordmark-{tag}.svg", svg(advance * s, ascent + 2, word_group(word, p, 0, ascent, s)))

        # Horizontal lockup: mark 48 high; x-height 21 (centred on the mark); gap 12.
        s = 21 / x_height
        mark_h, gap = 48, 12
        baseline = SIZE / 2 + 10.5
        width = mark_h + gap + advance * s + LO  # right margin matches the mark's left margin
        write(f"lockup-horizontal-{tag}.svg", svg(width, mark_h, mark_group(p) + word_group(word, p, mark_h + gap, baseline, s)))

        # Stacked lockup: mark above, wordmark centred below.
        s = 20 / x_height
        ww = advance * s
        width = max(48, ww)
        height = 48 + 10 + 20 + 4
        write(
            f"lockup-stacked-{tag}.svg",
            svg(width, height, mark_group(p, (width - 48) / 2) + word_group(word, p, (width - ww) / 2, 48 + 10 + 20, s)),
        )

    # App icon and avatar: mark on the light background, full square (platforms round it themselves).
    icon = svg(SIZE, SIZE, mark_group(PALETTES["light"], SIZE * 0.1, SIZE * 0.1, 0.8), bg=LIGHT_BG)
    write("app-icon.svg", icon)
    for name, px in (("app-icon-512.png", 512), ("apple-touch-icon.png", 180), ("github-avatar.png", 500)):
        png(OUT / "app-icon.svg", OUT / name, px)
    for tag in ("light", "dark", "black", "white"):
        png(OUT / f"mark-{tag}.svg", OUT / f"mark-{tag}-512.png", 512)

    # Social preview (Open Graph), 1200 x 630: horizontal lockup centred on the light background.
    s = 21 / x_height
    lock_w = 48 + 12 + advance * s + LO
    scale = 640 / lock_w
    og = svg(
        1200, 630,
        f'<g transform="translate({(1200 - 640) / 2:g} {(630 - 48 * scale) / 2:g}) scale({scale:g})">'
        + mark_group(PALETTES["light"]) + word_group(word, PALETTES["light"], 60, SIZE / 2 + 10.5, s) + "</g>",
        bg=LIGHT_BG,
    )
    write("og-image.svg", og)
    png(OUT / "og-image.svg", OUT / "og-image.png", 1200)

    # Repository icons: mark plus a badge with a pictogram; square, light background.
    repo_icons()

    # Repository social previews (GitHub: 1280 x 640): mark, repository name, description.
    social(font, load_font(font_path, 400))

    # Favicon: follows the browser's colour scheme.
    light, dark = PALETTES["light"], PALETTES["dark"]
    body = "".join(f'<path class="{kind}" d="{d}"/>' for kind, d in mark_paths())
    favicon = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}"><style>'
        f'.warp{{fill:{light["warp"]}}}.weft{{fill:{light["weft"]}}}'
        f'@media (prefers-color-scheme:dark){{.warp{{fill:{dark["warp"]}}}.weft{{fill:{dark["weft"]}}}}}'
        f"</style>{body}</svg>\n"
    )
    (ROOT / "public" / "favicon.svg").write_text(favicon)

    # Inline mark for the site pages (colours from CSS custom properties).
    inline = (
        f'<svg class="mark" viewBox="0 0 {SIZE} {SIZE}" aria-hidden="true" focusable="false">'
        + "".join(f'<path class="{kind}" d="{d}"/>' for kind, d in mark_paths())
        + "</svg>"
    )
    (ROOT / "brand" / "mark-inline.html").write_text(inline + "\n")

    # Inline horizontal lockup for the start page heading (colours from CSS custom properties).
    s = 21 / x_height
    d, _, _ = word
    lock_w = 48 + 12 + advance * s + LO
    lockup = (
        f'<svg class="lockup" viewBox="0 0 {lock_w:g} 48" role="img" aria-label="weft">'
        + "".join(f'<path class="{kind}" d="{pd}"/>' for kind, pd in mark_paths())
        + f'<path class="ink" transform="translate(60 {SIZE / 2 + 10.5:g}) scale({s:g} {-s:g})" d="{d}"/>'
        + "</svg>"
    )
    (ROOT / "brand" / "lockup-inline.html").write_text(lockup + "\n")
    print(f"wrote {len(list(OUT.iterdir()))} files to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1])
