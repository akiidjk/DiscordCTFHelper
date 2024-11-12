# CookieBotDiscord

## SDD

### 1. **Introduzione**

#### 1.1 Scopo

Il bot Discord è progettato per gestire eventi Capture The Flag (CTF) su Discord, interagendo con il sito `ctftime.org` per recuperare informazioni sugli eventi e creando notifiche per l'inizio e la fine degli eventi. Gli utenti possono creare e gestire eventi CTF attraverso comandi Discord, e il bot invia notifiche via embed nei canali di testo.

#### 1.2 Obiettivi

- Recupero delle informazioni sugli eventi dal sito `ctftime.org`.
- Gestione della creazione, modifica e cancellazione di eventi CTF.
- Notifica agli utenti sull'inizio e la fine degli eventi CTF.
- Utilizzo di un database SQLite per memorizzare le informazioni sugli eventi e sui server.
- Gestione dei permessi di accesso tramite ruoli e categorie di Discord.

### 2. **Panoramica del Sistema**

Il bot interagisce con il server Discord e il sito `ctftime.org` per recuperare e gestire gli eventi CTF. Il flusso di lavoro del bot include:

- **Comandi:** gli utenti interagiscono con il bot attraverso comandi Discord.
- **API:** il bot interroga `ctftime.org` per ottenere informazioni sugli eventi.
- **Notifiche:** il bot invia notifiche riguardo l'inizio e la fine degli eventi.
- **Database:** tutte le informazioni vengono memorizzate in un database SQLite.

### 3. **Requisiti**

#### 3.1 Requisiti Funzionali

- **Recupero dei dati sugli eventi CTF:** Il bot deve essere in grado di recuperare le informazioni sugli eventi da `ctftime.org`.
- **Gestione eventi CTF:** Il bot può creare, eventi CTF attraverso i comandi di Discord.
- **Notifiche di evento:** Il bot deve inviare notifiche quando un evento inizia e finisce, includendo informazioni come data di inizio e fine, descrizione, premi, etc.
- **Gestione dei permessi:** Solo gli utenti con i permessi di amministratore possono eseguire comandi di configurazione.
- **Gestione dei canali e ruoli:** I canali di testo e i ruoli vengono creati e gestiti in base agli eventi CTF.
- **Rate Limiting:** (Non implementato) Il bot deve limitare il numero di richieste al sito esterno per evitare di essere bloccato.

#### 3.2 Requisiti Non Funzionali

- **Performance:** Il bot deve rispondere rapidamente ai comandi e non sovraccaricare il server con troppe richieste simultanee.
- **Affidabilità:** Il bot deve funzionare senza interruzioni, gestendo correttamente gli errori di rete e di database.
- **Scalabilità:** Il bot deve poter gestire eventi multipli in contemporanea senza problemi.

### 4. **Architettura del Sistema**

#### 4.1 Componenti principali

1. **Bot Discord (Discord.py)**:
   - Gestisce la logica dei comandi.
   - Invia notifiche via embed nei canali di testo.
2. **API di `ctftime.org`:**
   - Il bot si connette all'API di `ctftime.org` per recuperare i dettagli degli eventi.
3. **Database SQLite:**
   - Memorizza le informazioni sugli eventi e sui server.
   - Utilizza tabelle come `server` e `ctf` per organizzare i dati.
4. **Logger:**
   - Gestisce la registrazione delle attività del bot (debug, errori, ecc.).

### 5. **Descrizione Dettagliata dei Moduli**

#### 5.1 Comandi Discord (`ctf.py`)

- **/help**: (Non implementato) Stampa un messaggio con la guida sui comandi
- **/init**: Permette agli amministratori di configurare il bot.
- **/create_ctf**: Crea un nuovo evento CTF, raccogliendo le informazioni dall'API e dal database.

#### 5.2 Funzione `get_ctf_info` (API `ctftime.org`)

Questa funzione è responsabile di interrogare `ctftime.org` per ottenere informazioni sugli eventi. Gestisce anche gli errori di rete e l'analisi dei dati JSON.

#### 5.3 Database SQLite (`DatabaseManager`)

Il modulo gestisce l'interazione con il database SQLite, inclusi l'aggiunta, la modifica e la cancellazione degli eventi CTF. Utilizza il modulo `aiosqlite` per lavorare in modo asincrono.

#### 5.4 Logger

Il logger personalizzato è responsabile della registrazione delle attività e degli errori. Utilizza una formattazione colorata per facilitare la lettura nei terminali.

### 6. **Flusso di Lavoro**

1. L'utente invia un comando Discord (ad esempio, `/create_ctf`).
2. Il bot interroga l'API `ctftime.org` tramite la funzione `get_ctf_info`.
3. Il bot memorizza le informazioni dell'evento nel database.
4. Il bot crea un canale di testo e un ruolo per l'evento, se necessario.
5. Il bot invia un messaggio di notifica (embed) con i dettagli dell'evento.
6. Quando l'evento inizia o finisce, il bot invia una notifica nel canale appropriato.

### 7. **Gestione degli Errori**

Il sistema gestisce vari tipi di errori, come:

- Errori di rete quando si interroga l'API.
- Errori nel database, come la violazione di vincoli o la connessione fallita.
- Errori di permessi quando un utente non ha il permesso per eseguire determinati comandi.

### 8. **Sicurezza**

- **Permessi di accesso:** Solo gli utenti con ruoli di amministratore possono eseguire comandi di configurazione.
- **Gestione dei dati:** Il bot non archivia dati sensibili oltre le informazioni sugli eventi e i server.

### 9. **Piani Futuri**

- Implementazione del rate limiting per evitare il blocco da parte dell'API di `ctftime.org`.
- Espandere il sistema per supportare più tipi di eventi o altre piattaforme.

### 10. **Conclusione**

Il bot Discord descritto in questo SDD fornisce una gestione semplice e automatizzata degli eventi CTF, con un'architettura modulare e ben strutturata. Questo SDD funge da guida per lo sviluppo, la manutenzione e l'espansione del bot.
