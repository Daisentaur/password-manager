"""Vault file: [4-byte magic "PWV1"][16-byte salt][12-byte nonce + ciphertext].

The ciphertext is JSON: {"entry name": {"user": ..., "pw": ..., "notes": ...}}.
Salt and nonce are not secrets; everything sensitive is inside the ciphertext.
"""

import json
import os
import shutil

from cryptography.exceptions import InvalidTag

from . import crypto

MAGIC = b"PWV1"


class VaultError(Exception):
    """Anything wrong with opening or reading a vault, with a human message."""


def load(path: str, password: str) -> dict:
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        raise VaultError(f"no vault at {path} — run 'init' first")
    if raw[:4] != MAGIC:
        raise VaultError(f"{path} is not a vault file (bad magic bytes)")
    salt = raw[4 : 4 + crypto.SALT_LEN]
    key = crypto.derive_key(password, salt)
    try:
        plaintext = crypto.decrypt(key, raw[4 + crypto.SALT_LEN :])
    except InvalidTag:
        raise VaultError("wrong master password (or the vault file is corrupted)")
    return json.loads(plaintext)


def save(path: str, password: str, entries: dict) -> None:
    salt = os.urandom(crypto.SALT_LEN)
    key = crypto.derive_key(password, salt)
    blob = MAGIC + salt + crypto.encrypt(key, json.dumps(entries).encode())
    # Keep the previous version as .bak: one-step undo for corruption or mistakes.
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")
    # Write to a temp file then rename: a crash mid-write can't destroy the vault.
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(blob)
    os.replace(tmp, path)
