"""Lead capture conversation in bot DM:
name -> contact -> question -> save to SQLite + alert the owner.
"""

from __future__ import annotations

import html
import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from core import store
from core.config import Config
from core.text import safe_html
from handlers.owner import alert_owner

log = logging.getLogger(__name__)

NAME, CONTACT, QUESTION = range(3)


async def lead_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["lead_source"] = "button"
    await query.edit_message_text(
        "📝 Great — let's take your details.\n\n1/3 · What's your name?"
    )
    return NAME


async def lead_start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["lead_source"] = "command"
    await update.message.reply_text(
        "📝 Great — let's take your details.\n\n1/3 · What's your name?"
    )
    return NAME


async def got_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["lead_name"] = update.message.text.strip()[:128]
    await update.message.reply_text("2/3 · Best way to reach you? (phone, @username, email…)")
    return CONTACT


async def got_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["lead_contact"] = update.message.text.strip()[:256]
    await update.message.reply_text("3/3 · What do you need help with?")
    return QUESTION


async def got_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cfg: Config = context.bot_data["config"]
    user = update.effective_user
    question = update.message.text.strip()[:2000]
    name = context.user_data.get("lead_name", "")
    contact = context.user_data.get("lead_contact", "")
    source = context.user_data.get("lead_source", "chat")

    lead_id = store.add_lead(
        chat_id=str(update.effective_chat.id),
        username=(user.username if user else "") or "",
        first_name=(user.first_name if user else "") or "",
        source=source,
        name=name,
        contact=contact,
        question=question,
    )

    await update.message.reply_text(
        safe_html(cfg.lead_thank_you), parse_mode="HTML"
    )

    await alert_owner(
        context, cfg,
        f"🟢 <b>New lead #{lead_id}</b>\n"
        f"Name: {html.escape(name)}\n"
        f"Contact: {html.escape(contact)}\n"
        f"Needs: {html.escape(question[:400])}\n"
        f"TG: @{html.escape((user.username if user else '') or 'no username')} "
        f"(chat <code>{update.effective_chat.id}</code>)\n"
        f"<i>Commands: /leads · /answered {lead_id} · /leadscsv</i>",
    )
    log.info("lead #%d captured from chat %s", lead_id, update.effective_chat.id)
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("No problem — type /start whenever you're ready.")
    return ConversationHandler.END
