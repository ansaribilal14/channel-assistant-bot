"""Owner tools: alerts helper, /leads, /answered, /pending, /resolved,
/leadscsv, /reload, /id."""

from __future__ import annotations

import html
import logging
import os

from telegram import Update
from telegram.ext import ContextTypes

from core import store
from core.config import Config

log = logging.getLogger(__name__)


async def alert_owner(context: ContextTypes.DEFAULT_TYPE, cfg: Config, text: str) -> None:
    """Send an alert to the owner chat. Never raises: if the owner hasn't
    started the bot yet (Telegram forbids bots messaging users first) we log
    instead so the demo keeps running."""
    owner_id = os.getenv("OWNER_ID", "").strip() or cfg.owner_id
    if not owner_id or not owner_id.lstrip("-").isdigit():
        log.warning("Owner alert suppressed (owner id not set): %s", text[:120])
        return
    try:
        await context.bot.send_message(chat_id=int(owner_id), text=text, parse_mode="HTML")
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "Owner alert failed (%s). The owner must /start the bot once before "
            "it can message them.", exc,
        )


def _is_owner(update: Update, cfg: Config) -> bool:
    owner_id = os.getenv("OWNER_ID", "").strip() or cfg.owner_id
    user = update.effective_user
    return bool(owner_id and user and owner_id.lstrip("-").isdigit() and str(user.id) == owner_id)


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Setup helper: prints the chat id to paste into config.yaml owner.id."""
    chat = update.effective_chat
    user = update.effective_user
    await update.message.reply_text(
        f"This chat id: <code>{chat.id}</code>\n"
        f"Your user id: <code>{user.id if user else '?'}</code>\n\n"
        f"Put the user id into config.yaml → owner.id (or .env → OWNER_ID).",
        parse_mode="HTML",
    )


async def cmd_leads(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.bot_data["config"]
    if not _is_owner(update, cfg):
        await update.message.reply_text("Owner only.")
        return
    rows = store.list_leads(10)
    if not rows:
        await update.message.reply_text("No leads yet.")
        return
    lines = []
    for r in rows:
        flag = "✅" if r["status"] == "done" else "🟢"
        lines.append(
            f"{flag} #{r['id']} · {r['created_at']}\n"
            f"  {html.escape(r['name'])} — {html.escape(r['contact'])}\n"
            f"  {html.escape((r['question'] or '')[:120])}"
        )
    await update.message.reply_text("Last leads:\n\n" + "\n\n".join(lines), parse_mode="HTML")


async def cmd_answered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.bot_data["config"]
    if not _is_owner(update, cfg):
        await update.message.reply_text("Owner only.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /answered <lead id>")
        return
    ok = store.mark_lead_done(int(context.args[0]))
    await update.message.reply_text("Marked done ✅" if ok else "Lead id not found.")


async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.bot_data["config"]
    if not _is_owner(update, cfg):
        await update.message.reply_text("Owner only.")
        return
    rows = store.list_unanswered(10)
    if not rows:
        await update.message.reply_text("Nothing pending — the bot answered everything.")
        return
    lines = [
        f"❓ #{r['id']} · {r['created_at']}\n  {html.escape((r['text'] or '')[:150])}"
        for r in rows
    ]
    await update.message.reply_text(
        "Questions the bot couldn't answer:\n\n" + "\n\n".join(lines)
        + "\n\nWhen handled: /resolved <id>. Consider adding these to your FAQs.",
        parse_mode="HTML",
    )


async def cmd_resolved(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.bot_data["config"]
    if not _is_owner(update, cfg):
        await update.message.reply_text("Owner only.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /resolved <question id>")
        return
    ok = store.mark_unanswered_done(int(context.args[0]))
    await update.message.reply_text("Marked resolved ✅" if ok else "Id not found.")


async def cmd_leadscsv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.bot_data["config"]
    if not _is_owner(update, cfg):
        await update.message.reply_text("Owner only.")
        return
    buf = store.export_leads_csv()
    await update.message.reply_document(
        document=buf, filename="leads.csv",
        caption="All captured leads — import into your CRM/sheet.",
    )


async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.bot_data["config"]
    if not _is_owner(update, cfg):
        await update.message.reply_text("Owner only.")
        return
    try:
        fresh = Config.load(cfg.path)
        context.bot_data["config"] = fresh
        await update.message.reply_text(
            f"Reloaded ✅ — {len(fresh.faqs)} FAQs, prospect “{fresh.prospect}”."
        )
    except Exception as exc:  # noqa: BLE001
        await update.message.reply_text(f"Reload failed: {html.escape(str(exc))}", parse_mode="HTML")
