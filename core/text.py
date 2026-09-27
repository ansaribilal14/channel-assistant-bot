"""Text safety — bulletproof Telegram HTML for config-authored strings.

Two trust levels:
  * TRUSTED but fragile: text from config.yaml. It may intentionally use
    formatting tags (<b>...</b>) but must survive literal "<" and "&"
    characters (e.g. "Price < $99 & shipping") without Telegram 400 errors.
    -> safe_html(): escape everything, then re-enable a tiny tag whitelist.
  * UNTRUSTED: user-supplied values (names, questions, contacts).
    -> plain html.escape() only, never un-escaped.

Ordering rule: apply safe_html() to a config TEMPLATE *before* injecting
escaped user values (Config.render does the injection).
"""

from __future__ import annotations

import html

# Tags Telegram HTML supports and we re-enable after escaping.
_WHITELIST = ("b", "i", "u", "s", "code", "pre")


def safe_html(text: str) -> str:
    """Escape all HTML, then un-escape only whitelisted formatting tags."""
    escaped = html.escape(text or "", quote=False)
    for tag in _WHITELIST:
        escaped = escaped.replace(f"&lt;{tag}&gt;", f"<{tag}>")
        escaped = escaped.replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    return escaped
