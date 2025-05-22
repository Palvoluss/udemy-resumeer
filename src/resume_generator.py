#!/usr/bin/env python3
"""
Resume Generator: Tool per riassumere corsi strutturati in cartelle.

Questo script analizza una struttura di cartelle del corso, estrae testo da file VTT e PDF,
e genera riassunti intelligenti utilizzando l'API di OpenAI.
"""
import argparse
import os
import logging
from pathlib import Path
import webvtt # type: ignore
import PyPDF2 # type: ignore
from typing import List, Optional, Union # Union potrebbe essere necessario per coerenza con altre funzioni, lo lascio per ora
from langchain_text_splitters import RecursiveCharacterTextSplitter # type: ignore
from .api_key_manager import APIKeyManager # IMPORT AGGIUNTO
# from dotenv import load_dotenv
# import hashlib
import openai # type: ignore
import re # Necessario per find_related_pdf
from dotenv import load_dotenv # IMPORT AGGIUNTO
from .markdown_formatter import MarkdownFormatter # NUOVO IMPORT

# Configurazione del logger
logger = logging.getLogger(__name__)

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

def setup_output_directory(course_dir: str, output_dir: Optional[str] = None) -> Path:
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
        # Mantengo il logging dell'errore come da originale se presente, 
        # ma la modifica principale è ripristinare la firma e la logica base
        logger.error(f"La directory del corso '{course_dir}' non esiste o non è una directory.")
        raise ValueError(f"La directory del corso '{course_dir}' non esiste o non è una directory.")
    
    if output_dir is None:
        course_name = course_path.name
        # Ripristino la logica originale per il nome della directory di output
        output_path = Path(f"resume_{course_name}")
        logger.info(f"Nessuna directory di output specificata. Default a: {output_path}")
    else:
        output_path = Path(output_dir)
        logger.info(f"Directory di output specificata: {output_path}")
    
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Directory di output '{output_path}' assicurata.")
    except OSError as e:
        logger.error(f"Errore durante la creazione della directory di output '{output_path}': {e}")
        raise
    
    return output_path

def list_chapter_directories(course_dir: Union[str, Path]) -> List[Path]:
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

def list_vtt_files(chapter_dir: Union[str, Path]) -> List[Path]:
    """
    Elenca tutti i file VTT all'interno di una directory di capitolo.
    # Aggiungo nota sulla gestione dei file nascosti se era presente e rilevante
    Ignora i file che iniziano con '._' (file nascosti di macOS).

    Args:
        chapter_dir (Union[str, Path]): Percorso della directory del capitolo.
            
    Returns:
        List[Path]: Lista ordinata di oggetti Path che rappresentano i file VTT.
        
    Raises:
        ValueError: Se chapter_dir non esiste o non è una directory.
    """
    chapter_path = Path(chapter_dir)
    logger.debug(f"Elenco dei file VTT nella directory del capitolo: {chapter_path}")

    if not chapter_path.exists() or not chapter_path.is_dir():
        logger.error(f"La directory del capitolo '{chapter_dir}' non esiste o non è una directory.")
        raise ValueError(f"La directory del capitolo '{chapter_dir}' non esiste o non è una directory.")

    vtt_files = [
        item for item in chapter_path.iterdir()
        if item.is_file() and item.suffix.lower() == '.vtt' and not item.name.startswith('._')
    ]

    vtt_files.sort()

    logger.info(f"Trovati {len(vtt_files)} file VTT nel capitolo '{chapter_path.name}'.")
    if not vtt_files:
        logger.warning(f"Nessun file VTT trovato nel capitolo '{chapter_path.name}'.")
    return vtt_files

def extract_text_from_vtt(vtt_file_path: Union[str, Path]) -> str:
    """
    Estrae il testo parlato da un file VTT.
    
    Utilizza la libreria webvtt-py per analizzare il file VTT ed estrarre solo il contenuto
    testuale (escludendo timestamp, impostazioni dei sottotitoli e l'intestazione WEBVTT).
    
    Args:
        vtt_file_path (Union[str, Path]): Percorso del file VTT da processare.
            
    Returns:
        str: Il testo estratto dal file VTT, con sottotitoli separati da spazi o nuove linee.
        
    Raises:
        ValueError: Se il file non esiste o non è un file VTT valido.
        Exception: Per altri errori durante il parsing del file VTT.
    """
    vtt_path = Path(vtt_file_path)
    
    if not vtt_path.exists() or not vtt_path.is_file():
        raise ValueError(f"Il file VTT '{vtt_file_path}' non esiste o non è un file.")
    
    if vtt_path.suffix.lower() != '.vtt':
        raise ValueError(f"Il file '{vtt_file_path}' non è un file VTT (estensione attesa: .vtt).")
    
    try:
        logging.debug(f"Estrazione del testo dal file VTT: {vtt_path}")
        
        # Parse del file VTT utilizzando webvtt-py
        vtt_content = webvtt.read(str(vtt_path))
        
        # Estrai solo il testo dai sottotitoli, unendolo in una singola stringa
        extracted_text = "\n".join(caption.text for caption in vtt_content)
        
        logging.debug(f"Testo estratto ({len(extracted_text)} caratteri).")
        return extracted_text
        
    except webvtt.errors.MalformedFileError as e:
        raise ValueError(f"Il file VTT '{vtt_file_path}' è malformato: {str(e)}")
    except Exception as e:
        raise Exception(f"Errore durante l'estrazione del testo dal file VTT '{vtt_file_path}': {str(e)}")

def extract_text_from_pdf(pdf_file_path: Union[str, Path]) -> str:
    """
    Estrae il testo da un file PDF.
    Utilizza la libreria PyPDF2 per estrarre il testo da tutte le pagine del documento PDF.

    Args:
        pdf_file_path (Union[str, Path]): Percorso del file PDF da processare.
            
    Returns:
        str: Il testo estratto dal file PDF. Vuoto se il file è protetto o illeggibile.
        
    Raises:
        ValueError: Se il file non esiste o non è un file PDF valido.
    """
    pdf_path = Path(pdf_file_path)
    logger.debug(f"Tentativo di estrazione del testo dal file PDF: {pdf_path}")

    if not pdf_path.exists() or not pdf_path.is_file():
        logger.error(f"Il file PDF '{pdf_file_path}' non esiste o non è un file.")
        raise ValueError(f"Il file PDF '{pdf_file_path}' non esiste o non è un file.")

    if pdf_path.suffix.lower() != '.pdf':
        logger.error(f"Il file '{pdf_file_path}' non è un file PDF (estensione attesa: .pdf).")
        raise ValueError(f"Il file '{pdf_file_path}' non è un file PDF (estensione attesa: .pdf).")

    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            if pdf_reader.is_encrypted:
                try:
                    pdf_reader.decrypt('')
                    logger.warning(f"Il file PDF '{pdf_path}' era criptato ed è stato decriptato con una password vuota.")
                except Exception as decrypt_error:
                    logger.error(f"Il file PDF '{pdf_path}' è criptato e non può essere decriptato con una password vuota. Errore: {decrypt_error}")
                    return ""

            all_text: List[str] = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        all_text.append(page_text)
                    else:
                        logger.warning(f"Nessun testo estratto dalla pagina {page_num + 1} del file PDF '{pdf_path}'.")
                except Exception as page_extract_error:
                    logger.error(f"Errore durante l'estrazione del testo dalla pagina {page_num + 1} del PDF '{pdf_path}': {page_extract_error}")
            
            extracted_text = "\n\n".join(all_text).strip()
            
            if not extracted_text:
                logger.warning(f"Nessun testo estratto dal PDF '{pdf_path}'.")
            else:
                logger.info(f"Testo estratto con successo dal PDF '{pdf_path}' ({len(extracted_text)} caratteri).")
            return extracted_text
        
    except PyPDF2.errors.PdfReadError as e:
        logger.error(f"Errore di lettura PyPDF2 per il file PDF '{pdf_path}': {e}.")
        return ""
    except FileNotFoundError:
        logger.error(f"File PDF non trovato: '{pdf_path}'.")
        raise ValueError(f"Il file PDF '{pdf_file_path}' non è stato trovato.")
    except Exception as e:
        logger.error(f"Errore generico durante l'estrazione del testo dal file PDF '{pdf_path}': {e}")
        return ""

def chunk_text(text: str, max_chunk_size: int = 4000, overlap: int = 200) -> List[str]: # Ripristinato List[str]
    """
    Divide un testo lungo in chunks più piccoli mantenendo il significato semantico.
    
    Utilizza il RecursiveCharacterTextSplitter di LangChain per dividere il testo
    in modo che ciascun chunk non superi la dimensione massima specificata,
    preservando il significato semantico e cercando di non interrompere frasi o paragrafi.
    
    Args:
        text (str): Il testo da dividere in chunks.
        max_chunk_size (int, optional): Dimensione massima in caratteri per ciascun chunk.
            Default a 4000, che è adeguato per la maggior parte delle richieste API.
        overlap (int, optional): La dimensione del sovrapporsi tra i chunk.
            
    Returns:
        list[str]: Lista di chunks di testo, ciascuno di dimensione <= max_chunk_size.
        
    Raises:
        ValueError: Se il testo è vuoto o la dimensione massima del chunk è troppo piccola.
    """
    if not text or not text.strip():
        logging.warning("Il testo fornito a chunk_text è vuoto o contiene solo spazi.")
        return []
    
    if max_chunk_size < 100:
        raise ValueError(f"La dimensione massima del chunk ({max_chunk_size}) è troppo piccola. "
                         "Deve essere almeno 100 caratteri.")
    
    try:
        logging.debug(f"Divisione del testo ({len(text)} caratteri) in chunks di massimo {max_chunk_size} caratteri.")
        
        text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ". ", " ", ""],
            chunk_size=max_chunk_size,
            chunk_overlap=overlap,
            length_function=len,
            is_separator_regex=False
        )
        
        chunks = text_splitter.split_text(text)
        
        logging.info(f"Testo diviso in {len(chunks)} chunks.")
        
        return chunks
        
    except Exception as e:
        logging.error(f"Errore durante la divisione del testo in chunks: {e}")
        raise Exception(f"Errore durante la divisione del testo in chunks: {e}")

def summarize_with_openai(text_content: str, api_key: str, system_prompt_content: Optional[str] = None) -> str:
    """
    Genera un riassunto di un testo utilizzando l'API Chat Completions di OpenAI.
    # Ripristino docstring originale e logica interna se alterata.
    Args:
        text_content (str): Il testo da riassumere.
        api_key (str): La chiave API di OpenAI.
        system_prompt_content (Optional[str]): Il contenuto del prompt di sistema. 
                                               Se None, utilizza un prompt di default.

    Returns:
        str: Il testo riassunto.
        
    Raises:
        ValueError: Se text_content è vuoto o api_key non è fornita.
        openai.APIConnectionError: Se ci sono problemi di connessione all'API.
        openai.RateLimitError: Se il rate limit dell'API è stato superato.
        openai.AuthenticationError: Se la chiave API non è valida.
        openai.APIStatusError: Per altri errori API.
    """
    logger.debug(f"Tentativo di riassumere il testo con OpenAI. Lunghezza testo: {len(text_content)} caratteri.")

    if not text_content.strip():
        logger.warning("Il contenuto del testo per il riassunto è vuoto o contiene solo spazi bianchi.")
        return "Il contenuto fornito per il riassunto era vuoto."

    if not api_key:
        logger.error("La chiave API di OpenAI non è stata fornita per il riassunto.")
        raise ValueError("La chiave API di OpenAI è richiesta per il riassunto.")

    # Definizioni dei nuovi system prompt
    DEFAULT_SYSTEM_PROMPT = (
        "Presenta i seguenti contenuti in modo chiaro, dettagliato e ben strutturato, come se stessi spiegando direttamente l'argomento. "
        "Evita ogni riferimento al fatto che stai analizzando un testo (es. non usare frasi come 'il testo originale afferma', 'questo documento descrive'). "
        "L'obiettivo è estrarre e presentare direttamente i concetti chiave, le definizioni, i processi e le informazioni cruciali. "
        "Utilizza elenchi puntati, numerati o tabelle se appropriato per migliorare la chiarezza e l'organizzazione. "
        "Mantieni un tono oggettivo, informativo e autorevole, assicurando accuratezza e completezza. Scrivi in italiano fluente."
    )

    current_prompt = system_prompt_content if system_prompt_content is not None else DEFAULT_SYSTEM_PROMPT
    
    if system_prompt_content is None:
        logger.debug("Utilizzo del prompt di sistema di default per il riassunto.")
    else:
        logger.debug(f"Utilizzo del prompt di sistema personalizzato: \"{system_prompt_content[:100]}...\"")

    try:
        client = openai.OpenAI(api_key=api_key)
        logger.info("Chiamata all'API Chat Completions di OpenAI con il modello gpt-3.5-turbo.")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": current_prompt},
                {"role": "user", "content": text_content}
            ],
            temperature=0.5,
        )
        
        summary = response.choices[0].message.content
        if summary:
            logger.info(f"Riassunto generato con successo da OpenAI. Lunghezza riassunto: {len(summary)} caratteri.")
        else:
            logger.warning("OpenAI ha restituito un riassunto vuoto.")
            summary = "L'API di OpenAI ha restituito un riassunto vuoto."

        return summary.strip() if summary else ""

    except openai.APIConnectionError as e:
        logger.error(f"Errore di connessione all'API OpenAI: {e}")
        raise
    except openai.RateLimitError as e:
        logger.error(f"Rate limit dell'API OpenAI superato: {e}")
        raise
    except openai.AuthenticationError as e:
        logger.error(f"Errore di autenticazione con l'API OpenAI (chiave API non valida?): {e}")
        raise
    except openai.APIStatusError as e:
        logger.error(f"Errore API OpenAI (status {e.status_code}): {e.response}")
        raise
    except Exception as e:
        logger.error(f"Errore imprevisto durante la chiamata all'API OpenAI: {e}")
        raise Exception(f"Errore imprevisto durante la chiamata all'API OpenAI: {e}")

def summarize_long_text(text: str, api_key: str, max_chunk_size: int = 3800, overlap: int = 150) -> str:
    """
    Riassume un testo lungo, gestendo il chunking e utilizzando un approccio map-reduce.

    Args:
        text (str): Il testo lungo da riassumere.
        api_key (str): La chiave API di OpenAI.
        max_chunk_size (int, optional): La dimensione massima di ciascun chunk.
        overlap (int, optional): La dimensione del sovrapporsi tra i chunk.

    Returns:
        str: Il riassunto finale del testo.
    """
    logger.info(f"Inizio riassunto testo lungo (lunghezza: {len(text)} caratteri).")
    chunks = chunk_text(text, max_chunk_size, overlap)
    logger.info(f"Testo diviso in {len(chunks)} chunks.")

    if not chunks:
        logger.warning("Il testo non ha prodotto chunks, restituisco stringa vuota.")
        return ""

    if len(chunks) == 1:
        logger.info("Il testo è composto da un singolo chunk. Riassumo direttamente.")
        summary = summarize_with_openai(chunks[0], api_key)
        logger.info("Riassunto del singolo chunk completato.")
        return summary

    # Map: riassumere ogni chunk individualmente
    individual_summaries = []
    SYSTEM_PROMPT_CHUNK = ( # Definito qui per chiarezza o potrebbe essere globale
        "Fornisci una spiegazione chiara e concisa dei seguenti contenuti. "
        "Presenta le informazioni come se stessi insegnando direttamente l'argomento. "
        "Evita ogni riferimento al fatto che stai analizzando un testo (es. non usare frasi come 'il testo dice', 'l'autore menziona'). "
        "Concentrati sull'estrazione e la presentazione diretta dei concetti chiave, delle definizioni e dei processi descritti. "
        "Mantieni un tono oggettivo, informativo e autorevole. L'output deve essere in italiano fluente."
    )
    for i, chunk in enumerate(chunks):
        logger.info(f"Riassumo chunk {i+1}/{len(chunks)}...")
        try:
            chunk_summary = summarize_with_openai(chunk, api_key, system_prompt_content=SYSTEM_PROMPT_CHUNK)
            individual_summaries.append(chunk_summary)
            logger.info(f"Riassunto chunk {i+1} completato.")
        except Exception as e:
            logger.error(f"Errore durante il riassunto del chunk {i+1}: {e}")
            # Puoi decidere se continuare con gli altri chunk o interrompere
            # In questo caso, aggiungiamo un placeholder o saltiamo il chunk
            individual_summaries.append(f"[Errore nel riassumere il chunk {i+1}]")


    combined_summaries_text = "\\n\\n---===NEXT CHUNK SUMMARY===---\\n\\n".join(individual_summaries)
    logger.info(f"Riassunti individuali combinati (lunghezza totale: {len(combined_summaries_text)}).")

    # Reduce: riassumere i riassunti combinati
    logger.info("Creazione del meta-riassunto dei chunk combinati...")
    SYSTEM_PROMPT_META_SUMMARY = ( # Definito qui per chiarezza o potrebbe essere globale
        "Sei un esperto nella sintesi di informazioni complesse. Il testo fornito è una sequenza di spiegazioni dettagliate "
        "provenienti da diverse sezioni di un documento o lezione più ampio. Il tuo compito è integrare queste spiegazioni "
        "in un discorso unico, coerente e completo che copra l'intero argomento originale. "
        "Presenta il risultato come una trattazione organica dell'argomento, non come un riassunto di altri testi. "
        "Assicurati che tutte le informazioni e i concetti chiave siano mantenuti e integrati fluidamente. "
        "L'esposizione finale deve essere dettagliata, precisa e presentata in italiano fluente e autorevole, come se stessi spiegando direttamente la materia. "
        "Utilizza elenchi puntati o numerati, o tabelle, se aiutano a chiarire e strutturare le informazioni. "
        "Evita assolutamente frasi come 'il testo precedente diceva', 'combinando i punti precedenti', o qualsiasi riferimento al processo di sintesi."
    )
    final_summary = summarize_with_openai(combined_summaries_text, api_key, system_prompt_content=SYSTEM_PROMPT_META_SUMMARY)
    logger.info("Meta-riassunto completato.")
    return final_summary

def write_lesson_summary(formatter: MarkdownFormatter, lesson_title: str, vtt_summary: str, pdf_summary: Optional[str], output_file_path: Path) -> None: # Modificata firma
    """ 
    Scrive il riassunto di una lezione in un file Markdown, usando MarkdownFormatter.
    Include una sezione separata per il riassunto dei PDF, se presente.
    """
    logger.info(f"Scrittura del riassunto della lezione '{lesson_title}' in: {output_file_path}")
    output_file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        content = []
        content.append(formatter.format_header(lesson_title, level=2))
        content.append(formatter.new_line())
        
        if vtt_summary and vtt_summary.strip():
            content.append(vtt_summary)
        else:
            content.append(formatter.format_italic("Nessun riassunto disponibile per il contenuto video principale."))
        
        content.append(formatter.new_line())

        if pdf_summary and pdf_summary.strip():
            content.append(formatter.new_line()) # Linea vuota prima della regola orizzontale
            content.append(formatter.horizontal_rule())
            content.append(formatter.new_line())
            content.append(formatter.format_header("Approfondimenti dai Materiali PDF", level=3))
            content.append(formatter.new_line())
            content.append(pdf_summary)
        
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(content))
        logger.info(f"Riassunto della lezione '{lesson_title}' scritto con successo.")
    except IOError as e:
        logger.error(f"Errore di I/O durante la scrittura del file di riassunto della lezione '{output_file_path}': {e}")
    except Exception as e:
        logger.error(f"Errore imprevisto durante la scrittura del riassunto della lezione '{lesson_title}': {e}")

def find_related_pdf(vtt_file_path: Path, chapter_dir: Path) -> List[Path]:
    """
    Trova i file PDF correlati a un file VTT in base al prefisso numerico del nome del file.

    Args:
        vtt_file_path (Path): Il percorso del file VTT.
        chapter_dir (Path): La directory del capitolo che contiene il file VTT e potenziali PDF.

    Returns:
        List[Path]: Una lista di percorsi a file PDF corrispondenti.
                    Restituisce una lista vuota se non vengono trovati PDF corrispondenti
                    o se il nome del file VTT non ha un prefisso numerico.
    """
    logger.debug(f"Ricerca PDF correlati per VTT: '{vtt_file_path.name}' nella directory '{chapter_dir}'.")
    
    vtt_filename = vtt_file_path.name
    
    # Estrai il prefisso numerico dal nome del file VTT (es. "01" da "01_Welcome.vtt")
    # Cerca prima cifre all'inizio esatto del nome.
    match = re.match(r"^(\d+)", vtt_filename)
    if not match: # Se non trovato, cerca numeri preceduti da qualsiasi carattere non numerico.
        match = re.match(r"^\D*(\d+)", vtt_filename)

    if not match:
        logger.warning(f"Nessun prefisso numerico valido trovato nel nome del file VTT '{vtt_filename}'. Impossibile cercare PDF correlati.")
        return []
        
    numeric_prefix = match.group(1)
    logger.info(f"Prefisso numerico estratto da '{vtt_filename}': '{numeric_prefix}'.")
    
    related_pdfs: List[Path] = []
    if not chapter_dir.exists() or not chapter_dir.is_dir():
        logger.error(f"La directory del capitolo specificata '{chapter_dir}' non esiste o non è una directory.")
        return []

    # Pattern per matchare il prefisso all'inizio del nome del file PDF,
    # seguito da un carattere non alfanumerico o dalla fine del nome del file (per "[prefix].pdf")
    # Questo aiuta a distinguere "01" da "010" se il prefisso fosse "01".
    # re.escape(numeric_prefix) è usato per trattare il prefisso letteralmente se contenesse caratteri speciali regex.
    # (?:[^a-zA-Z0-9]|$) significa: un carattere non alfanumerico OPPURE la fine della stringa.
    pdf_prefix_pattern = rf"^{re.escape(numeric_prefix)}(?:[^a-zA-Z0-9].*|\.pdf$)"
    # Alternativa più semplice che matcha se il nome del file PDF inizia con "[prefisso]" seguito da "_", ".", "-", " "
    # o se è esattamente "[prefisso].pdf"

    for item in chapter_dir.iterdir():
        # Ignora i file nascosti di macOS (che iniziano con ._)
        if item.is_file() and item.suffix.lower() == '.pdf' and not item.name.startswith('._'):
            pdf_filename = item.name
            
            # Logica di matching migliorata:
            # 1. Controlla un match esatto del prefisso all'inizio del nome del file PDF,
            #    assicurandosi che sia seguito da un separatore comune o dalla fine del nome.
            #    Questo evita che "1" matchi "10_file.pdf".
            #    Esempi di separatori: "_", "-", ".", " "
            if re.match(rf"^{re.escape(numeric_prefix)}([\s_.-].*|\.pdf)$", pdf_filename, re.IGNORECASE):
                logger.info(f"Trovato PDF correlato (match primario): '{pdf_filename}' per il prefisso '{numeric_prefix}'.")
                related_pdfs.append(item)
            # 2. Fallback: se il nome del file inizia semplicemente con il prefisso numerico.
            #    Questo potrebbe essere meno preciso ma cattura casi semplici.
            #    Ad esempio, se il VTT è "01Video.vtt" e il PDF è "01Material.pdf".
            elif pdf_filename.startswith(numeric_prefix):
                # Aggiungiamo un controllo per evitare che "01" matchi "011extra.pdf"
                # Verifichiamo che il carattere dopo il prefisso non sia una cifra, se presente.
                if len(pdf_filename) > len(numeric_prefix) and pdf_filename[len(numeric_prefix)].isdigit():
                    pass # Non è un match valido, es. "01" in "010_file.pdf"
                else:
                    logger.info(f"Trovato PDF correlato (match startswith): '{pdf_filename}' per il prefisso '{numeric_prefix}'.")
                    related_pdfs.append(item)

    if not related_pdfs:
        logger.info(f"Nessun PDF correlato trovato per il prefisso '{numeric_prefix}' nella directory '{chapter_dir}'.")
    else:
        # Rimuovi duplicati se la logica di match dovesse aggiungerne (improbabile con la logica attuale ma sicuro)
        # e ordina i risultati per consistenza.
        unique_related_pdfs = sorted(list(set(related_pdfs)))
        logger.info(f"Trovati {len(unique_related_pdfs)} PDF correlati per il prefisso '{numeric_prefix}': {unique_related_pdfs}")
        return unique_related_pdfs
    
    return [] # Restituisce lista vuota se non trovati o dopo logica di deduplicazione se related_pdfs rimane vuota

def process_lesson(formatter: MarkdownFormatter, vtt_file: Path, chapter_dir: Path, base_output_dir: Path, api_key: str) -> Optional[Path]:
    lesson_name = vtt_file.stem
    sanitized_lesson_name = re.sub(r'[\\\\/:*? \"<>|]', '_', lesson_name)
    lesson_output_filename = f"{sanitized_lesson_name}_summary.md"
    chapter_name_for_path = chapter_dir.name
    lesson_output_path = base_output_dir / chapter_name_for_path / lesson_output_filename
    
    logger.info(f"--- Inizio elaborazione lezione: {lesson_name} ---")

    try:
        vtt_text = extract_text_from_vtt(vtt_file)
        logger.info(f"Testo estratto da VTT '{vtt_file.name}': {len(vtt_text)} caratteri.")

        vtt_summary = "" # Inizializza vtt_summary
        if vtt_text.strip():
            logger.info(f"Riassumo il testo VTT per la lezione '{lesson_name}' ({len(vtt_text)} caratteri)...")
            vtt_summary = summarize_long_text(vtt_text, api_key)
            if vtt_summary:
                logger.info(f"Riassunto VTT generato per '{lesson_name}': {len(vtt_summary)} caratteri.")
            else:
                logger.warning(f"Riassunto VTT per '{lesson_name}' è vuoto.")
        else:
            logger.warning(f"Testo VTT per '{lesson_name}' è vuoto. Nessun riassunto VTT generato.")

        related_pdfs = find_related_pdf(vtt_file, chapter_dir)
        pdf_texts: List[str] = []
        if related_pdfs:
            logger.info(f"Trovati {len(related_pdfs)} PDF correlati per '{vtt_file.name}'.")
            for pdf_file in related_pdfs:
                try:
                    pdf_text_content = extract_text_from_pdf(pdf_file)
                    if pdf_text_content:
                        logger.info(f"Testo estratto da PDF '{pdf_file.name}': {len(pdf_text_content)} caratteri.")
                        pdf_texts.append(pdf_text_content)
                    else:
                        logger.warning(f"Nessun testo estratto o PDF vuoto: {pdf_file.name}")
                except Exception as e_pdf:
                    logger.error(f"Errore durante l'estrazione del testo da PDF '{pdf_file.name}': {e_pdf}")
        else:
            logger.info(f"Nessun PDF correlato trovato per '{vtt_file.name}'.")

        pdf_summary_content: Optional[str] = None # Inizializza pdf_summary_content
        if pdf_texts:
            combined_pdf_text = "\n\n--- Separatore PDF Interno ---\n\n".join(pdf_texts)
            if combined_pdf_text.strip():
                logger.info(f"Riassumo il testo PDF combinato per '{lesson_name}' ({len(combined_pdf_text)} caratteri)...")
                pdf_summary_content = summarize_long_text(combined_pdf_text, api_key)
                if pdf_summary_content:
                    logger.info(f"Riassunto PDF generato per '{lesson_name}': {len(pdf_summary_content)} caratteri.")
                else:
                    logger.warning(f"Riassunto PDF per '{lesson_name}' è vuoto.")
            else:
                logger.info(f"Nessun contenuto testuale PDF combinato da riassumere per '{lesson_name}'.")
        
        # Scrivi il riassunto solo se almeno uno dei due (VTT o PDF) è stato generato
        if (vtt_summary and vtt_summary.strip()) or (pdf_summary_content and pdf_summary_content.strip()):
            write_lesson_summary(formatter, lesson_name, vtt_summary, pdf_summary_content, lesson_output_path)
            # logger.info(f"Riassunto della lezione '{lesson_name}' scritto in: {lesson_output_path}") # Già loggato da write_lesson_summary
            return lesson_output_path
        else:
            logger.warning(f"Nessun riassunto (VTT o PDF) valido generato per la lezione '{lesson_name}'. Nessun file scritto.")
            return None

    except ValueError as ve:
        logger.error(f"Errore di valore durante l'elaborazione della lezione '{lesson_name}': {ve}")
    except openai.APIError as api_err: # type: ignore
        logger.error(f"Errore API OpenAI durante l'elaborazione della lezione '{lesson_name}': {api_err}")
    except Exception as e:
        logger.error(f"Errore imprevisto durante l'elaborazione della lezione '{lesson_name}' ({vtt_file.name}): {e}")
    
    return None

def process_chapter(formatter: MarkdownFormatter, chapter_dir: Path, base_output_dir: Path, api_key: str) -> List[Optional[Path]]: # Modificata firma
    """
    Processa tutti i file VTT in una directory di capitolo.
    # ... (docstring unchanged) ...
    """
    chapter_name = chapter_dir.name
    logger.info(f"=== Inizio elaborazione capitolo: {chapter_name} ===")
    
    # Crea la sottodirectory per l'output del capitolo, se non esiste
    chapter_output_dir = base_output_dir / chapter_name
    try:
        chapter_output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Directory di output per il capitolo '{chapter_name}' assicurata: {chapter_output_dir}")
    except OSError as e:
        logger.error(f"Errore durante la creazione della directory di output per il capitolo '{chapter_name}': {e}")
        return [] # Ritorna una lista vuota se non si può creare la directory del capitolo

    vtt_files = list_vtt_files(chapter_dir)
    if not vtt_files:
        logger.warning(f"Nessun file VTT trovato nel capitolo '{chapter_name}'.")
        return []

    processed_lesson_files: List[Optional[Path]] = []
    for vtt_file in vtt_files:
        # Assicurati che process_lesson ritorni un Path o None
        # e che questo venga aggiunto a processed_lesson_files
        lesson_summary_path = process_lesson(formatter, vtt_file, chapter_dir, base_output_dir, api_key) # Passa formatter
        if lesson_summary_path:
            processed_lesson_files.append(lesson_summary_path)
        else:
            # Anche se una lezione fallisce, potremmo voler continuare con le altre
            # e registrare None per indicare il fallimento.
            processed_lesson_files.append(None) 
            
    logger.info(f"=== Fine elaborazione capitolo: {chapter_name}. {len(processed_lesson_files)} lezioni processate. ===")
    return processed_lesson_files

def create_chapter_summary(formatter: MarkdownFormatter, chapter_dir: Path, lesson_summary_files: List[Optional[Path]], base_output_dir: Path) -> Optional[Path]: # Modificata firma
    """
    Crea un file di riepilogo per il capitolo, usando MarkdownFormatter.
    # ... (docstring unchanged) ...
    """
    chapter_name = chapter_dir.name
    # Sanitizza il nome del capitolo per creare un nome di file valido
    sanitized_chapter_name = re.sub(r'[\\\\/:*?\"<>|]', '_', chapter_name)
    summary_file_name = f"_CHAPTER_SUMMARY_{sanitized_chapter_name}.md"
    # Il file di riassunto del capitolo va nella directory principale del corso di output,
    # o nella directory del capitolo stesso? Il piano originale (1.1.5) suggerisce "capitoli (inizialmente con link)".
    # `progress.md` Step 15 dice "crea un file di riepilogo per il capitolo".
    # Lo metto nella directory base_output_dir per ora, per coerenza con l'index principale.
    # Modifica: lo metto all'interno della cartella del capitolo per una migliore organizzazione.
    chapter_output_dir = base_output_dir / chapter_name
    summary_file_path = chapter_output_dir / summary_file_name

    logger.info(f"Creazione del riassunto per il capitolo '{chapter_name}' in '{summary_file_path}'")

    # Assicura che la directory del capitolo esista (dovrebbe essere già stata creata da process_chapter)
    summary_file_path.parent.mkdir(parents=True, exist_ok=True)

    valid_lesson_files = [f for f in lesson_summary_files if f is not None]

    if not valid_lesson_files:
        logger.warning(f"Nessun file di riassunto di lezione valido fornito per il capitolo '{chapter_name}'.")
        return None

    try:
        content = []
        content.append(formatter.format_header(f"Riepilogo Capitolo: {chapter_name}", level=1))
        content.append(formatter.new_line())
        content.append("Questo capitolo include le seguenti lezioni:")
        content.append(formatter.new_line())

        for lesson_file_path in valid_lesson_files:
            lesson_name = lesson_file_path.stem.replace('_summary', '')
            # Crea un link relativo dalla posizione del file di riassunto del capitolo
            # al file della lezione.
            # Esempio: _CHAPTER_SUMMARY_NomeCapitolo.md -> NomeLezione_summary.md
            relative_lesson_path = lesson_file_path.name # Link al file nella stessa directory
            link = formatter.format_link(lesson_name, relative_lesson_path)
            content.append(formatter.format_list_item(link))
        
        content.append(formatter.new_line())
        content.append(formatter.horizontal_rule())
        content.append(formatter.new_line())
        content.append(f"*Riepilogo generato per il capitolo '{chapter_name}'.*")

        with open(summary_file_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(content))
        
        logger.info(f"File di riassunto del capitolo '{summary_file_path}' creato con successo.")
        return summary_file_path
    except IOError as e:
        logger.error(f"Errore di I/O durante la scrittura del file di riassunto del capitolo '{summary_file_path}': {e}")
    except Exception as e:
        logger.error(f"Errore imprevisto durante la creazione del riassunto del capitolo '{chapter_name}': {e}")
    
    return None

def create_main_index(formatter: MarkdownFormatter, course_name: str, chapter_summary_files: List[Optional[Path]], base_output_dir: Path) -> Optional[Path]: # Modificata firma
    """
    Crea un file index.md principale per il corso, usando MarkdownFormatter.
    # ... (docstring unchanged) ...
    """
    # Sanitizza il nome del corso per creare un nome di file valido per l'indice
    # Anche se 'index.md' è standard, se il nome del corso fosse usato altrove, la sanitizzazione è buona pratica.
    sanitized_course_name = re.sub(r'[\\\\/:*?\"<>|]', '_', course_name)
    index_file_name = "index.md" # Nome standard per l'indice
    index_file_path = base_output_dir / index_file_name

    logger.info(f"Creazione del file indice principale per il corso '{course_name}' in '{index_file_path}'")

    valid_chapter_files = [f for f in chapter_summary_files if f is not None]

    if not valid_chapter_files:
        logger.warning(f"Nessun file di riassunto di capitolo valido fornito per il corso '{course_name}'.")
        return None

    try:
        content = []
        content.append(formatter.format_header(f"Indice del Corso: {course_name}", level=1))
        content.append(formatter.new_line())
        content.append("Questo corso è organizzato nei seguenti capitoli:")
        content.append(formatter.new_line())

        for chapter_file_path in valid_chapter_files:
            # chapter_file_path è tipo: base_output_dir/NomeCapitolo/_CHAPTER_SUMMARY_NomeCapitolo.md
            # Vogliamo linkare a base_output_dir/NomeCapitolo/_CHAPTER_SUMMARY_NomeCapitolo.md
            # da base_output_dir/index.md
            # Quindi il link relativo è NomeCapitolo/_CHAPTER_SUMMARY_NomeCapitolo.md
            
            chapter_dir_name = chapter_file_path.parent.name # Estrae "NomeCapitolo"
            relative_chapter_path = chapter_file_path.relative_to(base_output_dir)

            # chapter_name = chapter_file_path.stem.replace('_CHAPTER_SUMMARY_', '')
            # Il nome del capitolo è meglio prenderlo dal nome della directory
            chapter_name = chapter_dir_name

            link = formatter.format_link(f"Capitolo: {chapter_name}", str(relative_chapter_path))
            content.append(formatter.format_list_item(link))
            
        content.append(formatter.new_line())
        content.append(formatter.horizontal_rule())
        content.append(formatter.new_line())
        content.append(f"*Indice generato per il corso '{course_name}'.*")

        with open(index_file_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(content))
        
        logger.info(f"File indice principale '{index_file_path}' creato con successo.")
        return index_file_path
    except IOError as e:
        logger.error(f"Errore di I/O durante la scrittura del file indice '{index_file_path}': {e}")
    except Exception as e:
        logger.error(f"Errore imprevisto durante la creazione del file indice per '{course_name}': {e}")
        
    return None

def main():
    """
    Funzione principale per eseguire il generatore di riassunti.
    """
    configure_logging()
    args = parse_arguments()
    
    load_dotenv() # Carica le variabili d'ambiente dal file .env
    
    try:
        # Inizializza il gestore delle chiavi API
        # Specifica il nome della variabile d'ambiente se diverso da OPENAI_API_KEY
        api_key_manager = APIKeyManager(key_name="OPENAI_API_KEY")
        openai_api_key = api_key_manager.get_key()
        # Logga solo un hash della chiave per sicurezza
        logger.info(f"Chiave API OpenAI caricata con successo. Hash: {api_key_manager._hash_key(openai_api_key)}")
        
        # Configura la directory di output
        output_dir = setup_output_directory(args.course_dir, args.output_dir)
        course_name = Path(args.course_dir).name # Nome del corso dalla directory di input

        # Istanzia il MarkdownFormatter
        formatter = MarkdownFormatter() # NUOVA ISTANZA

        # Elenca le directory dei capitoli
        chapter_dirs = list_chapter_directories(args.course_dir)
        if not chapter_dirs:
            logger.warning(f"Nessun capitolo trovato nella directory del corso '{args.course_dir}'.")
            return

        all_chapter_summary_files: List[Optional[Path]] = []

        for chapter_dir in chapter_dirs:
            # Processa ogni capitolo (lezioni al suo interno)
            # process_chapter ora ritorna una lista di Path ai file di riassunto delle lezioni
            lesson_summary_files_for_chapter = process_chapter(formatter, chapter_dir, output_dir, openai_api_key) # Passa formatter
            
            # Filtra i None se alcune lezioni non hanno prodotto un output
            valid_lesson_summary_files = [f for f in lesson_summary_files_for_chapter if f is not None]
            
            if valid_lesson_summary_files:
                # Crea il file di riassunto del capitolo
                chapter_summary_file = create_chapter_summary(formatter, chapter_dir, valid_lesson_summary_files, output_dir) # Passa formatter
                all_chapter_summary_files.append(chapter_summary_file)
            else:
                logger.warning(f"Nessun riassunto di lezione valido generato per il capitolo '{chapter_dir.name}'.")
                all_chapter_summary_files.append(None) # Aggiungi None per mantenere la corrispondenza se necessario

        # Filtra i None se alcuni capitoli non hanno prodotto un output
        valid_chapter_summary_files = [f for f in all_chapter_summary_files if f is not None]

        if valid_chapter_summary_files:
            # Crea l'indice principale del corso
            create_main_index(formatter, course_name, valid_chapter_summary_files, output_dir) # Passa formatter
        else:
            logger.warning(f"Nessun file di riassunto di capitolo valido generato per il corso '{course_name}'.")

        logger.info("Elaborazione del corso completata.")
        
    except ValueError as ve:
        logger.error(f"Errore di configurazione o di input: {ve}")
    except openai.APIError as api_err: # type: ignore
        # Questo blocco potrebbe essere ridondante se gli errori API sono già gestiti
        # nelle funzioni chiamate, ma può servire come un catch-all finale.
        logger.error(f"Errore API OpenAI durante l'esecuzione principale: {api_err}")
    except Exception as e:
        logger.error(f"Errore imprevisto durante l'esecuzione principale: {e}", exc_info=True)

if __name__ == '__main__':
    main()