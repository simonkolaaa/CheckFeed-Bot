#!/usr/bin/env python3
"""
Script interattivo per cifrare il config.json.

Uso:
  1. Imposta la variabile d'ambiente CHECKFEED_SECRET con la tua password master
  2. Esegui: python encrypt_config.py
  3. Il file config.json verrà sovrascritto con i campi sensibili cifrati
  4. Un backup del file originale viene salvato come config.backup.json

I campi cifrati nel config avranno il prefisso 'enc_' (es. enc_telegram_token).
"""

import json
import os
import shutil
import sys


def main():
    config_path = "config.json"

    # Verifica che CHECKFEED_SECRET sia impostata
    if not os.environ.get("CHECKFEED_SECRET"):
        print("❌ Errore: variabile d'ambiente CHECKFEED_SECRET non impostata!")
        print()
        print("Impostala prima di eseguire questo script:")
        print("  Windows CMD:     set CHECKFEED_SECRET=la_tua_password_segreta")
        print("  Windows PS:      $env:CHECKFEED_SECRET='la_tua_password_segreta'")
        print("  Linux/Mac:       export CHECKFEED_SECRET=la_tua_password_segreta")
        sys.exit(1)

    # Verifica che config.json esista
    if not os.path.exists(config_path):
        print(f"❌ File {config_path} non trovato.")
        print("Copia config.example.json in config.json e personalizzalo prima.")
        sys.exit(1)

    # Carica il config
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Importa crypto (dopo aver verificato CHECKFEED_SECRET)
    from bot.crypto import encrypt_config, is_config_encrypted, SENSITIVE_FIELDS

    # Verifica se è già cifrato
    if is_config_encrypted(config):
        print("⚠️  Il config è già cifrato. Nessuna azione necessaria.")
        print("Campi cifrati trovati:", [f"enc_{f}" for f in SENSITIVE_FIELDS if f"enc_{f}" in config])
        sys.exit(0)

    # Mostra cosa verrà cifrato
    print("🔐 Campi che verranno cifrati:")
    for field in SENSITIVE_FIELDS:
        if field in config and config[field] and not config[field].startswith("INSERISCI"):
            masked = config[field][:8] + "..." + config[field][-4:] if len(config[field]) > 12 else "****"
            print(f"  • {field}: {masked}")
        elif field in config:
            print(f"  • {field}: (placeholder, verrà ignorato)")
        else:
            print(f"  • {field}: (non presente)")

    # Conferma
    print()
    response = input("Procedere con la cifratura? (s/n): ").strip().lower()
    if response not in ("s", "si", "sì", "y", "yes"):
        print("Operazione annullata.")
        sys.exit(0)

    # Backup
    backup_path = "config.backup.json"
    shutil.copy2(config_path, backup_path)
    print(f"📋 Backup salvato in: {backup_path}")

    # Cifra
    encrypted_config = encrypt_config(config)

    # Salva
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(encrypted_config, f, indent=2, ensure_ascii=False)

    print("✅ Config cifrato con successo!")
    print()
    print("⚠️  IMPORTANTE:")
    print("  • Ricorda la password in CHECKFEED_SECRET — serve ad ogni avvio del bot")
    print("  • Il backup NON cifrato è in config.backup.json — eliminalo dopo aver verificato")
    print(f"  • Aggiungi 'config.backup.json' al .gitignore!")


if __name__ == "__main__":
    main()
