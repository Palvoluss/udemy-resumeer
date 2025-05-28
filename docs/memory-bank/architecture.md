# Architettura dell'Agente di Riassunto Corsi

## Panoramica

L'agente di riassunto corsi è un'applicazione Python modulare progettata per processare corsi didattici strutturati in cartelle, estrarre il testo dalle trascrizioni (VTT) e dai materiali di supporto (PDF), e generare riassunti intelligenti utilizzando l'API di OpenAI. L'architettura è organizzata secondo principi di responsabilità singola e separazione delle preoccupazioni.

## Struttura del Progetto

Il progetto è organizzato come segue:

```
udemy-course-resumeeer/
├── .courses/             # Directory di esempio per i corsi input e output (non tracciata da git)
├── .env                  # File per variabili d'ambiente (es. OPENAI_API_KEY, OPENAI_MODEL_NAME) (non tracciato)
├── docs/
│   └── memory-bank/      # Documentazione di progetto, piani, requisiti
├── src/
│   ├── __init__.py       # Rende 'src' un package Python
│   ├── resume_generator.py # Script principale, orchestra il processo
│   ├── api_key_manager.py  # Gestisce le chiavi API
│   ├── markdown_formatter.py # Classe per la formattazione Markdown
│   ├── prompt_manager.py   # Gestisce i template dei prompt per OpenAI (AGGIUNTO)
│   └── langfuse_tracker.py # Gestisce il tracciamento con Langfuse (AGGIUNTO)
├── tests/
│   ├── __init__.py       # Rende 'tests' un package Python
│   ├── test_api_key_manager.py # Test per APIKeyManager
│   ├── test_markdown_formatter.py # (Da creare) Test per MarkdownFormatter
│   └── ...               # Altri file di test
├── requirements.txt      # Dipendenze Python del progetto
├── README.md             # README principale del progetto
└── .gitignore            # Specifica i file da ignorare in git
```

### Componenti Chiave in `src/`

*   **`resume_generator.py`**: 
    *   Punto di ingresso principale dell'applicazione quando eseguito come modulo (`python -m src.resume_generator`).
    *   Gestisce l'analisi degli argomenti da riga di comando.
    *   Configura il logging e la directory di output.
    *   Orchestra il processo di elaborazione del corso: 
        *   Naviga la struttura del corso (capitoli, lezioni).
        *   Utilizza `api_key_manager` per ottenere la chiave OpenAI.
        *   Utilizza `prompt_manager` per ottenere il template del prompt corretto.
        *   Utilizza `langfuse_tracker` per avviare una sessione di tracciamento per il corso e span per i capitoli.
        *   Chiama le funzioni per estrarre testo da file VTT e PDF.
        *   Utilizza le funzioni di riassunto (che a loro volta chiamano OpenAI con il prompt formattato e tracciano la chiamata con `langfuse_tracker`) per generare i contenuti dei riassunti per VTT e PDF separatamente.
        *   Utilizza `markdown_formatter` per creare i file di output in formato Markdown (indice principale, riassunti dei capitoli, riassunti delle lezioni con sezioni distinte per VTT e PDF).
        *   Registra metriche aggregate (token, tempi) con `langfuse_tracker` alla fine dell'elaborazione del corso e dei capitoli.
*   **`api_key_manager.py`**: 
    *   Definisce la classe `APIKeyManager`.
    *   Responsabile del caricamento sicuro della chiave API OpenAI da variabili d'ambiente o da un file `.env`.
    *   Fornisce metodi per ottenere la chiave e per ottenere un hash della chiave a scopo di logging.
*   **`markdown_formatter.py`**: 
    *   Definisce la classe `MarkdownFormatter`.
    *   Fornisce una serie di metodi per generare stringhe formattate secondo la sintassi Markdown (es. intestazioni, elenchi, link, blocchi di codice, linee orizzontali).
    *   Utilizzata da `resume_generator.py` per costruire il contenuto dei file di output.
*   **`prompt_manager.py`**: (AGGIUNTO)
    *   Definisce la classe `PromptManager`.
    *   Responsabile della gestione e fornitura dei template dei prompt utilizzati per le chiamate all'API OpenAI.
    *   Permette di centralizzare i prompt, facilitando la loro modifica e l'aggiunta di nuovi template specifici per tipo di contenuto o lezione.
    *   Utilizzato da `resume_generator.py` (specificamente dalla funzione `summarize_with_openai`) per ottenere il prompt appropriato prima di interrogare l'LLM.
*   **`langfuse_tracker.py`**: (AGGIUNTO)
    *   Definisce la classe `LangfuseTracker`.
    *   Responsabile dell'inizializzazione e della gestione delle interazioni con Langfuse.
    *   Fornisce metodi per:
        *   Avviare e terminare sessioni di tracciamento (`trace`) per l'intera elaborazione del corso, includendo metadati generali e informazioni sui prompt.
        *   Avviare e terminare span specifici per l'elaborazione di ogni capitolo, registrando metriche aggregate del capitolo (token, tempo).
        *   Tracciare singole chiamate ai modelli LLM (`generation`), registrando input, output, modello utilizzato, token consumati, latenza, eventuali errori, e informazioni sul prompt specifico utilizzato.
        *   Registrare metriche di valutazione complessive per l'elaborazione del corso (es. numero di lezioni processate, token totali, tempo totale di elaborazione).
    *   Utilizzato estensivamente da `resume_generator.py` per monitorare le prestazioni, i costi (indirettamente, dato che Langfuse li calcola), e il comportamento dell'applicazione durante l'elaborazione dei riassunti.

### Flusso di Esecuzione Principale (semplificato)

1.  L'utente esegue `python -m src.resume_generator <course_dir> [options]`.
2.  `main()` in `resume_generator.py` viene invocata.
3.  Vengono letti gli argomenti, configurato il logging e la directory di output.
4.  `APIKeyManager` carica la chiave OpenAI.
5.  `LangfuseTracker` viene inizializzato e una sessione (`trace`) per il corso viene avviata.
6.  L'applicazione naviga le directory dei capitoli del corso.
7.  Per ogni capitolo:
    a.  Viene avviato uno `span` in Langfuse per il capitolo.
    b.  Vengono identificate le lezioni (file VTT).
    c.  Per ogni lezione:
        i.  Viene estratto il testo dal file VTT.
        ii. Vengono cercati e processati i file PDF correlati, estraendo il loro testo.
        iii. Il testo VTT viene riassunto usando OpenAI. La chiamata LLM, i metadati (incluso `prompt_info`), i token e la latenza vengono tracciati con `LangfuseTracker`.
        iv. Se presente, il testo dei PDF viene riassunto usando OpenAI. Anche questa chiamata LLM è tracciata.
        v.  `MarkdownFormatter` viene usato per scrivere un file `.md` per la lezione.
    d.  Viene creato un file di riepilogo per il capitolo.
    e.  Lo `span` Langfuse per il capitolo viene terminato, registrando metriche aggregate del capitolo.
8.  Viene creato un file indice principale per il corso.
9.  Le metriche complessive del corso (lezioni processate, token totali, tempo totale) vengono registrate in Langfuse.
10. La sessione (`trace`) Langfuse per il corso viene terminata e i dati inviati.