"""Incident explanation. The AI is an advisor outside the root of trust: this module only
reads logged evidence and returns text. It cannot touch trust, states or actions.

Gemini is used when GEMINI_API_KEY is set and the call succeeds; otherwise a
deterministic template produces the same three-sentence shape, so the demo button
looks identical offline."""
from __future__ import annotations

import json
import os
import urllib.request

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

PROMPT = """You are the incident explainer for ARES, a trust engine for edge sensors.
Explain the incident below to a control-room operator in exactly three plain sentences:
1) what was claimed and by whom, 2) what evidence contradicted it and what the challenge found,
3) what ARES did and what a human should check. No headings, no bullet points, no speculation
beyond the evidence. Do not recommend any action other than physical inspection.

Incident JSON:
{incident}
"""


def template(incident: dict) -> str:
    ev = incident.get("evidence", {}) or {}
    claim = incident.get("claim", "a claim")
    by = ", ".join(ev.get("by", [])) or "no witness"
    against = ev.get("against", []) or []
    reasons = ev.get("reasons", {}) or {}
    states = ev.get("states", {}) or {}
    if against:
        liar = against[0]
        why = reasons.get(liar, "it disagreed with the other witnesses")
        return (f"{by} reported {claim}, while {', '.join(against)} reported none. "
                f"ARES challenged {liar} because {why}; its current state is {states.get(liar, 'unknown').lower()}. "
                f"The {claim} alarm was raised on the corroborated evidence and {liar}'s reports were set aside; "
                f"an operator should physically check the {claim} area and inspect {liar} before restoring it.")
    return (f"{incident.get('summary', 'An incident was recorded')}. "
            f"No witness contradicted the corroborating evidence from {by}. "
            f"ARES acted only on corroborated evidence; an operator should verify the {claim} area in person.")


def gemini(incident: dict) -> str | None:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    body = {"contents": [{"parts": [{"text": PROMPT.format(incident=json.dumps(incident, indent=1))}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300}}
    req = urllib.request.Request(GEMINI_URL.format(model=GEMINI_MODEL, key=key),
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.load(r)
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return text or None
    except Exception as exc:  # any failure falls back to the template, silently for the audience
        print(f"[explain] gemini unavailable: {exc!r}")
        return None


def explain(incident: dict) -> dict:
    text = gemini(incident)
    if text:
        return {"text": text, "source": "gemini", "model": GEMINI_MODEL}
    return {"text": template(incident), "source": "template"}
