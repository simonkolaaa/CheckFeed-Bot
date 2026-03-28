from threading import Thread
from bot.telegram import TELEGRAM_TOKEN, send_long_message, send_message, send_news_message, send_photo_message, API_BASE
from bot.db_user import activate_user, add_user, deactivate_user, update_keywords
from bot.db_news import get_recent_news
from bot.news_fetcher import fetch_news
from bot.report_generator import generate_report
from bot.logger import log
from bot.config_loader import get_config
from bot.utils import cleanHTMLPreview
from bot.ai_summary import generate_ai_summary
from bot.worldy_scraper import scrape_worldy_category
import requests
import time
import json
import html as html_module

API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
CONFIG = get_config()
MACHINE_NAME = CONFIG.get("machine_name", "Bot")

def build_help_message():
    cfg = get_config()
    sites = cfg.get("sites", [])
    polling = cfg.get("polling_minutes", 10)
    report_time = cfg.get("daily_report_time", "18:00")
    retention = cfg.get("data_retention_days", 7)
    feed_list = "\n".join([f"\u2022 {s['name']}" for s in sites]) if sites else "\u26a0\ufe0f Nessun feed configurato."
    return f"""
\U0001f916 <b>CheckFeed Bot</b> \u2014 servizio attivo.

<b>Comandi disponibili:</b>
/start \u2014 registra l'utente e mostra questo messaggio
/stop \u2014 sospende le notifiche per questo utente
/setkeywords parola1, parola2, PAROLA COMPOSTA \u2014 aggiunge parole chiave (separate da virgole)
/removekeywords parola1, parola2, PAROLA COMPOSTA \u2014 rimuove keyword specifiche
/keywords \u2014 mostra le tue keyword attive
/fetch \u2014 aggiorna manualmente le notizie
/report \u2014 genera e invia il report giornaliero
/latest [n] \u2014 mostra le ultime n notizie (default 5)
/top5 \u2014 digest AI delle 5 cose piu importanti nel tech
/worldy [categoria] \u2014 ultime notizie da Worldy.it
/commands \u2014 elenco rapido comandi

<b>Scheduler:</b>
\u2022 Fetch ogni {polling} minuti
\u2022 Report giornaliero alle {report_time}
\u2022 Retention notizie e log: {retention} giorni

<b>Feed monitorati:</b>
{feed_list}
"""

def handle_commands():
    offset = None
    while True:
        try:
            resp = requests.get(f"{API_URL}/getUpdates", params={"timeout": 10, "offset": offset})
            data = resp.json()

            for result in data.get("result", []):
                offset = result["update_id"] + 1
                message = result.get("message", {})
                text = message.get("text", "")
                if not text:
                    continue
                text = text.strip()
                telegram_id = message["chat"]["id"]
                username = message["chat"].get("username", "")

                if text.startswith("/start"):
                    added = add_user(telegram_id, username)
                    if added:
                        send_message("\U0001f44b Benvenuto! Imposta le tue parole chiave con /setkeywords parola1, parola2, PAROLA COMPOSTA", chat_id=telegram_id)
                    else:
                        activate_user(telegram_id)
                        send_message("\U0001f44b Bentornato! Le notifiche sono attive. Usa /setkeywords per aggiornare.", chat_id=telegram_id)

                    # invia il messaggio di help completo
                    help_msg = build_help_message()
                    send_message(help_msg.strip(), parse_mode="HTML", chat_id=telegram_id)

                elif text.startswith("/stop"):
                    deactivate_user(telegram_id)
                    send_message("\u2705 Hai disattivato le notifiche. Usa /start per riattivarle.", chat_id=telegram_id)

                elif text.startswith("/setkeywords"):
                    keywords_text = text[len("/setkeywords"):].strip()
                    if not keywords_text:
                        send_message("\u2757 Usa: /setkeywords parola1, parola2, PAROLA COMPOSTA, ...", chat_id=telegram_id)
                        continue
                    
                    new_keywords = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]
                    if not new_keywords:
                        send_message("\u2757 Usa: /setkeywords parola1, parola2, PAROLA COMPOSTA, ...", chat_id=telegram_id)
                        continue
                    
                    from bot.db_user import get_users
                    current_user = None
                    for user in get_users():
                        if user["telegram_id"] == telegram_id:
                            current_user = user
                            break
                    
                    existing_keywords = []
                    if current_user and current_user["keywords"]:
                        existing_keywords = [kw.strip() for kw in current_user["keywords"] if kw.strip()]
                    
                    keyword_map = {kw.lower(): kw for kw in existing_keywords}
                    
                    added_keywords = []
                    skipped_keywords = []
                    
                    for new_kw in new_keywords:
                        if new_kw.lower() not in keyword_map:
                            keyword_map[new_kw.lower()] = new_kw
                            added_keywords.append(new_kw)
                        else:
                            skipped_keywords.append(new_kw)
                    
                    final_keywords = existing_keywords + added_keywords
                    
                    if not added_keywords:
                        send_message(f"\u274c Tutte le keyword specificate sono gia presenti.\n\U0001f4dd Keyword attuali: {', '.join(existing_keywords)}", chat_id=telegram_id)
                        continue
                    
                    update_keywords(telegram_id, final_keywords)
                    
                    msg = f"\u2705 Keyword aggiunte: {', '.join(added_keywords)}"
                    if skipped_keywords:
                        msg += f"\n\u26a0\ufe0f Gia presenti: {', '.join(skipped_keywords)}"
                    msg += f"\n\U0001f4dd Totale keyword: {len(final_keywords)}"
                    
                    send_message(msg, chat_id=telegram_id)

                elif text.startswith("/removekeywords"):
                    keywords_text = text[len("/removekeywords"):].strip()
                    if not keywords_text:
                        send_message("\u2757 Usa: /removekeywords parola1, parola2, PAROLA COMPOSTA, ...", chat_id=telegram_id)
                        continue
                    
                    keywords_to_remove = [kw.strip().lower() for kw in keywords_text.split(",") if kw.strip()]
                    if not keywords_to_remove:
                        send_message("\u2757 Usa: /removekeywords parola1, parola2, PAROLA COMPOSTA, ...", chat_id=telegram_id)
                        continue
                    
                    from bot.db_user import get_users
                    current_user = None
                    for user in get_users():
                        if user["telegram_id"] == telegram_id:
                            current_user = user
                            break
                    
                    if not current_user or not current_user["keywords"]:
                        send_message("\u274c Non hai keyword impostate. Usa /setkeywords per aggiungerne.", chat_id=telegram_id)
                        continue
                    
                    original_keywords = [kw.strip() for kw in current_user["keywords"] if kw.strip()]
                    keyword_map = {kw.lower(): kw for kw in original_keywords}
                    
                    keywords_to_remove_original = []
                    keywords_not_found = []
                    
                    for remove_kw in keywords_to_remove:
                        if remove_kw in keyword_map:
                            keywords_to_remove_original.append(keyword_map[remove_kw])
                        else:
                            keywords_not_found.append(remove_kw)
                    
                    if not keywords_to_remove_original:
                        current_display = [keyword_map[k] for k in keyword_map.keys()]
                        send_message(f"\u274c Nessuna delle keyword specificate e stata trovata.\n\U0001f4dd Keyword attuali: {', '.join(current_display)}", chat_id=telegram_id)
                        continue
                    
                    final_keywords = [kw for kw in original_keywords if kw not in keywords_to_remove_original]
                    
                    update_keywords(telegram_id, final_keywords)
                    
                    if final_keywords:
                        send_message(f"\u2705 Keyword rimosse: {', '.join(keywords_to_remove_original)}\n\U0001f4dd Keyword rimanenti: {', '.join(final_keywords)}", chat_id=telegram_id)
                    else:
                        send_message(f"\u2705 Keyword rimosse: {', '.join(keywords_to_remove_original)}\n\U0001f4dd Non hai piu keyword impostate.", chat_id=telegram_id)

                elif text.startswith("/keywords"):
                    from bot.db_user import get_users
                    current_user = None
                    for user in get_users():
                        if user["telegram_id"] == telegram_id:
                            current_user = user
                            break
                    
                    if not current_user or not current_user["keywords"]:
                        send_message("\u274c Non hai keyword impostate.\n\U0001f4a1 Usa /setkeywords per aggiungerne alcune!", chat_id=telegram_id)
                    else:
                        keywords_list = [kw.strip() for kw in current_user["keywords"] if kw.strip()]
                        keywords_count = len(keywords_list)
                        keywords_text = "\n".join([f"\u2022 {kw}" for kw in keywords_list])
                        
                        msg = f"\U0001f4dd <b>Le tue keyword attive ({keywords_count}):</b>\n\n{keywords_text}\n\n\U0001f4a1 Usa /setkeywords per modificare o /removekeywords per rimuovere."
                        send_message(msg, parse_mode="HTML", chat_id=telegram_id)

                elif text.startswith("/commands"):
                    commands_list = """
\U0001f4cb <b>Elenco comandi disponibili:</b>

/start \u2014 registra e mostra informazioni complete
/stop \u2014 sospende le notifiche
/setkeywords parola1, parola2, PAROLA COMPOSTA \u2014 aggiunge keyword (separate da virgole)  
/removekeywords parola1, parola2, PAROLA COMPOSTA \u2014 rimuove keyword specifiche
/keywords \u2014 mostra le tue keyword attive
/fetch \u2014 aggiorna notizie manualmente
/report \u2014 genera report giornaliero
/latest [n] \u2014 mostra ultime n notizie (default 5)
/top5 \u2014 digest AI delle 5 cose piu importanti nel tech
/worldy [categoria] \u2014 ultime notizie da Worldy.it (tech, finance, sport, worldy, music)
/commands \u2014 mostra questo elenco

\U0001f4a1 <i>Usa /start per informazioni complete su feed e scheduler.</i>
"""
                    send_message(commands_list.strip(), parse_mode="HTML", chat_id=telegram_id)

                elif text.startswith("/fetch"):
                    fetch_news()
                    send_message("\u2705 Notizie aggiornate manualmente.", chat_id=telegram_id)

                elif text.startswith("/report"):
                    generate_report(target_chat_id=telegram_id)
                    send_message("\u2705 Report generato manualmente.", chat_id=telegram_id)

                elif text.startswith("/latest"):
                    handle_latest_command(telegram_id, text)

                elif text.startswith("/top5"):
                    handle_top5_command(telegram_id)

                elif text.startswith("/worldy"):
                    handle_worldy_command(telegram_id, text)

        except Exception as e:
            log(f"\u274c Errore comandi Telegram: {e}")
            time.sleep(5)


def handle_latest_command(telegram_id, text):
    parts = text.split()
    n = 5
    if len(parts) > 1 and parts[1].isdigit():
        n = int(parts[1])

    rows = get_recent_news(limit=n)
    if not rows:
        send_message("\u26a0\ufe0f Nessuna notizia disponibile.", chat_id=telegram_id)
        return

    lines = [f"\U0001f4f0 <b>Ultime {len(rows)} notizie</b>:\n"]
    for r in rows:
        title = html_module.escape(r["title"])
        source = html_module.escape(r["source"] or "Sorgente")
        link = r["link"]
        published = r["published_at"] or ""
        preview = cleanHTMLPreview(r.get("content", "") or "")
        lines.append(
            f"<b>{title}</b>\n"
            f"\U0001f4e1 {source} \u2014 {published[:16]}\n"
            f"<i>{preview}</i>\n"
            f"\U0001f517 <a href=\"{link}\">Leggi</a>\n"
        )

    lines.append(f"\n\U0001f5a5\ufe0f {html_module.escape(MACHINE_NAME)}")
    send_long_message("\n\n".join(lines), chat_id=telegram_id, parse_mode="HTML")


def handle_top5_command(telegram_id):
    """Genera un digest AI: le 5 cose piu importanti nel mondo tech."""
    send_message("\u23f3 Genero il digest AI delle top 5 tech news...", chat_id=telegram_id)

    rows = get_recent_news(limit=15)
    if not rows:
        send_message("\u26a0\ufe0f Nessuna notizia disponibile per generare il digest.", chat_id=telegram_id)
        return

    titles_text = "\n".join([f"- {r['title']} ({r['source']})" for r in rows])

    try:
        import google.generativeai as genai

        config = get_config()
        api_key = config.get("gemini_api_key", "")
        if not api_key or api_key.startswith("INSERISCI"):
            send_message("\u26a0\ufe0f API Gemini non configurata.", chat_id=telegram_id)
            return

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        prompt = (
            "Sei un giornalista tech italiano. Dalla seguente lista di notizie recenti, "
            "seleziona le 5 piu importanti e rilevanti per il mondo della tecnologia. "
            "Per ciascuna, scrivi un titolo breve e una spiegazione di 1 riga. "
            "Formatta cosi (HTML Telegram):\n"
            "1. <b>Titolo</b>\nSpiegazione breve\n\n"
            "2. <b>Titolo</b>\nSpiegazione breve\n\n"
            "...e cosi via fino a 5.\n"
            "Rispondi esclusivamente in italiano. Non aggiungere introduzioni.\n\n"
            f"Notizie disponibili:\n{titles_text}"
        )

        response = model.generate_content(prompt)
        digest = response.text.strip()

        msg = f"\U0001f525 <b>Top 5 Tech News</b>\n\n{digest}\n\n\U0001f5a5\ufe0f {html_module.escape(MACHINE_NAME)}"
        send_long_message(msg, chat_id=telegram_id, parse_mode="HTML")
        log(f"\U0001f525 Digest Top 5 inviato a {telegram_id}")

    except Exception as e:
        log(f"\u274c Errore generazione Top 5: {e}")
        send_message(f"\u274c Errore nella generazione del digest: {e}", chat_id=telegram_id)


def handle_worldy_command(telegram_id, text):
    """Mostra le ultime notizie da Worldy.it con foto e descrizione."""
    parts = text.split()
    category = "tech"
    if len(parts) > 1:
        category = parts[1].lower()

    valid_categories = ["worldy", "tech", "finance", "sport", "music"]
    if category not in valid_categories:
        send_message(
            f"\u26a0\ufe0f Categoria non valida. Usa: {', '.join(valid_categories)}\n"
            f"Esempio: /worldy tech",
            chat_id=telegram_id
        )
        return

    send_message(f"\u23f3 Scarico le ultime notizie da Worldy/{category} con foto...", chat_id=telegram_id)

    articles = scrape_worldy_category(category, max_articles=5, fetch_details=True)
    if not articles:
        send_message(f"\u26a0\ufe0f Nessun articolo trovato su Worldy/{category}.", chat_id=telegram_id)
        return

    sent = 0
    for a in articles:
        title = html_module.escape(a["title"])
        link = a["link"]
        image_url = a.get("image_url")
        description = a.get("description", "") or ""

        if image_url:
            # Invia come foto con didascalia
            caption = f"\U0001f30d <b>{title}</b>\n\n"
            if description:
                desc_short = description[:300] + "..." if len(description) > 300 else description
                caption += f"{html_module.escape(desc_short)}\n\n"
            caption += f"#Worldy #{category.capitalize()}"

            send_photo_message(
                chat_id=telegram_id,
                photo_url=image_url,
                caption=caption,
                link=link
            )
            sent += 1
            time.sleep(0.5)  # evita rate limit
        else:
            # Fallback: invia come testo se non c'e immagine
            msg = f"\U0001f30d <b>{title}</b>\n"
            if description:
                desc_short = description[:300] + "..." if len(description) > 300 else description
                msg += f"\n{html_module.escape(desc_short)}\n"
            msg += f"\n\U0001f517 <a href=\"{link}\">Leggi su Worldy</a>"
            send_message(msg, parse_mode="HTML", chat_id=telegram_id)
            sent += 1
            time.sleep(0.5)

    send_message(f"\u2705 Inviate {sent} notizie da Worldy/{category}.", chat_id=telegram_id)


def start_telegram_listener():
    Thread(target=handle_commands, daemon=True).start()


def normalize_text(text):
    """Normalizza il testo sostituendo diversi tipi di apostrofi"""
    return text.replace("\u2018", "'").replace("\u2019", "'")
