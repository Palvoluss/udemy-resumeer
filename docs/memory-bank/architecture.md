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
│   ├── langfuse_tracker.py # Gestisce il tracciamento con Langfuse (AGGIUNTO)
│   ├── html_parser.py      # Estrae testo e immagini da file HTML (AGGIUNTO)
│   └── image_describer.py  # Genera descrizioni per immagini tramite LLM (AGGIUNTO)
├── tests/
│   ├── __init__.py       # Rende 'tests' un package Python
│   ├── test_api_key_manager.py # Test per APIKeyManager
│   ├── test_markdown_formatter.py # Test per MarkdownFormatter
│   ├── test_html_parser.py      # Test per HTMLParser
│   ├── test_image_describer.py  # Test per ImageDescriber
│   └── ...               # Altri file di test (PDF, VTT, Chunking)
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
        *   Chiama le funzioni per estrarre testo da file VTT, PDF e HTML (tramite `html_parser`).
        *   Se vengono trovate immagini in file HTML, utilizza `image_describer` per generare descrizioni testuali.
        *   Utilizza le funzioni di riassunto (che a loro volta chiamano OpenAI con il prompt formattato e tracciano la chiamata con `langfuse_tracker`) per generare i contenuti dei riassunti per VTT, PDF e HTML (quest'ultimo arricchito dalle descrizioni delle immagini).
        *   Utilizza `markdown_formatter` per creare i file di output in formato Markdown (indice principale, riassunti dei capitoli, riassunti delle lezioni con sezioni distinte per VTT, PDF e HTML).
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
        *   Tracciare singole chiamate ai modelli LLM (`generation`), registrando input, output, modello utilizzato, token consumati, latenza, eventuali errori, e informazioni sul prompt specifico utilizzato (include chiamate per riassunti testuali e descrizioni immagini).
        *   Registrare metriche di valutazione complessive per l'elaborazione del corso (es. numero di lezioni processate, token totali, tempo totale di elaborazione).
    *   Utilizzato estensivamente da `resume_generator.py` per monitorare le prestazioni, i costi (indirettamente, dato che Langfuse li calcola), e il comportamento dell'applicazione durante l'elaborazione dei riassunti.
*   **`html_parser.py`**: (AGGIUNTO)
    *   Definisce la funzione `extract_text_and_images_from_html`.
    *   Utilizza `BeautifulSoup` per analizzare il contenuto HTML.
    *   Responsabile dell'estrazione del testo pulito (rimuovendo tag non contenutistici come script, style, nav, footer, header, aside) e dell'identificazione dei tag `<img>` con i loro attributi `src` e `alt`.
    *   Utilizzato da `resume_generator.py` per processare i file HTML trovati nelle lezioni del corso.
*   **`image_describer.py`**: (AGGIUNTO)
    *   Definisce la classe `ImageDescriber`.
    *   Responsabile dell'interfacciamento con modelli LLM multimodali (es. OpenAI GPT-4V) per generare descrizioni testuali di immagini.
    *   Il metodo `describe_image_url` accetta un URL di immagine e restituisce una descrizione. Include la gestione base della chiave API e degli errori API.
    *   Contiene un segnaposto per `describe_image_data` per la futura gestione di immagini da dati binari.
    *   Utilizzato da `resume_generator.py` quando vengono identificate immagini nei file HTML, per arricchire il contenuto testuale prima del riassunto.

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
        iii.Vengono cercati e processati i file HTML correlati:
            1.  Il testo viene estratto usando `html_parser`.
            2.  Le immagini vengono identificate. Per ogni immagine accessibile, `image_describer` genera una descrizione testuale.
            3.  Le descrizioni delle immagini vengono integrate nel testo HTML estratto.
        iv. Vengono identificati e associati i file "orfani" (PDF/HTML non direttamente collegati a un VTT) alla lezione VTT corrente (se è la più vicina precedente).
        v.  Il testo VTT viene riassunto usando OpenAI. La chiamata LLM, i metadati, i token e la latenza vengono tracciati con `LangfuseTracker`.
        vi. Se presente, il testo dei PDF viene riassunto usando OpenAI. Anche questa chiamata LLM è tracciata.
        vii. Se presente, il testo HTML arricchito (con descrizioni immagini) viene riassunto usando OpenAI. Anche questa chiamata è tracciata.
        viii. Se presenti, i contenuti aggregati dei file orfani associati (testo da PDF, testo e descrizioni immagini da HTML) vengono riassunti usando OpenAI. Anche questa chiamata è tracciata.
        ix. `MarkdownFormatter` viene usato per scrivere un file `.md` per la lezione, includendo sezioni per VTT, PDF, HTML e una sezione per il materiale aggiuntivo proveniente dai file orfani.
    d.  Viene creato un file di riepilogo per il capitolo.
    e.  Lo `span` Langfuse per il capitolo viene terminato, registrando metriche aggregate del capitolo.
8.  Viene creato un file indice principale per il corso.
9.  Le metriche complessive del corso (lezioni processate, token totali, tempo totale) vengono registrate in Langfuse.
10. La sessione (`trace`) Langfuse per il corso viene terminata e i dati inviati.

## Testing e Qualità del Codice

L'approccio ai test unitari e di integrazione si basa sui seguenti principi e strumenti:

*   **Framework**: `unittest` dalla libreria standard Python.
*   **Directory dei Test**: Tutti i test risiedono nella directory `tests/`.
*   **Convenzioni**: I file di test seguono il pattern `test_*.py` e le classi di test ereditano da `unittest.TestCase`.
*   **Mocking**: 
    *   Per le dipendenze interne, si utilizza `unittest.mock`.
    *   Per le chiamate API esterne (come OpenAI), si predilige l'uso di `respx` per mockare a livello HTTP. Questo approccio è stato adottato per i test di `ImageDescriber` per garantire maggiore robustezza e isolamento dalle implementazioni interne delle librerie client.
*   **Copertura del Codice**: `coverage.py` viene utilizzato per monitorare la percentuale di codice coperta dai test. Un file `.coveragerc` è configurato per escludere blocchi non pertinenti (es. `if __name__ == '__main__':`).
*   **Documentazione dei Test**: I progressi specifici, le decisioni architetturali sui test e le problematiche riscontrate sono documentate in `docs/memory-bank/test-implementation-progress.md`.