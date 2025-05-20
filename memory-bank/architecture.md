# Architettura dell'Agente di Riassunto Corsi

## Panoramica

L'agente di riassunto corsi è un'applicazione Python modulare progettata per processare corsi didattici strutturati in cartelle, estrarre il testo dalle trascrizioni (VTT) e dai materiali di supporto (PDF), e generare riassunti intelligenti utilizzando l'API di OpenAI. L'architettura è organizzata secondo principi di responsabilità singola e separazione delle preoccupazioni.

## Struttura del Progetto

```
udemy-course-resumeeer/
│
├── resume_generator.py        # Script principale che orchestra l'intero processo
├── README.md                  # Documentazione del progetto
├── memory-bank/               # Directory per la documentazione del progetto
│   ├── architecture.md        # Documento di architettura
│   ├── tech-stack.md          # Stack tecnologico
│   └── product-requirements.md # Requisiti del prodotto
├── .env                       # File di configurazione per le chiavi API (non sotto controllo versione)
├── progress.md                # Documentazione del progresso dell'implementazione
└── output/                    # Directory per l'output generato (riassunti in markdown)
```

## Componenti Principali

### 1. Gestione degli Argomenti da Riga di Comando

Il modulo principale `resume_generator.py` utilizza `argparse` per processare gli argomenti della riga di comando:

```python
def parse_arguments():
    """
    Analizza gli argomenti da riga di comando.
    
    Returns:
        argparse.Namespace: Gli argomenti analizzati.
    """
    parser = argparse.ArgumentParser(
        description="Tool per riassumere corsi strutturati in cartelle."
    )
    
    parser.add_argument(
        "course_dir",
        type=str,
        help="Directory contenente il corso da processare."
    )
    
    parser.add_argument(
        "--output_dir",
        "-o",
        type=str,
        help="Directory di output per i riassunti generati. Se non specificata, "
             "verrà creata una directory 'resume_[nome_corso]' nella directory corrente."
    )
    
    return parser.parse_args()
```

Questa funzione definisce gli argomenti che lo script accetta:
- `course_dir`: Argomento posizionale obbligatorio che specifica la directory del corso da processare.
- `--output_dir` o `-o`: Argomento opzionale che specifica la directory di output. Se non fornito, viene creata una directory `resume_[nome_corso]`.

### 2. Configurazione della Directory di Output

La funzione `setup_output_directory` gestisce la creazione della directory di output:

```python
def setup_output_directory(course_dir, output_dir=None):
    """
    Configura la directory di output.
    
    Args:
        course_dir (str): Percorso della directory del corso.
        output_dir (str, optional): Percorso della directory di output specificata.
            
    Returns:
        Path: Percorso della directory di output configurata.
    """
    course_path = Path(course_dir)
    
    if not course_path.exists() or not course_path.is_dir():
        raise ValueError(f"La directory del corso '{course_dir}' non esiste o non è una directory.")
    
    if output_dir is None:
        # Se non è specificata una directory di output, crea 'resume_[nome_corso]'
        course_name = course_path.name
        output_path = Path(f"resume_{course_name}")
    else:
        output_path = Path(output_dir)
    
    # Crea la directory di output se non esiste
    output_path.mkdir(parents=True, exist_ok=True)
    
    return output_path
```

Questa funzione:
1. Verifica che la directory del corso esista e sia effettivamente una directory.
2. Se non è specificata una directory di output, crea una directory con nome `resume_[nome_corso]`.
3. Crea la directory di output se non esiste.
4. Restituisce il percorso della directory di output configurata.

### 3. Sistema di Logging

Il sistema di logging è configurato utilizzando il modulo `logging` standard di Python:

```python
def configure_logging():
    """
    Configura il sistema di logging di base.
    
    Imposta il formato dei messaggi di log per includere timestamp, livello e messaggio.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
```

Il sistema di logging:
1. Imposta un livello di logging di base (INFO).
2. Formatta i messaggi di log per includere timestamp, livello e il messaggio effettivo.
3. Viene utilizzato in tutto lo script per registrare eventi importanti durante l'esecuzione.
4. Permette un monitoraggio dettagliato del flusso di esecuzione e dei potenziali errori.

Nella funzione `main()`, il logging viene utilizzato per:
- Registrare l'avvio dello script.
- Registrare i parametri forniti dall'utente.
- Registrare il successo nella configurazione della directory di output.
- Registrare eventuali errori in modo dettagliato.

### 4. Navigazione della Struttura del Corso

La funzione `list_chapter_directories` è responsabile dell'identificazione dei capitoli del corso:

```python
def list_chapter_directories(course_dir):
    """
    Elenca le sottodirectory dirette di course_dir come capitoli.
    
    Args:
        course_dir (str o Path): Percorso della directory del corso.
            
    Returns:
        list: Lista ordinata di oggetti Path che rappresentano le directory dei capitoli.
        
    Raises:
        ValueError: Se course_dir non esiste o non è una directory.
    """
    course_path = Path(course_dir)
    
    if not course_path.exists() or not course_path.is_dir():
        raise ValueError(f"La directory del corso '{course_dir}' non esiste o non è una directory.")
    
    # Ottieni tutte le sottodirectory dirette
    chapter_dirs = [item for item in course_path.iterdir() if item.is_dir()]
    
    # Ordina le directory alfabeticamente
    chapter_dirs.sort()
    
    logging.info(f"Trovati {len(chapter_dirs)} capitoli nella directory del corso.")
    
    return chapter_dirs
```

Questa funzione:
1. Verifica che la directory del corso esista e sia effettivamente una directory.
2. Identifica tutte le sottodirectory dirette come capitoli del corso.
3. Ordina alfabeticamente le directory trovate.
4. Registra un messaggio di log con il numero di capitoli identificati.
5. Restituisce una lista ordinata di oggetti `Path` rappresentanti le directory dei capitoli.

Questa funzione è un componente fondamentale per la navigazione della struttura del corso, dato che fornisce al sistema la lista di capitoli da processare. L'ordinamento alfabetico garantisce che i capitoli vengano processati in un ordine prevedibile, anche se in futuro potrebbe essere utile implementare un ordinamento più sofisticato che tenga conto di prefissi numerici nei nomi delle directory.

La funzione `list_vtt_files` è responsabile dell'identificazione dei file VTT all'interno di un capitolo:

```python
def list_vtt_files(chapter_dir):
    """
    Elenca tutti i file VTT all'interno di una directory di capitolo.
    
    Args:
        chapter_dir (str o Path): Percorso della directory del capitolo.
            
    Returns:
        list: Lista ordinata di oggetti Path che rappresentano i file VTT.
        
    Raises:
        ValueError: Se chapter_dir non esiste o non è una directory.
    """
    chapter_path = Path(chapter_dir)
    
    if not chapter_path.exists() or not chapter_path.is_dir():
        raise ValueError(f"La directory del capitolo '{chapter_dir}' non esiste o non è una directory.")
    
    # Ottieni tutti i file VTT direttamente nella directory del capitolo
    vtt_files = [item for item in chapter_path.iterdir() if item.is_file() and item.suffix.lower() == '.vtt']
    
    # Ordina i file alfabeticamente
    vtt_files.sort()
    
    logging.info(f"Trovati {len(vtt_files)} file VTT nel capitolo '{chapter_path.name}'.")
    
    return vtt_files
```

Questa funzione:
1. Verifica che la directory del capitolo esista e sia effettivamente una directory.
2. Identifica tutti i file con estensione `.vtt` presenti direttamente nella directory del capitolo.
3. Verifica l'estensione dei file in modo case-insensitive, assicurando che tutti i file vengano rilevati.
4. Ordina alfabeticamente i file trovati.
5. Registra un messaggio di log con il numero di file VTT identificati.
6. Restituisce una lista ordinata di oggetti `Path` rappresentanti i file VTT.

Questa funzione è essenziale per identificare le lezioni all'interno di ciascun capitolo, dato che i file VTT contengono le trascrizioni delle lezioni che dovranno essere processate. L'ordinamento alfabetico garantisce che le lezioni vengano elaborate in un ordine prevedibile.

### 5. Gestore delle Chiavi API (APIKeyManager)

Responsabile della gestione sicura delle chiavi API, incluso il caricamento da file .env o variabili d'ambiente, l'hashing per il logging sicuro.

```python
class APIKeyManager:
    def __init__(self, key_name: str = "OPENAI_API_KEY"):
        # ...
    
    def get_key(self) -> str:
        # Ottiene la chiave API da varie fonti in modo sicuro
        # ...
```

### 6. Generatore di Riassunti (SimpleResumeGenerator)

Classe principale responsabile dell'orchestrazione dell'intero processo:

```python
class SimpleResumeGenerator:
    def __init__(self, course_dir, output_dir=None, ...):
        # ...
    
    def generate_resume(self):
        # Processo principale
        # ...
```

#### Sotto-componenti:

1. **Estrattori di Testo**:
   - `extract_text_from_vtt(vtt_file)`: Estrae testo dai file di trascrizione WebVTT
   - `extract_text_from_pdf(pdf_file)`: Estrae testo dai documenti PDF

2. **Processore di Chunk**:
   - `process_long_text(text)`: Divide testi lunghi in chunk per gestire i limiti del contesto LLM

3. **Riassuntori di Testo**:
   - `summarize_with_openai(text)`: Genera riassunti utilizzando l'API di OpenAI
   - `summarize_text_simple(text)`: Fallback per il riassunto basato su estrazione quando l'API non è disponibile

4. **Processore di Capitoli**:
   - `process_chapter(chapter_dir)`: Elabora una directory di capitolo con tutte le sue lezioni

5. **Generatore di Output**:
   - `create_index(chapters)`: Crea un file indice con collegamenti a tutti i capitoli riassunti

### 7. Sistema di Processing del Testo con LangChain (Estensione Prevista)

Per gestire meglio il contesto e i token con documenti lunghi, è prevista l'integrazione di LangChain con:

1. **Embedding e Vector Store**: 
   - Memorizzazione e indicizzazione di chunk di testo per ricerca semantica.
   - Utilizzo di FAISS per ricerca vettoriale efficiente.

2. **Catene di Riassunto**:
   - Strategia Map-Reduce: Riassume ogni chunk e poi combina i riassunti.
   - Strategia Refine: Riassume un chunk e poi raffina progressivamente con l'informazione dei chunk successivi.

## Flusso dei Dati

1. **Input**: Directory strutturata del corso con capitoli e lezioni
2. **Elaborazione**:
   - Scansione della struttura del corso
   - Estrazione del testo da VTT e PDF
   - Chunking del testo se necessario
   - Generazione di riassunti tramite API OpenAI o metodo fallback
3. **Output**: File Markdown per ogni capitolo + indice generale

## Gestione degli Errori

- Logging completo a vari livelli di dettaglio
- Fallback al riassunto semplice in caso di errori API
- Gestione robusta delle eccezioni durante l'elaborazione dei file

## Considerazioni sulla Scalabilità

Per corsi molto grandi o con numerosi PDF, l'architettura può essere estesa per:

1. **Elaborazione parallela**: Processare capitoli in parallelo
2. **Caching dei riassunti**: Evitare di rigenerare riassunti già creati
3. **Elaborazione progressiva**: Elaborare il corso in batch per evitare problemi di memoria

## Schema del Flusso di Elaborazione

```
Input (Corso) → Scansione della Struttura → Per ogni Capitolo → Per ogni Lezione → Estrazione Testo → Chunking → Riassunto → Output Markdown
                                                             └→ Per ogni PDF → Estrazione Testo → Chunking → Riassunto → 
```

### Implementazione Attuale

Attualmente, il progetto ha implementato:

#### `resume_generator.py`
Lo script principale che orchestrerà l'intero processo di generazione dei riassunti. Include:

1. **Gestione degli Argomenti da Riga di Comando**: Utilizza `argparse` per processare gli argomenti della riga di comando.
   - `course_dir`: Directory del corso da processare (obbligatorio).
   - `--output_dir` o `-o`: Directory di output per i riassunti (opzionale).

2. **Configurazione della Directory di Output**: La funzione `setup_output_directory` verifica che la directory del corso esista e crea la directory di output appropriata.

3. **Navigazione della Struttura del Corso**:
   - La funzione `list_chapter_directories` identifica le sottodirectory dirette come capitoli.
   - La funzione `list_vtt_files` identifica i file VTT all'interno di un capitolo.

4. **Funzione Main**: Orchestrazione iniziale del processo, con gestione degli errori di base.

Nelle prossime fasi, lo script sarà esteso per includere:
- Estrazione del testo da file VTT e PDF
- Chunking del testo per gestire documenti lunghi
- Integrazione con l'API di OpenAI per la generazione di riassunti
- Generazione di output in formato Markdown