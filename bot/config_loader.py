import json
import os

CONFIG_FILE = "config.json"

# Cache del config decodificato
_config_cache = None


def get_config():
    """
    Carica e restituisce la configurazione.
    Se il config è cifrato (campi enc_*), lo decifra automaticamente.
    Il risultato viene cachato per evitare decifrature ripetute.
    """
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(
            f"❌ Configurazione mancante: {CONFIG_FILE}.\n"
            f"Copia 'config.example.json' in '{CONFIG_FILE}' e personalizzalo."
        )

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Se il config contiene campi cifrati, decripta
    from bot.crypto import is_config_encrypted, decrypt_config
    if is_config_encrypted(config):
        config = decrypt_config(config)

    _config_cache = config
    return config


def reload_config():
    """Forza il ricaricamento del config (utile per aggiornamenti a caldo)."""
    global _config_cache
    _config_cache = None
    return get_config()
