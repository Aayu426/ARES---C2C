"""Canonical strings and HMAC helpers. Mirrors CONTRACTS.md section 2 exactly.

Signatures are computed over a pipe-joined canonical string, never over JSON, so the
ESP32 (C++) and the gateway (Python) produce byte-identical input.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets


def fmt_temp(value) -> str:
    """Two decimals, never scientific notation. Empty string when absent."""
    if value is None or value == "":
        return ""
    return f"{float(value):.2f}"


def fmt_bit(value) -> str:
    if value is None or value == "":
        return ""
    return "1" if int(value) else "0"


def telemetry_canonical(msg: dict) -> str:
    """node_id|seq|ts|motion|temp|water"""
    return "|".join([
        str(msg.get("node_id", "")),
        str(msg.get("seq", "")),
        str(msg.get("ts", "")),
        fmt_bit(msg.get("motion")),
        fmt_temp(msg.get("temp")),
        fmt_bit(msg.get("water")),
    ])


def witness_canonical(msg: dict) -> str:
    """node_id|seq|ts|claim|value"""
    return "|".join([
        str(msg.get("node_id", "")),
        str(msg.get("seq", "")),
        str(msg.get("ts", "")),
        str(msg.get("claim", "")),
        fmt_bit(msg.get("value")),
    ])


def response_canonical(node_id: str, challenge_id: str, nonce: str, fw: str) -> str:
    """node_id|challenge_id|nonce|fw"""
    return "|".join([node_id, challenge_id, nonce, fw or ""])


def sign(key: bytes, canonical: str) -> str:
    return hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def verify(key: bytes, canonical: str, signature: str | None) -> bool:
    if not signature:
        return False
    expected = sign(key, canonical)
    return hmac.compare_digest(expected, str(signature).lower())


def new_nonce() -> str:
    return secrets.token_hex(16)


def new_key_hex() -> str:
    return secrets.token_hex(32)
