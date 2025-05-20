# Stack Tecnologico per l'Agente di Riassunto Corsi

## Linguaggio di Programmazione
- **Python 3.6+**: Scelto per la sua leggibilità, estensibilità e vasto ecosistema di librerie per l'elaborazione del testo e l'integrazione con API esterne.

## Componenti Principali

### 1. Gestione del File System
- **pathlib**: Libreria built-in di Python per la navigazione e manipolazione del file system in modo object-oriented.
- **os**: Modulo standard per operazioni sul sistema operativo e percorsi di file.

### 2. Estrazione e Processing del Testo
- **webvtt-py**: Libreria per il parsing e l'estrazione del testo dai file di trascrizione WebVTT.
- **PyPDF2**: Per l'estrazione del testo da documenti PDF.
- **re (regex)**: Per la pulizia e la manipolazione dei testi estratti.
- **nltk**: Natural Language Toolkit per l'elaborazione del testo (tokenizzazione, stopwords).

### 3. Gestione del Contesto e Chunking
- **LangChain**: Framework per costruire applicazioni con LLM, specializzato nella gestione del contesto.
  - Document Loaders: Per caricare documenti da varie fonti
  - Text Splitters: Per dividere documenti in chunk gestibili
  - Embedding Models: Per trasformare testo in vettori
  - Vector Stores (FAISS): Per la ricerca semantica efficiente
  - Summarization Chains: Per implementare strategie di riassunto come map-reduce o refine

### 4. Interazione con LLM
- **openai**: Libreria client ufficiale per interagire con l'API di OpenAI.
- **requests**: Per effettuare chiamate HTTP alle API di OpenAI.

### 5. Sicurezza e Configurazione
- **python-dotenv**: Per la gestione sicura delle variabili d'ambiente (API key).
- **hashlib**: Per l'hashing delle chiavi API nei log.
- **argparse**: Per la gestione degli argomenti da riga di comando.

### 6. Output
- **Markdown**: Per la formattazione dei riassunti generati.

## Perché Questo Stack?

Questo stack è ottimizzato per bilanciare semplicità e robustezza. Utilizza principalmente librerie standard Python dove possibile, con l'aggiunta strategica di LangChain per gestire le complessità legate all'integrazione con LLM e alla gestione dei token nelle richieste.

Il principale vantaggio di questa configurazione è che:

1. **Offre gestione avanzata del contesto**: Tramite LangChain possiamo implementare strategie come map-reduce per riassumere documenti molto lunghi.
2. **È modulare e manutenibile**: Ogni componente ha una responsabilità chiara.
3. **Bilancia prestazioni e semplicità**: Evita framework complessi quando non necessari.
4. **Scala con la dimensione dei dati**: Può gestire efficacemente corsi con molte lezioni e materiali allegati.

## Dipendenze
```
langchain>=0.0.267
openai>=0.27.0
faiss-cpu>=1.7.4
python-dotenv>=0.21.0
requests>=2.28.0
pathlib>=1.0.1
PyPDF2>=3.0.0
nltk>=3.8.0
webvtt-py>=0.4.6