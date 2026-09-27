"""Config loader — one YAML file holds everything a demo needs to adapt:
prospect name, welcome text, buttons, 10 FAQs, fallback message, owner chat id.

This is deliberate: the business brief requires that a demo can be re-cut for a
new client in minutes by editing a single file. No code changes needed.
"""

from __future__ import annotations

import html
import os
from dataclasses import dataclass
from typing import Any

import yaml


class ConfigError(Exception):
    """Raised when the config file is missing or invalid."""


_REQUIRED_TOP = ("prospect", "welcome", "faq")

DEFAULT_GROUP_WELCOME = (
    "👋 Welcome {first_name} to {prospect}!\n\n"
    "I'm the group assistant — mention @{bot_username} with any question, "
    "or tap a button below."
)


@dataclass
class Faq:
    keywords: list[str]
    question: str
    answer: str


@dataclass
class Config:
    prospect: str
    welcome_text: str
    buttons: list[dict[str, str]]
    faqs: list[Faq]
    faq_menu_title: str
    fallback_text: str
    notify_owner_on_fallback: bool
    lead_thank_you: str
    owner_id: str
    owner_username: str
    group_reply_mode: str
    group_welcome_new_members: bool
    group_welcome_text: str
    threshold: float
    data_dir: str
    path: str = ""

    # ------------------------------------------------------------------ load
    @classmethod
    def load(cls, path: str) -> "Config":
        if not os.path.exists(path):
            raise ConfigError(
                f"Config file not found: {path}\n"
                f"  Copy the example:  cp config.example.yaml config.yaml"
            )
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc

        missing = [k for k in _REQUIRED_TOP if k not in raw]
        if missing:
            raise ConfigError(f"{path}: missing required section(s): {', '.join(missing)}")

        welcome = raw.get("welcome") or {}
        faq = raw.get("faq") or {}
        lead = raw.get("lead") or {}
        owner = raw.get("owner") or {}
        group = raw.get("group") or {}

        faq_items: list[Faq] = []
        for i, item in enumerate(faq.get("items") or []):
            try:
                faq_items.append(
                    Faq(
                        keywords=[str(k) for k in (item.get("keywords") or [])],
                        question=str(item["question"]),
                        answer=str(item["answer"]),
                    )
                )
            except KeyError as exc:
                raise ConfigError(f"faq.items[{i}]: missing field {exc}") from exc
        if not faq_items:
            raise ConfigError(f"{path}: faq.items is empty — add at least one Q&A")

        buttons = [
            {"label": str(b["label"]), "action": str(b["action"])}
            for b in (welcome.get("buttons") or [])
            if isinstance(b, dict) and "label" in b and "action" in b
        ]

        threshold_raw = faq.get("threshold", 2.0)
        try:
            threshold = float(threshold_raw)
        except (TypeError, ValueError):
            threshold = 2.0

        cfg = cls(
            prospect=str(raw["prospect"]),
            welcome_text=str(welcome.get("text", "")),
            buttons=buttons,
            faqs=faq_items,
            faq_menu_title=str(faq.get("menu_title", "Pick a question:")),
            fallback_text=str(
                faq.get("fallback_text",
                        "I'm not sure about that — I'll ask the owner and get back to you.")
            ),
            notify_owner_on_fallback=bool(faq.get("notify_owner", True)),
            lead_thank_you=str(
                lead.get("thank_you", "Thanks! The owner will get back to you soon.")
            ),
            owner_id=str(owner.get("id") or "").strip(),
            owner_username=str(owner.get("username") or "").strip(),
            group_reply_mode=str(group.get("reply_mode", "mention")).lower(),
            group_welcome_new_members=bool(group.get("welcome_new_members", True)),
            group_welcome_text=str(group.get("welcome_text") or DEFAULT_GROUP_WELCOME),
            threshold=threshold,
            data_dir=str(raw.get("data_dir", "data")),
            path=path,
        )
        return cfg

    # --------------------------------------------------------------- helpers
    def render(self, text: str, **kwargs: str) -> str:
        """Format a config template ({first_name}, {prospect}, {bot_username}, ...).
        `prospect` defaults to this config's value, HTML-escaped (a prospect like
        "Q&A Academy" must not break Telegram HTML parsing). Tolerant: unknown
        placeholders stay as-is instead of raising."""
        kwargs.setdefault("prospect", html.escape(self.prospect, quote=False))

        class _SafeDict(dict):
            def __missing__(self, key: str) -> str:
                return "{" + key + "}"
        try:
            return text.format_map(_SafeDict(**kwargs))
        except (ValueError, IndexError):
            return text
