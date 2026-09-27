# Research — base projects evaluated before building

> Objective: build the Channel Assistant **on top of high-rated, battle-tested
> open source** instead of from scratch. Researched Sep 2026.

## 1. Framework comparison (what to build on)

| Framework | Language | Stars* | License | Verdict for this project |
|---|---|---|---|---|
| [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) | Python | ~28k | MIT | ✅ **Chosen.** Highest-rated, best-documented, async, handler/conversation abstractions map 1:1 to the brief (buttons, flows, filters). v22.x current (docs.python-telegram-bot.org v22.6–22.8). |
| [aiogram](https://github.com/aiogram/aiogram) | Python | ~6k | MIT | Strong modern alternative (fully async, routers/middleware). Rejected here: PTB's examples & docs coverage beat it for rapid client re-cuts; PTB conversations are first-class. |
| [Telegraf](https://github.com/telegraf/telegraf) | Node.js | ~8k | MIT | Solid JS option; wrong ecosystem — target stack is Python (client's existing skills, aiogram/PTB freelance demand). |
| [grammY](https://github.com/grammyjs/grammY) | TypeScript | ~4k | MIT | Excellent TS framework, great for serverless webhooks. Same ecosystem reason as Telegraf. |
| [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) | Python | ~7k | GPL-2 | Simpler sync API but GPL license is worse for client templates and no structured conversation state. |

\* stars rounded, Sep 2026. Key tiebreakers: MIT license, official examples for
inline keyboards + conversations, strongest Stack Overflow coverage (verified via
docs + SO activity searches).

## 2. Existing projects / patterns studied (not forked — adapted)

- **PTB official `examples/`** — `inlinekeyboard.py` (button menus → FAQ menu),
  `conversationbot.py` (multi-step lead capture), `persistentconversationbot.py`
  (state patterns). MIT, canonical.
- **Curated landscape** — [awesome-telegram-ai-bots](https://github.com/sm1ck/awesome-telegram-ai-bots):
  confirmed aiogram/grammY/Telegraf as the reference set; no maintained MIT
  "FAQ + lead-capture + owner-alert" template existed combining all three —
  hence this repo.
- **Support-bot templates** (various `telegram-support-bot` repos): common gap —
  they are ticket systems (heavy for a 1–3 day pilot) and none ship a
  one-file client config. The brief explicitly requires "prospect name, FAQ and
  buttons in one config file".
- **Marketplace reality check** (from the brief's own sweep): open freelance
  listings demanded ManyChat/Tidio/n8n **or hand-coded Python** — a clean,
  auditable Python repo is the differentiator, not another no-code setup.

## 3. Zero-cost runtime (the brief's "nothing" promise)

| Component | Choice | Cost |
|---|---|---|
| Bot runtime | local long polling (PTB `run_polling`) | $0 |
| Database | SQLite single file (`data/assistant.db`) | $0 |
| FAQ engine | keyword scoring (`core/matcher.py`) | $0 |
| LLM (optional) | Groq free tier / any OpenAI-compatible (verified active 2026) | $0 |
| Hosting later | free container tiers / own box / systemd | $0 |

No webhook server needed → no domain, no TLS, no cloud bill. Paid APIs are
contractually excluded until the client pays.

## 4. Business framing (why this converts)

- Chatbot platform pricing anchors value: SaaS bot builders run $20–50/mo and
  custom builds quote $5k–50k (2025-2026 industry guides) — a working,
  personalized pilot at pilot-pricing is an easy yes for revenue businesses.
- Target buyers (course sellers, coaches, online stores) already live in
  Telegram/WhatsApp; the demo runs where they already are.
- The "human takes over" fallback (owner alert) is the trust feature that
  separates this from no-code bots that trap customers in loops.

## 5. Sources

- python-telegram-bot docs (v22.6–22.8), docs.python-telegram-bot.org
- github.com/python-telegram-bot/python-telegram-bot (examples/, MIT)
- github.com/sm1ck/awesome-telegram-ai-bots (framework landscape)
- Groq free-tier availability + OpenAI-compatible endpoints (2026 articles)
- Chatbot pricing benchmarks 2025-2026 (chatbotbuilder.net, evacodes.com)
