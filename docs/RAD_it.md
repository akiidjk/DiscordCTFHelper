# Requirements Analysis Document (RAD)

## Introduzione

Il progetto consiste nello sviluppo di un bot Discord in grado di automatizzare la gestione e l'organizzazione di eventi Capture The Flag (CTF) all'interno di un server Discord, basandosi sui dati forniti dall'API di CTFTime. Questo bot permetterà agli amministratori del server di creare facilmente canali, ruoli, e notifiche per ogni evento CTF, semplificando la comunicazione e il coinvolgimento dei membri della community.

## Obiettivi del progetto

- **Automatizzare la gestione delle CTF** all'interno dei server Discord, riducendo il carico di lavoro per gli amministratori e aumentando l'efficienza nell'organizzazione di eventi CTF.
- **Creare e gestire canali, ruoli e eventi Discord** specifici per ogni CTF, facilitando la comunicazione e il coordinamento tra i partecipanti.
- **Integrare con la piattaforma CTFTime** per recuperare e utilizzare informazioni accurate e aggiornate sugli eventi CTF.

## Requisiti funzionali

1. **Creazione automatica di canali dedicati**:
   - Dato un URL di un evento CTF su CTFTime, il bot crea un canale dedicato per l'evento nella categoria "CTF Attive" precedentemente configurata.
   - Il bot invia un messaggio con embed nel canale, contenente informazioni dettagliate sull'evento CTF, inclusi titolo, descrizione, date di inizio e fine, logo e link al sito di CTFTime.

2. **Gestione degli eventi Discord**:
   - Il bot crea un evento Discord per ogni CTF con le date di inizio e fine recuperate da CTFTime.
   - All'inizio e alla fine dell'evento, il bot invia automaticamente notifiche ai partecipanti, aggiornando lo stato dell'evento nel server.

3. **Gestione dei ruoli**:
   - Creazione di un ruolo associato alla CTF per i partecipanti, con nome e permessi personalizzabili.
   - Assegnazione automatica del ruolo ai membri che reagiscono all'embed relativo all'evento CTF nel canale dedicato, semplificando il processo di adesione.

4. **Notifiche per l'inizio e la fine di ogni evento**:
   - Quando l'evento inizia, il bot tagga automaticamente i membri con il ruolo associato nel canale della CTF, inviando un messaggio di avvio.
   - Quando l'evento termina, il bot invia un messaggio di avviso e sposta automaticamente il canale nella categoria "CTF Archiviate", organizzando gli eventi passati.

5. **Configurazione delle categorie e dei ruoli**:
   - Comando di configurazione per definire la categoria delle CTF attive, la categoria delle CTF archiviate e il ruolo richiesto per gestire le CTF (basato sulla posizione dei ruoli).
   - Solo gli utenti con il ruolo definito possono creare nuovi eventi CTF.

## Requisiti non funzionali

1. **Scalabilità**:
   - Il bot deve essere in grado di gestire più CTF in contemporanea su diversi server, permettendo l'uso su larga scala.

2. **Affidabilità**:
   - Gestione robusta degli errori durante la creazione di canali, eventi e ruoli. Eventuali problemi devono essere segnalati in tempo reale all'amministratore del server con messaggi di errore appropriati.

3. **Sicurezza**:
   - Accesso limitato ai comandi in base a fattori come i permessi del membro sul server (richiesto permesso Amministratore sul server discord per il comando /init) o la richiesta di un ruolo preciso (Per il comando /create_ctf e' necessario di definire un ruolo manager).
   - Gestione sicura dei dati ricevuti da CTFTime per prevenire possibili exploit.

4. **Manutenibilità e facilità di configurazione**:
   - Documentazione chiara per gli amministratori su come configurare e utilizzare il bot.
   - Architettura del bot che permette facilmente modifiche e aggiornamenti, garantendo compatibilità con futuri cambiamenti dell'API di CTFTime o di Discord.

5. **Tempo di risposta**:
   - Il bot deve rispondere ai comandi in modo rapido, minimizzando i tempi di attesa per gli utenti, specialmente durante la creazione di canali ed eventi.

## Definizione delle feature (comandi)

### Comando `/init`

- **Descrizione**: Comando di inizializzazione che configura le impostazioni di base per la gestione delle CTF nel server.
- **Parametri**:
  - `categoria_ctf_attive`: Categoria in cui saranno inseriti i canali delle CTF attive.
  - `categoria_ctf_archiviate`: Categoria in cui saranno spostati i canali delle CTF archiviate.
  - `ruolo_manager`: Ruolo manager, richiesto per poter creare le CTF sul server.
- **Funzionalità**:
  - Imposta le categorie e il ruolo manager per la creazioni delle CTF sul server.
  - Se la configurazione è completata correttamente, il bot conferma con un messaggio; in caso di errore, segnala il problema all'utente.

### Comando `/create_ctf`

- **Descrizione**: Comando per creare un evento CTF all'interno del server.
- **Parametri**:
  - `url`: URL dell'evento su CTFTime nel formato `https://ctftime.org/event/<id>`.
- **Funzionalità**:
  - Recupera le informazioni sulla CTF dall'API di CTFTime, verificando la validità dell'URL.
  - Crea un canale dedicato nella categoria "CTF Attive", con un embed contenente i dettagli dell'evento.
  - Crea un evento Discord per la CTF con date di inizio e fine, notificando i partecipanti all'inizio e alla fine dell'evento.
  - Crea un ruolo dedicato alla CTF e lo assegna ai membri che reagiscono all'embed.
  - Se l'evento è già presente nel server, invia un messaggio di avviso informando che la CTF esiste già.

## Diagramma di flusso delle operazioni principali

1. **Configurazione (`/init`)**:
   - Un utente con il permesso amministratore sul server, invia il comando `/init` in qualsiasi canale con i parametri necessari.
   - Il bot salva le categorie e il ruolo per gestire le CTF.
   - Il bot conferma con un messaggio o segnala errori in caso di parametri mancanti.

2. **Creazione Evento CTF (`/create_ctf`)**:
   - Un utente che possiede il ruolo definito nel comando `/init` invia il comando `/create_ctf` in qualsiasi canale con l'URL dell'evento CTFTime.
   - Il bot verifica il ruolo del utente e se la ctf esiste gia'.
   - Il bot verifica l'URL e recupera i dati dell'evento.
   - Il bot crea il canale nella categoria "CTF Attive".
   - Il bot crea l'evento Discord e il ruolo per i partecipanti.
   - Il bot invia un embed nel canale, permette l'assegnazione del ruolo con reazione, e notifica all'inizio e alla fine dell'evento.

## Casi d'Uso

### Caso d'Uso 1: Configurazione iniziale del bot

- **Attori**: Utente con permessi di amministratore nel server Discord
- **Descrizione**: L'Utente del server esegue il comando `/init` per configurare le impostazioni di base per la gestione delle CTF.
- **Flusso principale**:
  1. L'Utente esegue il comando `/init` specificando le categorie e il ruolo per gestire le CTF.
  2. Il bot salva le impostazioni e conferma la configurazione.
- **Estensioni**:
  - Se il comando `/init` non include tutti i parametri necessari, il bot invia un messaggio d'errore e richiede le informazioni mancanti.
- **Pre-condizioni**: L' Utente che invia il messaggio deve avere i permessi necessari per eseguire il comando.
- **Post-condizioni**: La configurazione del bot è completata, pronta per l'uso.

### Caso d'Uso 2: Creazione di un evento CTF

- **Attori**: Utente con il ruolo definito in /init nel server Discord
- **Descrizione**: L'Utente crea un nuovo evento CTF utilizzando il comando `/create_ctf`.
- **Flusso principale**:
  1. L'Utente invia il comando `/create_ctf` con l'URL dell'evento su CTFTime.
  2. Il bot recupera le informazioni sull'evento dall'API di CTFTime.
  3. Il bot crea un canale nella categoria "CTF Attive" e pubblica un embed con i dettagli dell'evento.
  4. Il bot crea un evento Discord per il CTF, definendo le date di inizio e fine.
  5. Il bot crea un ruolo per i partecipanti e assegna il ruolo agli utenti che reagiscono all'embed nel canale.
  6. Il bot programma le notifiche per l'inizio e la fine dell'evento.
- **Estensioni**:
  - Se l'URL dell'evento non è valido o l'API di CTFTime non risponde, il bot invia un messaggio d'errore all'amministratore.
  - Se l'evento CTF esiste già nel server, il bot invia un avviso senza duplicare i canali o ruoli.
- **Pre-condizioni**: Il bot deve essere stato configurato con il comando `/init`.
- **Post-condizioni**: L'evento CTF è creato con canale, embed informativo, evento Discord e ruolo partecipanti.

### Caso d'Uso 3: Partecipazione dei membri a una CTF

- **Attori**: Membro del server Discord
- **Descrizione**: Un membro del server si unisce all'evento CTF reagendo all'embed informativo nel canale dedicato.
- **Flusso principale**:
  1. Il membro del server visualizza l'embed con le informazioni della CTF nel canale.
  2. Il membro reagisce all'embed con qualsiasi emoji.
  3. Il bot assegna automaticamente al membro il ruolo creato per la CTF.
- **Pre-condizioni**: La CTF deve essere stata creato dal bot
- **Post-condizioni**: Il membro ottiene il ruolo della CTF

### Caso d'Uso 4: Notifica di inizio evento

- **Attori**: Bot Discord
- **Descrizione**: Quando la data di inizio di un evento CTF è raggiunta, il bot invia automaticamente una notifica nel canale dedicato.
- **Flusso principale**:
  1. All'ora di inizio dell'evento, il bot invia un messaggio nel canale della CTF, taggando i membri con il ruolo associato per informarli dell'inizio dell'evento.
- **Pre-condizioni**: Il canale e il ruolo della CTF devono essere stati creati, e il bot deve avere i permessi per inviare notifiche.
- **Post-condizioni**: I partecipanti vengono notificati dell'inizio della CTF.

### Caso d'Uso 5: Conclusione e archiviazione dell'evento

- **Attori**: Bot Discord
- **Descrizione**: Alla fine di un evento CTF, il bot notifica i partecipanti e archivia il canale.
- **Flusso principale**:
  1. Alla data di fine dell'evento, il bot invia un messaggio nel canale della CTF informando i partecipanti della conclusione dell'evento.
  2. Il bot sposta automaticamente il canale della CTF nella categoria "CTF Archiviate" per organizzare gli eventi passati.
- **Pre-condizioni**: L'evento deve essere attivo e il bot configurato con le categorie per l'archiviazione.
- **Post-condizioni**: Il canale viene archiviato, i membri vengono informati del termine dell'evento e il ruolo viene reso grigio chiaro (tutti i ruoli creati dopo dal bot verrano messi sopra il ruolo precedente in modo che sia sempre messo in primo piano il ruolo della ctf attiva).

### Considerazioni aggiuntive

- **Integrazione API**: Assicurarsi che l'API di CTFTime sia accessibile e gestire eventuali limiti di rate per evitare blocchi.

## Conclusione

Il bot Discord proposto automatizzerà la gestione delle CTF, semplificando la creazione e la gestione di eventi complessi e migliorando l'esperienza degli utenti del server. Grazie alla sua integrazione con CTFTime, il bot fornirà informazioni sempre aggiornate sulle CTF, mentre l'automazione dei canali, eventi e ruoli renderà l'organizzazione efficiente e professionale.
