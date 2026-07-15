# pw-manager

A local, encrypted password manager that lives in your terminal. No browser,
no cloud, no daemon — one encrypted file on disk and a small Python CLI in
front of it.

```
$ python pw.py get github
master password:
username: dt@example.com
password copied to clipboard
```

## Install

From PyPI (recommended — [pipx](https://pipx.pypa.io) keeps CLI tools isolated):

```bash
pipx install basic-password-manager    # or: pip install basic-password-manager
pw init
```

From source:

```bash
git clone https://github.com/Daisentaur/password-manager && cd password-manager
pipx install .
```

For development: `python3 -m venv venv && ./venv/bin/pip install -e .`

## Usage

Run `pw` with no arguments for the interactive TUI: unlock, then `/` to
filter, Enter to copy the selected password, `n` to add, `e` to edit,
`d` to delete, `t` to switch themes (persisted across runs), `q` to quit.
Rarer operations live in the command palette (`ctrl+p`), e.g. changing the
master password.
The bundled themes — muted-slate (default), dawn, matrix — are borrowed with
admiration from [tuxedo](https://github.com/webstonehq/tuxedo); Textual's
built-in themes are in the picker too.

Or use the subcommands:

| Command | What it does |
|---|---|
| `pw init` | create a new empty vault |
| `pw add github` | store an entry (prompts for username/password/notes) |
| `pw add github --gen` | same, but generates a strong random password |
| `pw get github` | copy the password to the clipboard, show the username |
| `pw edit github` | update an entry field by field (Enter keeps current) |
| `pw passwd` | change the master password |
| `pw ls` | list entry names |
| `pw rm github` | delete an entry |
| `pw find bank` | search entry names, usernames, and notes |
| `pw gen -l 32` | just print a random password |
| `pw import passwords.csv` | import a browser CSV export (see below) |

The vault lives at `~/.local/share/pw-manager/vault`. Set the `PW_VAULT`
environment variable to put it somewhere else.

The `notes` field takes any text you want kept secret alongside the password —
recovery codes, PINs, the answer to "what was your first pet".

### Moving off browser password storage

1. Export: Chrome → `chrome://password-manager/settings` → "Export passwords".
   Firefox → `about:logins` → ⋯ menu → "Export passwords". Both produce a CSV.
2. `pw import passwords.csv`
3. **Delete the CSV** — it is every password you own in plaintext:
   `shred -u passwords.csv`
4. Turn off saving and delete saved passwords in the browser settings.

## How it works

Three layers, ~120 lines total. Read them in this order:

### 1. `crypto.py` — password → key, key → ciphertext

An AES key must be 32 unpredictable bytes; your master password is neither.
**Argon2id** bridges the gap: `derive_key(password, salt)` always returns the
same 32 bytes for the same inputs — that's what makes unlocking possible.
It is deliberately slow and memory-hungry (64 MiB per guess), so an attacker
who steals the vault file can't brute-force short passwords on a GPU the way
they could against a plain hash.

The **salt** is 16 random bytes stored *unencrypted* in the vault file. It's
not a secret: its job is making your derived key unique so precomputed
attack tables are useless.

Encryption is **AES-256-GCM**, which is *authenticated*: decrypting with the
wrong key, or decrypting data that was modified by even one bit, fails loudly
instead of returning garbage. Each encryption uses a fresh random 12-byte
**nonce** (also stored unencrypted — also not a secret). The one iron rule of
GCM is that a (key, nonce) pair must never repeat, which is why it's random
every time.

### 2. `vault.py` — the file format

```
[4 bytes "PWV1"][16-byte salt][12-byte nonce][ciphertext...]
```

The ciphertext is just your entries as JSON, encrypted. Load = read →
derive key → decrypt → `json.loads`. Save = the reverse, with a fresh salt
and nonce, written to a temp file and atomically renamed so a crash mid-write
can't destroy the vault.

Your master password is never stored anywhere, in any form. "Wrong password"
is detected purely by GCM authentication failing.

### 3. `cli.py` and `tui.py` — the interfaces

Both are thin skins over the same two modules — `tui.py` (built with
[Textual](https://textual.textualize.io)) holds the decrypted entries in
memory for the session; the CLI re-derives the key per command.

argparse subcommands over the two modules above. Passwords are copied to the
clipboard (`wl-copy`/`xclip`/`xsel`, whichever exists) rather than printed,
so they don't sit in your terminal scrollback. `find` searches names,
usernames, and notes — deliberately *not* passwords, so fragments of secrets
never land in your shell history.

## Backups

Every save automatically keeps the previous version as `vault.bak` next to
the vault — one-step undo if a save goes wrong or you delete the wrong entry.

That protects against mistakes, not against the disk dying. For that, the
vault is one file: copy it anywhere — another disk, a USB stick, even
somewhere untrusted, since it's useless without the master password.

```bash
cp ~/.local/share/pw-manager/vault /some/backup/location/
```

## Troubleshooting

**"I forgot the master password."** The data is gone. Not "gone until support
resets it" — mathematically gone; that's the entire design. This is why you
keep the master password memorable (a long passphrase beats `Tr0ub4dor&3`)
and why backups protect you from file loss but not from forgetting.

**"wrong master password (or the vault file is corrupted)"** — 99% of the
time it's a typo'd password. If you're *certain* the password is right, the
file was damaged; restore the automatic backup
(`cp ~/.local/share/pw-manager/vault.bak ~/.local/share/pw-manager/vault`)
or an off-machine copy.

**Deleted or overwrote an entry by mistake** — the state before your last
save is in `vault.bak`; restore it as above. Only one generation is kept, so
do it before the next save.

**"not a vault file (bad magic bytes)"** — the file at the vault path isn't
one of ours (truncated, overwritten, or wrong path). Check `echo $PW_VAULT`
and restore from a backup.

**"no vault at ..."** — run `pw init`, or `PW_VAULT` points somewhere
unexpected.

**Password gets printed instead of copied** — no clipboard tool was found.
Install one: `sudo apt install wl-clipboard` (Wayland) or `xclip` (X11).

**Unlock feels slow (~1s)** — that's Argon2 doing its job; the delay is the
brute-force resistance. It's per-command, not per-keystroke.

**`MemoryError` from Argon2** — the KDF needs 64 MiB free; something is
eating your RAM.

**Import brought in junk entries** — browser CSVs include everything, even
ancient accounts. `pw rm <name>` the ones you don't want, or edit the CSV
before importing.

## Honest limitations

- No clipboard auto-clear: the password stays on the clipboard until you copy
  over it. Copy something else when you're done.
- While a command runs, decrypted data briefly exists in process memory.
  Malware already on your machine could read it — true of every password
  manager; the vault protects the file at rest, not a compromised machine.
- Single file, no sync. Syncing is your problem (and `cp` is a fine answer).

## Running the checks

```bash
./venv/bin/python test_vault.py
```
