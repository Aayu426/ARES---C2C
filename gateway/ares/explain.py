"""Incident explanation. The AI is an advisor outside the root of trust: this module only
reads logged evidence and returns text. It cannot touch trust, states or actions.

Groq is used when GROQ_API_KEY is set and the call succeeds; otherwise a
deterministic template produces the same three-sentence shape, so the demo button
looks identical offline."""
from __future__ import annotations

import json

from .ai import groq_chat

EXPLAIN_SYSTEM = ("You are the incident explainer for ARES, a trust engine for edge sensors. "
    "Explain the incident to a control-room operator in exactly three plain sentences: "
    "1) what was claimed and by whom, 2) what evidence contradicted it and what the challenge found, "
    "3) what ARES did and what a human should check. No headings, no bullet points, no speculation "
    "beyond the evidence. Do not recommend any action other than physical inspection.")


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


def _model(incident: dict) -> str | None:
    payload = "Incident JSON:\n" + json.dumps(incident, indent=1, default=str)
    return groq_chat(EXPLAIN_SYSTEM, payload, max_tokens=300)


def explain(incident: dict) -> dict:
    text = _model(incident)
    if text:
        import os
        return {"text": text, "source": "groq", "model": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")}
    return {"text": template(incident), "source": "template"}
