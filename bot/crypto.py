"""
Modulo di cifratura per proteggere i dati sensibili del config.
Usa Fernet (AES-128-CBC + HMAC) con chiave derivata via PBKDF2 da una password master.

La password master viene letta dalla variabile d'ambiente CHECKFEED_SECRET.
"""

import os
import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Salt fisso per derivazione chiave (può essere cambiato, ma deve restare costante)
# Generato una volta e hardcodato — non è un segreto, serve solo per PBKDF2
SALT = b"CheckFeed_Bot_2026_Salt_v1"

# Campi sensibili da cifrare nel config
SENSITIVE_FIELDS = ["telegram_token", "gemini_api_key"]


def _get_master_password():
    """Legge la password master dalla variabile d'ambiente."""
    secret = os.environ.get("CHECKFEED_SECRET")
    if not secret:
        raise EnvironmentError(
            "❌ Variabile d'ambiente CHECKFEED_SECRET non impostata!\n"
            "Imposta la password master con:\n"
            "  Windows:  set CHECKFEED_SECRET=la_tua_password_segreta\n"
            "  Linux:    export CHECKFEED_SECRET=la_tua_password_segreta\n"
            "  Docker:   -e CHECKFEED_SECRET=la_tua_password_segreta"
        )
    return secret


def _derive_key(password: str) -> bytes:
    """Deriva una chiave Fernet dalla password usando PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=480_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
    return key


def get_fernet():
    """Restituisce un'istanza Fernet pronta per cifrare/decifrare."""
    password = _get_master_password()
    key = _derive_key(password)
    return Fernet(key)


def encrypt_value(value: str) -> str:
    """Cifra un singolo valore stringa. Restituisce il ciphertext in base64."""
    f = get_fernet()
    encrypted = f.encrypt(value.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_value(encrypted_value: str) -> str:
    """Decifra un singolo valore stringa."""
    f = get_fernet()
    decrypted = f.decrypt(encrypted_value.encode("utf-8"))
    return decrypted.decode("utf-8")


def encrypt_config(config: dict) -> dict:
    """
    Prende un config dict e restituisce una copia con i campi sensibili cifrati.
    I campi cifrati vengono rinominati con prefisso 'enc_' per identificarli.
    """
    encrypted = config.copy()
    for field in SENSITIVE_FIELDS:
        if field in encrypted and encrypted[field]:
            plain_value = encrypted[field]
            # Non cifrare valori placeholder
            if plain_value.startswith("INSERISCI"):
                continue
            encrypted[f"enc_{field}"] = encrypt_value(plain_value)
            del encrypted[field]
    return encrypted


def decrypt_config(config: dict) -> dict:
    """
    Prende un config dict con campi 'enc_*' e li decifra,
    restituendo il config con i nomi originali.
    """
    decrypted = config.copy()
    for field in SENSITIVE_FIELDS:
        enc_key = f"enc_{field}"
        if enc_key in decrypted:
            decrypted[field] = decrypt_value(decrypted[enc_key])
            del decrypted[enc_key]
    return decrypted


def is_config_encrypted(config: dict) -> bool:
    """Verifica se il config contiene campi cifrati."""
    return any(f"enc_{field}" in config for field in SENSITIVE_FIELDS)
