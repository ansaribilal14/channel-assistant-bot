"""Welcome flow: /start renders the configured greeting with inline buttons."""

from __future__ import annotations

import html
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.config import Config

log = logging.getLogger(__name__)

# config action -> (callback data, emoji prefix)
_ACTION_CB = {
    "faq_menu": "menu:faq",
    "lead_start": "lead:start",
    "owner_handoff": "owner:handoff",
}


def welcome_keyboard(cfg: Config) -> InlineKeyboardMarkup:
    rows = []
    for b in cfg.buttons:
        cb = _ACTION_CB.get(b["action"])
        if cb:
            rows.append([InlineKeyboardButton(b["label"], callback_data=cb)])
    if not rows:  # defensive default
        rows = [[InlineKeyboardButton("❓ Browse FAQs", callback_data="menu:faq")]]
    return InlineKeyboardMarkup(rows)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.bot_data["config"]
    user = update.effective_user
    source = ""
    if context.args:  # deep link payload, e.g. t.me/bot?start=instagram_post
        source = " ".join(context.args)[:64]

    name = html.escape(user.first_name or "there") if user else "there"
    text = cfg.render(cfg.welcome_text, first_name=name, prospect=html.escape(cfg.prospect))
    if not text.strip():
        text = f"👋 Hi {name}! Welcome to {html.escape(cfg.prospect)}. How can I help?"

    await update.message.reply_text(
        text, reply_markup=welcome_keyboard(cfg), parse_mode=ParseMode.HTML
    )
    if source and user:
        log.info("start payload=%s user=%s (%s)", source, user.id, user.username)


async def back_home_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """« Back to start button — re-shows the welcome card."""
    query = update.callback_query
    await query.answer()
    cfg: Config = context.bot_data["config"]
    user = update.effective_user
    name = html.escape(user.first_name or "there") if user else "there"
    text = cfg.render(cfg.welcome_text, first_name=name, prospect=html.escape(cfg.prospect))
    if not text.strip():
        text = f"👋 Hi {name}! Welcome to {html.escape(cfg.prospect)}. How can I help?"
    await query.edit_message_text(
        text, reply_markup=welcome_keyboard(cfg), parse_mode=ParseMode.HTML
    )
