"""Welcome flows: /start card in DM, group-aware keyboards, auto-welcome."""

from __future__ import annotations

import html
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.config import Config
from core.text import safe_html

log = logging.getLogger(__name__)

# config action -> callback data
_ACTION_CB = {
    "faq_menu": "menu:faq",
    "lead_start": "lead:start",
    "owner_handoff": "owner:handoff",
}


def welcome_keyboard(cfg: Config, bot_username: str = "", in_group: bool = False) -> InlineKeyboardMarkup:
    """Inline keyboard from config buttons. In groups the lead-capture button
    becomes a link into the bot's DM: the 3-step lead conversation must run in
    DM (with group privacy mode on, plain replies aren't delivered to bots)."""
    rows: list[list[InlineKeyboardButton]] = []
    for b in cfg.buttons:
        cb = _ACTION_CB.get(b["action"])
        if not cb:
            continue
        if in_group and b["action"] == "lead_start":
            if bot_username:
                rows.append([InlineKeyboardButton(
                    f"{b['label']} → DM me",
                    url=f"https://t.me/{bot_username}",
                )])
            continue
        rows.append([InlineKeyboardButton(b["label"], callback_data=cb)])
    if not rows:  # defensive default
        rows = [[InlineKeyboardButton("❓ Browse FAQs", callback_data="menu:faq")]]
    return InlineKeyboardMarkup(rows)


def _welcome_text(cfg: Config, first_name: str | None, bot_username: str) -> str:
    name = html.escape(first_name or "there", quote=False)
    text = cfg.render(safe_html(cfg.welcome_text), first_name=name,
                      bot_username=bot_username)
    if not text.strip():
        text = f"👋 Hi {name}! Welcome to {html.escape(cfg.prospect, quote=False)}. How can I help?"
    return text


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.bot_data["config"]
    user = update.effective_user
    if context.args:  # deep link payload, e.g. t.me/bot?start=instagram_post
        log.info("start payload=%s user=%s (%s)",
                 " ".join(context.args)[:64], user.id if user else "?",
                 user.username if user else "?")
    text = _welcome_text(cfg, user.first_name if user else None, context.bot.username)
    await update.message.reply_text(
        text, reply_markup=welcome_keyboard(cfg, context.bot.username), parse_mode=ParseMode.HTML
    )


async def back_home_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """« Start over button — re-shows the welcome card."""
    query = update.callback_query
    await query.answer()
    cfg: Config = context.bot_data["config"]
    user = update.effective_user
    text = _welcome_text(cfg, user.first_name if user else None, context.bot.username)
    await query.edit_message_text(
        text, reply_markup=welcome_keyboard(cfg, context.bot.username), parse_mode=ParseMode.HTML
    )
