"""Optional free-LLM fallback — never a paid dependency.

If the keyword matcher cannot answer, and the operator has configured a free
OpenAI-compatible endpoint (e.g. Groq's free tier), we try it. Any failure
falls back silently to the "I'll ask the owner" path. Default: disabled.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

from core.config import Config

log = logging.getLogger(__name__)


def available() -> bool:
    return bool(os.getenv("LLM_API_BASE", "").strip() and os.getenv("LLM_API_KEY", "").strip())


def _base() -> str:
    return os.getenv("LLM_API_BASE", "").strip().rstrip("/")


def _model() -> str:
    return os.getenv("LLM_MODEL", "llama-3.3-70b-versatile").strip()


def answer(question: str, cfg: Config, timeout: float = 12.0) -> Optional[str]:
    """Ask the configured LLM, grounded on the FAQ content. Returns text or None."""
    if not available():
        return None

    faq_block = "\n".join(
        f"Q: {f.question}\nA: {f.answer}" for f in cfg.faqs
    )
    system = (
        f"You are the assistant for {cfg.prospect}. Answer ONLY using the FAQ "
        f"knowledge below. If the answer is not covered, reply exactly: "
        f"FALLBACK. Keep replies short and friendly.\n\n--- FAQ ---\n{faq_block}"
    )
    try:
        resp = httpx.post(
            f"{_base()}/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('LLM_API_KEY', '').strip()}",
                "Content-Type": "application/json",
            },
            json={
                "model": _model(),
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": question},
                ],
                "temperature": 0.2,
                "max_tokens": 300,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        if not content or content == "FALLBACK":
            return None
        return content
    except Exception as exc:  # noqa: BLE001 — any LLM problem must never break the bot
        log.warning("LLM hook failed, using fallback: %s", exc)
        return None
