"""FAQ flows: button menu, keyword answering in DM, polite group mode,
group auto-welcome for new members, and the owner-handoff button."""

from __future__ import annotations

import html
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core import llm, store
from core.config import Config
from core.matcher import best_answer
from core.text import safe_html
from handlers.owner import alert_owner
from handlers.welcome import welcome_keyboard

log = logging.getLogger(__name__)


# ------------------------------------------------------------------ buttons
def _faq_menu_kb(cfg: Config) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f.question[:64], callback_data=f"faq:{i}")]
        for i, f in enumerate(cfg.faqs)
    ]
    rows.append([InlineKeyboardButton("« Start over", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def _faq_answer_text(item) -> str:
    """Question bold, answer safe-HTML: literal '<' or '&' in config answers
    can no longer break Telegram message parsing."""
    return f"<b>{html.escape(item.question, quote=False)}</b>\n\n{safe_html(item.answer)}"


async def faq_menu_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    cfg: Config = context.bot_data["config"]
    await query.edit_message_text(
        safe_html(cfg.faq_menu_title), reply_markup=_faq_menu_kb(cfg), parse_mode=ParseMode.HTML
    )


async def faq_item_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    cfg: Config = context.bot_data["config"]
    try:
        idx = int(query.data.split(":", 1)[1])
        item = cfg.faqs[idx]
    except (ValueError, IndexError):
        await query.edit_message_text(
            safe_html(cfg.faq_menu_title), reply_markup=_faq_menu_kb(cfg), parse_mode=ParseMode.HTML
        )
        return
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« All questions", callback_data="menu:faq")]]
    )
    await query.edit_message_text(
        _faq_answer_text(item), reply_markup=kb, parse_mode=ParseMode.HTML
    )


async def owner_handoff_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """« Talk to the owner» button — notify the owner, tell the user what happens."""
    query = update.callback_query
    await query.answer()
    cfg: Config = context.bot_data["config"]
    user = update.effective_user

    if user:
        await alert_owner(
            context,
            cfg,
            f"🙋 <b>{html.escape(user.first_name or 'Someone', quote=False)}</b> "
            f"(@{html.escape(user.username or 'no username', quote=False)}, "
            f"id <code>{user.id}</code>) pressed <b>Talk to the owner</b> "
            f"in @{context.bot.username}.",
        )

    extra = (
        f"\n\nYou can also write directly: {html.escape(cfg.owner_username, quote=False)}"
        if cfg.owner_username else ""
    )
    await query.edit_message_text(
        "✅ Noted — the owner has been notified and will reply here as soon as possible."
        + extra,
        parse_mode=ParseMode.HTML,
    )


# --------------------------------------------------------------- commands
async def cmd_faqs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.bot_data["config"]
    lines = [f"{i + 1}. {f.question}" for i, f in enumerate(cfg.faqs)]
    await update.message.reply_text(
        "Questions I can answer:\n" + "\n".join(lines)
        + "\n\nJust type your question, or tap a button."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.bot_data["config"]
    await update.message.reply_text(
        f"I'm the assistant for {cfg.prospect}.\n"
        "• Ask me anything — I answer the common questions instantly\n"
        "• /faqs — list everything I know\n"
        "• /request — leave your contact so the owner can reach you\n"
        "• If I don't know something, I pass it to the owner."
    )


# --------------------------------------------------------------- free text
async def _answer_text(cfg: Config, text: str, context: ContextTypes.DEFAULT_TYPE,
                       chat_id: str, username: str, in_group: bool = False) -> str:
    """Shared answering logic. Returns what was sent ('faq' | 'llm' | 'fallback')."""
    idx, _score = best_answer(text, cfg.faqs, cfg.threshold)
    if idx is not None:
        if in_group:
            # Lead conversation runs in DM only (group privacy mode keeps bots
            # blind to plain replies) — point to the DM instead.
            kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton("❓ All questions", callback_data="menu:faq"),
                  InlineKeyboardButton("📝 Leave a request → DM",
                                       url=f"https://t.me/{context.bot.username}")]]
            )
        else:
            kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton("❓ All questions", callback_data="menu:faq"),
                  InlineKeyboardButton("📝 Leave a request", callback_data="lead:start")]]
            )
        await context.bot.send_message(
            chat_id=chat_id,
            text=_faq_answer_text(cfg.faqs[idx]),
            reply_markup=kb,
            parse_mode=ParseMode.HTML,
        )
        return "faq"

    llm_text = llm.answer(text, cfg) if llm.available() else None
    if llm_text:
        await context.bot.send_message(chat_id=chat_id, text=llm_text)
        return "llm"

    # Fallback: tell the user the owner will handle it; log + alert the owner.
    await context.bot.send_message(
        chat_id=chat_id, text=safe_html(cfg.fallback_text), parse_mode=ParseMode.HTML
    )
    store.add_unanswered(chat_id, username, text)
    if cfg.notify_owner_on_fallback:
        await alert_owner(
            context, cfg,
            f"❓ <b>Question I couldn't answer</b>\n"
            f"From: {html.escape(username or 'unknown', quote=False)} "
            f"(chat <code>{html.escape(chat_id, quote=False)}</code>)\n"
            f"Text: {html.escape(text[:500], quote=False)}",
        )
    return "fallback"


async def dm_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.bot_data["config"]
    user = update.effective_user
    mode = await _answer_text(
        cfg, update.message.text, context,
        chat_id=str(update.effective_chat.id),
        username=(user.username if user else "") or "",
    )
    log.info("dm answer mode=%s", mode)


async def group_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Group mode: only speak when mentioned (@bot) or replied to — never noisy."""
    cfg: Config = context.bot_data["config"]
    if cfg.group_reply_mode == "off":
        return
    msg = update.message
    bot_username = context.bot.username

    mentioned = f"@{bot_username.lower()}" in (msg.text or "").lower()
    replied_to_bot = bool(
        msg.reply_to_message
        and msg.reply_to_message.from_user
        and msg.reply_to_message.from_user.id == context.bot.id
    )
    if not (mentioned or replied_to_bot):
        return

    question = (msg.text or "").replace(f"@{bot_username}", "").strip()
    if not question:
        return
    user = update.effective_user
    await _answer_text(
        cfg, question, context,
        chat_id=str(update.effective_chat.id),
        username=(user.username if user else "") or "",
        in_group=True,
    )


# ------------------------------------------------------------ group welcome
def build_group_welcome(cfg: Config, member_names: list[str], bot_username: str) -> str:
    """Trusted config template -> safe HTML first, then escaped names injected."""
    names = ", ".join(html.escape(n or "friend", quote=False) for n in member_names)
    return cfg.render(
        safe_html(cfg.group_welcome_text),
        first_name=names,
        bot_username=bot_username,
        group_title="",  # kept for template compatibility
    )


async def new_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Auto-welcome new group members (pitch feature) and introduce the bot
    when IT joins a group."""
    cfg: Config = context.bot_data["config"]
    if cfg.group_reply_mode == "off" or not cfg.group_welcome_new_members:
        return
    msg = update.message
    if not msg or not msg.new_chat_members:
        return

    if any(u.id == context.bot.id for u in msg.new_chat_members):
        # The bot itself was added — introduce itself briefly.
        await msg.reply_text(
            f"👋 Hi! I'm the assistant for {html.escape(cfg.prospect, quote=False)}.\n"
            f"Ask me a question by mentioning @{context.bot.username}, "
            f"or DM me for FAQs and to leave a request.",
            parse_mode=ParseMode.HTML,
        )
        return

    joining = [u for u in msg.new_chat_members if not u.is_bot]
    if not joining:
        return
    names = [u.first_name for u in joining]
    text = build_group_welcome(cfg, names, context.bot.username)
    await msg.reply_text(
        text,
        reply_markup=welcome_keyboard(cfg, context.bot.username, in_group=True),
        parse_mode=ParseMode.HTML,
    )
