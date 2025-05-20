# Generatore di Riassunti per Corsi Udemy

Questo script Python permette di generare riassunti in formato Markdown dei corsi Udemy scaricati. Lo script estrae i testi dalle trascrizioni (file VTT) e dai PDF, li divide in parti più piccole se necessario, e può generare riassunti di queste parti utilizzando l'API di OpenAI.

## Caratteristiche

- Estrazione automatica dei testi dalle trascrizioni VTT e da file PDF.
- Funzionalità di base per la generazione di riassunti tramite API OpenAI (richiede configurazione API).
- Gestione di testi lunghi tramite divisione in chunk (la strategia di riassunto combinato dei chunk è in sviluppo).
- Gestione sicura delle chiavi API OpenAI tramite file `.env` o variabili d'ambiente.
- Creazione di file Markdown (funzionalità di output dettagliata in sviluppo).

## Requisiti

- Python 3.6+
- Librerie: `python-dotenv`, `pathlib`, `PyPDF2`, `webvtt-py`, `langchain_text_splitters` (parte di `langchain`), `openai`

## Installazione

```bash
# Clona questo repository
# git clone https://github.com/tuousername/udemy-course-resumeeer.git
# cd udemy-course-resumeeer

# Installa le dipendenze
pip install -r requirements.txt
```

## Configurazione API OpenAI

Per utilizzare la funzionalità di riassunto tramite Intelligenza Artificiale, è **necessario** configurare una chiave API di OpenAI. Il progetto utilizza la classe `APIKeyManager` per gestire le chiavi API. Esistono due modi per configurare la chiave:

1. **File .env** (consigliato per sviluppo locale):
   Crea un file `.env` nella directory principale del progetto con il seguente contenuto:
   ```
   OPENAI_API_KEY=la_tua_chiave_api_openai
   ```
   Puoi copiare l'esempio da `docs/env_example.txt` (se disponibile) e modificarlo.

2. **Variabile d'ambiente**:
   Imposta una variabile d'ambiente denominata `OPENAI_API_KEY` con la tua chiave API.
   ```bash
   export OPENAI_API_KEY="la_tua_chiave_api_openai"
   ```
Se la chiave API non viene trovata o non è valida, la funzionalità di riassunto AI non sarà disponibile e lo script potrebbe terminare con un errore durante il tentativo di usarla.

## Utilizzo

Per eseguire lo script, specifica la directory del corso e, opzionalmente, una directory di output.

```bash
python resume_generator.py "/percorso/alla/tua/directory/del/corso" -o "/percorso/alla/directory/di/output"
```

Se la directory di output non è specificata, verrà creata una cartella `resume_[nome_corso]` nella directory corrente.

### Argomenti

- `course_dir`: (Obbligatorio) Percorso della directory contenente il materiale del corso da processare.
- `--output_dir` o `-o`: (Opzionale) Percorso della directory dove verranno salvati i riassunti generati.

## Funzionalità Attuali e Future

### Estrazione e Chunking del Testo
- Lo script può estrarre testo da file `.vtt` e `.pdf`.
- I testi lunghi vengono divisi in "chunk" più piccoli utilizzando `RecursiveCharacterTextSplitter` di Langchain per poter essere processati da modelli linguistici.

### Riassunto con OpenAI
- È implementata una funzione (`summarize_with_openai`) che può prendere un singolo chunk di testo e inviarlo all'API di OpenAI (modello `gpt-3.5-turbo`) per generare un riassunto dettagliato.
- **Importante**: L'orchestrazione completa del riassunto di interi corsi, capitoli o lezioni (che potrebbero richiedere il riassunto di multipli chunk e la combinazione di questi riassunti) è parte degli sviluppi futuri (come descritto nello Step 11 e successivi del piano di implementazione).

### Output
- La struttura finale dell'output in Markdown, con file per capitoli, lezioni e un indice generale, è pianificata ma non ancora completamente implementata nel flusso principale.

## Sicurezza delle chiavi API

Il modulo `api_key_manager.py` gestisce le chiavi API:
- Caricamento da file `.env` o variabili d'ambiente.
- Logging di un hash della chiave (non la chiave stessa) per verifica, se il logging è impostato a livelli di debug.
- Messaggi di errore chiari se la chiave non è configurata.

## Gestione degli Errori

- Lo script include logging per tracciare il processo e gli errori.
- Le chiamate all'API OpenAI includono una gestione di base degli errori (es. `APIConnectionError`, `RateLimitError`, `AuthenticationError`). In caso di errore API, solitamente viene sollevata un'eccezione che interrompe il processo per quel task specifico.
- Non sono attualmente implementati meccanismi di *retry* automatico per le chiamate API fallite o *fallback* a metodi di riassunto alternativi nel flusso principale.

## Esempio di output (Previsto)

La struttura di output finale prevista (ma ancora in sviluppo attivo) includerà:

```markdown
# Indice del Corso: [Nome Corso]

- [Capitolo 1: Introduzione](#capitolo-1-introduzione)
- [Capitolo 2: Concetti Avanzati](#capitolo-2-concetti-avanzati)

## Capitolo 1: Introduzione

### Riassunto del Capitolo
Questo capitolo introduce i concetti base...

### Lezione 1.1: Benvenuto
**Riassunto:** ...
**Testo Originale Chunk 1:** ...

### Lezione 1.2: Panoramica
**Riassunto:** ...
```

## Licenza

MIT 