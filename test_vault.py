"""Smallest checks that fail if the crypto or vault logic breaks.

Run: ./venv/bin/python test_vault.py
"""

import os
import tempfile

from pw_manager import crypto, vault

with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, "vault")

    # round trip
    data = {"github": {"user": "dt", "pw": "hunter2", "notes": ""}}
    vault.save(path, "master-pw", data)
    assert vault.load(path, "master-pw") == data

    # wrong password fails loudly, never returns garbage
    try:
        vault.load(path, "wrong-pw")
        raise AssertionError("wrong password was accepted")
    except vault.VaultError:
        pass

    # saving again leaves the previous version recoverable as .bak
    vault.save(path, "master-pw", {**data, "extra": {"user": "u", "pw": "p", "notes": ""}})
    assert vault.load(path + ".bak", "master-pw") == data

    # tampering (flip one ciphertext byte) is detected
    raw = bytearray(open(path, "rb").read())
    raw[-1] ^= 0xFF
    open(path, "wb").write(bytes(raw))
    try:
        vault.load(path, "master-pw")
        raise AssertionError("tampered vault was accepted")
    except vault.VaultError:
        pass

    # same password + same salt -> same key; different salt -> different key
    salt = os.urandom(16)
    assert crypto.derive_key("x", salt) == crypto.derive_key("x", salt)
    assert crypto.derive_key("x", salt) != crypto.derive_key("x", os.urandom(16))

print("all checks passed")
