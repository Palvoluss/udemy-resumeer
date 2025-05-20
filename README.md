# Generatore di Riassunti per Corsi Udemy

Questo script Python permette di generare riassunti in formato Markdown dei corsi Udemy scaricati. Lo script estrae i testi dalle trascrizioni (file VTT), genera riassunti e crea file Markdown strutturati con i contenuti del corso.

## Caratteristiche

- Estrazione automatica dei testi dalle trascrizioni VTT
- Generazione di riassunti tramite API OpenAI (opzionale)
- Gestione intelligente di testi lunghi con chunking automatico
- Gestione sicura delle chiavi API con supporto per rotazione e hashing
- Creazione di file Markdown per ogni capitolo del corso
- Inclusione di riferimenti ai file PDF presenti nel corso
- Generazione di un indice con collegamenti a tutti i capitoli

## Requisiti

- Python 3.6+
- Librerie: requests, python-dotenv, pathlib

## Installazione

```bash
# Clona questo repository
git clone https://github.com/tuousername/udemy-course-resumeeer.git
cd udemy-course-resumeeer

# Installa le dipendenze
pip install requests python-dotenv
```

## Configurazione API

Esistono tre modi per configurare la chiave API di OpenAI:

1. **File .env** (consigliato):
   ```bash
   # Crea un file .env di esempio
   python resume_generator.py --create_env
   
   # Modifica il file .env creato con la tua chiave API
   nano .env
   ```

2. **Variabile d'ambiente**:
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   ```

3. **Parametro da riga di comando**:
   ```bash
   python resume_generator.py --api_key "your-openai-api-key"
   ```

## Utilizzo

### Uso base

```bash
python resume_generator.py
```

### Opzioni disponibili

```bash
python resume_generator.py \
  --course_dir "/path/to/your/udemy/course" \
  --output_dir "resume_output" \
  --use_ai \
  --api_key "your-openai-api-key"
```

### Parametri avanzati

```bash
python resume_generator.py \
  --model "gpt-4" \
  --max_tokens 800 \
  --chunk_size 15000 \
  --rotate_key \
  --new_key "your-new-openai-api-key"
```

### Parametri

- `--course_dir`: Directory contenente il corso Udemy scaricato
- `--output_dir`: Directory di output per i file Markdown generati
- `--use_ai`: Usa l'API OpenAI per generare riassunti intelligenti (default: True)
- `--api_key`: Chiave API di OpenAI per la generazione dei riassunti
- `--create_env`: Crea un file .env di esempio (non esegue il programma)
- `--model`: Modello di OpenAI da utilizzare (default: gpt-3.5-turbo)
- `--max_tokens`: Numero massimo di token per i riassunti (default: 500)
- `--chunk_size`: Dimensione in caratteri dei chunk per testi lunghi (default: 10000)
- `--rotate_key`: Ruota la chiave API (richiede una nuova chiave)
- `--new_key`: Nuova chiave API per la rotazione

## Gestione di testi lunghi

Lo script utilizza una strategia di chunking avanzata per gestire testi lunghi che supererebbero il limite di contesto dei modelli AI:

1. Divide il testo in chunk di dimensione appropriata (configurabile)
2. Riassume ogni chunk separatamente
3. Combina i riassunti dei chunk
4. Se necessario, esegue un riassunto finale dei riassunti combinati

Questa strategia permette di elaborare trascrizioni di qualsiasi lunghezza senza incorrere in errori di "context length exceeded".

## Sicurezza delle chiavi API

Questo script implementa diverse misure di sicurezza per la gestione delle chiavi API:

1. **Hashing delle chiavi nei log**: Le chiavi non vengono mai mostrate in chiaro nei log
2. **Rotazione delle chiavi**: Possibilità di aggiornare facilmente le chiavi API
3. **Gestione delle chiavi temporanee**: Supporto per chiavi usa-e-getta per ambienti di test
4. **Caricamento sicuro dal file .env**: Le chiavi vengono caricate in modo sicuro

## Struttura del file .env

Il file .env è un file di configurazione che permette di memorizzare la chiave API in modo sicuro:

```
# Inserisci qui la tua chiave API di OpenAI
OPENAI_API_KEY=your-api-key-here
```

## Struttura dei file generati

- `indice.md`: File di indice con collegamenti a tutti i capitoli
- `capitolo_XX.md`: File Markdown per ogni capitolo del corso, contenente:
  - Riassunto del capitolo
  - Trascrizioni complete delle lezioni
  - Link ai file PDF inclusi nel capitolo

## Note sull'API OpenAI

Per utilizzare la funzionalità di riassunto AI, è necessaria una chiave API di OpenAI. È possibile specificarla in tre modi:

1. Nel file .env (metodo consigliato per sviluppo locale)
2. Come argomento da riga di comando: `--api_key "your-api-key"`
3. Come variabile d'ambiente: `export OPENAI_API_KEY="your-api-key"`

Se non viene fornita una chiave API, lo script utilizzerà un metodo di riassunto semplice basato sul troncamento del testo.

## Gestione degli errori

Lo script include diversi meccanismi per gestire gli errori comuni:

- **Riprovare in caso di rate limiting**: Attende automaticamente e riprova se l'API è sovraccarica
- **Fallback al riassunto semplice**: Se l'API non è disponibile, utilizza un metodo di riassunto basato sul troncamento
- **Troncamento intelligente**: Tronca i testi in modo da mantenere il contesto se necessario

## Esempio di output

```markdown
# Capitolo 1: Introduzione al corso

## Riassunto del capitolo

Questo capitolo introduce i concetti base del web marketing...

## Contenuto delle lezioni

### Lezione 001: Introduzione al corso

**Riassunto:** Il docente Fabio presenta il corso di web marketing...

**Trascrizione completa:**
Ciao sono Fabio e ti voglio dare un caloroso benvenuto all'interno del mio corso di web marketing...
```

## Licenza

MIT 