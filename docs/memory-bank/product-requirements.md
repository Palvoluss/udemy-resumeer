# Requisiti del Prodotto per l'Agente di Riassunto Corsi

## Obiettivo

Creare un agente software che processi un corso strutturato in cartelle, estragga il contenuto testuale dalle trascrizioni e dai materiali, e generi riassunti completi e ben organizzati in formato Markdown.

## Funzionalità Principali

### 1. Gestione della Struttura del Corso

- **Requisito**: L'agente deve navigare correttamente una struttura di cartelle che rappresenta un corso.
- **Dettagli**:
  - Processare una directory principale del corso
  - Identificare le sottodirectory che rappresentano capitoli
  - All'interno di ogni capitolo, processare le lezioni (file VTT) e materiali correlati (PDF)
  - Preservare la struttura gerarchica del corso nei riassunti generati

### 2. Estrazione del Testo

- **Requisito**: L'agente deve estrarre il testo da diversi formati di file.
- **Dettagli**:
  - Estrarre testo dai file di trascrizione WebVTT
  - Rimuovere timestamp e metadati per ottenere testo pulito
  - Estrarre testo da file PDF quando presenti
  - Gestire correttamente formati e codifiche dei file

### 3. Riassunto Intelligente

- **Requisito**: Generare riassunti di alta qualità utilizzando l'API di OpenAI (o un metodo fallback).
- **Dettagli**:
  - Utilizzare GPT-3.5/GPT-4 per generare riassunti concisi ma informativi
  - Mantenere tutti i concetti chiave e le informazioni importanti
  - Supportare la generazione di schemi e tabelle quando appropriato
  - Gestire efficacemente i limiti di token dell'API

### 4. Gestione del Contesto e dei Token

- **Requisito**: Gestire efficacemente testi lunghi che supererebbero i limiti di contesto dei modelli.
- **Dettagli**:
  - Implementare il chunking intelligente del testo
  - Utilizzare strategie come Map-Reduce o Refine per riassumere testi lunghi
  - Combinare riassunti di chunk in modo coerente
  - Preferire un approccio basato su LangChain per la gestione del contesto

### 5. Output in Markdown

- **Requisito**: Generare riassunti ben strutturati in formato Markdown.
- **Dettagli**:
  - Creare file Markdown per ogni capitolo
  - Includere titoli, sottotitoli e formattazione appropriata
  - Generare un indice con collegamenti a tutti i capitoli
  - Supportare la generazione di tabelle e schemi

### 6. Gestione delle Chiavi API

- **Requisito**: Gestire in modo sicuro le chiavi API di OpenAI.
- **Dettagli**:
  - Supportare multiple fonti per la chiave (file .env, variabili d'ambiente, argomenti)
  - Implementare hash delle chiavi nei log per evitare esposizione
  - Fornire meccanismo di fallback a un metodo semplice se l'API non è disponibile

### 7. Parametrizzazione e Flessibilità

- **Requisito**: Permettere all'utente di personalizzare il comportamento dell'agente.
- **Dettagli**:
  - Supportare filtri per specifiche lezioni o range di lezioni
  - Permettere la specificazione di directory di output
  - Consentire di attivare/disattivare l'uso dell'API
  - Offrire controllo sulla lunghezza dei riassunti

## Requisiti Non Funzionali

### 1. Usabilità

- Interfaccia a riga di comando semplice e intuitiva
- Documentazione chiara su installazione e utilizzo
- Messaggi di errore informativi e actionable

### 2. Robustezza

- Gestione appropriata degli errori e delle eccezioni
- Fallback a metodi alternativi in caso di errori API
- Ripresa dell'elaborazione dopo errori quando possibile

### 3. Sicurezza

- Protezione delle chiavi API
- Nessuna esposizione di dati sensibili nei log
- Gestione sicura delle credenziali

### 4. Prestazioni

- Elaborazione efficiente di corsi di grandi dimensioni
- Ottimizzazione dell'uso dell'API per minimizzare costi
- Tempo di elaborazione ragionevole anche per corsi estesi

## Casi d'Uso Principali

1. **Caso d'Uso 1**: Un utente vuole generare riassunti di un intero corso con trascrizioni VTT.
2. **Caso d'Uso 2**: Un utente vuole generare riassunti solo per specifiche lezioni di un corso.
3. **Caso d'Uso 3**: Un utente vuole processare un corso che include sia trascrizioni VTT che materiali PDF.
4. **Caso d'Uso 4**: Un utente vuole generare riassunti senza utilizzare l'API di OpenAI (usando il metodo semplice).

## Criteri di Accettazione

1. L'agente deve processare correttamente la struttura di un corso Udemy di esempio con almeno 5 capitoli.
2. I riassunti generati devono mantenere tutti i concetti chiave dalle trascrizioni originali.
3. L'agente deve gestire correttamente testi molto lunghi attraverso il chunking.
4. I riassunti devono essere ben formattati in Markdown con titoli, sottotitoli e indice.
5. L'agente deve avere un fallback funzionante in caso di errori API.
