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

# Mark geometry on a 48-unit grid: 2x2 plain weave, square ends, real gaps.
SIZE, W, GAP, PITCH, LO, HI = 48, 6, 2.6, 16, 5, 43
WORD_WEIGHT = 600  # Inter weight for the wordmark


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


def load_font(path):
    font = TTFont(path)
    return instancer.instantiateVariableFont(font, {"wght": WORD_WEIGHT, "opsz": 32}, inplace=False) if "fvar" in font else font


def word_outline(font, text):
    """Path data for `text` in font units (y up), plus advance width and x-height."""
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    x, parts = 0, []
    for ch in text:
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
        width = mark_h + gap + advance * s
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
    lock_w = 48 + 12 + advance * s
    scale = 640 / lock_w
    og = svg(
        1200, 630,
        f'<g transform="translate({(1200 - 640) / 2:g} {(630 - 48 * scale) / 2:g}) scale({scale:g})">'
        + mark_group(PALETTES["light"]) + word_group(word, PALETTES["light"], 60, SIZE / 2 + 10.5, s) + "</g>",
        bg=LIGHT_BG,
    )
    write("og-image.svg", og)
    png(OUT / "og-image.svg", OUT / "og-image.png", 1200)

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
    lock_w = 48 + 12 + advance * s
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
