"""Headless TUI checks using Textual's Pilot.

Run: ./venv/bin/python test_tui.py
"""

import asyncio
import os
import tempfile

d = tempfile.mkdtemp()
os.environ["PW_VAULT"] = os.path.join(d, "vault")

from pw_manager import vault  # noqa: E402

vault.save(
    os.environ["PW_VAULT"],
    "testmaster",
    {
        "github": {"user": "dt", "pw": "hunter2", "notes": "work"},
        "reddit": {"user": "dt-r", "pw": "sekrit", "notes": ""},
    },
)

import pw_manager.tui as tui_mod  # noqa: E402
from pw_manager.tui import MainScreen, PwApp, UnlockScreen, VaultCommands  # noqa: E402

tui_mod.THEME_FILE = os.path.join(d, "theme")  # never touch the real preference


async def run() -> None:
    app = PwApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, UnlockScreen)

        # wrong password stays on the unlock screen with an error
        app.screen.query_one("#master").value = "wrongpw"
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, UnlockScreen)
        assert "wrong master password" in str(app.screen.query_one("#unlock-error").render())

        # right password reaches the table
        app.screen.query_one("#master").value = "testmaster"
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, MainScreen)
        table = app.screen.query_one("#table")
        assert table.row_count == 2

        # multi-word search across fields, any order; highlight spans on matches
        from textual.coordinate import Coordinate

        search = app.screen.query_one("#search")
        search.value = "work dt"
        await pilot.pause()
        assert table.row_count == 1
        assert table.get_cell_at(Coordinate(0, 1)).spans, "expected highlight spans"

        # passwords are searched but never highlighted (they aren't displayed)
        search.value = "unter"
        await pilot.pause()
        assert table.row_count == 1
        assert not table.get_cell_at(Coordinate(0, 0)).spans
        search.value = ""
        await pilot.pause()

        # add entry via modal; empty password generates one
        await pilot.press("n")
        await pilot.pause()
        app.screen.query_one("#e-name").value = "bank"
        app.screen.query_one("#e-user").value = "dt-bank"
        await pilot.press("enter")
        await pilot.pause()
        assert table.row_count == 3
        assert len(vault.load(os.environ["PW_VAULT"], "testmaster")["bank"]["pw"]) == 20

        # edit: rename + keep password on empty field
        old_pw = vault.load(os.environ["PW_VAULT"], "testmaster")["bank"]["pw"]
        await pilot.press("e")
        await pilot.pause()
        app.screen.query_one("#e-name").value = "sbi-bank"
        app.screen.query_one("#e-user").value = "dt-sbi"
        await pilot.press("enter")
        await pilot.pause()
        saved = vault.load(os.environ["PW_VAULT"], "testmaster")
        assert "bank" not in saved and saved["sbi-bank"]["pw"] == old_pw

        # delete whatever the cursor sits on, with confirmation
        victim = app.screen.selected_name()
        await pilot.press("d")
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()
        assert victim not in vault.load(os.environ["PW_VAULT"], "testmaster")

        # palette provider offers the vault commands
        titles = [c[0] for c in VaultCommands(app.screen)._commands]
        assert titles == ["Import browser CSV", "Open on phone", "Change master password"]

        # master rotation: wrong current refused, correct one re-encrypts
        app._change_master()
        await pilot.pause()
        app.screen.query_one("#p-current").value = "WRONG"
        app.screen.query_one("#p-new").value = "newmaster99"
        app.screen.query_one("#p-confirm").value = "newmaster99"
        await pilot.press("enter")
        await pilot.pause()
        assert "wrong" in str(app.screen.query_one("#p-error").render())
        app.screen.query_one("#p-current").value = "testmaster"
        await pilot.press("enter")
        await pilot.pause()
        vault.load(os.environ["PW_VAULT"], "newmaster99")  # decrypts under new master

        # mobile modal: QR must render unwrapped at exactly its own width —
        # a wrapped QR is scrambled and unscannable (regression: 0.4.1)
        from pw_manager import mobile
        from pw_manager.tui import _qr_text

        # no network in tests: stub the session, we only test the rendering
        mobile.start_session = lambda *a, **k: (_ for _ in ()).throw(
            mobile.MobileError("stubbed in test")
        )
        app._mobile()
        await pilot.pause()
        url = "https://buyers-modes-instrumentation-dance.trycloudflare.com/uqO26mXxvBNf8Au1fMNGzg"
        app.screen._show_qr(url)
        await pilot.pause()
        qr_widget = app.screen.query_one("#qr")
        _, width = _qr_text(url, app.current_theme.primary)
        assert qr_widget.size.width == width
        lines = str(qr_widget.render()).strip("\n").split("\n")
        assert all(len(line) == width for line in lines), "QR lines wrapped/broken"
        await pilot.press("escape")
        await pilot.pause()

        # theme picker: current marked + preselected, preview on move,
        # esc reverts, enter commits + persists
        from textual.widgets import OptionList

        from pw_manager.tui import ThemeModal

        assert app.theme == "muted-slate"
        app.screen.action_theme()
        await pilot.pause()
        assert isinstance(app.screen, ThemeModal)
        ol = app.screen.query_one(OptionList)
        cur = ol.get_option_at_index(ol.highlighted)
        assert cur.id == "muted-slate" and "✓" in str(cur.prompt)
        await pilot.press("down")
        await pilot.pause()
        assert app.theme != "muted-slate", "cursor move should preview"
        await pilot.press("escape")
        await pilot.pause()
        assert app.theme == "muted-slate", "escape should revert the preview"

        # ANSI themes use color *names* not hex — previewing them must not
        # crash the knight-tinting (regression: 0.4.4 bricked launch)
        app.screen.action_theme()
        await pilot.pause()
        from textual.widgets import OptionList as _OL

        ol2 = app.screen.query_one(_OL)
        ansi_idx = next(
            i for i in range(ol2.option_count)
            if ol2.get_option_at_index(i).id in ("ansi-dark", "ansi-light")
        )
        ol2.highlighted = ansi_idx  # preview an ansi theme
        await pilot.pause()
        assert app.theme in ("ansi-dark", "ansi-light")  # applied, no crash
        await pilot.press("escape")
        await pilot.pause()

        app.screen.action_theme()
        await pilot.pause()
        await pilot.press("down")
        await pilot.pause()
        chosen = app.theme
        await pilot.press("enter")
        await pilot.pause()
        assert app.theme == chosen and open(tui_mod.THEME_FILE).read() == chosen

    app2 = PwApp()
    async with app2.run_test() as pilot:
        await pilot.pause()
        assert app2.theme == chosen  # fresh app remembers the committed choice

    print("TUI checks passed")


asyncio.run(run())
