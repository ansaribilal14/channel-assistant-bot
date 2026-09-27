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
from core.text import safe_html
from handlers.faq import build_group_welcome

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


# ---------------------------------------------------------------- safe_html
def test_safe_html_escapes_lt_and_amp():
    # FAQ answers like "Price < $99 & shipping" must not break Telegram HTML
    assert safe_html("Price < $99 & shipping") == "Price &lt; $99 &amp; shipping"


def test_safe_html_keeps_whitelisted_tags():
    assert safe_html("<b>Bold</b> and <i>italic</i> and <code>x=1</code>") == \
        "<b>Bold</b> and <i>italic</i> and <code>x=1</code>"


def test_safe_html_neutralizes_non_whitelisted_tags():
    out = safe_html("<script>alert(1)</script> <a href='x'>link</a>")
    assert "<script>" not in out and "<a " not in out
    assert "&lt;script&gt;" in out


def test_faq_answer_survives_hostile_answer_text():
    from handlers.faq import _faq_answer_text
    from core.config import Faq
    item = Faq(keywords=["x"], question="Q & A?", answer="Cost < $5 & <b>bold</b>")
    text = _faq_answer_text(item)
    assert "<b>Q &amp; A?</b>" in text
    assert "Cost &lt; $5 &amp;" in text
    assert "<b>bold</b>" in text  # whitelisted tag preserved


# ------------------------------------------------------- prospect escaping
def test_render_escapes_prospect_with_special_chars(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(
        "prospect: \"Q&A <Academy>\"\n"
        "welcome:\n  text: hi\n"
        "faq:\n  items:\n    - keywords: [x]\n      question: q\n      answer: a\n"
    )
    cfg = Config.load(str(p))
    out = cfg.render("Welcome to {prospect}!")
    assert out == "Welcome to Q&amp;A &lt;Academy&gt;!"


# ------------------------------------------------------------ group welcome
def test_group_welcome_renders_names_and_bot():
    cfg = _cfg()
    assert cfg.group_welcome_new_members is True
    text = build_group_welcome(cfg, ["Ali", "Sara & Co"], "demo_bot")
    assert "Ali" in text and "Sara &amp; Co" in text
    assert "@demo_bot" in text
    assert "BrightPath" in text
    # must be parse-safe: no raw < or & outside whitelisted tags
    import re
    assert not re.search(r"<(?!/?(b|i|u|s|code|pre)>)[^>]*>", text)


def test_group_welcome_survives_tag_injection_names():
    cfg = _cfg()
    text = build_group_welcome(cfg, ["<b>evil</b>"], "demo_bot")
    assert "&lt;b&gt;evil&lt;/b&gt;" in text  # escaped, not executed
