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

## Fase 2: Miglioramento della Qualità e Struttura dei Contenuti

### 2.1 Ottimizzazione Struttura File di Capitolo (Contenuto Completo)
    **Descrizione**: Migliorare i file di riassunto del capitolo per includere il contenuto completo delle lezioni anziché solo link.
    **Passi di implementazione**:
        1. Modificare la funzione `create_chapter_summary()` (o equivalente) per incorporare i riassunti completi delle lezioni direttamente nel file del capitolo.
        2. Assicurare una navigazione chiara all'interno del file di capitolo (es. link interni o un piccolo indice all'inizio del file di capitolo).
    **Test**: Verificare che il riassunto del capitolo contenga effettivamente il testo completo di tutte le lezioni attraverso un test automatizzato che confronti il contenuto con i file delle singole lezioni (o una verifica manuale accurata).

### 2.2 Implementazione Metriche di Base in Langfuse
    **Descrizione**: Configurare Langfuse per monitorare metriche chiave di prestazione, costo e utilizzo.
    **Passi di implementazione**:
        1. Definire e registrare metriche chiave: token utilizzati (per riassunto, per capitolo, per corso), costo stimato (se applicabile), tempo di elaborazione.
        2. Implementare tagging in Langfuse per separare diverse esecuzioni (es. per corso specifico, per versione del prompt utilizzata).
        3. Creare sessioni di tracciamento distinte per ciascun corso elaborato.
    **Test**: Verificare che le metriche definite vengano correttamente visualizzate nella dashboard Langfuse dopo l'elaborazione di un corso completo.

### 2.3 Meccanismo di Rigenerazione Manuale dei Riassunti
    **Descrizione**: Implementare la capacità di rigenerare manualmente un riassunto con parametri o prompt modificati, a seguito di una tua valutazione di bassa qualità.
    **Passi di implementazione**:
        1. Sviluppare una funzione o interfaccia (es. a riga di comando) che permetta di specificare una lezione o un chunk di testo da rigenerare.
        2. Permettere l'input di un prompt modificato o di parametri specifici (es. modello, temperatura) per la singola rigenerazione.
        3. Eseguire la chiamata LLM con i nuovi input e aggiornare o sostituire il riassunto precedente.
        4. Tracciare questa rigenerazione in Langfuse come un evento separato o correlato alla traccia originale.
    **Test**: Simulare una valutazione di bassa qualità, utilizzare il meccanismo per rigenerare un riassunto con un nuovo prompt e verificare che il risultato sia aggiornato e la rigenerazione tracciata.

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