"""CLI for the vault. Installed as the `paladin` command."""

import argparse
import csv
import getpass
import os
import secrets
import shutil
import string
import subprocess
import sys
from urllib.parse import urlparse

from . import vault

VAULT_PATH = os.environ.get(
    "PW_VAULT", os.path.expanduser("~/.local/share/pw-manager/vault")
)


def generate(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def to_clipboard(text: str) -> bool:
    # ponytail: no auto-clear timer; clear manually or copy something else over it
    for cmd in (["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "-b"]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, input=text.encode(), check=True)
            return True
    return False


def ask_master(confirm: bool = False) -> str:
    pw = getpass.getpass("master password: ")
    if confirm:
        if getpass.getpass("confirm master password: ") != pw:
            sys.exit("passwords do not match")
        if len(pw) < 8:
            sys.exit("master password must be at least 8 characters")
    return pw


def cmd_init(args):
    if os.path.exists(VAULT_PATH):
        sys.exit(f"vault already exists at {VAULT_PATH}")
    os.makedirs(os.path.dirname(VAULT_PATH), exist_ok=True)
    vault.save(VAULT_PATH, ask_master(confirm=True), {})
    if sys.stdout.isatty():
        from . import logo

        print(logo.says(f"empty vault created at {VAULT_PATH}"))
    else:
        print(f"empty vault created at {VAULT_PATH}")


def cmd_about(args):
    from importlib.metadata import PackageNotFoundError, version

    try:
        v = version("basic-password-manager")
    except PackageNotFoundError:
        v = "dev"  # running from source without an install
    from . import logo

    print(logo.ascii_art())
    print(f"The Paladin ⚔ v{v}")
    print("your passwords, guarded locally — no browser, no cloud, no mercy")
    print("https://github.com/Daisentaur/password-manager")


def cmd_add(args):
    master = ask_master()
    entries = vault.load(VAULT_PATH, master)
    if args.name in entries and input(f"'{args.name}' exists, overwrite? [y/N] ").lower() != "y":
        sys.exit("aborted")
    user = input("username: ")
    if args.gen:
        pw = generate()
        print("generated a 20-character password")
    else:
        pw = getpass.getpass("password: ")
    notes = input("notes (optional): ")
    entries[args.name] = {"user": user, "pw": pw, "notes": notes}
    vault.save(VAULT_PATH, master, entries)
    print(f"stored '{args.name}'")
    if args.gen and to_clipboard(pw):
        print("password copied to clipboard")


def cmd_get(args):
    entries = vault.load(VAULT_PATH, ask_master())
    if args.name not in entries:
        sys.exit(f"no entry '{args.name}' — try 'ls'")
    e = entries[args.name]
    print(f"username: {e['user']}")
    if e.get("notes"):
        print(f"notes:    {e['notes']}")
    if to_clipboard(e["pw"]):
        print("password copied to clipboard")
    else:
        # no clipboard tool found; showing it is the only option left
        print(f"password: {e['pw']}")


def cmd_edit(args):
    """Per-field update; Enter keeps the shown current value."""
    master = ask_master()
    entries = vault.load(VAULT_PATH, master)
    if args.name not in entries:
        sys.exit(f"no entry '{args.name}' — try 'ls'")
    e = entries[args.name]
    user = input(f"username [{e['user']}]: ") or e["user"]
    pw = getpass.getpass("password (empty = keep current): ") or e["pw"]
    notes = input(f"notes [{e.get('notes', '')}]: ") or e.get("notes", "")
    entries[args.name] = {"user": user, "pw": pw, "notes": notes}
    vault.save(VAULT_PATH, master, entries)
    print(f"updated '{args.name}'")


def cmd_passwd(args):
    """Change the master password: decrypt with old, re-encrypt with new."""
    entries = vault.load(VAULT_PATH, ask_master())
    print("choose a new master password")
    new = getpass.getpass("new master password: ")
    if getpass.getpass("confirm new master password: ") != new:
        sys.exit("passwords do not match")
    if len(new) < 8:
        sys.exit("master password must be at least 8 characters")
    vault.save(VAULT_PATH, new, entries)
    print("master password changed (old one is now useless)")


def cmd_ls(args):
    entries = vault.load(VAULT_PATH, ask_master())
    for name in sorted(entries):
        print(name)
    if not entries:
        print("(vault is empty)")


def cmd_rm(args):
    master = ask_master()
    entries = vault.load(VAULT_PATH, master)
    if args.name not in entries:
        sys.exit(f"no entry '{args.name}'")
    del entries[args.name]
    vault.save(VAULT_PATH, master, entries)
    print(f"removed '{args.name}'")


def cmd_gen(args):
    print(generate(args.length))


def cmd_find(args):
    """Every word of the query must appear somewhere in name/username/notes.
    Deliberately not over passwords: a password fragment typed as a CLI
    argument lands in shell history (the TUI search does cover passwords)."""
    entries = vault.load(VAULT_PATH, ask_master())
    words = args.term.lower().split()
    hits = {
        name: e
        for name, e in sorted(entries.items())
        if all(w in f"{name} {e['user']} {e.get('notes', '')}".lower() for w in words)
    }
    for name, e in hits.items():
        print(f"{name}  ({e['user']})")
    if not hits:
        sys.exit(f"nothing matches '{args.term}'")


def import_csv(csv_file: str, entries: dict) -> int:
    """Merge a browser CSV export (Chrome: name,url,username,password /
    Firefox: url,...) into entries. Returns how many were added."""
    added = 0
    with open(csv_file, newline="") as f:
        for row in csv.DictReader(f):
            name = row.get("name") or urlparse(row.get("url", "")).netloc
            pw = row.get("password")
            if not name or not pw:
                continue
            entries[name] = {"user": row.get("username", ""), "pw": pw, "notes": ""}
            added += 1
    return added


def cmd_import(args):
    master = ask_master()
    entries = vault.load(VAULT_PATH, master)
    added = import_csv(args.csv_file, entries)
    vault.save(VAULT_PATH, master, entries)
    print(f"imported {added} entries — now delete {args.csv_file} securely")


def main():
    p = argparse.ArgumentParser(
        description="local encrypted password manager (run bare for the TUI)"
    )
    sub = p.add_subparsers(dest="command")

    sub.add_parser("init", help="create a new empty vault")
    a = sub.add_parser("add", help="add or update an entry")
    a.add_argument("name")
    a.add_argument("--gen", action="store_true", help="generate the password")
    g = sub.add_parser("get", help="copy an entry's password to clipboard")
    g.add_argument("name")
    e = sub.add_parser("edit", help="update an entry field by field")
    e.add_argument("name")
    sub.add_parser("passwd", help="change the master password")
    sub.add_parser("ls", help="list entry names")
    r = sub.add_parser("rm", help="delete an entry")
    r.add_argument("name")
    n = sub.add_parser("gen", help="print a random password")
    n.add_argument("-l", "--length", type=int, default=20)
    f = sub.add_parser("find", help="search entry names, usernames, notes")
    f.add_argument("term")
    i = sub.add_parser("import", help="import a browser CSV export")
    i.add_argument("csv_file")
    sub.add_parser("about", help="meet the knight")

    args = p.parse_args()
    if args.command is None:
        from . import tui  # imported lazily: textual is heavy, subcommands skip it

        tui.main()
        return
    try:
        globals()[f"cmd_{args.command}"](args)
    except vault.VaultError as e:
        sys.exit(str(e))
    except KeyboardInterrupt:
        sys.exit("\naborted")


if __name__ == "__main__":
    main()
