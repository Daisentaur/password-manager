"""Self-checks for the mobile server plumbing (not the browser crypto — that's
proven separately with node). Run: ./venv/bin/python test_mobile.py
"""

import os
import time
import urllib.request

os.environ.setdefault("PW_VAULT", "/tmp/paladin-mobile-test/vault")

from pw_manager import mobile, vault  # noqa: E402

os.makedirs(os.path.dirname(os.environ["PW_VAULT"]), exist_ok=True)
vault.save(os.environ["PW_VAULT"], "pw", {"a": {"user": "u", "pw": "p", "notes": ""}})

# the page template is fully substituted — no placeholder survives
page = mobile._build_page(open(os.environ["PW_VAULT"], "rb").read())
for leftover in (b"__SALT__", b"__BLOB__", b"/*__ARGON2__*/", b"__NONCE_LEN__", b"__KEYLEN__"):
    assert leftover not in page, f"unsubstituted placeholder: {leftover}"
assert b"argon2id" in page and b"AES-GCM" in page

# token rotates only after the TTL
tok_path = os.path.join(mobile._data_dir(), "mobile-token")
if os.path.exists(tok_path):
    os.remove(tok_path)
t1 = mobile._load_token()
assert mobile._load_token() == t1, "token must be stable within its TTL"
with open(tok_path, "w") as f:
    f.write(f"{time.time() - mobile.TOKEN_TTL - 1}:{t1}")
assert mobile._load_token() != t1, "token must rotate after the TTL"

# the server serves the page only at /<token>, 404 everywhere else
token = mobile._load_token()
server = mobile._serve(os.environ["PW_VAULT"], token)
port = server.server_address[1]
import threading

threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/{token}") as r:
        body = r.read()
        assert r.status == 200 and b"argon2id" in body
        assert r.headers["Cache-Control"] == "no-store"
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/wrong")
        raise AssertionError("wrong path should 404")
    except urllib.error.HTTPError as e:
        assert e.code == 404
finally:
    server.shutdown()

print("mobile self-checks passed")
