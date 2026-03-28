import json
import requests
from datetime import datetime
from bot.db_news import get_today_news
from bot.db_user import get_users
from bot.logger import log
from bot.telegram import send_long_message, API_BASE, SLEEP_BETWEEN_MSGS
from bot.config_loader import get_config
from bot.utils import cleanHTMLPreview
import html as html_module
import time

CONFIG = get_config()
MACHINE_NAME = CONFIG.get("machine_name", "Bot")


def _send_report_message(chat_id, text, news_links=None):
    """
    Invia il report con un bottone InlineKeyboard opzionale
    se c'è un solo link (altrimenti solo testo lungo).
    """
    # Per il report usiamo send_long_message perché il report può essere lungo
    send_long_message(text, chat_id=chat_id, parse_mode="HTML")


def generate_report(target_chat_id=None):
    today_news = get_today_news()

    if not today_news:
        msg = "🗓️ Nessuna notizia per oggi."
        if target_chat_id:
            send_long_message(msg, chat_id=target_chat_id, parse_mode="HTML")
        else:
            users = get_users()
            for u in users:
                send_long_message(msg, chat_id=u["telegram_id"], parse_mode="HTML")
        log("🗓️ Nessuna notizia per oggi.")
        return

    lines = [f"📢 <b>Report del {datetime.now():%d/%m/%Y}</b> — {len(today_news)} notizie trovate\n"]

    for n in today_news:
        title = html_module.escape((n.get("title") or "Titolo non disponibile").strip())
        source = html_module.escape(n.get("source") or "Sorgente sconosciuta")
        link = n.get("link") or ""
        content = n.get("content") or ""
        preview = cleanHTMLPreview(content)
        published = n.get("published_at", "")[:16]

        lines.append(
            f"🗞️ <b>{title}</b>\n"
            f"📡 {source} — {published}\n"
            f"<i>{preview}</i>\n"
            f"🔗 <a href=\"{link}\">Leggi</a>\n"
        )

    # Footer
    lines.append(f"\n🖥️ {html_module.escape(MACHINE_NAME)}")

    text = "\n".join(lines).strip()

    # log diagnostico prima dell'invio
    log(f"🔎 Report length: {len(text)} chars; preview: {text[:200]!r}")

    if target_chat_id:
        send_long_message(text, chat_id=target_chat_id, parse_mode="HTML")
        log(f"📄 Report inviato manualmente a {target_chat_id}.")
    else:
        users = get_users()
        if not users:
            log("⚠️ Nessun utente attivo per l'invio del report.")
            return
        sent = 0
        for u in users:
            try:
                send_long_message(text, chat_id=u["telegram_id"], parse_mode="HTML")
                sent += 1
            except Exception as e:
                log(f"⚠️ Errore nell'invio report a {u['telegram_id']}: {e}")
        log(f"📄 Report Telegram inviato a {sent} utenti ({len(today_news)} notizie).")
