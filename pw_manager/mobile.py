"""`paladin mobile`: serve the vault to your phone over an HTTPS tunnel.

The phone gets one self-contained page with the *encrypted* vault embedded.
The master password is typed on the phone and the key is derived and the
vault decrypted entirely in the phone's browser — the laptop, the tunnel,
and the network only ever carry ciphertext.
"""

import base64
import hashlib
import http.server
import os
import platform
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.request
from importlib.resources import files

from . import crypto, logo, vault

# Pinned so the binary is reproducible and the checksums below are meaningful.
CF_VERSION = "2026.7.2"
CF_SHA256 = {
    "cloudflared-linux-amd64": "ec905ea7b7e327ff8abdde8cb64697a2152de74dbcdbf6aec9db8364eb3886cd",
    "cloudflared-linux-arm64": "405df476437e027fc6d18729a5a77155c0a33a6082aeee60a799a688f3052e66",
    "cloudflared-darwin-amd64.tgz": "4ee0d3b48a990a2f9b5faec5838f73ec1f400aa8e0a4864be576adfafec406cb",
    "cloudflared-darwin-arm64.tgz": "2086e51c61d6565781d84117a5007d0c826d03ffdc74acb91c08c167f9f8cd7c",
    "cloudflared-windows-amd64.exe": "cdb5d4432f6ae1595654a692a51308b69d2bf7af961f5578d9391837cf072df9",
}
TOKEN_TTL = 30 * 24 * 3600  # 30 days


class MobileError(Exception):
    """Something stopped the mobile session, with a human message."""


def _data_dir() -> str:
    d = os.path.dirname(
        os.environ.get("PW_VAULT", os.path.expanduser("~/.local/share/pw-manager/vault"))
    )
    os.makedirs(d, exist_ok=True)
    return d


def _asset_name() -> str:
    system = platform.system()
    arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "amd64"
    if system == "Linux":
        return f"cloudflared-linux-{arch}"
    if system == "Darwin":
        return f"cloudflared-darwin-{arch}.tgz"
    if system == "Windows":
        return f"cloudflared-windows-{arch}.exe"
    raise MobileError(f"no cloudflared build for {system}; install it manually")


def cloudflared_path() -> str:
    """Find cloudflared on PATH, or in our cache, or fetch the pinned official
    binary (checksum-verified) into the cache."""
    found = shutil.which("cloudflared")
    if found:
        return found
    cache = os.path.join(_data_dir(), "cloudflared")
    if os.path.exists(cache):
        return cache

    asset = _asset_name()
    url = f"https://github.com/cloudflare/cloudflared/releases/download/{CF_VERSION}/{asset}"
    print(f"fetching cloudflared {CF_VERSION} (one time)…", file=sys.stderr)
    try:
        with urllib.request.urlopen(url) as r:
            blob = r.read()
    except OSError as e:
        raise MobileError(f"couldn't download cloudflared ({e}); check your connection")
    if hashlib.sha256(blob).hexdigest() != CF_SHA256[asset]:
        raise MobileError("cloudflared checksum mismatch — refusing to run it")

    if asset.endswith(".tgz"):
        with tempfile.TemporaryDirectory() as td:
            tgz = os.path.join(td, asset)
            open(tgz, "wb").write(blob)
            with tarfile.open(tgz) as t:
                member = next(m for m in t.getmembers() if m.name.endswith("cloudflared"))
                t.extract(member, td)
                shutil.move(os.path.join(td, member.name), cache)
    else:
        open(cache, "wb").write(blob)
    os.chmod(cache, os.stat(cache).st_mode | stat.S_IEXEC | stat.S_IRUSR)
    return cache


def _load_token() -> str:
    """A path segment that rotates every 30 days (matters in --url mode; the
    quick tunnel URL is already random)."""
    path = os.path.join(_data_dir(), "mobile-token")
    try:
        created, token = open(path).read().split(":", 1)
        if time.time() - float(created) < TOKEN_TTL:
            return token.strip()
    except (OSError, ValueError):
        pass
    token = secrets.token_urlsafe(16)
    with open(path, "w") as f:
        f.write(f"{time.time()}:{token}")
    return token


def _theme_colors() -> dict:
    """Resolve the theme saved by the TUI to a full color palette. The page
    is baked with whatever theme is current when the QR is generated."""
    default = {
        "background": "#1A1D23", "surface": "#1F232B", "panel": "#2A2F38",
        "foreground": "#C8CCD4", "primary": "#8AA9C9", "warning": "#D3B06A",
        "error": "#E07A7A", "text-muted": "#6B7280",
    }
    try:
        from textual.theme import BUILTIN_THEMES

        from .tui import THEME_FILE, TUXEDO_THEMES

        name = open(THEME_FILE).read().strip()
        registry = {t.name: t for t in TUXEDO_THEMES}
        registry.update(BUILTIN_THEMES)
        cs = registry[name].to_color_system().generate()
        # ANSI themes resolve to names like 'ansi_blue', not hex — the browser
        # can't use those and the knight can't tint from them, so fall back
        if not str(cs.get("background", "")).startswith("#"):
            return default
        return {**default, **cs}
    except (OSError, KeyError, ImportError):
        return default


def _build_page(raw_vault: bytes) -> bytes:
    salt = raw_vault[4 : 4 + crypto.SALT_LEN]
    blob = raw_vault[4 + crypto.SALT_LEN :]  # nonce + ciphertext+tag
    argon_js = files("pw_manager.web").joinpath("argon2.umd.min.js").read_text()
    template = files("pw_manager.web").joinpath("page.html").read_text()
    c = _theme_colors()
    knight = logo.svg(tint=c["primary"], accent=c.get("warning", c["primary"]))
    return (
        template.replace("/*__ARGON2__*/", argon_js)
        .replace("__KNIGHT__", f'<div id="knight">{knight}</div>')
        .replace("__C_BG__", c["background"])
        .replace("__C_SURFACE__", c["surface"])
        .replace("__C_PANEL__", c["panel"])
        .replace("__C_FG__", c["foreground"])
        .replace("__C_PRIMARY__", c["primary"])
        .replace("__C_ERROR__", c["error"])
        .replace("__C_DIM__", c.get("text-muted", "#6B7280"))
        .replace("__SALT__", base64.b64encode(salt).decode())
        .replace("__BLOB__", base64.b64encode(blob).decode())
        .replace("__NONCE_LEN__", str(crypto.NONCE_LEN))
        .replace("__TIME__", "3")
        .replace("__MEM_KIB__", str(64 * 1024))
        .replace("__PAR__", "4")
        .replace("__KEYLEN__", str(crypto.KEY_LEN))
    ).encode()


def _serve(vault_path: str, token: str, port: int = 0, on_fetch=None) -> http.server.HTTPServer:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.rstrip("/") != f"/{token}":
                self.send_error(404)
                return
            # rebuild per request so edits made on the laptop show on refresh
            page = _build_page(open(vault_path, "rb").read())
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(page)
            if on_fetch:
                on_fetch()

        def log_message(self, *a):
            pass  # fetch visibility goes through on_fetch instead

    # threading server: a phone holding a connection open can't stall shutdown
    return http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)


def _start_tunnel(cf: str, port: int) -> tuple[subprocess.Popen, str]:
    proc = subprocess.Popen(
        [cf, "tunnel", "--url", f"http://127.0.0.1:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    url_re = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
    deadline = time.time() + 30
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        m = url_re.search(line)
        if m:
            return proc, m.group(0)
    proc.terminate()
    raise MobileError("cloudflared didn't produce a tunnel URL in time")


def start_session(
    vault_path: str, stable_url: str | None = None, port: int = 0, on_fetch=None
) -> tuple[http.server.HTTPServer, subprocess.Popen | None, str]:
    """Start server (+ tunnel unless a stable URL is configured). Returns
    (server, tunnel_process_or_None, full_url)."""
    if not os.path.exists(vault_path):
        raise MobileError(f"no vault at {vault_path} — run 'paladin init' first")

    # env defaults so `paladin mobile` alone can serve your own subdomain
    stable_url = stable_url or os.environ.get("PALADIN_MOBILE_URL")
    if stable_url and not port:
        port = int(os.environ.get("PALADIN_MOBILE_PORT", "8787"))

    token = _load_token()
    server = _serve(vault_path, token, port, on_fetch=on_fetch)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    proc = None
    if stable_url:
        base = stable_url.rstrip("/")  # your reverse proxy points here → 127.0.0.1:port
    else:
        try:
            cf = cloudflared_path()
            proc, base = _start_tunnel(cf, port)
        except BaseException:
            server.shutdown()
            raise
    return server, proc, f"{base}/{token}"


def stop_session(server, proc) -> None:
    """Tunnel first (no new requests), then server; a second Ctrl+C during
    cleanup must never produce a traceback."""
    try:
        if proc:
            proc.terminate()
        server.shutdown()
    except KeyboardInterrupt:
        pass


def run(vault_path: str, stable_url: str | None = None, port: int = 0) -> None:
    def fetched():
        print(f"  vault page served to a device at {time.strftime('%H:%M:%S')}")

    print("\n  creating your secure link…", flush=True)
    server, proc, url = start_session(vault_path, stable_url, port, on_fetch=fetched)

    import qrcode

    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    print("\n  scan with your phone camera:\n")
    qr.print_ascii(invert=True)
    print(f"\n  {url}\n")
    print("  the master password is typed on your phone; only ciphertext leaves this machine.")
    print("  every page load is logged below — Ctrl+C to stop the session.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nsession ended.")
    finally:
        stop_session(server, proc)
