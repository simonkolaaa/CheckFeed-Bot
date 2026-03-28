import google.generativeai as genai
from bot.config_loader import get_config
from bot.logger import log

# Cache della configurazione Gemini
_gemini_configured = False


def _ensure_configured():
    """Configura Gemini API una sola volta."""
    global _gemini_configured
    if _gemini_configured:
        return True

    config = get_config()
    api_key = config.get("gemini_api_key", "")
    if not api_key or api_key == "INSERISCI_LA_TUA_API_KEY_GEMINI":
        return False

    genai.configure(api_key=api_key)
    _gemini_configured = True
    return True


def generate_ai_summary(content_text):
    """
    Genera un riassunto in 3 punti stile Worldy.it usando Google Gemini.
    Restituisce il testo formattato o None in caso di errore/API non configurata.
    """
    if not content_text or len(content_text.strip()) < 50:
        return None

    if not _ensure_configured():
        return None

    # Limita il contenuto per evitare costi eccessivi
    truncated = content_text[:3000]

    prompt = (
        "Sei un assistente editoriale. Riassumi questa notizia in esattamente 3 punti elenco "
        "brevi, chiari e pronti per la lettura rapida su mobile. "
        "Ogni punto deve iniziare con '• ' e stare su una sola riga. "
        "Non aggiungere titoli, introduzioni o conclusioni. "
        "Rispondi esclusivamente in italiano.\n\n"
        f"{truncated}"
    )

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        summary = response.text.strip()

        # Validazione: deve contenere almeno 2 bullet points
        if summary.count("•") < 2:
            log(f"⚠️ Gemini ha restituito un riassunto non valido, scarto.")
            return None

        return summary

    except Exception as e:
        log(f"⚠️ Errore Gemini AI: {e}")
        return None
