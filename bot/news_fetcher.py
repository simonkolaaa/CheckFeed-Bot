import feedparser
import re
from datetime import datetime
from bot.config_loader import get_config
from bot.db_news import add_news
from bot.logger import log
from bot.telegram import send_news_message
from bot.db_user import get_users
from bot.utils import cleanHTMLPreview
from bot.ai_summary import generate_ai_summary
from bot.worldy_scraper import scrape_all_worldy

CONFIG = get_config()
SITES = CONFIG["sites"]
BLACKLIST = [w.lower() for w in CONFIG.get("blacklist", [])]
URGENCY_KEYWORDS = [w.lower() for w in CONFIG.get("urgency_keywords", [])]
MACHINE_NAME = CONFIG.get("machine_name", "Bot")
WORLDY_CATEGORIES = CONFIG.get("worldy_categories", ["worldy", "tech", "finance"])


def _is_blacklisted(text):
    """Controlla se il testo contiene parole in blacklist."""
    text_lower = text.lower()
    for bl_word in BLACKLIST:
        if bl_word in text_lower:
            return True
    return False


def _is_urgent(text):
    """Controlla se il testo contiene keyword di urgenza (word boundary match)."""
    text_lower = text.lower()
    for kw in URGENCY_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
            return True
    return False


def _process_news_entry(title, link, source, published, text_content, category):
    """Processa una singola notizia: blacklist, DB, urgenza, AI, notifiche."""

    full_text = f"{title} {text_content}"

    # === 1. BLACKLIST CHECK ===
    if _is_blacklisted(full_text):
        log(f"🚫 Blacklist: scartata '{title}' da {source}")
        return False

    # === 2. Salva in DB ===
    is_new = add_news(title, link, source, published, text_content)
    if not is_new:
        return False  # news già presente

    # === 3. Classifica urgenza ===
    urgent = _is_urgent(full_text)

    # === 4. Genera summary AI (solo per news NON urgenti) ===
    ai_summary = None
    if not urgent:
        ai_summary = generate_ai_summary(text_content)

    # === 5. Prepara preview testuale (fallback se AI non disponibile) ===
    preview = cleanHTMLPreview(text_content)

    # === 6. Notifiche utenti filtrate per keywords ===
    for user in get_users():
        kws = [k.strip().lower() for k in user["keywords"] if k.strip()]
        if not kws:
            continue

        matched_keywords = []
        for kw in kws:
            if re.search(r'\b' + re.escape(kw) + r'\b', full_text.lower()):
                matched_keywords.append(kw)

        if matched_keywords:
            log(f"📨 Notifica inviata a {user['telegram_id']} per keyword: {', '.join(matched_keywords)} | "
                f"{'🚨 URGENTE' if urgent else '📰 Normal'} | Titolo: {title}")

            send_news_message(
                chat_id=user["telegram_id"],
                title=title,
                link=link,
                source=source,
                preview=preview,
                is_urgent=urgent,
                ai_summary=ai_summary,
                category=category,
                machine_name=MACHINE_NAME,
            )

    return True


def fetch_news():
    new_entries = []

    # === FASE 1: Feed RSS ===
    for site in SITES:
        parsed = feedparser.parse(site["url"])
        category = site.get("category", "Tech")

        for entry in parsed.entries:
            link = entry.link
            title = entry.title
            source = site["name"]
            published = entry.get("published", datetime.now().isoformat())
            content_val = entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""
            description = entry.get("description", "")
            text_content = content_val or description or entry.get("summary", "")

            if _process_news_entry(title, link, source, published, text_content, category):
                new_entries.append(link)

    # === FASE 2: Worldy.it Scraping ===
    if WORLDY_CATEGORIES:
        worldy_articles = scrape_all_worldy(
            categories=WORLDY_CATEGORIES,
            max_per_category=5
        )
        for article in worldy_articles:
            if _process_news_entry(
                title=article["title"],
                link=article["link"],
                source=article["source"],
                published=datetime.now().isoformat(),
                text_content=article["title"],  # Worldy non ha contenuto completo dallo scraping
                category=article["category"],
            ):
                new_entries.append(article["link"])

    if new_entries:
        log(f"➕ Aggiunte {len(new_entries)} nuove notizie da {len(SITES)} feed + Worldy.")

