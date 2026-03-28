# bot/telegram.py
import requests
import time
import html
import json
from bot.config_loader import get_config
from bot.db_user import get_users
from bot.logger import log
from bot.utils import get_category_hashtag

CONFIG = get_config()
TELEGRAM_TOKEN = CONFIG["telegram_token"]
DISABLE_WEB_PAGE_PREVIEW = CONFIG.get("disable_web_page_preview", True)
API_BASE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Parametri
MAX_MSG_LEN = 4000         # Telegram ~4096, resto conservativo
SLEEP_BETWEEN_MSGS = 0.35  # evita di colpire rate limits

def send_message(text, parse_mode=None, chat_id=None, disable_web_page_preview=None):
    """Invia un messaggio Telegram (a uno o più utenti)."""
    if chat_id is None:
        users = get_users()
        for user in users:
            uid = user.get("telegram_id")
            if uid:
                _send_single_message(text, parse_mode=parse_mode, chat_id=uid)
        return

    return _send_single_message(text, parse_mode=parse_mode, chat_id=chat_id, disable_web_page_preview=disable_web_page_preview)


def _send_single_message(text, parse_mode=None, chat_id=None, disable_web_page_preview=None):
    """Funzione privata: invia un singolo messaggio a Telegram."""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": DISABLE_WEB_PAGE_PREVIEW if disable_web_page_preview is None else disable_web_page_preview
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        resp = requests.post(f"{API_BASE}/sendMessage", data=payload, timeout=15)
        try:
            data = resp.json()
        except ValueError:
            data = {"ok": False, "status_code": resp.status_code, "text": resp.text}

        if not resp.ok or not data.get("ok"):
            log(f"❌ Telegram error {resp.status_code} - chat_id={chat_id} - resp={data}")
            return {"ok": False, "status_code": resp.status_code, "data": data}

        return {"ok": True, "result": data.get("result")}

    except Exception as e:
        log(f"❌ Errore invio Telegram: {e}")
        return {"ok": False, "exception": str(e)}



def send_long_message(text, chat_id, parse_mode="HTML"):
    """
    Spezza e invia un testo lungo in più messaggi rispettando il limite.
    Ritorna lista di esiti.
    """
    # Normalizza input
    if not text:
        return []

    parts = []
    remaining = text.strip()

    while remaining:
        if len(remaining) <= MAX_MSG_LEN:
            parts.append(remaining)
            break

        # cerca taglio intelligente: doppia newline > newline > space
        cut = remaining.rfind("\n\n", 0, MAX_MSG_LEN)
        if cut == -1:
            cut = remaining.rfind("\n", 0, MAX_MSG_LEN)
        if cut == -1:
            cut = remaining.rfind(" ", 0, MAX_MSG_LEN)
        if cut == -1 or cut < int(MAX_MSG_LEN * 0.6):
            cut = MAX_MSG_LEN

        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()

    results = []
    for p in parts:
        res = send_message(p, parse_mode=parse_mode, chat_id=chat_id)
        results.append(res)
        time.sleep(SLEEP_BETWEEN_MSGS)
    return results


def send_news_message(chat_id, title, link, source, preview, is_urgent,
                      ai_summary=None, category="Tech", machine_name="Bot"):
    """
    Invia una news formattata con InlineKeyboard e sistema di urgenza.

    - 🚨 Errore di Prezzo → notifica con suono (disable_notification=False)
    - 📰 Tech News → notifica silenziosa (disable_notification=True)
    - Bottone inline "🔗 Leggi l'articolo" con link alla fonte
    - Footer con hashtag categoria e nome macchina
    """
    emoji = "🚨" if is_urgent else "📰"
    label = "Errore di Prezzo" if is_urgent else "Tech News"
    hashtag = get_category_hashtag(category)

    # Costruzione messaggio
    text_parts = [
        f"{emoji} <b>{label}</b>",
        "",
        f"<b>{html.escape(title)}</b>",
        f"📡 {html.escape(source)}",
        "",
    ]

    # Riassunto AI o preview testuale
    if ai_summary:
        text_parts.append("📌 <b>In breve:</b>")
        text_parts.append(ai_summary)
        text_parts.append("")
    elif preview:
        text_parts.append(f"<i>{preview}</i>")
        text_parts.append("")

    # Footer
    text_parts.append(f"{hashtag} | 🖥️ {html.escape(machine_name)}")

    text = "\n".join(text_parts)

    # InlineKeyboardButton con link alla fonte
    keyboard = {
        "inline_keyboard": [[
            {"text": "🔗 Leggi l'articolo", "url": link}
        ]]
    }

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "disable_notification": not is_urgent,
        "reply_markup": json.dumps(keyboard)
    }

    try:
        resp = requests.post(f"{API_BASE}/sendMessage", data=payload, timeout=15)
        try:
            data = resp.json()
        except ValueError:
            data = {"ok": False, "status_code": resp.status_code, "text": resp.text}

        if not resp.ok or not data.get("ok"):
            log(f"❌ Telegram news error {resp.status_code} - chat_id={chat_id} - resp={data}")
            return {"ok": False, "status_code": resp.status_code, "data": data}

        return {"ok": True, "result": data.get("result")}

    except Exception as e:
        log(f"❌ Errore invio news Telegram: {e}")
        return {"ok": False, "exception": str(e)}


def send_photo_message(chat_id, photo_url, caption, link=None):
    """
    Invia una foto con didascalia su Telegram.
    Se link e' fornito, aggiunge un InlineKeyboardButton.
    """
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML",
    }

    if link:
        keyboard = {
            "inline_keyboard": [[
                {"text": "\U0001f517 Leggi su Worldy", "url": link}
            ]]
        }
        payload["reply_markup"] = json.dumps(keyboard)

    try:
        resp = requests.post(f"{API_BASE}/sendPhoto", data=payload, timeout=15)
        try:
            data = resp.json()
        except ValueError:
            data = {"ok": False, "status_code": resp.status_code, "text": resp.text}

        if not resp.ok or not data.get("ok"):
            log(f"❌ Telegram photo error {resp.status_code} - chat_id={chat_id} - resp={data}")
            return {"ok": False, "status_code": resp.status_code, "data": data}

        return {"ok": True, "result": data.get("result")}

    except Exception as e:
        log(f"❌ Errore invio foto Telegram: {e}")
        return {"ok": False, "exception": str(e)}
