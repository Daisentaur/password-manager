# The Paladin ⚔ — the friendly guide

This is for you if you've never used a password manager or a terminal much.
No jargon, promise. (The technical version lives in [README.md](README.md).)

## What this is

A locked box on your own computer that remembers all your passwords, so you
only ever have to remember **one**: the master password that opens the box.
Nothing is sent anywhere — no cloud, no account, no company. The box is a
single scrambled file on your disk that is unreadable without your master
password.

## The one rule

**If you forget the master password, everything in the box is lost. Nobody
can reset it — not you, not us, nobody.** That's not a bug; it's what makes
the box safe.

So pick a master password that is long and memorable. Four random words like
`corridor-velvet-mango-thunder` beat something short and cryptic — easier for
you, brutally hard for a computer to guess.

## One-time setup

Open a terminal and run:

```
pipx install basic-password-manager
pw init
```

It asks you to choose your master password (typing is invisible — that's
normal, type anyway), then confirms it. Done: you have an empty vault.

## Everyday use

**Save a password** (it will ask for your master password first, then the details):

```
pw add netflix
```

Better: let it invent a strong password for you, so it's not one you reuse:

```
pw add netflix --gen
```

**Get a password back:**

```
pw get netflix
```

It shows the username and silently copies the password — go paste it
(Ctrl+V) into the login page. It's never displayed on screen. cause if you're a windows user just having somethign on your screen isn't safe sometimes.

**Can't remember what you called something?**

```
pw ls            (shows every name in the box)
pw find bank     (searches names, usernames, and your notes)
```

**Change a stored password** (say, after a website makes you reset it):

```
pw edit netflix
```

It shows each detail and asks what to change — just press Enter to keep
something as it is.

**Change your master password:**

```
pw passwd
```

You need the current one to do this — it re-locks the whole box with the new
one. (This is *changing* it, not recovering it — a forgotten master password
is still gone for good.) In the visual interface, press `ctrl+p` and type
"master" to find the same thing.

**Store things that aren't passwords** — WiFi keys, recovery codes, a PIN:
run `pw add wifi-home` and put the secret in the password prompt or the
notes.

## Moving your passwords out of the browser

1. In Chrome: Settings → Passwords → Export. In Firefox: Logins → Export.
   Either way you get a file, usually `passwords.csv`.
2. Run: `pw import passwords.csv` — or in the visual interface, press
   `ctrl+p`, type "import", and give it the file's location.
3. **Delete that file immediately** — it contains every password unprotected:
   `shred -u passwords.csv`
4. In the browser settings, turn off "offer to save passwords" and delete the
   saved ones.

## Keeping it safe

- The vault makes its own automatic backup (`vault.bak`) every time it
  changes, so one mistake is always undoable.
- Once a month, copy the vault file somewhere else (USB stick, another
  computer). It's safe to store anywhere — it's gibberish without your
  master password:

  ```
  cp ~/.local/share/pw-manager/vault /wherever/you/like/
  ```

## When something goes wrong

| What you see | What it means |
|---|---|
| "wrong master password" | Almost always a typo — try again slowly |
| "no vault at ..." | You haven't run `pw init` yet |
| The password prints on screen instead of copying | Install a clipboard tool: `sudo apt install wl-clipboard` |
| It thinks for a second before answering | Normal — that pause is the lock being hard to pick |

More detail in the README's troubleshooting section.

## The visual interface

Don't want to remember commands? Just run `pw` with nothing after it. It asks
for your master password, then shows all your entries in a table:

- **type `/`** and start typing to filter the list as you type — word
  order doesn't matter and half-remembered middles are fine ("count bank"
  finds "sbi-bank / my-account"); it even matches inside the passwords
  themselves, for when all you remember is what you typed on that site.
  What matched lights up in the accent color
- **arrow keys** move, **Enter** copies the selected password to the clipboard
- **n** adds a new entry (leave the password box empty and it invents a
  strong one for you)
- **e** edits the selected entry — everything is prefilled; leave the
  password box empty to keep the old password
- **d** deletes the selected entry (asks first)
- **t** opens the theme picker — pick with arrows, Enter applies, and your
  choice is remembered next time
- **q** quits

Every key is also listed in the bar at the bottom of the screen, so there's
nothing to memorize.
