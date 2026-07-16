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


def rich_text() -> Text:
    """The knight as a Rich Text, for Textual widgets."""
    text = Text()
    for row in _pixel_pairs():
        for top, bottom in row:
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


def says(message: str) -> str:
    """Cowsay, but it's a knight."""
    border = "_" * (len(message) + 2)
    return (
        f" {border}\n< {message} >\n {'-' * (len(message) + 2)}\n"
        f"       \\\n" + ansi(indent="        ")
    )
