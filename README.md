# Channel Assistant 🤖

**A zero-cost, config-driven Telegram assistant that answers customer FAQs, captures leads, and alerts the owner — built to demo to a client in minutes and re-cut for a new client in ~10.**

Built on [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) — the highest-rated Python Telegram framework (MIT, ~28k★) — with patterns adapted from its official examples. No LLM required, no paid APIs, runs locally with long polling.

```
Revenue business (courses, coaching, store)
        │  wants: fewer repeated questions, more captured leads
        ▼
Channel Assistant (this repo)
  • welcome buttons          • keyword FAQ answers (10 editable Q&As)
  • "leave a request" flow   • lead saved to SQLite + CSV export
  • can't answer? → "I'll ask the owner" → instant owner alert
```

---

## What it does (demo brief, exactly)

| Brief requirement | Where |
|---|---|
| Welcome buttons in bot DM | `config.yaml → welcome.buttons` → inline keyboard |
| Answers grounded in 10 editable FAQs | `config.yaml → faq.items` + keyword matcher (`core/matcher.py`) |
| "I'll ask the owner" when it can't answer | fallback text + unanswered log + owner alert |
| Lead capture in bot DM | 3-step conversation → SQLite (`data/assistant.db`) |
| Owner alert | instant Telegram message to `owner.id` |
| Auto-welcome new group members | `group.welcome_text` → `new_members` handler (bot also introduces itself when added to a group) |
| One config file per prospect | everything client-specific lives in `config.yaml` |
| Local long polling, no paid deps | `python bot.py` — only `python-telegram-bot` |
| Keyword matching, LLM optional | pure keyword by default; free OpenAI-compatible tier optional |
| Formatting-safe messages | `core/text.py` escapes `<`/`&` in config text; `<b> <i> <u> <s> <code> <pre>` whitelisted |

---

## 5-minute setup

**1. Create the bot** — open [@BotFather](https://t.me/BotFather) in Telegram → `/newbot` → copy the token.

**2. Configure**
```bash
cp .env.example .env          # paste BOT_TOKEN
cp config.example.yaml config.yaml
```

**3. Install & validate** (Python 3.9+; developed on 3.12)
```bash
pip install -r requirements.txt
python bot.py --check         # validates config, prints what's set/missing
```

**4. Get your owner id** — run the bot, open your bot in Telegram, send `/id`, copy the user id into `config.yaml → owner.id` (or `.env → OWNER_ID`). **Important:** send `/start` to the bot from your own account first — Telegram does not allow bots to message a user first.

**5. Run**
```bash
python bot.py
```

Docker alternative: `docker build -t channel-assistant . && docker run --env-file .env -v $(pwd)/config.yaml:/app/config.yaml channel-assistant`

---

## Try it (2 minutes)

1. `/start` → welcome card with **❓ Browse FAQs · 📝 Leave a request · 👤 Talk to the owner**
2. Tap a FAQ → clean answer → « All questions
3. Type *"how much does it cost?"* → matched by keywords (try *"pricing"*, *"fees"*, *"trial class"*, *"when are classes"*)
4. Type something unknown (*"do you sell pizza?"*) → fallback + **you get an owner alert**
5. `📝 Leave a request` → name → contact → need → thank-you + **lead alert**
6. Owner commands: `/leads` · `/answered <id>` · `/pending` · `/resolved <id>` · `/leadscsv` (CSV export)
7. `/reload` after editing `config.yaml` — no restart needed
8. Add the bot to a test group → it introduces itself; kick & re-add a friend (or your second account) → **auto-welcome with buttons**; mention `@yourbot how much is it?` in the group → keyword answer with a DM link for requests

## Owner commands (owner only)

| Command | What |
|---|---|
| `/leads` | last 10 captured leads |
| `/answered <id>` | mark a lead handled |
| `/pending` | questions the bot couldn't answer (add these to your FAQs!) |
| `/resolved <id>` | mark an unanswered question handled |
| `/leadscsv` | download all leads as CSV |
| `/reload` | re-read `config.yaml` live |
| `/id` | show chat/user id (setup helper) |

---

## Re-cut for a new client in ~10 minutes

1. Open `config.yaml` → change `prospect`
2. Rewrite `welcome.text` in the client's voice
3. Replace the 10 FAQ items with the client's real questions + answers (grab their website FAQ / WhatsApp replies)
4. Adjust keywords so their customers' wording matches (any user question that fell through → `/pending` shows it → add keywords)
5. Set `owner.id` to the client's Telegram id
6. `python bot.py --check` → run → record the demo

The full test script and the 60-second recording shot-list are in **[DEMO_SCRIPT.md](DEMO_SCRIPT.md)**.

## Optional: free LLM fallback (never a paid dependency)

Keyword matching handles the demo. If you want softer handling of odd phrasings, add a **free** OpenAI-compatible endpoint (e.g. [Groq](https://console.groq.com) free tier) to `.env`:

```env
LLM_API_BASE=https://api.groq.com/openai/v1
LLM_API_KEY=gsk_...
LLM_MODEL=llama-3.3-70b-versatile
```

The LLM is grounded strictly on your FAQ content; on any failure it silently falls back to the owner-alert path. Leave it empty and the bot works 100% without it.

## Deploying later (still $0)

Long polling on a machine you already have costs nothing. When a paying client needs 24/7: a $0-tier container host (Railway/Render free tier), a home server, or `systemd`:

```ini
# /etc/systemd/system/channel-assistant.service
[Service]
WorkingDirectory=/opt/channel-assistant
ExecStart=/usr/bin/python3 bot.py
Restart=always
[Install]
WantedBy=multi-user.target
```

## Troubleshooting

- **Owner alerts don't arrive** → the owner hasn't sent `/start` to the bot yet (Telegram restriction), or `owner.id` is empty.
- **Bot is silent in groups** → with BotFather privacy mode ON (default) the bot sees mentions, replies and join events only — exactly enough for mention mode + auto-welcome. For free-text listening in groups, disable privacy mode in BotFather (`/setprivacy` → Disable) and re-add the bot.
- **FAQ answer shows raw `&amp;` or breaks with "can't parse entities"** → shouldn't happen anymore (`core/text.py` escapes config text, whitelists formatting tags). If you intentionally want `<b>` in answers, it's supported. Arbitrary tags like `<a>` are intentionally not whitelisted.
- **Startup warning about per_message** → expected and harmless; already suppressed in code.
- **It missed a question I expected it to answer** → lower `faq.threshold` (e.g. 1.5) or add keywords.

## Project layout

```
bot.py                  entry point (--check for dry validation)
core/config.py          one-file client config loader + validation
core/matcher.py         keyword scoring (exact/phrase/prefix/substring)
core/text.py            safe_html: escape < & then whitelist b/i/u/s/code/pre
core/llm.py             optional free OpenAI-compatible fallback
core/store.py           SQLite: leads + unanswered (+ CSV export)
handlers/welcome.py     /start + welcome buttons (group-aware)
handlers/faq.py         FAQ menu, keyword answering, group mode, auto-welcome, handoff
handlers/lead.py        3-step lead capture conversation
handlers/owner.py       owner alerts + management commands
tests/test_smoke.py     17 tests: config, matcher, safe_html, store, group welcome, wiring
```

## Credits & provenance

Built on the shoulders of top-rated open source:
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) (~28k★, MIT) — async framework, handler patterns adapted from the official `examples/` (inline keyboard, conversation handlers)
- [awesome-telegram-ai-bots](https://github.com/sm1ck/awesome-telegram-ai-bots) & [aiogram](https://github.com/aiogram/aiogram), [grammY](https://github.com/grammyjs/grammY) — evaluated in `RESEARCH.md` before choosing PTB

MIT license. Free to fork, adapt, and ship.
