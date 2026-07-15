"""Interactive TUI, launched by running `pw` with no arguments.

Theme palettes copied from tuxedo (github.com/webstonehq/tuxedo,
src/theme.rs); "muted-slate" is the default. `t` opens the theme picker,
and Textual's own built-in themes are available there too.
"""

import os

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen, Screen
from textual.theme import Theme
from textual.widgets import DataTable, Footer, Input, Label, Static

from . import vault
from .cli import VAULT_PATH, generate, to_clipboard

THEME_FILE = os.path.expanduser("~/.local/share/pw-manager/theme")

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
            yield Label("pw-manager", id="unlock-title")
            yield Input(password=True, placeholder="master password", id="master")
            yield Static("", id="unlock-error")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one("#unlock-error", Static).update("unlocking…")
        try:
            self.app.entries = vault.load(VAULT_PATH, event.value)
        except vault.VaultError as e:
            self.query_one("#unlock-error", Static).update(str(e))
            self.query_one("#master", Input).clear()
            return
        self.app.master = event.value
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
        Binding("t", "app.change_theme", "theme"),
        Binding("escape", "clear_search", show=False),
        Binding("q", "quit", "quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Input(placeholder="/ to search", id="search")
        yield DataTable(id="table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("name", "username", "notes")
        self.refresh_table()
        table.focus()

    def refresh_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        term = self.query_one("#search", Input).value.lower()
        for name, e in sorted(self.app.entries.items()):
            if (
                term in name.lower()
                or term in e["user"].lower()
                or term in e.get("notes", "").lower()
            ):
                table.add_row(name, e["user"], e.get("notes", ""), key=name)

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
            self.notify("no clipboard tool (install wl-clipboard)", severity="error")

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

    def action_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_clear_search(self) -> None:
        search = self.query_one("#search", Input)
        search.clear()
        self.query_one(DataTable).focus()


class PwApp(App):
    TITLE = "pw-manager"

    # Colors come from $theme-variables so every theme applies everywhere;
    # widgets without rules here (table, footer, toasts) use Textual's own
    # theme-aware defaults.
    CSS = """
    #unlock-box {
        align: center middle;
        width: 44;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: round $panel;
    }
    #unlock-title {
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


def main() -> None:
    PwApp().run()


if __name__ == "__main__":
    main()
