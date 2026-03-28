"""
Scraper per Worldy.it - estrae notizie con immagini e descrizioni.
Non ha feed RSS, quindi usiamo scraping HTML + meta tag OG.
"""

import requests
from bs4 import BeautifulSoup
from bot.logger import log

BASE_URL = "https://worldy.com"

# Categorie disponibili su Worldy
WORLDY_CATEGORIES = {
    "worldy": f"{BASE_URL}/worldy",
    "tech": f"{BASE_URL}/tech",
    "finance": f"{BASE_URL}/finance",
    "sport": f"{BASE_URL}/sport",
    "music": f"{BASE_URL}/music",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def _fetch_article_details(url):
    """
    Apre la pagina dell'articolo e estrae immagine OG e descrizione OG.
    Restituisce (image_url, description) o (None, None) in caso di errore.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Estrai og:image
        og_image = soup.find("meta", property="og:image")
        image_url = og_image["content"] if og_image and og_image.get("content") else None

        # Estrai og:description
        og_desc = soup.find("meta", property="og:description")
        description = og_desc["content"] if og_desc and og_desc.get("content") else None

        return image_url, description

    except Exception as e:
        log(f"⚠️ Errore fetch dettagli articolo {url}: {e}")
        return None, None


def scrape_worldy_category(category="tech", max_articles=10, fetch_details=False):
    """
    Scrapa le ultime notizie di una categoria Worldy.
    Se fetch_details=True, apre ogni articolo per estrarre immagine e descrizione.
    Restituisce una lista di dict con: title, link, category, source, [image_url, description].
    """
    url = WORLDY_CATEGORIES.get(category.lower())
    if not url:
        log(f"⚠️ Categoria Worldy '{category}' non trovata.")
        return []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        log(f"❌ Errore scraping Worldy ({category}): {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = []

    # Trova tutti i link agli articoli (URL formato: /post/...)
    seen_links = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]

        # Filtra solo i link agli articoli
        if "/post/" not in href:
            continue

        # Normalizza URL
        if href.startswith("/"):
            href = BASE_URL + href

        # Evita duplicati
        if href in seen_links:
            continue
        seen_links.add(href)

        # Estrai il titolo dal testo del link
        title = a_tag.get_text(strip=True)
        if not title or len(title) < 10:
            continue

        article = {
            "title": title,
            "link": href,
            "source": f"Worldy ({category.capitalize()})",
            "category": category.capitalize(),
            "image_url": None,
            "description": None,
        }

        # Se richiesto, scarica i dettagli dell'articolo
        if fetch_details:
            image_url, description = _fetch_article_details(href)
            article["image_url"] = image_url
            article["description"] = description

        articles.append(article)

        if len(articles) >= max_articles:
            break

    log(f"📰 Worldy/{category}: trovati {len(articles)} articoli" +
        (" (con dettagli)" if fetch_details else "") + ".")
    return articles


def scrape_all_worldy(categories=None, max_per_category=5):
    """
    Scrapa piu categorie Worldy e restituisce tutte le notizie.
    Non scarica i dettagli per il fetch automatico (troppo lento).
    """
    if categories is None:
        categories = ["worldy", "tech", "finance"]

    all_articles = []
    for cat in categories:
        articles = scrape_worldy_category(cat, max_articles=max_per_category, fetch_details=False)
        all_articles.extend(articles)

    return all_articles
