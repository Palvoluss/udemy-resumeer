# Piano di Sviluppo Futuro (Revisionato)

Questo documento definisce una roadmap aggiornata per le implementazioni future del sistema di generazione riassunti per corsi, basata sui recenti chiarimenti. Ogni passo è progettato per essere specifico, testabile e orientato al miglioramento dell'architettura esistente, seguendo un approccio incrementale.

## Fase 1: Fondamenta e Monitoraggio Essenziale

### 1.1 Setup Iniziale del Progetto e Output di Base
    **Descrizione**: Stabilire la struttura del progetto e implementare le funzionalità core per l'elaborazione del corso e la generazione di output Markdown basilari.
    **Passi di implementazione**:
        1. Definire la struttura del progetto Python modulare (seguendo `docs/memory-bank/architecture.md`).
        2. Implementare le funzionalità di navigazione delle cartelle del corso.
        3. Implementare l'estrazione del testo da file VTT e PDF.
        4. Creare una classe `MarkdownFormatter` (implementazione base) per gestire la formattazione.
        5. Implementare template Markdown basilari per riassunti di lezioni, capitoli (inizialmente con link o riassunti grezzi) e un indice principale.
    **Test**: Verificare che il sistema processi un corso di esempio, estragga il testo e generi file Markdown strutturati secondo i template base.

### 1.2 Integrazione con Langfuse per Monitoraggio LLM
    **Descrizione**: Integrare Langfuse per tracciare e monitorare le interazioni con i modelli LLM.
    **Passi di implementazione**:
        1. Aggiungere `langfuse` alle dipendenze (es. `requirements.txt`).
        2. Implementare una classe `LangfuseTracker` per la configurazione e le interazioni.
        3. Configurare variabili d'ambiente per le chiavi Langfuse (LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY).
        4. Definire una funzione di inizializzazione per Langfuse all'avvio dell'applicazione.
        5. Modificare la funzione `summarize_with_openai()` (o equivalente) per tracciare le chiamate.
        6. Registrare input, output, modello utilizzato, token consumati e latenza per ogni chiamata.
        7. Aggiungere metadati utili (capitolo, lezione, tipo di contenuto).
        8. Implementare tracciamento di errori e tentativi falliti.
    **Test**: Verificare che Langfuse sia correttamente configurato ed eseguendo una chiamata di test, controllare che appaia nella dashboard di Langfuse. Verificare che ogni chiamata API venga correttamente tracciata in Langfuse, con tutti i metadati previsti.

### 1.3 Sistema di Template per Prompt
    **Descrizione**: Creare un sistema flessibile per la gestione dei prompt, iniziando con un prompt ottimizzato per "lezione pratico teorica faccia a faccia".
    **Passi di implementazione**:
        1. Creare una struttura (classe o modulo) per gestire i template dei prompt.
        2. Implementare il prompt iniziale ottimizzato per "lezione pratico teorica faccia a faccia".
        3. Assicurare che il sistema di riassunto utilizzi questo template.
    **Test**: Verificare che i riassunti siano generati utilizzando il prompt specificato e che sia possibile modificarlo centralmente.

## Fase 2: Miglioramento della Qualità, Struttura dei Contenuti e Fonti

### 2.1 Implementazione Metriche di Base in Langfuse
    **Descrizione**: Configurare Langfuse per monitorare metriche chiave di prestazione, costo e utilizzo.
    **Passi di implementazione**:
        1. Definire e registrare metriche chiave: token utilizzati (per riassunto, per capitolo, per corso), costo stimato (se applicabile), tempo di elaborazione.
        2. Implementare tagging in Langfuse per separare diverse esecuzioni (es. per corso specifico, per versione del prompt utilizzata).
        3. Creare sessioni di tracciamento distinte per ciascun corso elaborato.
    **Test**: Verificare che le metriche definite vengano correttamente visualizzate nella dashboard Langfuse dopo l'elaborazione di un corso completo.

### 2.2 Estrazione Testo e Descrizione Immagini da File HTML
    **Descrizione**: Estendere le capacità di elaborazione dei file HTML per includere sia l'estrazione del testo sia l'identificazione e la descrizione del contenuto delle immagini rilevanti presenti nei file.
    **Passi di implementazione**:
        1. Identificare e integrare una libreria Python per il parsing di HTML (es. BeautifulSoup).
        2. Aggiornare la logica di elaborazione dei file per:
            a. Riconoscere e processare i file `.html`.
            b. Identificare tag `<img>` ed estrarre gli attributi `src` (e possibilmente `alt` per un contesto iniziale).
        3. Implementare una funzione specifica per estrarre il contenuto testuale rilevante dai file HTML, escludendo elementi non pertinenti (es. script, style, navigazione, footer).
        4. Sviluppare un modulo/classe `ImageDescriber` per:
            a. Accedere/scaricare i dati dell'immagine dall'URL/path estratto.
            b. Interfacciarsi con un modello LLM multimodale (es. OpenAI GPT-4V o simile, da configurare separatamente) per ottenere una descrizione testuale dell'immagine.
            c. Gestire errori (es. immagini non accessibili, fallimenti API del modello visivo).
        5. Integrare le descrizioni delle immagini nel contenuto estratto dal file HTML, posizionandole in modo contestualmente appropriato (es., inserendo un testo come "Contenuto immagine: [descrizione generata dall'IA]").
        6. Modificare il flusso di lavoro di generazione dei riassunti per includere questo contenuto arricchito (testo + descrizioni immagini).
        7. Valutare e implementare strategie per gestire il costo e le prestazioni (es. processare solo immagini con attributo `alt` significativo, limitare il numero di immagini per pagina, consentire la disattivazione della funzione).
        8. Aggiornare il tracciamento Langfuse per includere le chiamate al modello di visione, i relativi costi e le metriche di performance.
    **Test**: 
        - Verificare che il sistema processi file HTML, estragga testo e identifichi correttamente i tag immagine e i loro sorgenti.
        - Verificare che le immagini vengano inviate al modello di visione e che le descrizioni testuali siano generate in modo accurato.
        - Verificare che le descrizioni delle immagini siano integrate correttamente nel materiale utilizzato per il riassunto.
        - Testare la gestione degli errori per immagini mancanti o API non disponibili.
        - Verificare il corretto tracciamento in Langfuse delle operazioni relative alle immagini.

### 2.3 Ottimizzazione Struttura File di Capitolo e Valutazione Riassunti
    **Descrizione**: Migliorare i file di riassunto del capitolo per includere il contenuto completo delle lezioni anziché solo link e implementare un sistema base per la valutazione manuale dei riassunti.
    **Passi di implementazione**:
        1. Modificare la funzione `create_chapter_summary()` (o equivalente) per incorporare i riassunti completi delle lezioni direttamente nel file del capitolo.
        2. Assicurare una navigazione chiara all'interno del file di capitolo (es. link interni o un piccolo indice all'inizio del file di capitolo).
        3. Implementare un sistema per la valutazione manuale dei riassunti: Aggiungere un campo `user_score: ` (con un range suggerito, es. 0-100, da definire) nel YAML frontmatter di ogni file di riassunto generato. Questo campo sarà inizialmente vuoto o con un valore placeholder.
    **Test**:
        - Verificare che il riassunto del capitolo contenga effettivamente il testo completo di tutte le lezioni attraverso un test automatizzato che confronti il contenuto con i file delle singole lezioni (o una verifica manuale accurata).
        - Verificare che il campo `user_score` sia presente nel frontmatter dei file di riassunto.

### 2.4 Meccanismo di Rigenerazione Manuale dei Riassunti (Funzionalità Rimandata)
    **Descrizione**: (Rimandato) Implementare un sistema per la capacità di rigenerare i riassunti con parametri o prompt modificati. La valutazione manuale (tramite `user_score`) è gestita nello step 2.3.
    **Passi di implementazione**:
        *(I seguenti passi sono rimandati e verranno dettagliati quando la funzionalità sarà ripresa)*
        1. Sviluppare una funzione o interfaccia (es. a riga di comando) che permetta di specificare una lezione o un chunk di testo da rigenerare, basandosi sulla sua valutazione o identificativo.
        2. Permettere l'input di un prompt modificato o di parametri specifici (es. modello, temperatura) per la singola rigenerazione.
        3. Eseguire la chiamata LLM con i nuovi input e aggiornare o sostituire il riassunto precedente.
        4. Tracciare questa rigenerazione in Langfuse come un evento separato o correlato alla traccia originale, includendo i parametri di rigenerazione e, se disponibile, lo score precedente e quello nuovo.
    **Test**: (Rimandato) Simulare una valutazione di bassa qualità (utilizzando lo `user_score` definito in 2.3), utilizzare il meccanismo (quando implementato) per rigenerare un riassunto con un nuovo prompt e verificare che il risultato sia aggiornato, e la rigenerazione sia tracciata.

### 2.5 Gestione Avanzata dei File di Contenuto Orfani
    **Descrizione**: Implementare una logica per associare file di contenuto non direttamente collegati a una lezione VTT (es. file HTML, PDF isolati) alla lezione valida immediatamente precedente. Questo assicura che nessun materiale del corso venga ignorato.
    **Passi di implementazione**:
        1. Modificare il processo di scansione del corso per identificare i file che non hanno un file `.vtt` corrispondente all'interno della stessa "unità di lezione" (basata sulla numerazione o convenzione dei nomi).
        2. Implementare una funzione che, per ogni file "orfano" identificato, cerchi a ritroso la lezione precedente che possiede un file `.vtt` (la "lezione genitore valida").
        3. Estrarre il contenuto rilevante dai file orfani (testo da PDF, testo e descrizione immagini da HTML come definito nello step 2.2).
        4. Integrare il contenuto estratto dai file orfani nel materiale della "lezione genitore valida" identificata. Questo contenuto dovrebbe essere aggiunto in modo chiaro, ad esempio in una sezione "Materiale Aggiuntivo" o "Approfondimenti" alla fine del riassunto della lezione genitore.
        5. Gestire correttamente casi di file orfani multipli consecutivi: tutti devono essere associati alla stessa lezione genitore valida più vicina.
        6. Aggiornare i template Markdown e la logica di `MarkdownFormatter` per presentare questo contenuto aggiuntivo in modo leggibile.
        7. Assicurare che il tracciamento Langfuse rifletta l'elaborazione di questi file orfani e la loro associazione.
    **Test**:
        - Preparare una struttura di corso d'esempio con file `.vtt` e file orfani (`.html`, `.pdf`) singoli e consecutivi.
        - Verificare che i file orfani vengano correttamente identificati.
        - Verificare che il contenuto dei file orfani sia estratto e aggiunto al riassunto della lezione precedente corretta.
        - Controllare che la formattazione del contenuto aggiunto sia chiara e ben integrata.
        - Verificare che il processo gestisca correttamente più file orfani consecutivi, aggregandoli alla lezione genitore corretta.

## Fase 3: Arricchimento Semantico del Contenuto

### 3.1 Identificazione di Parole Chiave con NLTK
    **Descrizione**: Creare un sistema per riconoscere automaticamente termini importanti nei testi elaborati utilizzando NLTK. (Nota: Il dizionario di domini specifici è stato skippato).
    **Passi di implementazione**:
        1. Integrare la libreria NLTK nel progetto (`requirements.txt` e importazioni).
        2. Implementare una classe `KeywordExtractor`.
        3. Utilizzare NLTK (es. tokenizzazione, POS tagging) per l'estrazione di frasi nominali e termini significativi.
        4. Integrare algoritmi di ranking delle parole chiave (es. TF-IDF implementato manualmente o tramite NLTK/scikit-learn, o TextRank) per identificare le più rilevanti.
        5. Salvare o rendere accessibili le parole chiave identificate per ogni lezione/capitolo.
    **Test**: Verificare che il sistema identifichi correttamente almeno l'80% delle parole chiave in un set di test predefinito, confrontando con un'annotazione manuale.

### 3.2 Implementazione Sistema di Backlinks Automatici (Sintassi Obsidian)
    **Descrizione**: Sviluppare un meccanismo per trasformare automaticamente le parole chiave identificate in backlinks interni, utilizzando la sintassi di Obsidian `[[parola chiave]]`.
    **Passi di implementazione**:
        1. Creare una funzione `add_obsidian_backlinks()` che prenda il testo Markdown finale e lo processi.
        2. Per ogni parola chiave identificata (dalla Fase 3.1) nel testo, trasformarla in un link Markdown tipo `[[parola chiave]]`.
        3. *Opzionale ma consigliato*: Costruire un indice o un set globale delle parole chiave del corso per garantire che i backlinks puntino a concetti effettivamente definiti o discussi, e per gestire varianti della stessa parola chiave.
        4. Sviluppare un meccanismo per evitare duplicazioni eccessive di backlinks per lo stesso termine in una singola pagina o sezione (es. linkare solo la prima occorrenza).
    **Test**: Verificare che le parole chiave nei file Markdown generati siano trasformate in backlinks. Testare che, aprendo i file in Obsidian, i link siano riconosciuti (anche se le pagine linkate potrebbero non esistere ancora).

## Fase 4: Feedback, Miglioramento Continuo e Formattazione Avanzata

### 4.1 Implementazione Metriche Automatiche di Qualità dei Riassunti (con Langfuse)
    **Descrizione**: Integrare metriche NLP standard per la valutazione automatica della qualità dei riassunti e registrarle in Langfuse.
    **Passi di implementazione**:
        1. Integrare librerie Python per il calcolo di metriche di valutazione testuale (es. `nltk.translate.bleu_score`, `rouge-score`).
        2. Dopo la generazione di un riassunto, calcolare queste metriche confrontando l'output con il testo originale (o una sua versione "ideale" se disponibile, anche se più complesso).
        3. Registrare gli score di queste metriche in Langfuse, associandoli alla traccia della generazione corrispondente.
    **Test**: Verificare che gli score di qualità siano calcolati e inviati correttamente a Langfuse per ogni riassunto.

### 4.2 Sistema di "Apprendimento da Esempi Migliorati"
    **Descrizione**: Creare un meccanismo per storare e potenzialmente utilizzare versioni di riassunti che hai migliorato manualmente, per informare l'affinamento futuro dei prompt.
    **Passi di implementazione**:
        1. Progettare un sistema semplice per salvare (es. in file separati con una convenzione di nomi, o in una sottocartella dedicata) le versioni dei riassunti che hai manualmente corretto o migliorato.
        2. Associare questi esempi "golden" al contesto originale (lezione, chunk di testo, prompt/parametri usati per la generazione originale).
        3. *Fase esplorativa successiva*: Valutare come questi esempi possano essere revisionati per identificare pattern e migliorare i prompt di base o come esempi "few-shot" se si decidesse in futuro di reintrodurre prompt più complessi.
    **Test**: Verificare che sia possibile salvare una versione "migliorata" di un riassunto e associarla al suo contesto originale in modo tracciabile.

### 4.3 Miglioramenti Avanzati della Formattazione Markdown (con Sintassi Obsidian)
    **Descrizione**: Standardizzare e arricchire ulteriormente la formattazione dei file Markdown generati, facendo uso estensivo della sintassi Obsidian per una migliore leggibilità e interattività all'interno di Obsidian.
    **Passi di implementazione**:
        1. Raffinare i template Markdown gestiti dalla classe `MarkdownFormatter`.
        2. Standardizzare l'uso di intestazioni, elenchi, tabelle e blocchi di codice.
        3. Integrare metadati strutturati (es. autore, data di generazione, versione del corso, tag rilevanti) all'inizio dei file Markdown (es. YAML frontmatter).
        4. Assicurare la presenza di un indice navigabile (Table of Contents) all'inizio di ogni file di capitolo.
        5. Creare una sezione "Concetti Chiave del Capitolo" (potrebbe attingere dalle parole chiave della Fase 3.1 e linkare alle relative sezioni).
        6. Implementare template per formattazione avanzata con sintassi Obsidian:
            - Callouts (es. `[!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]`, `[!QUESTION]`)
            - Blocchi di evidenziazione.
            - Eventuali altri elementi utili di Obsidian.
    **Test**: Verificare che i file Markdown generati utilizzino la formattazione avanzata, i metadati, gli indici e gli elementi strutturali previsti, e che siano resi correttamente in Obsidian.

## Funzionalità Rimandate o Skippate (per Chiarezza)

Le seguenti funzionalità dal piano originale sono state temporaneamente rimandate o skippate per focalizzare gli sforzi, come da discussione:
- **Endpoint Feedback Utenti (ex 1.4.1):** Skippato. Non si creeranno endpoint per raccogliere feedback utenti tramite Langfuse al momento.
- **Riassunti Multi-livello (ex 2.2):** Skippato. Non si implementerà la generazione di riassunti a diverse granularità (breve, medio, dettagliato) come funzionalità esplicita.
- **Dizionario di Domini Specifici (per NLTK, ex 4.1.2):** Skippato. Non si creerà un dizionario di domini specifici per l'estrazione di parole chiave.
- **Generare un Glossario Automatico (ex 4.3):** Skippato. Non si genererà un glossario automatico dei termini.
- **Pianificazione Futura Dettagliata (ex Sezione 5 originale):** Le idee generali (integrazione knowledge base, flashcard, UI web, più provider LLM, estrazione codice) rimangono valide per considerazioni future ma non sono dettagliate in questo piano operativo.

## Note per l'Implementazione (Invariate)

- Mantenere la modularità del codice, creando classi e funzioni con responsabilità ben definite.
- Documentare ogni nuova funzionalità con docstrings esaustive.
- Creare test unitari per ciascuna nuova funzionalità.
- Seguire i principi di Clean Code per garantire manutenibilità e leggibilità.
- Aggiornare la documentazione di architettura in `docs/memory-bank/architecture.md` dopo ogni milestone completata.