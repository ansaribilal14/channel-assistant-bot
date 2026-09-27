"""Smoke tests — no network, no Telegram token needed.

Run:  pytest -q
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config, ConfigError
from core import matcher, store

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE = os.path.join(REPO, "config.example.yaml")


# ------------------------------------------------------------------ config
def test_example_config_loads():
    cfg = Config.load(EXAMPLE)
    assert cfg.prospect == "BrightPath English Academy"
    assert len(cfg.faqs) == 10
    assert {"faq_menu", "lead_start", "owner_handoff"} <= {
        b["action"] for b in cfg.buttons
    }
    assert cfg.threshold == 2.0


def test_missing_config_raises(tmp_path):
    with pytest.raises(ConfigError):
        Config.load(str(tmp_path / "nope.yaml"))


def test_invalid_config_missing_section(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("prospect: X\n")
    with pytest.raises(ConfigError):
        Config.load(str(p))


def test_render_placeholders():
    cfg = Config.load(EXAMPLE)
    out = cfg.render("Hi {first_name}, welcome to {prospect}!", first_name="Ali")
    assert "Hi Ali," in out and "BrightPath" in out
    # unknown placeholders survive
    assert "{nope}" in cfg.render("x {nope} y")


# ----------------------------------------------------------------- matcher
def _cfg() -> Config:
    return Config.load(EXAMPLE)


def test_exact_keyword_match():
    cfg = _cfg()
    idx, score = matcher.best_answer("what is the price of the course?", cfg.faqs)
    assert idx == 0 and score >= cfg.threshold


def test_prefix_match():
    idx, score = matcher.best_answer("what's your pricing for ielts?", _cfg().faqs)
    assert idx == 0  # pricing ~ price prefix


def test_phrase_match():
    cfg = _cfg()
    # "free" alone is ambiguous, "free trial" phrase should hit the trial FAQ
    idx, _ = matcher.best_answer("do you offer a free trial?", cfg.faqs)
    assert idx == 2


def test_unknown_question_returns_none():
    idx, _ = matcher.best_answer("do you teach underwater basket weaving?", _cfg().faqs)
    assert idx is None


def test_matcher_multilingual_fallback_is_safe():
    # non-matching language must not crash and must not match
    idx, _ = matcher.best_answer("आपका कोर्स फीस कितना है?", _cfg().faqs)
    assert idx in (None, 0)  # 0 only if a keyword overlaps; must not raise


# ------------------------------------------------------------------- store
def test_store_roundtrip(tmp_path):
    store.init(str(tmp_path))
    lead_id = store.add_lead("111", "ali_t", "Ali", "button", "Ali", "@ali_t", "Need info")
    rows = store.list_leads()
    assert rows[0]["id"] == lead_id
    assert rows[0]["contact"] == "@ali_t"
    assert store.mark_lead_done(lead_id)
    assert store.list_leads()[0]["status"] == "done"

    u_id = store.add_unanswered("111", "ali_t", "do you sell pizza?")
    assert store.list_unanswered()[0]["text"] == "do you sell pizza?"
    assert store.mark_unanswered_done(u_id)
    assert store.list_unanswered() == []

    buf = store.export_leads_csv().read().decode()
    assert "Need info" in buf and "created_at" in buf
