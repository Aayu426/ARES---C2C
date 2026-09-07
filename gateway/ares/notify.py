"""Outbound incident notifications to an n8n workflow.

ARES posts every security incident to an n8n webhook (set N8N_WEBHOOK_URL). n8n then fans
the alert out to email / Slack / Telegram / a ticket — whatever the workflow is wired to.
This is purely additive and fire-and-forget: a missing URL or a failed POST is swallowed so
it can never affect detection or the live demo. The key/URL never reaches the browser.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.request

_UA = "ARES-Gateway/1.0"


def _severity(summary: str, claim: str) -> str:
    s = summary.upper()
    if "SLEEPER" in s:
        return "CRITICAL"
    if claim in ("identity", "integrity") or "FORGED" in s or "REPLAY" in s:
        return "HIGH"
    return "MEDIUM"


def _post(url: str, payload: dict) -> None:
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "User-Agent": _UA},
        )
        urllib.request.urlopen(req, timeout=6).read()
    except Exception as exc:  # never let a webhook failure touch the engine
        print(f"[notify] n8n webhook failed: {exc!r}", flush=True)


COOLDOWN = 20.0   # at most one alert per (event, node, type) in this window, so a burst attack = one email


def _alert_for(ev: dict) -> dict | None:
    """Turn a bus event into an alert payload, or None if it isn't an emailable security event."""
    e = ev.get("e")
    if e == "incident":
        # real security incidents only (attack / replay / physics / drift / sleeper),
        # not routine consensus confirmations (id prefix "i-")
        iid = str(ev.get("id") or "")
        if not iid.startswith(("atk-", "rep-", "phy-", "drf-", "slp-")):
            return None
        summary = str(ev.get("summary") or "")
        claim = str(ev.get("claim") or "")
        return {"node": ev.get("node_id"), "type": claim or "incident",
                "severity": _severity(summary, claim), "summary": summary,
                "incident_id": ev.get("id")}
    if e == "identity_failure":
        # a forged frame refused — the MQTT / spoof network attack
        node = ev.get("node_id")
        detail = str(ev.get("detail") or "invalid signature")
        attempted = ev.get("attempted") or {}
        network = "network (MQTT)" if "mqtt" in str(ev.get("source") or "") else "serial/local"
        summary = (f"FORGED FRAME REFUSED on {node}: {detail}. "
                   f"Attempted {attempted or 'unsigned frame'}. Source: {network}.")
        return {"node": node, "type": "identity", "severity": "HIGH",
                "summary": summary, "incident_id": None}
    return None


async def n8n_forwarder(bus) -> None:
    """Subscribe to the event bus and forward security incidents to n8n."""
    q = bus.subscribe()
    last_sent: dict[tuple, float] = {}
    print("[notify] n8n incident forwarder running (set N8N_WEBHOOK_URL to enable)", flush=True)
    try:
        while True:
            ev = await q.get()
            alert = _alert_for(ev)
            if alert is None:
                continue
            url = os.environ.get("N8N_WEBHOOK_URL")
            if not url:
                continue
            now = time.time()
            key = (ev.get("e"), alert["node"], alert["type"])
            if now - last_sent.get(key, 0) < COOLDOWN:
                continue
            last_sent[key] = now
            payload = {
                "alert": "ARES SECURITY INCIDENT",
                "system": "ARES Adaptive Trust Mesh",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ev.get("at", now))),
                **alert,
            }
            await asyncio.to_thread(_post, url, payload)
    except asyncio.CancelledError:
        pass
    finally:
        bus.unsubscribe(q)
