# Telegram News Bot

Un bot in **Python + Docker** che:

* raccoglie notizie da più siti (RSS/Feed)
* invia **alert immediati su Telegram** se trova keyword personalizzate
* genera un **report giornaliero** con le notizie del giorno
* gestisce automaticamente **log e retention**
* supporta **più utenti Telegram**, ciascuno con la propria configurazione
* memorizza le **news e i contenuti completi** su SQLite

---

## Novità implementate (Step-by-Step)

1. **Aggiornamento Sorgenti e Blacklist**
   * Sono stati aggiunti nuovi feed RSS predefiniti (TechCrunch, Hacker News, The Verge, HDBlog, Tom's Hardware).
   * È stata implementata una `blacklist` per escludere a monte articoli irrilevanti (es. contenenti le parole "volantino", "scaduto").
2. **Sistema di Urgenza (Urgency Check)**
   * Il sistema scansiona le notizie in arrivo cercando parole chiave critiche (es. "errore di prezzo", "bug").
   * Quando viene rilevata un'urgenza, la notifica bypassa il silenzio e attiva un alert sonoro su Telegram.
3. **Integrazione Intelligenza Artificiale (Google Gemini)**
   * Aggiunta l'interfaccia alle API di Gemini 2.0 Flash.
   * Le notizie non urgenti ottengono un riassunto automatico in 3 punti elenco, migliorando la leggibilità.
   * Aggiunto il comando `/top5` per generare un digest AI delle 5 notizie più importanti della giornata.
4. **Scraping Nativo di Worldy.it**
   * Creazione di uno scraper HTML personalizzato per Worldy.it (che non possiede feed RSS standard).
   * Aggiunto il comando `/worldy [categoria]` per estrarre articoli, immagini di copertina e descrizioni direttamente dal sito.
5. **Sicurezza e Cifratura (AES 128-CBC)**
   * I token sensibili (Telegram token e Gemini API Key) non vengono più salvati in chiaro nel `config.json`.
   * Implementata una cifratura AES tramite master password (`CHECKFEED_SECRET`) necessaria ad ogni avvio.
6. **Supporto Docker Aggiornato**
   * Riconfigurato `docker-compose.yml` per mappare i config in modo sicuro e accettare la variabile d'ambiente per la decifratura automatica al bootstrap.

---

## Funzionalità principali

* Polling periodico dei feed RSS (intervallo configurabile)
* Scraping nativo di Worldy per recuperare articoli e immagini
* Notifiche immediate via Telegram su keyword specifiche
* Sistema di urgenza per notifiche sonore sulle notizie prioritarie
* Filtro Blacklist per ignorare notizie contenenti precise parole chiave
* Riassunti AI con Google Gemini per le notizie in arrivo
* Cifratura AES per proteggere Token Telegram e API Key Gemini
* Report giornaliero automatico alle ore configurate
* Deduplica automatica delle notizie gia viste
* Gestione log e news con cancellazione automatica
* Supporto multi-utente con SQLite
* Contenuto e anteprime foto memorizzate nel DB
* Comandi interattivi con feedback dettagliato

---

## Configurazione iniziale

### Crea la tua configurazione

Copia il file di esempio:

```bash
cp config.example.json config.json
```

### Modifica config.json

Esempio base:

```json
{
  "telegram_token": "852...:AAB...",
  "gemini_api_key": "AIza...",
  "machine_name": "Server-01",
  "sites": [
    {
      "name": "The Verge",
      "url": "https://www.theverge.com/rss/index.xml",
      "category": "Tech"
    }
  ],
  "blacklist": ["volantino", "scaduto"],
  "urgency_keywords": ["errore", "prezzo"],
  "daily_report_time": "18:00",
  "polling_minutes": 15,
  "data_retention_days": 10,
  "disable_web_page_preview": true,
  "worldy_categories": ["worldy", "tech", "finance"]
}
```

**Campi principali / Nuovi:**
* `telegram_token` -> token del bot ottenuto da BotFather
* `gemini_api_key` -> API key per generare i riassunti AI (Google Gemini)
* `blacklist` -> parole per scartare in automatico la notizia
* `urgency_keywords` -> parole per ricevere notifiche sonore (urgenza)
* `worldy_categories` -> categorie Worldy da cui importare le notizie

### Cifratura dei Dati
Le tue credenziali non saranno mai in chiaro! È previsto uno script che cifra le chiavi nel `config.json`.
Per utilizzarlo occorre avere una password master in una variabile d'ambiente:

**Se usi Windows PowerShell (prima di avviare il bot):**
```powershell
$env:CHECKFEED_SECRET='LaTuaPasswordSicura123!'
```
*(Su linux: `export CHECKFEED_SECRET="..."`)*

---

## Multi-utente con SQLite

Il bot ora salva gli utenti in **`data/checkfeed.db`**.

Ogni utente che invia `/start` viene registrato automaticamente e può:

* impostare le **proprie keyword** (`/setkeywords parola1, parola2, ...`)
* ricevere **solo le notizie rilevanti** per se
* ricevere report e comandi personalizzati

Niente piu config manuale: ogni utente Telegram ha il proprio profilo salvato in automatico.

---

## Comandi disponibili

| Comando                                     | Descrizione                                           |
| ------------------------------------------- | ----------------------------------------------------- |
| `/start`                                    | Registra l'utente e mostra informazioni complete      |
| `/stop`                                     | Sospende le notifiche per questo utente               |
| `/setkeywords parola1, parola2, COMPOSTA`   | **Aggiunge** parole chiave (separate da virgole)      |
| `/removekeywords parola1, parola2, ...`     | **Rimuove** keyword specifiche dall'elenco            |
| `/keywords`                                 | Mostra le tue keyword attualmente attive              |
| `/fetch`                                    | Aggiorna manualmente i feed                           |
| `/report`                                   | Genera e invia il report giornaliero                  |
| `/latest [n]`                               | Mostra le ultime *n* notizie (default: 5)             |
| `/top5`                                     | Genera digest AI delle 5 notizie tech migliori        |
| `/worldy [categoria]`                       | Invia articoli di Worldy con preview immagine         |
| `/commands`                                 | Elenco rapido di tutti i comandi disponibili          |

### Ricerca keyword migliorata
* Le keyword ora usano **ricerca esatta** delle parole
* "Rowe" **non** viene piu trovato in "Crowe"  
* "Demir" **non** viene piu trovato in "Ademir"
* Supporto per **parole composte** con spazi

### Gestione keyword intelligente
* `/setkeywords` **aggiunge** alle keyword esistenti (non le sostituisce)
* `/removekeywords` **rimuove** solo quelle specificate  
* **Controllo duplicati** automatico (case-insensitive)
* Feedback dettagliato su operazioni eseguite

All'avvio, il bot invia automaticamente un messaggio di **recap con tutti i comandi e i feed monitorati**.

---

## Esecuzione con Docker

1. Clona il repository

2. Cifra il `config.json` e ottieni la tua password master (`CHECKFEED_SECRET`).

3. Passa la variabile di sicurezza al comando:

   **Linux / WSL / Mac:**
   ```bash
   export CHECKFEED_SECRET="LaTuaPasswordSicura123!"
   docker-compose up -d --build
   ```

   **Windows PowerShell:**
   ```powershell
   $env:CHECKFEED_SECRET="LaTuaPasswordSicura123!"
   docker-compose up -d --build
   ```

Il volume mappato permette ai dati (`data/`) e al file di configurazione `config.json` decifrato di comunicare, garantendo al contempo che i log, le news e le categorie rimangano persistenti.

---

## Output di esempio

**Notifica immediata**

```
Nuova notizia da USR Emilia Romagna
Concorso docenti AM2A - graduatoria aggiornata
https://www.istruzioneer.gov.it/...
```

**Esempi di comandi**

```
/setkeywords scuola, docenti, GRADUATORIA FINALE
Keyword aggiunte: scuola, docenti, GRADUATORIA FINALE
Totale keyword: 3

/removekeywords docenti
Keyword rimosse: docenti  
Keyword rimanenti: scuola, GRADUATORIA FINALE

/keywords
Le tue keyword attive (2):
* scuola
* GRADUATORIA FINALE
```

**Report giornaliero**

```
Report del 2025-10-05 (3 notizie)
- Titolo 1 (USR Emilia Romagna)
- Titolo 2 (Miur)
```

**Log giornalieri**

```
data/logs/2025-10-05.log
```

---

## Manutenzione automatica

* Pulizia log e notizie vecchie ogni giorno
* Dati persistenti in data/
* Deduplica feed per evitare duplicati
* Database utenti in data/checkfeed.db

---

## Licenza

**MIT License** - libero utilizzo e modifica.
Creato per sviluppatori e scuole che vogliono restare aggiornati automaticamente

---

## Contributors

<a href="https://github.com/federicodiluca/CheckFeed-Bot/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=federicodiluca/CheckFeed-Bot" />
</a>
