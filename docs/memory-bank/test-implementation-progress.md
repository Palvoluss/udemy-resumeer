# Progresso Implementazione Unit Test e Linee Guida

## 1. Introduzione e Obiettivi

L'obiettivo principale dell'introduzione degli unit test è garantire la stabilità e la qualità del codebase `resumeeer` man mano che cresce in complessità. I test mirano a:

*   Prevenire regressioni durante lo sviluppo di nuove funzionalità o la refactorizzazione del codice esistente.
*   Verificare il corretto funzionamento delle singole unità di codice (funzioni, classi, metodi) in isolamento.
*   Fornire una documentazione vivente del comportamento atteso dei componenti del sistema.
*   Migliorare la manutenibilità e la fiducia nelle modifiche apportate al codice.

## 2. Architettura e Strumenti di Test

Per l'implementazione degli unit test, sono state fatte le seguenti scelte architetturali e sono stati adottati i seguenti strumenti:

### 2.1. Framework e Librerie Principali

*   **Framework di Test**: `unittest` (libreria standard di Python). È stato scelto per la sua integrazione nativa con Python e la sua diffusione.
*   **Code Coverage**: `coverage.py`. Utilizzato per misurare la percentuale di codice sorgente coperta dai test.
*   **Mocking HTTP**: `respx`. Selezionato specificamente per mockare le chiamate HTTP esterne, in particolare quelle verso l'API di OpenAI. Questo si è rivelato più robusto e manutenibile rispetto al patching diretto di oggetti client complessi.
*   **Mocking Generico**: `unittest.mock` (parte di `unittest`). Utilizzato per mockare oggetti e dipendenze interne al codebase.

### 2.2. Struttura delle Directory

*   I test sono collocati in una directory dedicata `tests/` alla radice del progetto, separata dal codice sorgente (`src/`).
*   Eventuali dati di test (fixtures) dovrebbero essere organizzati in una sottodirectory `tests/test_data/`, sebbene non ancora formalmente utilizzata in modo estensivo.

### 2.3. Convenzioni di Nomenclatura

*   **File di Test**: I nomi dei file di test seguono il pattern `test_*.py` (es. `test_markdown_formatter.py`).
*   **Classi di Test**: Le classi di test ereditano da `unittest.TestCase` e sono nominate con il prefisso `Test` seguito dal nome del modulo o della classe testata (es. `TestImageDescriber`).
*   **Metodi di Test**: I metodi di test all'interno delle classi sono nominati con il prefisso `test_*` (es. `test_describe_image_url_success`).

### 2.4. Strategie di Mocking

*   **Dipendenze Interne**: Per le dipendenze interne al progetto, si utilizza `unittest.mock.patch` o `unittest.mock.MagicMock` per isolare l'unità in fase di test.
*   **API Esterne (OpenAI)**: Le interazioni con l'API di OpenAI (e potenzialmente altre API HTTP future) sono mockate a livello di richiesta/risposta HTTP utilizzando `respx`. Questo approccio, adottato per `ImageDescriber`, permette di:
    *   Simulare risposte API di successo, errori specifici (es. 401, 429), ed errori di rete.
    *   Evitare la complessità del mocking diretto degli oggetti client della libreria `openai`, che si è dimostrato fragile.
    *   Avere test più stabili rispetto alle modifiche interne della libreria client.
*   **LangfuseTracker**: L'istanza di `LangfuseTracker` viene generalmente passata come `MagicMock` nei test che non si focalizzano specificamente sul tracciamento, per verificare che i metodi di tracciamento vengano chiamati come atteso senza dipendere da una reale istanza di Langfuse.

### 2.5. Gestione Dati di Test (Fixtures)

*   Per testare funzioni che operano su file (es. parser VTT, PDF), si utilizzano file di esempio reali o creati ad-hoc, gestiti tramite `tempfile` per garantire l'isolamento e la pulizia dopo i test.
*   L'intenzione è di consolidare i file di test riutilizzabili in `tests/test_data/`.

### 2.6. Code Coverage

*   La misurazione della copertura del codice viene eseguita con `coverage.py`.
*   È stato configurato un file `.coveragerc` per escludere dal report di copertura le sezioni di codice non rilevanti per i test unitari, come i blocchi `if __name__ == '__main__':`.
*   Comandi utilizzati:
    *   Esecuzione test con coverage: `coverage run --source=src -m unittest discover tests`
    *   Report testuale: `coverage report -m`
    *   Report HTML: `coverage html -d htmlcov` (per un'analisi più dettagliata)

## 3. Progresso dell'Implementazione

Al momento della stesura di questo documento, sono stati implementati o aggiornati i seguenti test:

*   **`tests/test_api_key_manager.py`**:
    *   Stato: Test preesistenti, corretti problemi di import.
    *   Copertura `src/api_key_manager.py`: 100%.
*   **`tests/test_pdf_extraction.py`**:
    *   Stato: Test preesistenti, corretti problemi di import.
    *   Copertura `src/resume_generator.py` (per la parte di `extract_text_from_pdf`): Buona, testata con `PdfExtractionTests`.
*   **`tests/test_real_chunking.py`** e **`tests/test_text_chunking.py`**:
    *   Stato: Test preesistenti, corretti problemi di import e rimossa la manipolazione di `sys.path`.
    *   Copertura `src/resume_generator.py` (per la parte di `chunk_text`): Buona.
*   **`tests/test_vtt_extraction.py`**:
    *   Stato: Test preesistenti, riscritti per utilizzare `unittest.TestCase`, corretti import e asserzioni sui messaggi di errore (gestione path relativi/assoluti).
    *   Copertura `src/resume_generator.py` (per la parte di `extract_text_from_vtt`): Buona, testata con `VTTExtractionTests`.
*   **`tests/test_markdown_formatter.py`**:
    *   Stato: Nuovi test implementati.
    *   Copertura `src/markdown_formatter.py`: 100%.
*   **`tests/test_html_parser.py`**:
    *   Stato: Nuovi test implementati, corretta un'asserzione relativa a newline.
    *   Copertura `src/html_parser.py`: 100% (escluso `if __name__ == '__main__':`).
*   **`tests/test_image_describer.py`**:
    *   Stato: Nuovi test implementati. Evoluzione significativa nella strategia di mocking, passando da `unittest.mock` con `create_autospec` a `respx` per gestire le chiamate all'API OpenAI. Questo ha risolto problemi di `AttributeError` e ha permesso un mocking più affidabile dei casi di successo, errore API e errore di rete.
    *   Copertura `src/image_describer.py`: 93% (mancano solo le linee del blocco `if __name__ == '__main__':`, escluse da `.coveragerc`).

**Copertura Totale Attuale (al 01/08/2024 circa):** 25%.
Il modulo `src/resume_generator.py` rimane quello con la copertura più bassa (13%) ed era identificato come il prossimo su cui focalizzarsi.

## 4. Problemi Riscontrati e Soluzioni Adottate

Durante l'implementazione dei test sono emersi alcuni ostacoli comuni:

*   **Errori di Importazione (`ModuleNotFoundError`, `ImportError`)**:
    *   Causa: Riorganizzazione della struttura del progetto (`src/`, `tests/`), esecuzione dei test come modulo.
    *   Soluzione: Correzione sistematica degli statement di import per utilizzare percorsi relativi corretti all'interno del package (es. `from src.modulo import Classe`) o assoluti se i test sono eseguiti dalla radice con `python -m unittest discover tests`.
*   **Mocking delle Chiamate API OpenAI**:
    *   Causa: Complessità e dettagli di implementazione interna del client `openai` (versione >= 1.0), che rendevano difficile e fragile il mocking diretto dei metodi del client (es. `client.chat.completions.create`). Tentativi con `unittest.mock.patch` e `create_autospec` portavano a `AttributeError` persistenti.
    *   Soluzione: Adozione della libreria `respx` per mockare le chiamate a livello HTTP. Questo ha disaccoppiato i test dall'implementazione specifica del client OpenAI, concentrandosi sul contratto dell'API HTTP. È stato necessario installare `respx`, aggiungerlo a `requirements.txt` e rifattorizzare i test di `ImageDescriber`.
*   **Asserzioni sui Messaggi di Errore**:
    *   Causa: I messaggi di errore esatti, specialmente quelli generati da eccezioni che includono path di file o corpi di risposta API, possono variare leggermente (es. path assoluti vs. relativi, formattazione di JSON con virgolette singole vs. doppie).
    *   Soluzione:
        *   Per i path, utilizzare `os.path.normpath` o costruire i messaggi attesi in modo dinamico.
        *   Per i messaggi di errore API wrappati dalla libreria `openai`, analizzare attentamente come `str(eccezione)` viene formattato e adeguare le asserzioni (es. gestione di `APIError` vs `APIConnectionError`, e il formato del corpo dell'errore).
*   **Rimozione Manipolazione `sys.path`**:
    *   Causa: Alcuni test più vecchi modificavano `sys.path` per risolvere gli import.
    *   Soluzione: Rimosse queste manipolazioni, preferendo una corretta configurazione degli import e dell'esecuzione dei test.

## 5. Prossimi Passi (Attualmente Sospesi)

Prima della richiesta di creare questo documento, il piano era di procedere con l'aumento della copertura per il modulo `src/resume_generator.py`, iniziando con funzioni più isolate come `find_related_files` e poi passando a quelle che gestiscono la logica di riassunto e l'orchestrazione, mockando le dipendenze come OpenAI e LangfuseTracker. 