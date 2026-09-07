"""Groq-backed language helpers for ARES.

The model is an ADVISOR outside the root of trust: everything here only reads logged
evidence and returns text. It never touches trust, states, or actions.

Groq (api.groq.com) runs fast open models with an OpenAI-compatible chat API. It is used
when GROQ_API_KEY is set and the call succeeds; otherwise a deterministic template gives
the same shape, so the demo works offline. Groq sits behind Cloudflare, which blocks the
default Python user-agent, so a real User-Agent header is required.
"""
from __future__ import annotations

import json
import os
import urllib.request

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ARES-Gateway/1.0"


def groq_chat(system: str, user: str, *, max_tokens: int = 320, temperature: float = 0.2) -> str | None:
    """One chat completion. Returns the assistant text, or None on any failure."""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    body = {
        "model": os.environ.get("GROQ_MODEL", GROQ_MODEL),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        GROQ_URL,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": _UA,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
        text = data["choices"][0]["message"]["content"].strip()
        return text or None
    except Exception as exc:  # any failure falls back to a template, silently for the audience
        print(f"[ai] groq unavailable: {exc!r}", flush=True)
        return None


# ------------------------------------------------------------------ audit-log Q&A

ASK_SYSTEM = (
    "You are the audit-log assistant for ARES, a zero-trust engine for edge sensors. "
    "Answer the operator's question using ONLY the incident evidence provided. "
    "Be concise: two or three plain sentences, no headings, no bullet points, no markdown. "
    "Explain what happened, which node and claim were involved, and what ARES did. "
    "The AI is advisory only and never decides; recommend only physical inspection. "
    "If the evidence does not contain the answer, say so plainly."
)


def _ask_template(question: str, incidents: list[dict]) -> str:
    if not incidents:
        return ("There are no incidents in the audit log yet. Once an attack or conflict is "
                "recorded, ask again and I will reconstruct what happened from the evidence.")
    latest = incidents[0]
    summary = latest.get("summary") or "an incident was recorded"
    claim = latest.get("claim", "a claim")
    return (f"The most recent audit entry: {summary}. It concerned the {claim} claim. "
            f"There are {len(incidents)} incident(s) logged in total; ARES acted only on "
            f"corroborated evidence and an operator should verify the affected area in person.")


def answer_question(question: str, incidents: list[dict]) -> dict:
    """Answer a free-text question about the audit log. Advisory, read-only."""
    context = json.dumps(incidents[:20], indent=1, default=str)
    user = f"Operator question: {question}\n\nAudit-log incidents (most recent first):\n{context}"
    text = groq_chat(ASK_SYSTEM, user)
    if text:
        return {"answer": text, "source": "groq", "model": os.environ.get("GROQ_MODEL", GROQ_MODEL)}
    return {"answer": _ask_template(question, incidents), "source": "template"}
