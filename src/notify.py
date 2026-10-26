"""Optional Telegram notifications (disabled unless TELEGRAM_* env vars are set)."""

from __future__ import annotations

import html
import os

import httpx
from rich.console import Console

console = Console()


def _credentials() -> tuple[str, str] | None:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if not token or not chat_id:
        return None
    return token, chat_id


def send_message(text: str, *, silent: bool = False) -> bool:
    """
    Send a plain-text Telegram message.
    Returns True if sent, False if disabled or failed.
    """
    creds = _credentials()
    if not creds:
        return False
    token, chat_id = creds
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text[:4000],
        "disable_notification": silent,
        "parse_mode": "HTML",
    }
    try:
        with httpx.Client(timeout=20) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
        return True
    except Exception as exc:
        # httpx error text embeds the request URL, which contains the bot token.
        msg = str(exc).replace(token, "***")
        console.print(f"[yellow]Telegram notify failed:[/yellow] {msg}")
        return False


def notify_run_summary(
    *,
    jobs_seen: int,
    jobs_scored: int,
    applied: int,
    skipped: int,
    failed: int,
    top_titles: list[str] | None = None,
) -> None:
    lines = [
        "<b>Naukri Apply run</b>",
        f"Seen: {jobs_seen} · Scored: {jobs_scored}",
        f"Applied: {applied} · Skipped: {skipped} · Failed: {failed}",
    ]
    if top_titles:
        lines.append("")
        lines.append("<b>Top matches</b>")
        for t in top_titles[:8]:
            lines.append(f"• {html.escape(t)}")
    send_message("\n".join(lines))


def notify_error(message: str) -> None:
    send_message(f"<b>Naukri Apply error</b>\n{html.escape(message[:500])}")


def notify_applied(title: str, company: str | None, score: float | None) -> None:
    sc = f" (score {score:.2f})" if score is not None else ""
    send_message(
        f"✅ Applied{sc}\n<b>{html.escape(title)}</b>\n{html.escape(company or '')}",
        silent=True,
    )
