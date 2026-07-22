# Changelog

## 0.4.4 — 2026-07-22
- The theme picker (`t`) now marks your current theme with a ✓ and starts
  the cursor on it, and previews each theme live as you arrow through —
  Enter keeps it, Esc reverts to what you had (like monkeytype's picker)

## 0.4.3 — 2026-07-20
- Fixed: copying only worked on Linux — the clipboard fallback chain never
  tried macOS's `pbcopy` or Windows's `clip` (both ship with the OS). Mac
  and Windows users were told to install wl-clipboard, which is a Linux
  tool. Now covered: wl-copy/xclip/xsel → pbcopy → clip → clip.exe (WSL)
- The "no clipboard tool" message no longer gives Linux advice to everyone

## 0.4.2 — 2026-07-19
- Fixed: the in-TUI QR could wrap inside its modal, scrambling the modules
  into an unscannable mess — the QR text is now unwrappable and the modal is
  pinned to the QR's exact width (with a regression test that measures every
  rendered line)
- The session URL now sits under the QR as selectable text instead of being
  baked into the QR block

## 0.4.1 — 2026-07-19
- Fixed: a phone holding its connection open could stall Ctrl+C on `paladin
  mobile`, and a second Ctrl+C during cleanup dumped a traceback — the server
  is now threaded and cleanup is interrupt-proof
- The TUI's "Open on phone" now shows the QR *inside* the app, in your theme's
  colors (auto-darkened so cameras can still read it) — no more dropping to
  the terminal; Esc ends the session
- Every page load is now logged live ("vault page served … at HH:MM:SS") in
  both the CLI and the TUI modal — you see every device that fetches your
  vault, and Ctrl+C/Esc ends the session on the spot
- "creating your secure link…" now prints immediately, so the tunnel
  start-up pause no longer looks like a hang

## 0.4.0 — 2026-07-19
- **`paladin mobile`**: open your vault on your phone with one QR scan. Serves
  a single page with the encrypted vault embedded over a throwaway HTTPS
  tunnel (cloudflared, auto-fetched and checksum-verified on first use); the
  master password is typed on the phone and the vault is decrypted in the
  phone's browser, so only ciphertext ever leaves your machine. Also in the
  TUI palette as "Open on phone".
- Page auto-locks after 5 minutes idle; nothing is stored on the phone.
- `--url https://vault.you.dev` serves at your own subdomain instead of a
  random tunnel (path auto-rotates every 30 days); `PALADIN_MOBILE_URL`
  makes it the default.
- The phone page wears your current TUI theme — colors and the pixel knight,
  baked in at QR-generation time.

## 0.3.0 — 2026-07-16
- **Breaking: the command is now `paladin`, not `pw`.** The knight has a
  name; the command should answer to it. After `pipx upgrade
  basic-password-manager`, type `paladin` (your vault, its location, and
  the `PW_VAULT` variable are all untouched)
- README and guide rewritten, now with demo gifs (recorded with vhs; the
  tape scripts live in `assets/tapes/`)

## 0.2.4 — 2026-07-16
- The unlock-screen knight now wears the active theme's colors (brightness
  kept, hue from the theme; sword guard takes the warning color) and
  re-tints live when you switch themes
- Top bar glyph is now ⚔ (the chess horse was a horse, not a knight)
- `pw about` renders the knight as monochrome ASCII art — each of his three
  appearances now has its own style: full color at `init`, theme livery at
  unlock, plain ASCII at `about`

## 0.2.3 — 2026-07-16
- The project now has a name: **The Paladin** (♞). Pixel-knight logo in the
  README, knight-glyph top bar in the TUI, same `basic-password-manager`
  install name, same `pw` command
- The knight renders as terminal pixel art: he announces your new vault on
  `pw init` (cowsay-style), guards the TUI unlock screen, and `pw about`
  summons him on demand

## 0.2.2 — 2026-07-16
- TUI: import a browser CSV straight from the command palette (`ctrl+p`)
- Search is now multi-word and forgiving: every word must match somewhere
  in an entry — any field, any position, any order, case-insensitive
- TUI search also matches inside passwords (never displayed or highlighted);
  CLI `find` still excludes them so fragments never land in shell history
- TUI: matched text is highlighted in the active theme's accent color
- Command palette: vault commands match on their descriptions, not just titles

## 0.2.1 — 2026-07-15
- Change the master password from the TUI command palette (`ctrl+p`);
  re-asks the current password so an unattended unlocked session can't
  lock you out

## 0.2.0 — 2026-07-15
- Interactive TUI: run bare `pw` to unlock, search live, copy with Enter,
  add/edit/delete entries
- Themes: muted-slate (default), dawn, matrix — palettes borrowed from
  tuxedo — plus Textual's built-ins; `t` opens the picker, choice persists
- CLI: `pw edit` (field-by-field update) and `pw passwd` (master rotation)

## 0.1.0 — 2026-07-15
- First release: Argon2id key derivation + AES-256-GCM encrypted vault
- CLI: init, add (`--gen`), get (clipboard), ls, rm, gen, find, import
  (browser CSV)
- Atomic saves, automatic `.bak` of the previous vault state
