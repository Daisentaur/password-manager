# Changelog

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
