# Architettura dell'Agente di Riassunto Corsi

## Panoramica

L'agente di riassunto corsi è un'applicazione Python modulare progettata per processare corsi didattici strutturati in cartelle, estrarre il testo dalle trascrizioni (VTT) e dai materiali di supporto (PDF), e generare riassunti intelligenti utilizzando l'API di OpenAI. L'architettura è organizzata secondo principi di responsabilità singola e separazione delle preoccupazioni.

## Struttura del Progetto

Il progetto è organizzato come segue:

```
udemy-course-resumeeer/
├── .courses/             # Directory di esempio per i corsi input e output (non tracciata da git)
├── .env                  # File per variabili d'ambiente (es. OPENAI_API_KEY) (non tracciato)
├── docs/
│   └── memory-bank/      # Documentazione di progetto, piani, requisiti
├── src/
│   ├── __init__.py       # Rende 'src' un package Python
│   ├── resume_generator.py # Script principale, orchestra il processo
│   ├── api_key_manager.py  # Gestisce le chiavi API
│   ├── markdown_formatter.py # Classe per la formattazione Markdown
│   └── ...               # Altri moduli futuri (es. langfuse_tracker.py)
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
        *   Chiama le funzioni per estrarre testo da file VTT e PDF.
        *   Utilizza le funzioni di riassunto (che a loro volta chiamano OpenAI) per generare i contenuti dei riassunti per VTT e PDF separatamente.
        *   Utilizza `markdown_formatter` per creare i file di output in formato Markdown (indice principale, riassunti dei capitoli, riassunti delle lezioni con sezioni distinte per VTT e PDF).
*   **`api_key_manager.py`**: 
    *   Definisce la classe `APIKeyManager`.
    *   Responsabile del caricamento sicuro della chiave API OpenAI da variabili d'ambiente o da un file `.env`.
    *   Fornisce metodi per ottenere la chiave e per ottenere un hash della chiave a scopo di logging.
*   **`markdown_formatter.py`**: 
    *   Definisce la classe `MarkdownFormatter`.
    *   Fornisce una serie di metodi per generare stringhe formattate secondo la sintassi Markdown (es. intestazioni, elenchi, link, blocchi di codice, linee orizzontali).
    *   Utilizzata da `resume_generator.py` per costruire il contenuto dei file di output.

### Flusso di Esecuzione Principale (semplificato)

1.  L'utente esegue `python -m src.resume_generator <course_dir> [options]`.
2.  `main()` in `resume_generator.py` viene invocata.
3.  Vengono letti gli argomenti, configurato il logging e la directory di output.
4.  `APIKeyManager` carica la chiave OpenAI.
5.  L'applicazione naviga le directory dei capitoli del corso.
6.  Per ogni capitolo:
    a.  Vengono identificate le lezioni (file VTT).
    b.  Per ogni lezione:
        i.  Viene estratto il testo dal file VTT.
        ii. Vengono cercati e processati i file PDF correlati, estraendo il loro testo.
        iii. Il testo VTT viene riassunto usando OpenAI (con prompt specifici).
        iv. Se presente, il testo dei PDF viene riassunto usando OpenAI (con prompt specifici).
        v.  `MarkdownFormatter` viene usato per scrivere un file `.md` per la lezione, contenente il titolo, il riassunto VTT, e una sezione separata con il riassunto dei PDF.
    c.  Viene creato un file di riepilogo per il capitolo (`_CHAPTER_SUMMARY_....md`) usando `MarkdownFormatter`, con link ai file delle lezioni.
7.  Viene creato un file indice principale (`index.md`) per il corso usando `MarkdownFormatter`, con link ai file di riepilogo dei capitoli.