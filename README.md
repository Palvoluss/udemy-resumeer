# Generatore di Riassunti per Corsi Udemy

Questo script Python permette di generare riassunti dettagliati in formato Markdown dei corsi Udemy (o simili) strutturati in cartelle. Lo script estrae i testi dalle trascrizioni (file VTT) e dai materiali di supporto (PDF), li riassume utilizzando l'API di OpenAI e genera una struttura navigabile di file Markdown.

## Caratteristiche Principali

-   **Struttura Modulare**: Codice organizzato in una directory `src/` per una migliore manutenibilità.
-   **Estrazione Testo Multi-formato**: Estrae automaticamente il testo da:
    -   File di trascrizione `.vtt`.
    -   Documenti `.pdf` associati alle lezioni.
-   **Riassunti Intelligenti con OpenAI**:
    -   Utilizza l'API di OpenAI (modello `gpt-3.5-turbo` o configurabile) per generare riassunti.
    -   Gestisce testi lunghi dividendoli in chunk significativi.
    -   I riassunti sono generati in uno stile diretto, evitando la terza persona (es. "il testo dice...") per una lettura più fluida e immediata.
-   **Output Markdown Strutturato**:
    -   Genera un file `index.md` principale per il corso con link ai riassunti dei capitoli.
    -   Crea un file di riepilogo per ogni capitolo (`[nome_capitolo]_summary.md`) con link ai riassunti delle singole lezioni.
    -   Produce un file di riassunto per ogni lezione (`[nome_lezione]_summary.md`), con:
        -   Il riassunto del contenuto della trascrizione VTT.
        -   Una sezione separata "Approfondimenti dai Materiali PDF" con il riassunto dei PDF associati (se presenti).
    -   Utilizza una classe `MarkdownFormatter` dedicata per garantire una formattazione Markdown consistente.
-   **Gestione Sicura delle API Key**: Carica la chiave API OpenAI da file `.env` o variabili d'ambiente.
-   **Logging Dettagliato**: Fornisce log per tracciare il processo di elaborazione.

## Requisiti

-   Python 3.7+
-   Librerie: `python-dotenv`, `pathlib`, `PyPDF2`, `webvtt-py`, `langchain_text_splitters`, `openai`
    (Consultare `requirements.txt` per le versioni esatte)

## Installazione

1.  **Clona il repository:**
    ```bash
    # git clone https://github.com/tuo_username/udemy-course-resumeeer.git # Sostituisci con il tuo URL
    # cd udemy-course-resumeeer
    ```

2.  **Crea un ambiente virtuale (consigliato):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Su Windows: venv\\Scripts\\activate
    ```

3.  **Installa le dipendenze:**
    ```bash
    pip install -r requirements.txt
    ```

## Configurazione API OpenAI

Per utilizzare la funzionalità di riassunto è **necessaria** una chiave API di OpenAI.

1.  **Crea un file `.env`** nella directory principale del progetto (accanto a `src/`).
2.  Aggiungi la tua chiave API al file `.env`:
    ```env
    OPENAI_API_KEY="la_tua_chiave_api_openai"
    ```
    Puoi copiare il file `docs/memory-bank/env_example.txt` (se presente) rinominandolo in `.env` e modificandolo.
    In alternativa, puoi impostare la variabile d'ambiente `OPENAI_API_KEY` nel tuo sistema.

## Utilizzo

Lo script viene eseguito come modulo Python. Specifica la directory del corso e, opzionalmente, una directory di output.

```bash
python -m src.resume_generator "/percorso/alla/tua/directory/del/corso" -o "/percorso/alla/directory/di/output"
```

-   Se la directory di output non è specificata, verrà creata una cartella `resume_[nome_corso]` (dove `[nome_corso]` è il nome della directory del corso) nella directory da cui viene eseguito lo script.

### Argomenti da Riga di Comando

-   `course_dir`: **(Obbligatorio)** Percorso della directory contenente il materiale del corso da processare.
-   `--output_dir` o `-o`: **(Opzionale)** Percorso della directory dove verranno salvati i riassunti generati.

## Struttura dell'Output Generato

Dato un corso con la seguente struttura di input:

```
mio_corso/
├── 01 - Introduzione/
│   ├── 01_Benvenuto.vtt
│   ├── 01_Materiale_Benvenuto.pdf
│   └── 02_Panoramica.vtt
└── 02 - Concetti Avanzati/
    └── 01_Primo_Concetto.vtt
```

L'output generato nella directory specificata (es. `output_resumeeer/mio_corso/`) sarà simile a:

```
output_resumeeer/mio_corso/
├── index.md                     # Indice principale del corso
├── 01 - Introduzione/
│   ├── 01_Benvenuto_summary.md
│   └── 02_Panoramica_summary.md
├── 01 - Introduzione_summary.md # Riepilogo del Capitolo 1
├── 02 - Concetti Avanzati/
│   └── 01_Primo_Concetto_summary.md
└── 02 - Concetti Avanzati_summary.md # Riepilogo del Capitolo 2
```

**Contenuto dei file:**
-   `index.md`: Titolo del corso e link ai file `_summary.md` di ogni capitolo.
-   `[nome_capitolo]_summary.md`: Titolo del capitolo e link ai file `_summary.md` di ogni lezione in quel capitolo.
-   `[nome_lezione]_summary.md`:
    -   Titolo della lezione.
    -   Riassunto del contenuto VTT.
    -   (Se presente) Sezione "Approfondimenti dai Materiali PDF" con il riassunto del PDF.

## Contribuire

Sentiti libero di aprire issue o pull request per suggerire miglioramenti o correggere bug.

## Licenza

MIT 