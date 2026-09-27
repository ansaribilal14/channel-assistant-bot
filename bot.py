#!/usr/bin/env python3
"""Channel Assistant — zero-cost Telegram FAQ & lead-capture bot.

Built on python-telegram-bot (https://github.com/python-telegram-bot/python-telegram-bot),
the highest-rated Python Telegram framework (MIT).

What it does (the demo brief):
  * welcome buttons in bot DM
  * answers grounded in editable FAQs (keyword matching — no LLM required)
  * "I'll ask the owner" fallback when it cannot answer
  * lead capture in bot DM (name / contact / question -> SQLite)
  * owner alerts + /leads, /pending, CSV export

Run locally with long polling. No paid dependencies. Optional free LLM tier
(OpenAI-compatible, e.g. Groq) is a fallback only — never required.

Usage:
    python bot.py            # start long polling
    python bot.py --check    # validate config and exit (no token needed)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import warnings

from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.warnings import PTBUserWarning

from core.config import Config, ConfigError
from core import store
from handlers import faq, lead, owner, welcome

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
log = logging.getLogger("channel-assistant")

# ConversationHandler with CallbackQueryHandler entry uses per_message=False by
# default — the correct mode here. PTB emits a noisy one-time warning about it;
# suppress so the demo console stays clean.
warnings.filterwarnings("ignore", category=PTBUserWarning)


def build_application(cfg: Config, token: str) -> Application:
    """Wire all handlers onto a python-telegram-bot Application."""

    async def post_init(app: Application) -> None:
        await app.bot.set_my_commands(
            [
                BotCommand("start", "Restart the assistant"),
                BotCommand("faqs", "List the questions I can answer"),
                BotCommand("request", "Leave a request / contact"),
                BotCommand("help", "What this bot can do"),
                BotCommand("id", "Show this chat's ID (setup helper)"),
            ]
        )

    app = Application.builder().token(token).post_init(post_init).build()
    app.bot_data["config"] = cfg

    # --- Lead capture conversation (bot DM) — added first so it wins over the
    # --- generic free-text FAQ handler while the conversation is active.
    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(lead.lead_start_cb, pattern=r"^lead:start$"),
            CommandHandler("request", lead.lead_start_cmd),
        ],
        states={
            lead.NAME: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, lead.got_name)],
            lead.CONTACT: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, lead.got_contact)],
            lead.QUESTION: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, lead.got_question)],
        },
        fallbacks=[CommandHandler("cancel", lead.cancel)],
        allow_reentry=True,
    )
    app.add_handler(conv)

    # --- Welcome + FAQ button flows
    app.add_handler(CommandHandler(["start"], welcome.cmd_start))
    app.add_handler(CallbackQueryHandler(faq.faq_menu_cb, pattern=r"^menu:faq$"))
    app.add_handler(CallbackQueryHandler(faq.faq_item_cb, pattern=r"^faq:(\d+)$"))
    app.add_handler(CallbackQueryHandler(welcome.back_home_cb, pattern=r"^menu:home$"))
    app.add_handler(CallbackQueryHandler(faq.owner_handoff_cb, pattern=r"^owner:handoff$"))

    # --- Free text
    app.add_handler(CommandHandler("faqs", faq.cmd_faqs))
    app.add_handler(CommandHandler("help", faq.cmd_help))
    app.add_handler(CommandHandler("id", owner.cmd_id))
    app.add_handler(
        MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, faq.dm_free_text)
    )
    app.add_handler(
        MessageHandler(filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, faq.group_text)
    )

    # --- Owner tools
    app.add_handler(CommandHandler("leads", owner.cmd_leads))
    app.add_handler(CommandHandler("answered", owner.cmd_answered))
    app.add_handler(CommandHandler("pending", owner.cmd_pending))
    app.add_handler(CommandHandler("resolved", owner.cmd_resolved))
    app.add_handler(CommandHandler("leadscsv", owner.cmd_leadscsv))
    app.add_handler(CommandHandler("reload", owner.cmd_reload))

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="Channel Assistant Telegram bot")
    parser.add_argument("--check", action="store_true", help="validate config and exit")
    args = parser.parse_args()

    config_path = os.getenv("CONFIG_PATH", "config.yaml")
    try:
        cfg = Config.load(config_path)
    except ConfigError as exc:
        print(f"[config error] {exc}", file=sys.stderr)
        return 1

    token = os.getenv("BOT_TOKEN", "").strip()
    owner_id = cfg.owner_id or os.getenv("OWNER_ID", "").strip()

    if args.check:
        print("OK   config            :", config_path)
        print(f"     prospect          : {cfg.prospect}")
        print(f"     FAQs              : {len(cfg.faqs)} items")
        print(f"     welcome buttons   : {len(cfg.buttons)}")
        print(f"     keyword threshold : {cfg.threshold}")
        print(f"     group reply mode  : {cfg.group_reply_mode}")
        print(f"     data dir          : {cfg.data_dir}")
        print(f"     owner id          : {owner_id or 'NOT SET (owner alerts disabled)'}")
        print(f"     bot token         : {'present' if token else 'MISSING (put it in .env)'}")
        print(f"     optional LLM hook : {'enabled (' + os.getenv('LLM_MODEL', '') + ')' if cfg_llm_on() else 'off (pure keyword mode)'}")
        return 0

    if not token:
        print("[error] BOT_TOKEN missing. Copy .env.example to .env and add your token "
              "from @BotFather.", file=sys.stderr)
        return 1

    store.init(cfg.data_dir)
    app = build_application(cfg, token)
    log.info("Channel Assistant up — prospect=%s faqs=%d owner=%s",
             cfg.prospect, len(cfg.faqs), owner_id or "unset")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
    return 0


def cfg_llm_on() -> bool:
    from core import llm
    return llm.available()


if __name__ == "__main__":
    sys.exit(main())
