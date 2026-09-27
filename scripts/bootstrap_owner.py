#!/usr/bin/env python3
"""One-shot bootstrap for the Channel Assistant demo bot.

Flow:
  1. Verify the bot token (getMe) and print the bot identity.
  2. If OWNER_ID is already set in .env -> hand straight to the bot.
  3. Otherwise long-poll getUpdates and wait for the owner's first message;
     the first human who messages the bot becomes the owner:
       - OWNER_ID is written into .env
       - a confirmation DM is sent back
       - the process exec()s into the real bot (same PID, fresh config)

Usage:
    BOT_TOKEN=... python3 scripts/bootstrap_owner.py   # from repo root
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def api(token: str, method: str, data: dict | None = None) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    if data:
        req = urllib.request.Request(url, urllib.parse.urlencode(data).encode())
    else:
        req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())


def read_env() -> tuple[list[str], dict[str, str]]:
    env_path = ROOT / ".env"
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    kv = {}
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip()
    return lines, kv


def main() -> int:
    lines, kv = read_env()
    token = (os.getenv("BOT_TOKEN") or kv.get("BOT_TOKEN") or "").strip()
    if not token:
        print("[bootstrap] BOT_TOKEN missing (set it in .env)", file=sys.stderr)
        return 1

    me = api(token, "getMe")
    if not me.get("ok"):
        print(f"[bootstrap] token rejected: {me}", file=sys.stderr)
        return 1
    bot = me["result"]
    print(f"[bootstrap] token OK — bot @{bot.get('username')} (id {bot.get('id')})")
    if kv.get("OWNER_ID", "").strip():
        print(f"[bootstrap] OWNER_ID already set ({kv['OWNER_ID']}) — starting bot")
        subprocess.run([sys.executable, "bot.py"], cwd=ROOT)
        return 0

    print("[bootstrap] waiting for the owner's first message (send /start to the bot)...")
    offset: int | None = None
    deadline = time.time() + 6 * 60 * 60  # give up after 6h
    while time.time() < deadline:
        params: dict = {"timeout": 30, "allowed_updates": json.dumps(["message"])}
        if offset is not None:
            params["offset"] = offset
        try:
            resp = api(token, "getUpdates", params)
        except Exception as exc:  # noqa: BLE001 — network hiccups must not kill bootstrap
            print(f"[bootstrap] getUpdates error: {exc}; retrying")
            time.sleep(2)
            continue
        for upd in resp.get("result", []):
            offset = upd["update_id"] + 1
            msg = upd.get("message") or {}
            frm = msg.get("from") or {}
            if frm.get("is_bot") or not frm.get("id"):
                continue
            uid = frm["id"]
            name = frm.get("first_name", "there")

            # persist OWNER_ID into .env (replace or append the line)
            out, replaced = [], False
            for line in lines:
                if line.startswith("OWNER_ID="):
                    out.append(f"OWNER_ID={uid}")
                    replaced = True
                else:
                    out.append(line)
            if not replaced:
                out.append(f"OWNER_ID={uid}")
            (ROOT / ".env").write_text("\n".join(out) + "\n")

            try:
                api(token, "sendMessage", {
                    "chat_id": uid,
                    "text": f"✅ Setup complete, {name}! You are now the owner of this bot.\n\n"
                            f"Owner alerts will arrive here. Send /start to begin the demo.",
                })
            except Exception as exc:  # noqa: BLE001
                print(f"[bootstrap] confirmation DM failed (owner may need to /start first): {exc}")

            print(f"[bootstrap] OWNER_ID captured: {uid} — handing over to the bot")
            os.execv(sys.executable, [sys.executable, "bot.py"])  # replace process with real bot
        # continue polling
    print("[bootstrap] timed out waiting for owner", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
