"""The Paladin, as terminal pixel art.

Extracted once from assets/logo.png (each letter below is one pixel; dev-time
script, no image libraries at runtime). Rendered with half-block characters:
one character cell shows two pixels — top half foreground, bottom half
background.
"""

from rich.style import Style
from rich.text import Text

PALETTE = {
    "k": (0, 0, 0), "s": (140, 139, 147), "w": (194, 191, 198),
    "o": (243, 243, 245), "g": (86, 85, 91), "d": (32, 32, 32),
    "l": (158, 157, 163), "b": (246, 120, 59), "r": (143, 64, 47),
}

ROWS = [
    "......kkk.........",
    ".....kswwkk.......",
    "....wwwwwwwk......",
    "...kwwwwwwwok.....",
    "...kowwwwwwwk.....",
    "...kgdooodgwk.....",
    "...kdddddddwk...k.",
    "...kwwdddwwwk..kok",
    "..kkwwwddwwwk.kgl.",
    ".ookoowddookk.glk.",
    "kgskkkwookkkbblk..",
    "kssswwkkksskkrk...",
    ".kkkssgggwwksk....",
    "...ksswwwwwkk.....",
    "...kgkkkkggk......",
    "....k.....k.......",
]


def _pixel_pairs():
    """Yield rows of (top_color, bottom_color) tuples, one per char cell."""
    for top, bottom in zip(ROWS[::2], ROWS[1::2]):
        yield [
            (PALETTE.get(t), PALETTE.get(b))
            for t, b in zip(top, bottom)
        ]


def ansi(indent: str = "") -> str:
    """The knight as a raw ANSI truecolor string, for print()."""
    out = []
    for row in _pixel_pairs():
        line = indent
        for top, bottom in row:
            if top is None and bottom is None:
                line += "\x1b[0m "
            elif bottom is None:
                line += "\x1b[0m\x1b[38;2;%d;%d;%dm▀" % top
            elif top is None:
                line += "\x1b[0m\x1b[38;2;%d;%d;%dm▄" % bottom
            else:
                line += "\x1b[38;2;%d;%d;%dm\x1b[48;2;%d;%d;%dm▀" % (top + bottom)
        out.append(line + "\x1b[0m")
    return "\n".join(out)


_ORANGE = (PALETTE["b"], PALETTE["r"])


def _tinted(pixel, tint, accent):
    """Recolor a pixel: keep its brightness, take its hue from the theme —
    the accent color for the sword guard, the tint for everything else."""
    if tint is None or pixel is None:
        return pixel
    base = accent if pixel in _ORANGE else tint
    lum = sum(pixel) / 765
    return tuple(int(c * lum) for c in base)


def _hex_rgb(color: str) -> tuple:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def rich_text(tint: str | None = None, accent: str | None = None) -> Text:
    """The knight as a Rich Text, for Textual widgets. Pass theme colors as
    hex strings to render him in the theme's livery instead of silver."""
    tint_rgb = _hex_rgb(tint) if tint else None
    accent_rgb = _hex_rgb(accent) if accent else tint_rgb
    text = Text()
    for row in _pixel_pairs():
        for top, bottom in row:
            top = _tinted(top, tint_rgb, accent_rgb)
            bottom = _tinted(bottom, tint_rgb, accent_rgb)
            if top is None and bottom is None:
                text.append(" ")
            elif bottom is None:
                text.append("▀", Style(color="rgb(%d,%d,%d)" % top))
            elif top is None:
                text.append("▄", Style(color="rgb(%d,%d,%d)" % bottom))
            else:
                text.append("▀", Style(color="rgb(%d,%d,%d)" % top, bgcolor="rgb(%d,%d,%d)" % bottom))
        text.append("\n")
    return text


def ascii_art() -> str:
    """The knight as plain monochrome ASCII — two chars per pixel to keep
    his proportions in terminal cells, denser glyphs for brighter armor."""
    lines = []
    for row in ROWS:
        line = ""
        for ch in row:
            pixel = PALETTE.get(ch)
            if pixel is None:
                line += "  "
            elif pixel in _ORANGE:
                line += "%%"
            else:
                lum = sum(pixel) / 765
                line += "::" if lum < 0.15 else "++" if lum < 0.45 else "==" if lum < 0.8 else "##"
        lines.append(line.rstrip())
    return "\n".join(lines)


def says(message: str) -> str:
    """Cowsay, but it's a knight."""
    border = "_" * (len(message) + 2)
    return (
        f" {border}\n< {message} >\n {'-' * (len(message) + 2)}\n"
        f"       \\\n" + ansi(indent="        ")
    )
