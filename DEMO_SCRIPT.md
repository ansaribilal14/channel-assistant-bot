# Demo Script — record this before any outreach

> Rule from the brief: **Do not say "I built it" until it runs.** Record the
> 60-second proof first. Keep the 2-minute walkthrough ready for live calls.

## Before recording (5 min)

- [ ] Bot running: `python bot.py` (console says `Channel Assistant up`)
- [ ] `config.yaml` uses the **prospect's real business name** and their FAQ wording
- [ ] `owner.id` set to YOUR id — you receive alerts on your phone
- [ ] Demo data only — no real customer names/numbers anywhere
- [ ] Phone + desktop both open (show the owner alert arriving on the phone)
- [ ] Bot link ready: `t.me/<your_bot_username>`

## The 60-second live proof (shot list)

| # | Action | What it proves |
|---|--------|----------------|
| 1 | `/start` | welcome card with 3 buttons, client's name on it |
| 2 | tap **❓ Browse FAQs** → any question | grounded answers, clean UX |
| 3 | type *"how much does it cost?"* | keyword answering works |
| 4 | type *"do you deliver pizza?"* (something unknown) | fallback: "I'll ask the owner" |
| 5 | **cut to your phone**: owner alert with the exact question | the owner never misses a lead |
| 6 | tap **📝 Leave a request** → fill 3 steps | lead capture end-to-end |
| 7 | **cut to phone again**: new-lead alert; desktop: `/leads`, `/leadscsv` | leads are stored & exportable |
| 8 | end card: "Re-cut for YOUR business in 10 minutes — one config file." | the actual offer |

Record with any screen recorder (OBS / phone screen record). No editing needed —
one clean take beats a produced video for credibility.

## The 2-minute walkthrough (live calls / follow-ups)

- 0:00–0:20 — the business problem: repeated questions eat hours; leads lost in DMs
- 0:20–0:50 — live FAQ answering with THEIR questions loaded
- 0:50–1:20 — unknown question → owner alert → human takes over (trust, not a black box)
- 1:20–1:50 — lead flow + CSV export ("your customer list, not mine")
- 1:50–2:00 — the ask: "Want this for your business this week? One config file, your FAQs, live in a day."

## Self-test matrix (run once, every re-cut)

- [ ] `/start` renders with the client's name + 3 buttons
- [ ] Every FAQ button opens and has a « back path
- [ ] Keyword hits: at least 5 phrasings from step 3 above
- [ ] Unknown question → fallback + owner alert arrives
- [ ] Lead flow completes; lead appears in `/leads` and `/leadscsv`
- [ ] `/reload` picks up config edits without restart
- [ ] In a group: bot answers only when @mentioned or replied to
- [ ] `python bot.py --check` passes after every config edit

## Outreach tie-in

- Live demo link = `t.me/<bot_username>` (keep the demo bot running during the week)
- Marketplace bid template (from the brief) points at this live demo + `github.com/ansaribilal14/channel-assistant-bot`
- After each serious reply: re-cut `config.yaml` with *their* name + 3 of their real
  questions, re-record 30 seconds, then send. Personalized demo > perfect demo.
