"""Interactive TUI, launched by running `pw` with no arguments.

Theme palettes copied from tuxedo (github.com/webstonehq/tuxedo,
src/theme.rs); "muted-slate" is the default. `t` opens the theme picker,
and Textual's own built-in themes are available there too.
"""

import csv
import os
import time

from rich.style import Style
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import DiscoveryHit, Hit, Hits, Provider
from textual.containers import Vertical
from textual.screen import ModalScreen, Screen
from textual.theme import Theme
from textual.widgets import DataTable, Footer, Input, Label, OptionList, Static
from textual.widgets.option_list import Option

from . import logo, vault
from .cli import VAULT_PATH, generate, import_csv, to_clipboard

THEME_FILE = os.path.expanduser("~/.local/share/pw-manager/theme")

APP_NAME = "The Paladin"
APP_ICON = "⚔"

TUXEDO_THEMES = [
    Theme(
        name="muted-slate",
        primary="#8aa9c9",
        secondary="#7fb3a8",
        accent="#9a8fc4",
        foreground="#c8ccd4",
        background="#1a1d23",
        surface="#1f232b",
        panel="#252a33",
        success="#7aa67a",
        warning="#d4b06a",
        error="#e07a7a",
        dark=True,
    ),
    Theme(
        name="dawn",
        primary="#a35d3a",
        secondary="#3a7a6a",
        accent="#7a4a8a",
        foreground="#3d3528",
        background="#faf6f0",
        surface="#f3ede2",
        panel="#ede2cc",
        success="#5a7a3a",
        warning="#a3722a",
        error="#b8483a",
        dark=False,
    ),
    Theme(
        name="matrix",
        primary="#9fff9f",
        secondary="#7fcc7f",
        accent="#cf9fff",
        foreground="#7fcc7f",
        background="#0a120a",
        surface="#0f1a0f",
        panel="#101c10",
        success="#9fff9f",
        warning="#ffd66e",
        error="#ff8c8c",
        dark=True,
    ),
]


class UnlockScreen(Screen):
    """Master password prompt shown before anything else."""

    def compose(self) -> ComposeResult:
        with Vertical(id="unlock-box"):
            yield Static(id="unlock-logo")
            yield Label(f"{APP_ICON} {APP_NAME}", id="unlock-title")
            yield Input(password=True, placeholder="master password", id="master")
            yield Static("", id="unlock-error")

    def on_mount(self) -> None:
        self._paint_logo()
        self.app.theme_changed_signal.subscribe(self, self._paint_logo)

    def _paint_logo(self, _theme: Theme | None = None) -> None:
        theme = self.app.current_theme
        self.query_one("#unlock-logo", Static).update(
            logo.rich_text(tint=theme.primary, accent=theme.warning or theme.primary)
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one("#unlock-error", Static).update("unlocking…")
        try:
            self.app.entries = vault.load(VAULT_PATH, event.value)
        except vault.VaultError as e:
            self.query_one("#unlock-error", Static).update(str(e))
            self.query_one("#master", Input).clear()
            return
        self.app.master = event.value
        # stop repainting the (now-hidden) unlock knight on every theme change
        self.app.theme_changed_signal.unsubscribe(self)
        self.app.push_screen(MainScreen())


class EntryModal(ModalScreen):
    """Add or edit an entry. Empty password = generate (add) / keep current (edit)."""

    BINDINGS = [Binding("escape", "dismiss", "cancel")]

    def __init__(self, name: str = "", entry: dict | None = None) -> None:
        super().__init__()
        self.initial_name = name
        self.entry = entry or {}

    def compose(self) -> ComposeResult:
        editing = bool(self.entry)
        with Vertical(classes="modal-box"):
            yield Label("edit entry" if editing else "new entry", classes="modal-title")
            yield Input(value=self.initial_name, placeholder="name (e.g. github)", id="e-name")
            yield Input(value=self.entry.get("user", ""), placeholder="username", id="e-user")
            yield Input(
                password=True,
                placeholder="password (empty = keep current)" if editing else "password (empty = generate)",
                id="e-pw",
            )
            yield Input(value=self.entry.get("notes", ""), placeholder="notes (optional)", id="e-notes")
            yield Static("enter saves · esc cancels", classes="modal-hint")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = self.query_one("#e-name", Input).value.strip()
        if not name:
            self.query_one("#e-name", Input).focus()
            return
        self.dismiss(
            {
                "name": name,
                "user": self.query_one("#e-user", Input).value,
                "pw": self.query_one("#e-pw", Input).value or self.entry.get("pw") or generate(),
                "notes": self.query_one("#e-notes", Input).value,
            }
        )


class ImportModal(ModalScreen):
    """Ask for the path of a browser CSV export."""

    BINDINGS = [Binding("escape", "dismiss", "cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Label("import browser CSV", classes="modal-title")
            yield Input(placeholder="path to export, e.g. ~/Downloads/passwords.csv", id="i-path")
            yield Static("enter imports · esc cancels", classes="modal-hint")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.value.strip():
            self.dismiss(os.path.expanduser(event.value.strip()))


def _qr_text(url: str, primary: str) -> tuple[Text, int]:
    """The QR as half-block art: theme-colored modules on white, darkened
    until cameras can read it. Returns (text, width_in_cells) — the caller
    must give the widget exactly that width: a wrapped QR is a dead QR."""
    import qrcode

    rgb = logo._hex_rgb(primary) or (0, 0, 0)  # ansi themes → plain black QR
    r, g, b = rgb
    while (r + g + b) / 765 > 0.45:
        r, g, b = int(r * 0.8), int(g * 0.8), int(b * 0.8)
    dark, light = f"rgb({r},{g},{b})", "rgb(255,255,255)"

    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make()
    matrix = qr.get_matrix()
    if len(matrix) % 2:
        matrix.append([False] * len(matrix[0]))
    text = Text(no_wrap=True)
    for top, bottom in zip(matrix[::2], matrix[1::2]):
        for t, btm in zip(top, bottom):
            text.append("▀", Style(color=dark if t else light, bgcolor=dark if btm else light))
        text.append("\n")
    return text, len(matrix[0])


class MobileModal(ModalScreen):
    """Serve the vault to a phone without leaving the TUI. The session lives
    while this modal is open; Esc ends it."""

    BINDINGS = [Binding("escape", "dismiss", "stop session")]

    def __init__(self) -> None:
        super().__init__()
        self.server = None
        self.proc = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box", id="mobile-box"):
            yield Label("open on phone", classes="modal-title")
            yield Static("creating your secure link…", id="qr")
            yield Static("", id="mobile-url")
            yield Static("", id="mobile-status")
            yield Static("esc ends the session", classes="modal-hint")

    def on_mount(self) -> None:
        self.run_worker(self._start, thread=True)

    def _start(self) -> None:
        from . import mobile

        try:
            self.server, self.proc, url = mobile.start_session(
                VAULT_PATH, on_fetch=self._on_fetch
            )
        except Exception as e:  # show any failure in the modal, don't die silently
            self.app.call_from_thread(
                self.query_one("#qr", Static).update, f"couldn't start: {e}"
            )
            return
        self.app.call_from_thread(self._show_qr, url)

    def _show_qr(self, url: str) -> None:
        qr, width = _qr_text(url, self.app.current_theme.primary)
        widget = self.query_one("#qr", Static)
        widget.update(qr)
        # pin every width to the QR's real size — auto-layout wrapping a QR
        # scrambles the modules and kills scannability
        widget.styles.width = width
        for wid in ("#mobile-url", "#mobile-status"):
            self.query_one(wid, Static).styles.width = width
        self.query_one("#mobile-box").styles.width = width + 6  # padding + border
        self.query_one("#mobile-url", Static).update(url)

    def _on_fetch(self) -> None:
        self.app.call_from_thread(
            self.query_one("#mobile-status", Static).update,
            f"vault page served to a device at {time.strftime('%H:%M:%S')}",
        )

    def on_unmount(self) -> None:
        from . import mobile

        if self.server:
            mobile.stop_session(self.server, self.proc)


class PasswdModal(ModalScreen):
    """Change the master password. Asks for the current one again so a
    walked-up-to unlocked session can't lock the real owner out."""

    BINDINGS = [Binding("escape", "dismiss", "cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Label("change master password", classes="modal-title")
            yield Input(password=True, placeholder="current master password", id="p-current")
            yield Input(password=True, placeholder="new master password (8+ chars)", id="p-new")
            yield Input(password=True, placeholder="confirm new master password", id="p-confirm")
            yield Static("enter saves · esc cancels", classes="modal-hint")
            yield Static("", id="p-error")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        current = self.query_one("#p-current", Input).value
        new = self.query_one("#p-new", Input).value
        error = self.query_one("#p-error", Static)
        if current != self.app.master:
            error.update("current master password is wrong")
            return
        if len(new) < 8:
            error.update("new master password must be at least 8 characters")
            return
        if new != self.query_one("#p-confirm", Input).value:
            error.update("new passwords do not match")
            return
        self.dismiss(new)


class ThemeModal(ModalScreen):
    """Theme picker: cursor starts on the current theme, moving it previews
    the theme live, Enter keeps it, Esc reverts to what you had."""

    BINDINGS = [Binding("escape", "cancel", "cancel")]

    def __init__(self) -> None:
        super().__init__()
        self.original = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box", id="theme-box"):
            yield Label("theme", classes="modal-title")
            yield OptionList(id="theme-list")
            yield Static("↑↓ preview · enter keeps · esc cancels", classes="modal-hint")

    def on_mount(self) -> None:
        self.original = self.app.theme
        names = sorted(self.app.available_themes)
        option_list = self.query_one(OptionList)
        for name in names:
            label = f"{name}  ✓" if name == self.original else name
            option_list.add_option(Option(label, id=name))
        option_list.highlighted = names.index(self.original)  # start on current

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if event.option.id:
            self.app.theme = event.option.id  # live preview

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id:
            self.app.theme = event.option.id  # commit (persists via theme signal)
        self.dismiss()

    def action_cancel(self) -> None:
        self.app.theme = self.original  # revert the preview
        self.dismiss()


class ConfirmModal(ModalScreen):
    """y/n confirmation."""

    BINDINGS = [
        Binding("y", "yes", "yes"),
        Binding("n,escape", "no", "no"),
    ]

    def __init__(self, question: str) -> None:
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Label(self.question, classes="modal-title")
            yield Static("y confirms · n cancels", classes="modal-hint")

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)


class MainScreen(Screen):
    BINDINGS = [
        Binding("enter", "copy", "copy password", priority=True),
        Binding("n", "new", "new entry"),
        Binding("e", "edit", "edit"),
        Binding("d", "delete", "delete"),
        Binding("slash", "search", "search"),
        Binding("t", "theme", "theme"),
        Binding("escape", "clear_search", show=False),
        Binding("q", "quit", "quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Static(f" {APP_ICON} {APP_NAME}", id="topbar")
        yield Input(placeholder="/ to search", id="search")
        yield DataTable(id="table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("name", "username", "notes")
        self.refresh_table()
        table.focus()
        # match-highlight color comes from the theme, so repaint on switch
        self.app.theme_changed_signal.subscribe(self, self._on_theme_change)

    def _on_theme_change(self, _theme: Theme) -> None:
        self.refresh_table()

    @staticmethod
    def _highlight(value: str, words: list[str], style: str) -> Text:
        text = Text(value)
        low = value.lower()
        for w in words:
            start = 0
            while (i := low.find(w, start)) != -1:
                text.stylize(style, i, i + len(w))
                start = i + 1
        return text

    def refresh_table(self) -> None:
        """Every search word must appear somewhere in the entry — name,
        username, notes, or the password itself. Passwords are searched but
        never displayed, so matches there can't be highlighted (by design)."""
        table = self.query_one(DataTable)
        table.clear()
        words = self.query_one("#search", Input).value.lower().split()
        style = f"bold {self.app.current_theme.primary}"
        for name, e in sorted(self.app.entries.items()):
            hay = f"{name} {e['user']} {e.get('notes', '')} {e['pw']}".lower()
            if all(w in hay for w in words):
                table.add_row(
                    self._highlight(name, words, style),
                    self._highlight(e["user"], words, style),
                    self._highlight(e.get("notes", ""), words, style),
                    key=name,
                )

    def save(self) -> None:
        vault.save(VAULT_PATH, self.app.master, self.app.entries)

    def selected_name(self) -> str | None:
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return None
        return table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value

    def on_input_changed(self, event: Input.Changed) -> None:
        self.refresh_table()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one(DataTable).focus()

    def action_copy(self) -> None:
        name = self.selected_name()
        if name is None:
            return
        if to_clipboard(self.app.entries[name]["pw"]):
            self.notify(f"password for '{name}' copied", severity="information")
        else:
            self.notify(
                "no clipboard tool found (on Linux: install wl-clipboard)",
                severity="error",
            )

    def action_new(self) -> None:
        def done(entry: dict | None) -> None:
            if entry:
                name = entry.pop("name")
                self.app.entries[name] = entry
                self.save()
                self.refresh_table()
                self.notify(f"stored '{name}'")

        self.app.push_screen(EntryModal(), done)

    def action_edit(self) -> None:
        name = self.selected_name()
        if name is None:
            return

        def done(entry: dict | None) -> None:
            if not entry:
                return
            new_name = entry.pop("name")
            if new_name != name:
                if new_name in self.app.entries:
                    self.notify(f"'{new_name}' already exists", severity="error")
                    return
                del self.app.entries[name]
            self.app.entries[new_name] = entry
            self.save()
            self.refresh_table()
            self.notify(f"updated '{new_name}'")

        self.app.push_screen(EntryModal(name, dict(self.app.entries[name])), done)

    def action_delete(self) -> None:
        name = self.selected_name()
        if name is None:
            return

        def done(confirmed: bool | None) -> None:
            if confirmed:
                del self.app.entries[name]
                self.save()
                self.refresh_table()
                self.notify(f"removed '{name}'")

        self.app.push_screen(ConfirmModal(f"delete '{name}'?"), done)

    def action_theme(self) -> None:
        self.app.push_screen(ThemeModal())

    def action_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_clear_search(self) -> None:
        search = self.query_one("#search", Input)
        search.clear()
        self.query_one(DataTable).focus()


class VaultCommands(Provider):
    """Palette commands for the unlocked vault. Unlike Textual's built-in
    provider, the query matches descriptions too, not just titles."""

    @property
    def _commands(self):
        if not isinstance(self.screen, MainScreen):
            return []
        app = self.app
        return [
            ("Import browser CSV", "add every entry from a Chrome/Firefox password export", app._import_csv),
            ("Open on phone", "serve the vault to your phone over an HTTPS tunnel (QR code)", app._mobile),
            ("Change master password", "re-encrypt the vault under a new master password", app._change_master),
        ]

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for title, help_text, callback in self._commands:
            score = matcher.match(f"{title} {help_text}")
            if score > 0:
                yield Hit(score, matcher.highlight(title), callback, help=help_text)

    async def discover(self) -> Hits:
        for title, help_text, callback in self._commands:
            yield DiscoveryHit(title, callback, help=help_text)


class PwApp(App):
    TITLE = APP_NAME
    COMMANDS = App.COMMANDS | {VaultCommands}

    # Colors come from $theme-variables so every theme applies everywhere;
    # widgets without rules here (table, footer, toasts) use Textual's own
    # theme-aware defaults.
    CSS = """
    #topbar {
        height: 1;
        background: $panel;
        color: $primary;
        text-style: bold;
    }
    #unlock-box {
        align: center middle;
        width: 44;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: round $panel;
    }
    #unlock-logo {
        width: 100%;
        text-align: center;
        margin-bottom: 1;
    }
    #unlock-title {
        width: 100%;
        text-align: center;
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }
    #unlock-error {
        color: $error;
        margin-top: 1;
    }
    UnlockScreen {
        align: center middle;
    }
    Input {
        background: $surface;
        border: round $panel;
    }
    Input:focus {
        border: round $primary;
    }
    ModalScreen {
        align: center middle;
        background: $background 60%;
    }
    .modal-box {
        width: 52;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: round $primary;
    }
    #mobile-box {
        width: auto;
    }
    #mobile-url {
        color: $text-muted;
        margin-top: 1;
    }
    .modal-title {
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }
    .modal-hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.entries: dict = {}
        self.master: str = ""

    def on_mount(self) -> None:
        for theme in TUXEDO_THEMES:
            self.register_theme(theme)
        try:
            saved = open(THEME_FILE).read().strip()
        except OSError:
            saved = ""
        self.theme = saved if saved in self.available_themes else "muted-slate"
        self.theme_changed_signal.subscribe(self, self._remember_theme)
        self.push_screen(UnlockScreen())

    def _remember_theme(self, theme: Theme) -> None:
        os.makedirs(os.path.dirname(THEME_FILE), exist_ok=True)
        with open(THEME_FILE, "w") as f:
            f.write(theme.name)

    def _import_csv(self) -> None:
        def done(path: str | None) -> None:
            if not path:
                return
            try:
                added = import_csv(path, self.entries)
            except (OSError, csv.Error) as e:
                self.notify(str(e), severity="error")
                return
            vault.save(VAULT_PATH, self.master, self.entries)
            if isinstance(self.screen, MainScreen):
                self.screen.refresh_table()
            self.notify(f"imported {added} entries — delete the CSV securely")

        self.push_screen(ImportModal(), done)

    def _mobile(self) -> None:
        self.push_screen(MobileModal())

    def _change_master(self) -> None:
        def done(new: str | None) -> None:
            if new:
                self.master = new
                vault.save(VAULT_PATH, self.master, self.entries)
                self.notify("master password changed (old one is now useless)")

        self.push_screen(PasswdModal(), done)


def main() -> None:
    PwApp().run()


if __name__ == "__main__":
    main()
