#!/usr/bin/env python3
"""
Resume Generator: Tool per riassumere corsi strutturati in cartelle.

Questo script analizza una struttura di cartelle del corso, estrae testo da file VTT e PDF,
e genera riassunti intelligenti utilizzando l'API di OpenAI.
"""
import argparse
import os
import logging
import time
from pathlib import Path
import webvtt # type: ignore
import PyPDF2 # type: ignore
from typing import List, Optional, Union, Dict, Tuple, Callable # Union potrebbe essere necessario per coerenza con altre funzioni, lo lascio per ora
from langchain_text_splitters import RecursiveCharacterTextSplitter # type: ignore
from .api_key_manager import APIKeyManager # IMPORT AGGIUNTO
from .langfuse_tracker import LangfuseTracker # NUOVO IMPORT
# from dotenv import load_dotenv
# import hashlib
import openai # type: ignore
import re # Necessario per find_related_pdf
from dotenv import load_dotenv # IMPORT AGGIUNTO
from .markdown_formatter import MarkdownFormatter # NUOVO IMPORT
from .prompt_manager import PromptManager # NUOVO IMPORT PER PROMPT_MANAGER
from .html_parser import extract_text_and_images_from_html # NUOVO IMPORT PER HTML
from .image_describer import ImageDescriber # NUOVO IMPORT PER IMMAGINI
from datetime import datetime # IMPORT AGGIUNTO

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

def get_file_prefix(file_path: Path) -> Optional[str]:
    """
    Estrae il prefisso numerico dal nome del file.
    Es. "01_Intro.vtt" -> "01", "Lecture 01 - Topic.pdf" -> "01"
    """
    name = file_path.stem # Nome del file senza estensione
    # Cerca numeri all'inizio del nome del file
    match = re.match(r"^(\d+)", name)
    if match:
        return match.group(1)
    
    # Cerca numeri preceduti da caratteri non numerici (es. "Lecture 01")
    match = re.search(r"\D(\d+)", name)
    if match:
        return match.group(1)
        
    return None

def identify_orphan_files(chapter_dir: Path, vtt_files: List[Path]) -> List[Path]:
    """
    Identifica i file PDF e HTML orfani in una directory di capitolo.
    Un file è orfano se non ha un file VTT corrispondente con lo stesso prefisso numerico.

    Args:
        chapter_dir (Path): Percorso della directory del capitolo.
        vtt_files (List[Path]): Lista dei percorsi dei file VTT nel capitolo.

    Returns:
        List[Path]: Lista ordinata dei percorsi dei file orfani (PDF e HTML).
    """
    logger.debug(f"Identificazione dei file orfani nella directory: {chapter_dir}")
    orphan_files: List[Path] = []
    
    vtt_prefixes = {get_file_prefix(vtt_file) for vtt_file in vtt_files if get_file_prefix(vtt_file) is not None}
    logger.debug(f"Prefissi VTT trovati: {vtt_prefixes}")

    for item in chapter_dir.iterdir():
        if item.is_file() and not item.name.startswith('._'):
            if item.suffix.lower() in ['.pdf', '.html']:
                file_prefix = get_file_prefix(item)
                logger.debug(f"Controllo file: {item.name}, prefisso: {file_prefix}")
                if file_prefix is None or file_prefix not in vtt_prefixes:
                    logger.info(f"File orfano identificato: {item.name} (prefisso: {file_prefix})")
                    orphan_files.append(item)
                # Se ha un prefisso ma questo prefisso non è tra quelli dei VTT, è orfano.
                # Se non ha un prefisso numerico riconosciuto, è anche considerato orfano 
                # (potrebbe essere un file generico del capitolo non legato a una lezione specifica).
                # Questa logica va raffinata se la definizione di orfano è strettamente "non ha VTT *corrispondente*".
                # Per ora, se non matcha un VTT esistente tramite prefisso, è orfano.

    orphan_files.sort()
    logger.info(f"Trovati {len(orphan_files)} file orfani (PDF/HTML) nel capitolo '{chapter_dir.name}'.")
    return orphan_files

def map_orphans_to_lessons(vtt_files: List[Path], orphan_files: List[Path]) -> Dict[Path, List[Path]]:
    """
    Associa i file orfani alla lezione VTT valida immediatamente precedente.

    Args:
        vtt_files (List[Path]): Lista ordinata dei file VTT.
        orphan_files (List[Path]): Lista ordinata dei file orfani.

    Returns:
        Dict[Path, List[Path]]: Un dizionario che mappa ogni file VTT
                                 a una lista dei file orfani ad esso associati.
    """
    if not vtt_files:
        logger.warning("Nessun file VTT fornito per mappare gli orfani. Tutti gli orfani saranno ignorati.")
        return {}

    # Combina e ordina tutti i file per nome per determinare la precedenza
    all_files_sorted: List[Tuple[Path, str]] = [] # (path, tipo)
    for vtt_file in vtt_files:
        all_files_sorted.append((vtt_file, "vtt"))
    for orphan_file in orphan_files:
        all_files_sorted.append((orphan_file, "orphan"))
    
    # Ordina per nome del file
    all_files_sorted.sort(key=lambda x: x[0].name)

    lesson_to_orphans_map: Dict[Path, List[Path]] = {vtt_file: [] for vtt_file in vtt_files}
    current_vtt_parent: Optional[Path] = None

    logger.debug(f"Mappatura orfani: file ordinati totali: {[f[0].name for f in all_files_sorted]}")

    for file_path, file_type in all_files_sorted:
        if file_type == "vtt":
            current_vtt_parent = file_path
            logger.debug(f"Trovato VTT: {file_path.name}. Impostato come parent corrente.")
        elif file_type == "orphan":
            if current_vtt_parent:
                lesson_to_orphans_map[current_vtt_parent].append(file_path)
                logger.info(f"File orfano '{file_path.name}' associato alla lezione VTT '{current_vtt_parent.name}'.")
            else:
                # Se un orfano appare prima di qualsiasi VTT, lo associamo al primo VTT della lista
                # Questo è un caso limite, idealmente tali file potrebbero essere gestiti a livello di capitolo
                # se non come materiale introduttivo alla prima lezione.
                first_vtt_file = vtt_files[0] # Sappiamo che vtt_files non è vuoto da controllo iniziale
                lesson_to_orphans_map[first_vtt_file].append(file_path)
                logger.warning(f"File orfano '{file_path.name}' trovato prima di qualsiasi VTT. Associato alla prima lezione VTT '{first_vtt_file.name}'.")

    for vtt_file, associated_orphans in lesson_to_orphans_map.items():
        if associated_orphans:
            logger.debug(f"Lezione '{vtt_file.name}' ha {len(associated_orphans)} file orfani associati: {[o.name for o in associated_orphans]}")
        else:
            logger.debug(f"Lezione '{vtt_file.name}' non ha file orfani associati.")
            
    return lesson_to_orphans_map

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

def summarize_with_openai(
    text_content: str, 
    api_key: str, 
    prompt_manager: PromptManager, # AGGIUNTO prompt_manager
    system_prompt_content: Optional[str] = None, # Questo potrebbe diventare obsoleto o gestito diversamente
    langfuse_tracker: Optional[LangfuseTracker] = None,
    chapter_name: Optional[str] = None,
    lesson_name: Optional[str] = None,
    content_type: str = "vtt",
    lesson_type_for_prompt: str = "practical_theoretical_face_to_face" # AGGIUNTO per tracciamento
) -> Tuple[str, Optional[Dict[str, int]]]:
    """
    Invia una richiesta di riassunto all'API di OpenAI.

    Utilizza il modello specificato (attualmente gpt-4o-mini) per generare
    un riassunto del testo fornito. Gestisce le eccezioni comuni dell'API.
    Traccia la chiamata con Langfuse se un tracker è fornito.

    Args:
        text_content (str): Il testo da riassumere.
        api_key (str): La chiave API di OpenAI.
        prompt_manager (PromptManager): Istanza di PromptManager per ottenere i prompt.
        system_prompt_content (str, optional): Contenuto del prompt di sistema. 
                                               Potrebbe essere rimosso o modificato in base all'uso di PromptManager.
        langfuse_tracker (Optional[LangfuseTracker], optional): Istanza di LangfuseTracker.
        chapter_name (Optional[str], optional): Nome del capitolo (per Langfuse).
        lesson_name (Optional[str], optional): Nome della lezione (per Langfuse).
        content_type (str): Tipo di contenuto (es. "vtt", "pdf", per Langfuse).
        lesson_type_for_prompt (str): Tipo di lezione usato per selezionare il prompt (per Langfuse).

    Returns:
        str: Il riassunto generato da OpenAI, o una stringa di errore in caso di fallimento.
        Tuple[str, Optional[Dict[str, int]]]: Riassunto e informazioni sull'uso dei token.
    """
    # openai.api_key = api_key # Rimosso perché la chiave è passata direttamente alla chiamata client
    max_retries = 3
    retry_delay = 5  # secondi
    # Legge il nome del modello dalla variabile d'ambiente o usa un default
    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini") 

    # Ottenere e formattare il prompt usando PromptManager
    # Per ora, usiamo il tipo di default. In futuro, potremmo voler passare un lesson_type specifico.
    try:
        current_prompt_template = prompt_manager.get_lesson_prompt(lesson_type=lesson_type_for_prompt) # USA lesson_type_for_prompt
        user_prompt_content = prompt_manager.format_prompt(current_prompt_template, lesson_transcript=text_content)
    except ValueError as e:
        logger.error(f"Errore nel recuperare o formattare il prompt: {e}")
        return f"Errore nella configurazione del prompt: {e}", None

    # Il system_prompt_content potrebbe non essere più necessario se il prompt principale è completo.
    # Se ancora necessario, dovrà essere integrato nella logica di PromptManager o passato separatamente.
    # Per ora, lo commentiamo se il prompt da PromptManager è inteso come prompt utente completo.
    messages = [
        # {"role": "system", "content": system_prompt_content if system_prompt_content else "Sei un assistente utile che riassume testi."}, # COMMENTATO/MODIFICABILE
        {"role": "user", "content": user_prompt_content}
    ]
    
    for attempt in range(max_retries):
        start_time_attempt = time.time() # Per la latenza di questo tentativo
        error_for_langfuse: Optional[str] = None
        summary_for_langfuse: str = ""
        token_usage_for_langfuse: Optional[Dict[str, int]] = None

        try:
            logger.info(f"Tentativo {attempt + 1} di chiamata API OpenAI per riassumere: lezione='{lesson_name}', tipo='{content_type}'.")
            
            client = openai.OpenAI(api_key=api_key)
            completion = client.chat.completions.create(
                model=model_name, # Utilizza la variabile model_name
                messages=messages, # type: ignore
                temperature=0.5,
            )
            
            duration_attempt = time.time() - start_time_attempt
            logger.info(f"Chiamata API OpenAI completata in {duration_attempt:.2f} secondi.")

            summary = completion.choices[0].message.content
            summary_for_langfuse = summary if summary else ""
            
            if completion.usage:
                token_usage_for_langfuse = {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens
                }

            if summary:
                logger.info(f"Riassunto generato con successo per: lezione='{lesson_name}', tipo='{content_type}'. Lunghezza: {len(summary)} caratteri.")
                # Chiamata a LangfuseTracker in caso di successo
                if langfuse_tracker:
                    prompt_info_for_langfuse = {"lesson_type_used": lesson_type_for_prompt, "model_used": model_name} # INFO PROMPT
                    langfuse_tracker.track_llm_call(
                        input_text=user_prompt_content, 
                        output_text=summary_for_langfuse,
                        model=model_name, # Assicura che model_name sia passato qui
                        chapter_name=chapter_name,
                        lesson_name=lesson_name,
                        content_type=content_type,
                        token_usage=token_usage_for_langfuse,
                        latency_ms=duration_attempt * 1000,
                        error=None,
                        prompt_info=prompt_info_for_langfuse # PASSATO prompt_info
                    )
                return summary.strip(), token_usage_for_langfuse
            else:
                logger.warning(f"La chiamata API OpenAI per '{lesson_name}' ('{content_type}') ha restituito un riassunto vuoto.")
                summary_for_langfuse = "Riassunto non disponibile (risposta vuota dall'API)."
                error_for_langfuse = "Empty summary returned by API" # Per Langfuse
                # Chiamata a LangfuseTracker in caso di riassunto vuoto (trattato come un "warning" o "errore logico")
                if langfuse_tracker:
                    prompt_info_for_langfuse = {"lesson_type_used": lesson_type_for_prompt, "model_used": model_name} # INFO PROMPT
                    langfuse_tracker.track_llm_call(
                        input_text=user_prompt_content,
                        output_text=summary_for_langfuse, 
                        model=model_name, # Assicura che model_name sia passato qui
                        chapter_name=chapter_name,
                        lesson_name=lesson_name,
                        content_type=content_type,
                        token_usage=token_usage_for_langfuse, # Potrebbe essere None se usage non è disponibile
                        latency_ms=duration_attempt * 1000,
                        error=error_for_langfuse,
                        prompt_info=prompt_info_for_langfuse # PASSATO prompt_info
                    )
                return summary_for_langfuse, token_usage_for_langfuse

        except openai.APIConnectionError as e:
            error_message = f"Errore di connessione API OpenAI dopo {attempt + 1} tentativi: {e}"
            logger.error(f"Errore di connessione API OpenAI (tentativo {attempt + 1}/{max_retries}): {e}")
            error_for_langfuse = f"APIConnectionError: {e}"
            if attempt == max_retries - 1:
                if langfuse_tracker:
                    prompt_info_for_langfuse = {"lesson_type_used": lesson_type_for_prompt, "model_used": model_name} # INFO PROMPT
                    langfuse_tracker.track_llm_call(input_text=user_prompt_content, output_text="", model=model_name, chapter_name=chapter_name, lesson_name=lesson_name, content_type=content_type, latency_ms=(time.time() - start_time_attempt) * 1000, error=error_for_langfuse, prompt_info=prompt_info_for_langfuse)
                return error_message, None
        except openai.RateLimitError as e:
            error_message = f"Errore di rate limit API OpenAI dopo {attempt + 1} tentativi: {e}"
            logger.warning(f"Rate limit API OpenAI raggiunto (tentativo {attempt + 1}/{max_retries}): {e}. Riprovo tra {retry_delay}s...")
            error_for_langfuse = f"RateLimitError: {e}"
            if attempt == max_retries - 1:
                if langfuse_tracker:
                    prompt_info_for_langfuse = {"lesson_type_used": lesson_type_for_prompt, "model_used": model_name} # INFO PROMPT
                    langfuse_tracker.track_llm_call(input_text=user_prompt_content, output_text="", model=model_name, chapter_name=chapter_name, lesson_name=lesson_name, content_type=content_type, latency_ms=(time.time() - start_time_attempt) * 1000, error=error_for_langfuse, prompt_info=prompt_info_for_langfuse)
                return error_message, None
        except openai.APIStatusError as e: 
            error_message = f"Errore API OpenAI (Status {e.status_code}) dopo {attempt + 1} tentativi: {e.message}"
            logger.error(f"Errore API OpenAI (Status {e.status_code}) (tentativo {attempt + 1}/{max_retries}): {e.message}")
            error_for_langfuse = f"APIStatusError {e.status_code}: {e.message}"
            if attempt == max_retries - 1:
                if langfuse_tracker:
                    prompt_info_for_langfuse = {"lesson_type_used": lesson_type_for_prompt, "model_used": model_name} # INFO PROMPT
                    langfuse_tracker.track_llm_call(input_text=user_prompt_content, output_text="", model=model_name, chapter_name=chapter_name, lesson_name=lesson_name, content_type=content_type, latency_ms=(time.time() - start_time_attempt) * 1000, error=error_for_langfuse, prompt_info=prompt_info_for_langfuse)
                return error_message, None
        except Exception as e: # Qualsiasi altra eccezione
            error_message = f"Errore imprevisto durante la chiamata API OpenAI: {e}"
            logger.error(f"Errore imprevisto durante la chiamata API OpenAI (tentativo {attempt + 1}/{max_retries}): {e}")
            error_for_langfuse = f"Unexpected error: {str(e)}" # str(e) per assicurare stringa
            if attempt == max_retries - 1:
                # Traccia l'errore finale con Langfuse
                if langfuse_tracker:
                    prompt_info_for_langfuse = {"lesson_type_used": lesson_type_for_prompt, "model_used": model_name} # INFO PROMPT
                    langfuse_tracker.track_llm_call(
                        input_text=user_prompt_content,
                        output_text="",
                        model=model_name, # Assicura che model_name sia passato qui
                        chapter_name=chapter_name,
                        lesson_name=lesson_name,
                        content_type=content_type,
                        token_usage=None, # Non disponibile in caso di errore grave prima della chiamata
                        latency_ms=(time.time() - start_time_attempt) * 1000,
                        error=error_for_langfuse,
                        prompt_info=prompt_info_for_langfuse # PASSATO prompt_info
                    )
                return error_message, None
        
        time.sleep(retry_delay)

    final_error_message = "Fallimento nella generazione del riassunto dopo tutti i tentativi."
    # Traccia il fallimento finale se tutti i tentativi sono esauriti
    if langfuse_tracker:
        prompt_info_for_langfuse = {"lesson_type_used": lesson_type_for_prompt, "model_used": model_name} # INFO PROMPT
        langfuse_tracker.track_llm_call(
            input_text=user_prompt_content,
            output_text="",
            model=model_name, # Assicura che model_name sia passato qui
            chapter_name=chapter_name,
            lesson_name=lesson_name,
            content_type=content_type,
            token_usage=None,
            latency_ms=(time.time() - start_time_attempt) * 1000, # Latenza dell'ultimo tentativo fallito
            error=final_error_message,
            prompt_info=prompt_info_for_langfuse # PASSATO prompt_info
        )
    return final_error_message, None

def summarize_long_text(
    text: str, 
    api_key: str, 
    prompt_manager: PromptManager, # AGGIUNTO prompt_manager
    max_chunk_size: int = 3800, 
    overlap: int = 150,
    langfuse_tracker: Optional[LangfuseTracker] = None,
    chapter_name: Optional[str] = None,
    lesson_name: Optional[str] = None,
    content_type: str = "vtt",
    lesson_type_for_prompt: str = "practical_theoretical_face_to_face" # AGGIUNTO esplicitamente
) -> Tuple[str, Optional[Dict[str, int]]]:
    """
    Gestisce il riassunto di testi lunghi dividendoli in chunk.

    Utilizza RecursiveCharacterTextSplitter per dividere il testo. 
    Attualmente, riassume solo il primo chunk se il testo supera max_chunk_size.
    TODO: Implementare una strategia di riassunto map-reduce o refine per testi lunghi.

    Args:
        text (str): Testo completo da riassumere.
        api_key (str): Chiave API OpenAI.
        prompt_manager (PromptManager): Istanza di PromptManager.
        max_chunk_size (int): Dimensione massima dei chunk di testo.
        overlap (int): Sovrapposizione tra i chunk.
        langfuse_tracker (Optional[LangfuseTracker]): Istanza di LangfuseTracker.
        chapter_name (Optional[str]): Nome del capitolo.
        lesson_name (Optional[str]): Nome della lezione.
        content_type (str): Tipo di contenuto.
        lesson_type_for_prompt (str): Tipo di lezione usato per selezionare il prompt.

    Returns:
        str: Riassunto generato (o del primo chunk se il testo è troppo lungo).
        Tuple[str, Optional[Dict[str, int]]]: Riassunto e informazioni sull'uso dei token.
    """
    # text_splitter = RecursiveCharacterTextSplitter(chunk_size=max_chunk_size, chunk_overlap=overlap)
    # chunks = text_splitter.split_text(text)
    
    # Calcolo approssimativo dei token (molto grezzo, OpenAI usa un tokenizzatore specifico)
    # Un token è approssimativamente 4 caratteri in inglese.
    estimated_tokens = len(text) / 3 # Stima più conservativa per essere sicuri
    
    # Limite di token del modello gpt-3.5-turbo-0125 è 16,385 tokens.
    # Teniamo un margine per il prompt e la risposta.
    # Ad esempio, se il prompt è ~200 token e vogliamo una risposta di ~1000-2000 token,
    # il testo di input non dovrebbe superare ~12000-13000 token.
    # max_chunk_size in caratteri dovrebbe riflettere questo.
    # Se max_chunk_size è 3800 caratteri, sono circa 1000-1300 token (a seconda della lingua e contenuto).
    # Questo è molto conservativo per un singolo chunk. Il limite di contesto del modello è molto più alto.
    # Il problema del chunking sorge quando il *testo intero* è troppo grande, non un singolo chunk.
    
    # Il system_prompt_content per summarize_with_openai potrebbe essere passato da qui o gestito internamente.
    # Per ora, summarize_with_openai lo gestirà o userà quello di default.
    
    if estimated_tokens > (max_chunk_size * 0.75): # Se i token stimati superano il 75% della dimensione massima del chunk (in caratteri)
                                                 # Questa logica andrà rivista con un tokenizzatore vero.
                                                 # Per ora, è una semplice euristica per evitare testi troppo lunghi per un singolo invio.
        logger.warning(f"Il testo per '{lesson_name}' ('{content_type}') è lungo ({len(text)} caratteri, stimati {estimated_tokens:.0f} tokens) "
                       f"e potrebbe superare i limiti. Verrà inviato così com'è per ora.")
        # In futuro: implementare map-reduce o refine qui.
        # Per ora, inviamo l'intero testo e lasciamo che summarize_with_openai gestisca la chiamata.
        # Se il testo è *davvero* troppo lungo per l'API (es. > 16k tokens per gpt-3.5-turbo),
        # la chiamata API fallirà. Il chunking deve essere fatto *prima* di chiamare summarize_with_openai.
        
        # ----- INIZIO LOGICA DI CHUNKING BASE (DA MIGLIORARE) -----
        # Questa è una logica di chunking molto semplificata.
        # Il text_splitter di Langchain è più robusto.
        
        # text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        #     model_name="gpt-3.5-turbo-0125", # Usa il tokenizzatore del modello target
        #     chunk_size=10000, # Token, non caratteri. Lascia spazio per prompt e output.
        #     chunk_overlap=200   # Token
        # )
        # chunks = text_splitter.split_text(text)
        
        # if len(chunks) > 1:
        #     logger.info(f"Testo diviso in {len(chunks)} chunks. Verrà riassunto solo il primo chunk (implementazione attuale).")
        #     # TODO: Implementare strategia map-reduce o refine per tutti i chunks.
        #     # Per ora, processiamo solo il primo chunk:
        #     return summarize_with_openai(
        #         text_content=chunks[0], 
        #         api_key=api_key, 
        #         prompt_manager=prompt_manager,
        #         langfuse_tracker=langfuse_tracker,
        #         chapter_name=chapter_name,
        #         lesson_name=f"{lesson_name} (chunk 1/{len(chunks)})" if lesson_name else f"chunk 1/{len(chunks)}",
        #         content_type=content_type
        #     )
        # else: # Se c'è un solo chunk (o il testo originale era abbastanza corto)
        #     return summarize_with_openai(
        #         text_content=text, # o chunks[0] che è lo stesso
        #         api_key=api_key, 
        #         prompt_manager=prompt_manager,
        #         langfuse_tracker=langfuse_tracker,
        #         chapter_name=chapter_name,
        #         lesson_name=lesson_name,
        #         content_type=content_type
        #     )
        # ----- FINE LOGICA DI CHUNKING BASE -----
        
        # Per ora, dato che il piano non include ancora il chunking avanzato come priorità immediata,
        # inviamo il testo intero. Sarà compito di un passo successivo implementare correttamente
        # il map-reduce o refine se il testo supera i limiti del singolo contesto del modello.
        # Il `max_chunk_size` attuale è più una salvaguardia per non inviare testi *enormi* senza preavviso.
        return summarize_with_openai(
            text_content=text, 
            api_key=api_key, 
            prompt_manager=prompt_manager,
            langfuse_tracker=langfuse_tracker,
            chapter_name=chapter_name,
            lesson_name=lesson_name,
            content_type=content_type,
            lesson_type_for_prompt=lesson_type_for_prompt # PROPAGATO esplicitamente
            # system_prompt_content va gestito da summarize_with_openai o PromptManager
        )

    else: # Il testo è abbastanza corto
        logger.info(f"Il testo per '{lesson_name}' ('{content_type}') è abbastanza corto ({len(text)} caratteri, stimati {estimated_tokens:.0f} tokens). Invio diretto.")
        return summarize_with_openai(
            text_content=text, 
            api_key=api_key, 
            prompt_manager=prompt_manager,
            langfuse_tracker=langfuse_tracker,
            chapter_name=chapter_name,
            lesson_name=lesson_name,
            content_type=content_type,
            lesson_type_for_prompt=lesson_type_for_prompt # PROPAGATO esplicitamente
            # system_prompt_content va gestito da summarize_with_openai o PromptManager
        )

def write_lesson_summary(
    formatter: MarkdownFormatter, 
    lesson_title: str, 
    vtt_summary: Optional[str], 
    pdf_summary: Optional[str], 
    html_summary: Optional[str], 
    orphan_summary: Optional[str], # AGGIUNTO orphan_summary
    output_file_path: Path,
    user_score_placeholder: bool = False # AGGIUNTO per step 2.3
) -> None:
    """
    Scrive il riassunto di una lezione (che può includere VTT, PDF, HTML e materiale orfano) 
    in un file Markdown.
    Aggiunge un placeholder per user_score nel frontmatter se user_score_placeholder è True.

    Args:
        formatter (MarkdownFormatter): Istanza di MarkdownFormatter.
        lesson_title (str): Titolo della lezione.
        vtt_summary (Optional[str]): Riassunto del contenuto VTT.
        pdf_summary (Optional[str]): Riassunto del contenuto PDF.
        html_summary (Optional[str]): Riassunto del contenuto HTML (arricchito).
        orphan_summary (Optional[str]): Riassunto del contenuto dei file orfani associati.
        output_file_path (Path): Percorso del file Markdown di output.
        user_score_placeholder (bool): Se True, aggiunge "user_score:" al frontmatter.
    """
    logger.debug(f"Preparazione scrittura riassunto per: {lesson_title} in {output_file_path}")

    # Prepara il frontmatter
    frontmatter_data = {
        "title": lesson_title,
        "source_type": "lesson_summary",
        "generated_at": datetime.now().isoformat()
    }
    if user_score_placeholder:
        frontmatter_data["user_score"] = "" # Placeholder per valutazione manuale

    # Utilizza il formatter per creare il frontmatter YAML
    frontmatter_str = formatter.format_frontmatter(frontmatter_data)
    # Assicurati che ci sia una riga vuota dopo il frontmatter se format_frontmatter non la include già come desiderato
    if not frontmatter_str.endswith("\\n\\n"):
        if frontmatter_str.endswith("\\n"):
            frontmatter_str += "\\n"
        else:
            frontmatter_str += "\\n\\n"

    # Utilizza il formatter per creare il contenuto Markdown del corpo della lezione
    lesson_content = formatter.format_lesson_summary(
        lesson_title,
        vtt_summary,
        pdf_summary,
        html_summary,
        orphan_summary # Passa orphan_summary al formatter
    )
    
    full_content = frontmatter_str + lesson_content

    try:
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        logger.info(f"Riassunto della lezione '{lesson_title}' scritto con successo in '{output_file_path}'")
    except IOError as e:
        logger.error(f"Errore di I/O durante la scrittura del file '{output_file_path}': {e}")
        raise # Rilancia l'eccezione per essere gestita dal chiamante se necessario
    except Exception as e:
        logger.error(f"Errore imprevisto durante la scrittura del file '{output_file_path}': {e}")
        raise # Rilancia l'eccezione

def find_related_files(vtt_file_path: Path, chapter_dir: Path) -> Dict[str, List[Path]]:
    """Trova file PDF e HTML correlati a un file VTT in una directory di capitolo.

    Si basa sull'estrazione di un prefisso numerico dal nome del file VTT
    (es. "01" da "01_Welcome.vtt") e cerca file PDF/HTML che iniziano
    con lo stesso prefisso.

    Args:
        vtt_file_path: Percorso del file VTT.
        chapter_dir: Percorso della directory del capitolo.

    Returns:
        Un dizionario con chiavi 'pdf' e 'html'. Ogni chiave mappa a una lista
        di oggetti Path per i file corrispondenti trovati, ordinati.
        Restituisce liste vuote se non vengono trovati file.
    """
    logger.debug(f"Ricerca file correlati per: {vtt_file_path.name} in {chapter_dir}")
    related_files: Dict[str, List[Path]] = {"pdf": [], "html": []}
    vtt_stem = vtt_file_path.stem # Nome file senza estensione

    # Logica per estrarre il prefisso numerico (migliorata)
    prefix_match = re.match(r"^(\d+)[_.-]?.*?", vtt_stem)
    if not prefix_match:
        # Prova a cercare numeri preceduti da testo non numerico, es. "Lecture 01"
        prefix_match = re.match(r"^[^\d]*(\d+)[_.-]?.*?", vtt_stem, re.IGNORECASE)
    
    if not prefix_match:
        logger.warning(f"Impossibile estrarre un prefisso numerico da '{vtt_stem}'. Impossibile cercare file correlati.")
        return related_files

    numeric_prefix = prefix_match.group(1)
    logger.debug(f"Prefisso numerico estratto da VTT '{vtt_stem}': '{numeric_prefix}'")

    for item in chapter_dir.iterdir():
        if item.is_file() and not item.name.startswith('._'):
            item_stem = item.stem
            item_suffix_lower = item.suffix.lower()

            # Logica di corrispondenza per il prefisso
            # Deve iniziare con il prefisso numerico, seguito opzionalmente da SPAZIO, underscore, punto, trattino o dalla fine del nome
            # o semplicemente iniziare con il prefispo se il nome del file è solo il prefispo + estensione (es. "01.pdf")
            if (re.match(rf"^{re.escape(numeric_prefix)}(?:[\s_.-].*|\.\w+$|$)", item_stem, re.IGNORECASE) or # AGGIUNTO \s per lo spazio
                re.match(rf"^{re.escape(numeric_prefix)}$", item_stem, re.IGNORECASE)):

                # Evita corrispondenze parziali (es. "01" in "010_file.pdf") se non è una corrispondenza esatta del prefispo
                # Questo controllo è più specifico per quando il nome del file è più lungo del solo prefispo.
                if len(item_stem) > len(numeric_prefix) and not re.match(rf"^{re.escape(numeric_prefix)}[\s_.-]", item_stem, re.IGNORECASE): # AGGIUNTO \s QUI
                    # Se il nome del file è più lungo del prefispo ma non inizia con prefispo+separatore (inclusi spazi ora),
                    # potrebbe essere una corrispondenza parziale (es. 01 vs 010). La saltiamo.
                    # A meno che item_stem non sia ESATTAMENTE il numeric_prefix (gestito dalla regex sopra).
                    if item_stem.startswith(numeric_prefix) and not item_stem == numeric_prefix:
                         logger.debug(f"Possibile corrispondenza parziale skippata (controllo specifico): prefisso '{numeric_prefix}', file '{item.name}'") # MODIFICATO Log
                         continue # Salta questa potenziale corrispondenza parziale

                if item_suffix_lower == '.pdf':
                    related_files["pdf"].append(item)
                    logger.debug(f"Trovato PDF correlato: {item.name}")
                elif item_suffix_lower == '.html' or item_suffix_lower == '.htm':
                    related_files["html"].append(item)
                    logger.debug(f"Trovato HTML correlato: {item.name}")
    
    related_files["pdf"].sort()
    related_files["html"].sort()
    
    if related_files["pdf"]:
        logger.info(f"Trovati {len(related_files['pdf'])} file PDF correlati per '{vtt_stem}'.")
    if related_files["html"]:
        logger.info(f"Trovati {len(related_files['html'])} file HTML correlati per '{vtt_stem}'.")
        
    return related_files

def process_lesson(
    formatter: MarkdownFormatter, 
    vtt_file: Path, 
    chapter_dir: Path, 
    base_output_dir: Path, 
    api_key: str,
    prompt_manager: PromptManager, # AGGIUNTO prompt_manager
    langfuse_tracker: Optional[LangfuseTracker] = None,
    image_describer: Optional[ImageDescriber] = None, # AGGIUNTO ImageDescriber
    associated_orphan_files: Optional[List[Path]] = None # AGGIUNTO per file orfani
) -> Tuple[Optional[Path], int]: # MODIFICATO TIPO DI RITORNO
    """
    Elabora una singola lezione: estrae testo da VTT, PDF correlati, HTML correlati (e orfani associati),
    genera riassunti e scrive il file Markdown.

    Args:
        formatter (MarkdownFormatter): Istanza di MarkdownFormatter.
        vtt_file (Path): Percorso del file VTT della lezione.
        chapter_dir (Path): Percorso della directory del capitolo.
        base_output_dir (Path): Directory di output base per il corso.
        api_key (str): Chiave API OpenAI.
        prompt_manager (PromptManager): Gestore dei prompt.
        langfuse_tracker (Optional[LangfuseTracker]): Tracker Langfuse.
        image_describer (Optional[ImageDescriber]): Istanza di ImageDescriber.
        associated_orphan_files (Optional[List[Path]]): Lista di file orfani associati a questa lezione.

    Returns:
        Tuple[Optional[Path], int]: Una tupla contenente il percorso del file di riassunto 
                                     generato (o None se fallisce) e il numero totale di token 
                                     utilizzati per la lezione.
    """
    lesson_name = vtt_file.stem
    chapter_name = chapter_dir.name # Per Langfuse

    # Determina il percorso di output previsto per il file di riassunto della lezione
    lesson_output_dir = base_output_dir / chapter_dir.name
    # Sanitize filename from lesson_name (e.g. vtt_file.stem)
    safe_lesson_name = re.sub(r'[^\w\-. ]', '_', lesson_name) # Sostituisce caratteri non validi
    output_file_name = f"{safe_lesson_name}.md"
    # Questo è il percorso che useremo per controllare e, se necessario, per scrivere
    output_file_path = lesson_output_dir / output_file_name

    # Verifica se il file di riassunto esiste già
    if output_file_path.exists():
        logger.info(f"Il file di riassunto '{output_file_path}' per la lezione '{lesson_name}' esiste già. Salto la generazione.")
        return output_file_path, 0 # Restituisce il percorso del file esistente e 0 token usati
    
    total_tokens_lesson = 0
    
    # Tracciamento Langfuse per la lezione - RIMOSSA CHIAMATA A START_LESSON_SPAN
    # if langfuse_tracker:
    #     langfuse_tracker.start_lesson_span(lesson_name, chapter_name)
    
    start_time_lesson = time.time() # Per Langfuse

    # LOGGING INIZIO ELABORAZIONE LEZIONE
    logger.info(f"Inizio elaborazione lezione: {lesson_name} nel capitolo {chapter_name}")

    # Estrazione testo da VTT
    vtt_text_content = ""
    vtt_summary_text: Optional[str] = None
    try:
        logger.info(f"Estrazione testo da VTT: {vtt_file.name}")
        vtt_text_content = extract_text_from_vtt(vtt_file)
        if vtt_text_content.strip():
            logger.info(f"Testo estratto da VTT '{vtt_file.name}', lunghezza: {len(vtt_text_content)} caratteri. Inizio riassunto.")
            summary, usage = summarize_long_text(
                text=vtt_text_content, 
                api_key=api_key, 
                prompt_manager=prompt_manager,
                langfuse_tracker=langfuse_tracker, 
                chapter_name=chapter_name, 
                lesson_name=lesson_name, 
                content_type="vtt"
            )
            vtt_summary_text = summary
            if usage and usage.get("total_tokens") is not None:
                total_tokens_lesson += usage["total_tokens"]
            logger.info(f"Riassunto VTT generato per '{vtt_file.name}'. Lunghezza: {len(vtt_summary_text) if vtt_summary_text else 'N/A'}")
        else:
            logger.info(f"Nessun contenuto testuale estratto da VTT '{vtt_file.name}' o contenuto vuoto.")
            vtt_summary_text = "Nessun contenuto VTT fornito o contenuto vuoto."
    except Exception as e:
        logger.error(f"Errore durante l'elaborazione del file VTT '{vtt_file.name}': {e}")
        vtt_summary_text = f"Errore durante l'elaborazione del file VTT: {e}"

    # Gestione dei file correlati (PDF, HTML) come da implementazione precedente
    related_files = find_related_files(vtt_file, chapter_dir)
    pdf_files = related_files.get('pdf', [])
    html_files = related_files.get('html', [])

    # Estrazione e riassunto testo da PDF correlati
    pdf_summary_text: Optional[str] = None
    if pdf_files:
        all_pdf_text = ""
        for pdf_file in pdf_files:
            try:
                logger.info(f"Estrazione testo da PDF correlato: {pdf_file.name}")
                pdf_text = extract_text_from_pdf(pdf_file)
                if pdf_text.strip():
                    all_pdf_text += pdf_text + "\n\n" # Aggiungi separatore
                    logger.info(f"Testo estratto da PDF '{pdf_file.name}', lunghezza: {len(pdf_text)} caratteri.")
                else:
                    logger.info(f"Nessun contenuto testuale estratto da PDF '{pdf_file.name}' o contenuto vuoto.")
            except Exception as e:
                logger.error(f"Errore nell'estrazione del testo dal PDF '{pdf_file.name}': {e}")
                all_pdf_text += f"Errore durante l'elaborazione del file PDF {pdf_file.name}: {e}\n\n"
        
        if all_pdf_text.strip():
            logger.info(f"Testo PDF aggregato per la lezione '{lesson_name}'. Inizio riassunto.")
            summary, usage = summarize_long_text(
                text=all_pdf_text, 
                api_key=api_key, 
                prompt_manager=prompt_manager,
                langfuse_tracker=langfuse_tracker, 
                chapter_name=chapter_name, 
                lesson_name=lesson_name, 
                content_type="pdf"
            )
            pdf_summary_text = summary
            if usage and usage.get("total_tokens") is not None:
                total_tokens_lesson += usage["total_tokens"]
            logger.info(f"Riassunto PDF generato per '{lesson_name}'. Lunghezza: {len(pdf_summary_text) if pdf_summary_text else 'N/A'}")
        else:
            logger.info(f"Nessun contenuto testuale aggregato dai PDF per la lezione '{lesson_name}'.")
            pdf_summary_text = "Nessun contenuto PDF fornito o contenuto vuoto."

    # Estrazione e riassunto testo da HTML correlati
    html_summary_text: Optional[str] = None
    if html_files:
        all_html_text_enriched = ""
        for html_file in html_files:
            try:
                logger.info(f"Estrazione testo e immagini da HTML correlato: {html_file.name}")
                text_content, image_urls = extract_text_and_images_from_html(html_file)
                enriched_html_content = text_content
                if image_describer and image_urls:
                    logger.info(f"Trovate {len(image_urls)} immagini in {html_file.name}. Inizio descrizione.")
                    for img_url in image_urls:
                        # Assumendo che image_describer.describe_image_url gestisca URL relativi/assoluti
                        # e che la base per i relativi sia la directory del file HTML
                        full_image_path = html_file.parent / img_url if not img_url.startswith(('http', '/')) else img_url
                        desc_text, 비용 = image_describer.describe_image_url(str(full_image_path), lesson_name, chapter_name, html_file.name)
                        if desc_text:
                            enriched_html_content += f"\n\nContenuto immagine ({img_url}): {desc_text}"
                        if 비용 and 비용.get("total_tokens") is not None:
                             total_tokens_lesson += 비용["total_tokens"]
                
                if enriched_html_content.strip():
                    all_html_text_enriched += enriched_html_content + "\n\n"
                    logger.info(f"Testo HTML arricchito estratto da '{html_file.name}', lunghezza: {len(enriched_html_content)} caratteri.")
                else:
                    logger.info(f"Nessun contenuto testuale/immagine estratto da HTML '{html_file.name}' o contenuto vuoto.")

            except Exception as e:
                logger.error(f"Errore nell'elaborazione del file HTML '{html_file.name}': {e}")
                all_html_text_enriched += f"Errore durante l'elaborazione del file HTML {html_file.name}: {e}\n\n"
        
        if all_html_text_enriched.strip():
            logger.info(f"Testo HTML arricchito aggregato per la lezione '{lesson_name}'. Inizio riassunto.")
            summary, usage = summarize_long_text(
                text=all_html_text_enriched, 
                api_key=api_key, 
                prompt_manager=prompt_manager,
                langfuse_tracker=langfuse_tracker, 
                chapter_name=chapter_name, 
                lesson_name=lesson_name, 
                content_type="html"
            )
            html_summary_text = summary
            if usage and usage.get("total_tokens") is not None:
                total_tokens_lesson += usage["total_tokens"]
            logger.info(f"Riassunto HTML generato per '{lesson_name}'. Lunghezza: {len(html_summary_text) if html_summary_text else 'N/A'}")
        else:
            logger.info(f"Nessun contenuto HTML arricchito aggregato per la lezione '{lesson_name}'.")
            html_summary_text = "Nessun contenuto HTML fornito o contenuto vuoto."

    # NUOVA SEZIONE: Elaborazione file orfani associati
    orphan_summary_text: Optional[str] = None
    if associated_orphan_files:
        logger.info(f"Inizio elaborazione di {len(associated_orphan_files)} file orfani associati a {lesson_name}.")
        all_orphan_content_text = ""
        for orphan_file in associated_orphan_files:
            logger.info(f"Elaborazione file orfano: {orphan_file.name}")
            try:
                if orphan_file.suffix.lower() == '.pdf':
                    text = extract_text_from_pdf(orphan_file)
                    logger.info(f"Testo estratto da PDF orfano '{orphan_file.name}', lunghezza: {len(text)}.")
                    all_orphan_content_text += f"Contenuto da {orphan_file.name}:\n{text}\n\n"
                elif orphan_file.suffix.lower() == '.html':
                    # CORREZIONE: Leggere il contenuto del file HTML prima di passarlo
                    with open(orphan_file, 'r', encoding='utf-8') as f_html_orphan:
                        html_content_str = f_html_orphan.read()
                    text, image_urls = extract_text_and_images_from_html(html_content_str)
                    enriched_content = text
                    if image_describer and image_urls:
                        logger.info(f"Trovate {len(image_urls)} immagini in HTML orfano {orphan_file.name}. Inizio descrizione.")
                        for img_url in image_urls:
                            full_image_path = orphan_file.parent / img_url if not img_url.startswith(('http', '/')) else img_url
                            desc, usage_img = image_describer.describe_image_url(str(full_image_path), lesson_name, chapter_name, orphan_file.name)
                            if desc:
                                enriched_content += f"\n\nContenuto immagine ({img_url}): {desc}"
                            if usage_img and usage_img.get("total_tokens") is not None:
                                total_tokens_lesson += usage_img["total_tokens"]
                    logger.info(f"Testo HTML arricchito da HTML orfano '{orphan_file.name}', lunghezza: {len(enriched_content)}.")
                    all_orphan_content_text += f"Contenuto da {orphan_file.name}:\n{enriched_content}\n\n"
            except Exception as e:
                logger.error(f"Errore durante l'elaborazione del file orfano '{orphan_file.name}': {e}")
                all_orphan_content_text += f"Errore durante l'elaborazione del file orfano {orphan_file.name}: {e}\n\n"
        
        if all_orphan_content_text.strip():
            logger.info(f"Testo aggregato da file orfani per '{lesson_name}' (lunghezza: {len(all_orphan_content_text)}). Inizio riassunto del materiale aggiuntivo.")
            summary, usage = summarize_long_text(
                text=all_orphan_content_text,
                api_key=api_key,
                prompt_manager=prompt_manager, # Assumendo che esista un prompt adatto o si usi quello di default
                langfuse_tracker=langfuse_tracker,
                chapter_name=chapter_name,
                lesson_name=lesson_name,
                content_type="orphan_material" # Nuovo tipo di contenuto per tracciamento
            )
            orphan_summary_text = summary
            if usage and usage.get("total_tokens") is not None:
                total_tokens_lesson += usage["total_tokens"]
            logger.info(f"Riassunto del materiale orfano generato per '{lesson_name}'. Lunghezza: {len(orphan_summary_text) if orphan_summary_text else 'N/A'}")
        else:
            logger.info(f"Nessun contenuto testuale aggregato dai file orfani per '{lesson_name}'.")
            # Non impostare orphan_summary_text a un messaggio di errore qui, lascialo None se non c'è contenuto.

    # Scrittura del riassunto della lezione
    # Determina il percorso di output del file di riassunto della lezione
    # lesson_output_dir = base_output_dir / chapter_dir.name # GIÀ CALCOLATO SOPRA
    # lesson_output_dir.mkdir(parents=True, exist_ok=True) # LA CREAZIONE DELLA DIR È GESTITA DA write_lesson_summary
    # Sanitize filename from lesson_name (e.g. vtt_file.stem)
    # safe_lesson_name = re.sub(r'[^\w\-. ]', '_', lesson_name) # GIÀ CALCOLATO SOPRA
    # output_file_name = f"{safe_lesson_name}.md" # GIÀ CALCOLATO SOPRA
    # output_file_path = lesson_output_dir / output_file_name # GIÀ CALCOLATO SOPRA E USATO PER IL CONTROLLO

    try:
        logger.info(f"Scrittura del riassunto della lezione su: {output_file_path}")
        write_lesson_summary(
            formatter=formatter,
            lesson_title=lesson_name, 
            vtt_summary=vtt_summary_text, 
            pdf_summary=pdf_summary_text, 
            html_summary=html_summary_text,
            orphan_summary=orphan_summary_text, # AGGIUNTO orphan_summary
            output_file_path=output_file_path,
            user_score_placeholder=True # Aggiunge placeholder per user_score come da step 2.3
        )
        logger.info(f"Riassunto della lezione '{lesson_name}' scritto con successo.")
    except Exception as e:
        logger.error(f"Errore durante la scrittura del riassunto della lezione '{lesson_name}' su '{output_file_path}': {e}")
        output_file_path = None # Indica fallimento

    # Fine tracciamento Langfuse per la lezione - RIMOSSA CHIAMATA A END_LESSON_SPAN
    # Le informazioni sulla lezione sono già tracciate in ogni track_llm_call
    # e le metriche aggregate per la lezione possono essere calcolate se necessario
    # al di fuori di uno span specifico di lezione, o aggiunte allo span del capitolo.
    # if langfuse_tracker:
    #     lesson_processing_time = time.time() - start_time_lesson
    #     # Qui potresti voler raccogliere metadati più specifici sulla lezione
    #     metadata = {
    #         "vtt_processed": bool(vtt_text_content.strip()),
    #         "pdf_processed": bool(pdf_files),
    #         "html_processed": bool(html_files),
    #         "orphans_processed": len(associated_orphan_files) if associated_orphan_files else 0,
    #         "vtt_summary_length": len(vtt_summary_text) if vtt_summary_text else 0,
    #         "pdf_summary_length": len(pdf_summary_text) if pdf_summary_text else 0,
    #         "html_summary_length": len(html_summary_text) if html_summary_text else 0,
    #         "orphan_summary_length": len(orphan_summary_text) if orphan_summary_text else 0,
    #     }
    #     langfuse_tracker.end_lesson_span(
    #         output={"summary_file": str(output_file_path) if output_file_path else "Error"},
    #         metadata=metadata,
    #         total_tokens_used=total_tokens_lesson,
    #         processing_time_seconds=lesson_processing_time,
    #         status="SUCCESS" if output_file_path else "ERROR"
    #     )

    logger.info(f"Completata elaborazione lezione: {lesson_name}. Token usati: {total_tokens_lesson}")
    return output_file_path, total_tokens_lesson

def process_chapter(
    formatter: MarkdownFormatter, 
    chapter_dir: Path, 
    base_output_dir: Path, 
    api_key: str,
    prompt_manager: PromptManager, # AGGIUNTO prompt_manager
    langfuse_tracker: Optional[LangfuseTracker] = None
) -> Tuple[List[Optional[Path]], int]: # MODIFICATO TIPO DI RITORNO
    """
    Processa tutti i file VTT e i relativi file PDF/HTML (inclusi gli orfani associati) in una directory di capitolo.
    Genera riassunti per ogni lezione e li salva in file Markdown.

    Args:
        formatter (MarkdownFormatter): Istanza di MarkdownFormatter.
        chapter_dir (Path): Percorso della directory del capitolo.
        base_output_dir (Path): Directory di output base per il corso.
        api_key (str): Chiave API OpenAI.
        prompt_manager (PromptManager): Gestore dei prompt.
        langfuse_tracker (Optional[LangfuseTracker]): Tracker Langfuse.

    Returns:
        Tuple[List[Optional[Path]], int]: Una tupla contenente la lista dei percorsi dei file 
                                           Markdown dei riassunti delle lezioni generati e il 
                                           numero totale di token utilizzati per il capitolo.
    """
    chapter_name = chapter_dir.name
    chapter_output_dir = base_output_dir / chapter_name
    try:
        chapter_output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Directory di output del capitolo assicurata: {chapter_output_dir}")
    except OSError as e:
        logger.error(f"Errore durante la creazione della directory '{chapter_output_dir}': {e}")
        # Considerare se propagare l'errore o gestire diversamente
        return [], 0 

    logger.info(f"Inizio elaborazione capitolo: {chapter_name}")
    start_time_chapter = time.time() # Per Langfuse

    vtt_files = list_vtt_files(chapter_dir)
    if not vtt_files:
        logger.warning(f"Nessun file VTT trovato nel capitolo '{chapter_name}'. Salto elaborazione lezioni.")
        # Assicurati che la directory del capitolo esista comunque per coerenza, se necessario
        # (chapter_output_dir.mkdir(parents=True, exist_ok=True) è già sopra)
        if langfuse_tracker:
            chapter_processing_time = time.time() - start_time_chapter
            # Potresti voler registrare uno span vuoto o con zero metriche se ha senso per il tracciamento
            # langfuse_tracker.log_chapter_span_metrics(chapter_name, 0, 0, chapter_processing_time)
        return [], 0
    
    # Identifica file orfani e mappa alle lezioni VTT
    orphan_files = identify_orphan_files(chapter_dir, vtt_files)
    orphans_map = map_orphans_to_lessons(vtt_files, orphan_files)

    lesson_summary_files: List[Optional[Path]] = []
    total_tokens_chapter = 0

    # Inizializza ImageDescriber se necessario (potrebbe essere fatto una volta per corso)
    image_describer = ImageDescriber(api_key=api_key, langfuse_tracker=langfuse_tracker) 

    for vtt_file in vtt_files:
        logger.info(f"Inizio elaborazione lezione VTT: {vtt_file.name}")
        # Recupera i file orfani associati a questo VTT
        associated_orphan_files = orphans_map.get(vtt_file, [])
        if associated_orphan_files:
            logger.info(f"File orfani associati a {vtt_file.name}: {[o.name for o in associated_orphan_files]}")
        
        summary_file_path, tokens_lesson = process_lesson(
            formatter=formatter,
            vtt_file=vtt_file,
            chapter_dir=chapter_dir, # Passato per coerenza, ma find_related_files ora è più mirato
            base_output_dir=base_output_dir,
            api_key=api_key,
            prompt_manager=prompt_manager,
            langfuse_tracker=langfuse_tracker,
            image_describer=image_describer, # Passa ImageDescriber
            associated_orphan_files=associated_orphan_files # Passa i file orfani associati
        )
        if summary_file_path:
            lesson_summary_files.append(summary_file_path)
        total_tokens_chapter += tokens_lesson

    # Log metriche capitolo per Langfuse
    if langfuse_tracker:
        # Calcola il tempo di elaborazione del capitolo
        chapter_processing_time = time.time() - start_time_chapter
        chapter_metrics = {
            "total_lessons_processed": len(vtt_files),
            "total_tokens_used": total_tokens_chapter,
            "processing_time_seconds": chapter_processing_time,
            # chapter_name è già parte dello span, non serve ripeterlo qui
            # se non specificamente richiesto dalla logica di end_chapter_span.
            # Dalla definizione di end_chapter_span, non sembra necessario.
        }
        langfuse_tracker.end_chapter_span(output=chapter_metrics, status="OK")

    logger.info(f"Completata elaborazione del capitolo: {chapter_name}. File di riassunto generati: {len(lesson_summary_files)}")
    return lesson_summary_files, total_tokens_chapter

def create_chapter_summary(formatter: MarkdownFormatter, chapter_dir: Path, lesson_summary_files: List[Optional[Path]], base_output_dir: Path) -> Optional[Path]: # Modificata firma
    """
    Crea un file Markdown di riepilogo per un capitolo, incorporando i contenuti delle lezioni.

    Args:
        formatter (MarkdownFormatter): Istanza del formattatore Markdown.
        chapter_dir (Path): Percorso della directory del capitolo.
        lesson_summary_files (List[Optional[Path]]): Lista dei percorsi ai file di riassunto delle lezioni.
        base_output_dir (Path): Directory di output base per il corso.

    Returns:
        Optional[Path]: Percorso del file di riepilogo del capitolo creato, o None se fallisce.
    """
    chapter_name = chapter_dir.name
    # Rimuove prefissi numerici comuni come '01-', '01_', '01.', '01 '
    # per un titolo di capitolo più pulito
    clean_chapter_name = re.sub(r"^\d+[-_\.\s]*", "", chapter_name)
    chapter_title = f"Capitolo: {clean_chapter_name}"
    
    # Sostituisce gli spazi con underscore e normalizza il nome per il file
    safe_chapter_name = chapter_name.replace(" ", "_").lower()
    # Rimuove caratteri non alfanumerici eccetto underscore
    safe_chapter_name = re.sub(r'[^a-z0-9_]', '', safe_chapter_name)
    chapter_summary_filename = f"CAPITOLO_{safe_chapter_name}.md"
    
    # Il file di riepilogo del capitolo va nella directory del capitolo specifica dentro l'output base
    chapter_output_dir = base_output_dir / chapter_dir.name # Mantiene la struttura originale
    chapter_output_dir.mkdir(parents=True, exist_ok=True)
    chapter_summary_path = chapter_output_dir / chapter_summary_filename

    logger.info(f"Creazione del riassunto del capitolo: {chapter_summary_path}")

    content_parts = []
    content_parts.append(formatter.format_header(chapter_title, level=1))
    content_parts.append(formatter.new_line())

    # Creazione di un piccolo indice per le lezioni
    if lesson_summary_files:
        content_parts.append(formatter.format_header("Indice delle Lezioni", level=2))
        content_parts.append(formatter.new_line()) # Assicura una nuova riga dopo l'header dell'indice

        for i, lesson_file_path in enumerate(lesson_summary_files):
            if lesson_file_path:
                lesson_title = lesson_file_path.stem # Nome del file senza estensione
                # Pulisce il titolo della lezione da prefissi numerici e lo usa per l'ancora
                clean_lesson_title_for_anchor = re.sub(r"^\d+[-_\.\s]*", "", lesson_title).replace(" ", "-").lower()
                clean_lesson_title_for_display = re.sub(r"^\d+[-_\.\s]*", "", lesson_title)
                # Sostituisce "SUMMARY_" se presente nel nome del file per il display
                clean_lesson_title_for_display = clean_lesson_title_for_display.replace("SUMMARY_", "").replace("_", " ")

                link_text = formatter.format_link(f"Lezione: {clean_lesson_title_for_display}", f"#{clean_lesson_title_for_anchor}")
                content_parts.append(formatter.format_list_item(link_text, ordered=False))
                content_parts.append(formatter.new_line()) # Assicura che ogni elemento della lista sia su una nuova riga
        
        # La riga seguente non è più necessaria perché ogni elemento della lista ora ha il suo new_line()
        # content_parts.append(formatter.new_line()) 
        content_parts.append(formatter.horizontal_rule())
        content_parts.append(formatter.new_line())

    # Incorpora il contenuto di ogni lezione
    for lesson_file_path in lesson_summary_files:
        if lesson_file_path and lesson_file_path.exists():
            try:
                with open(lesson_file_path, "r", encoding="utf-8") as f_lesson:
                    lesson_content = f_lesson.read()
                
                # Estrae il titolo dal frontmatter del file lezione per usarlo come H2
                # e rimuove il frontmatter dal contenuto da includere
                match = re.search(r"^---\s*$\n(.*?)^---\s*$\n(.*?)$", lesson_content, re.MULTILINE | re.DOTALL)
                lesson_title_from_frontmatter = chapter_name # Fallback se non trova il titolo
                actual_lesson_content_to_embed = lesson_content # Fallback

                if match:
                    frontmatter_str = match.group(1)
                    actual_lesson_content_to_embed = match.group(2).strip()
                    # Cerca il titolo nel frontmatter
                    title_match = re.search(r"^title:\s*(.+)$", frontmatter_str, re.MULTILINE)
                    if title_match:
                        lesson_title_from_frontmatter = title_match.group(1).strip()
                else:
                    # Se non c'è frontmatter, prova a usare il nome del file come titolo H2
                    # e includi tutto il contenuto
                    lesson_title_from_frontmatter = lesson_file_path.stem.replace("SUMMARY_","").replace("_", " ")
                    lesson_title_from_frontmatter = re.sub(r"^\d+[-_\.\s]*", "", lesson_title_from_frontmatter)
                
                # Crea un'ancora per il link dell'indice
                lesson_anchor = re.sub(r"^\d+[-_\.\s]*", "", lesson_title_from_frontmatter).replace(" ", "-").lower()

                content_parts.append(f'<a id="{lesson_anchor}"></a>') # Aggiunge l'ancora HTML
                content_parts.append(formatter.new_line())

                # Aggiungiamo l'header H2 per la lezione, preso dal frontmatter o dal nome del file
                content_parts.append(formatter.format_header(lesson_title_from_frontmatter, level=2))
                content_parts.append(formatter.new_line())

                # E poi il contenuto effettivo della lezione (post-frontmatter),
                # che dovrebbe già contenere le sue intestazioni di sezione (es. "## Riassunto Video (VTT)")
                # e il corpo del riassunto.
                content_parts.append(actual_lesson_content_to_embed)
                
                # Aggiunge una nuova riga prima della linea orizzontale per separazione
                content_parts.append(formatter.new_line())
                content_parts.append(formatter.horizontal_rule())
                content_parts.append(formatter.new_line())

            except IOError as e:
                logger.warning(f"Impossibile leggere il file di riassunto della lezione {lesson_file_path}: {e}")
        elif lesson_file_path:
            logger.warning(f"File di riassunto della lezione non trovato: {lesson_file_path}")

    final_content = "".join(content_parts)

    try:
        with open(chapter_summary_path, "w", encoding="utf-8") as f:
            f.write(final_content)
        logger.info(f"Riepilogo del capitolo '{chapter_name}' scritto con successo in {chapter_summary_path}")
        return chapter_summary_path
    except IOError as e:
        logger.error(f"Errore durante la scrittura del file di riepilogo del capitolo per '{chapter_name}': {e}")
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
    Funzione principale per orchestrare il processo di generazione dei riassunti.
    """
    configure_logging()
    load_dotenv() # Carica variabili da .env se presente

    args = parse_arguments()
    
    # Inizializza LangfuseTracker se le variabili d'ambiente sono impostate
    langfuse_tracker: Optional[LangfuseTracker] = None
    try:
        if os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY"):
            langfuse_tracker = LangfuseTracker()
            logger.info("LangfuseTracker inizializzato.")
            # Creiamo una sessione per questa esecuzione
            # langfuse_tracker.create_session(name="resume_generator_run") # O un nome più specifico
        else:
            logger.info("Variabili d'ambiente Langfuse non trovate. LangfuseTracker non attivo.")
    except Exception as e:
        logger.error(f"Errore durante l'inizializzazione di LangfuseTracker: {e}. Continuerà senza tracciamento Langfuse.")
        langfuse_tracker = None # Assicura che sia None in caso di errore

    # Inizializza APIKeyManager e ottieni la chiave
    # La gestione della chiave OpenAI è stata spostata qui per essere centrale
    api_key_manager = APIKeyManager()
    openai_api_key = api_key_manager.get_key()

    if not openai_api_key:
        logger.error("Chiave API OpenAI non trovata. Impossibile procedere con i riassunti.")
        # Qui potremmo decidere di uscire o continuare senza API, a seconda dei requisiti.
        # Per ora, usciamo se la chiave non è disponibile, poiché è essenziale.
        if langfuse_tracker: langfuse_tracker.shutdown() # Assicura lo shutdown se usciamo presto
        return

    # Inizializza PromptManager
    prompt_manager = PromptManager() # ISTANZIATO PROMPT_MANAGER
    logger.info("PromptManager inizializzato.")

    try:
        output_dir = setup_output_directory(args.course_dir, args.output_dir)
        course_name = Path(args.course_dir).name
        start_time_course = time.time() # Per il tempo totale di elaborazione del corso
        course_processing_time_s = 0.0 # INIZIALIZZAZIONE DI DEFAULT
        total_tokens_course = 0 # Per i token totali del corso
        lessons_processed_course = 0 # Contatore lezioni processate per il corso
        lessons_failed_course = 0 # Contatore lezioni fallite per il corso
        
        # Inizializza MarkdownFormatter
        formatter = MarkdownFormatter()
        logger.info("MarkdownFormatter inizializzato.")

        # Inizializza una traccia principale per l'intero corso con Langfuse
        if langfuse_tracker:
            # MODIFICATO: Chiamata a start_session invece di get_trace_or_span
            # AGGIUNTO: prompt_info basilare per la sessione
            session_prompt_info = {"default_prompt_type": "practical_theoretical_face_to_face", "prompt_manager_version": "1.0"} # Esempio
            langfuse_tracker.start_session(
                course_name=course_name, 
                session_metadata={"course_directory": args.course_dir, "output_directory": str(output_dir)},
                prompt_info=session_prompt_info 
            )
            logger.info(f"Sessione Langfuse avviata per il corso: {course_name}")

        chapter_dirs = list_chapter_directories(args.course_dir)
        if not chapter_dirs:
            logger.warning(f"Nessun capitolo trovato in {args.course_dir}. L'indice principale potrebbe essere vuoto.")
            # Potremmo comunque voler creare un index.md vuoto o con un messaggio.
            # create_main_index(formatter, course_name, [], output_dir) # Crea un indice vuoto
            # return # O esce se non ci sono capitoli

        all_chapter_summary_files: List[Optional[Path]] = [] # Per l'indice principale

        for chapter_dir in chapter_dirs:
            chapter_name = chapter_dir.name # Ottieni il nome del capitolo
            logger.info(f"Creazione directory di output per il capitolo: {chapter_name} in {output_dir}")
            # Assicura che la sottodirectory per il capitolo esista in output_dir
            chapter_output_dir = output_dir / chapter_name
            try:
                chapter_output_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Directory di output del capitolo '{chapter_output_dir}' assicurata.")
            except OSError as e:
                logger.error(f"Errore durante la creazione della directory di output per il capitolo '{chapter_name}': {e}. Salto capitolo.")
                continue # Salta al prossimo capitolo

            # Elabora le lezioni del capitolo
            lesson_summary_paths, tokens_chapter = process_chapter( # MODIFICATO: cattura tokens_chapter
                formatter, 
                chapter_dir, 
                output_dir, # Passa la directory di output base, process_chapter gestirà la sottocartella del capitolo
                openai_api_key,
                prompt_manager, # PASSATO prompt_manager
                langfuse_tracker=langfuse_tracker
            )
            total_tokens_course += tokens_chapter # Accumula token del capitolo
            
            # Contare lezioni processate/fallite basandosi sui path restituiti
            # Un path non None indica un successo (anche se il riassunto potrebbe essere un messaggio di errore)
            # Per una metrica più precisa di "fallimento elaborazione lezione", process_lesson dovrebbe indicarlo.
            # Per ora, contiamo i file generati come "processati".
            current_chapter_lessons_processed = sum(1 for p in lesson_summary_paths if p is not None)
            lessons_processed_course += current_chapter_lessons_processed
            # Questa è una stima, potremmo voler tracciare i fallimenti più esplicitamente da process_lesson
            # lessons_failed_course += (len(vtt_files) - current_chapter_lessons_processed) # se vtt_files è disponibile qui

            # Creazione del riassunto del capitolo
            # Filtra i None dalla lista prima di passarla
            valid_lesson_summary_paths = [path for path in lesson_summary_paths if path is not None]
            if valid_lesson_summary_paths: # Solo se ci sono riassunti di lezioni validi
                chapter_summary_file = create_chapter_summary(
                    formatter, 
                    chapter_dir, 
                    valid_lesson_summary_paths, 
                    output_dir # Directory base dove verrà creato _CHAPTER_SUMMARY_<NOME_CAPITOLO>.md
                )
                if chapter_summary_file:
                    all_chapter_summary_files.append(chapter_summary_file)
                    logger.info(f"Riassunto del capitolo '{chapter_name}' creato: {chapter_summary_file}")
                else:
                    logger.error(f"Fallimento nella creazione del riassunto per il capitolo '{chapter_name}'.")
                    all_chapter_summary_files.append(None) # Aggiungi None per mantenere la corrispondenza se necessario, o gestisci diversamente
            else:
                logger.warning(f"Nessun riassunto di lezione valido generato per il capitolo '{chapter_name}'. Salto la creazione del riassunto del capitolo.")
                # Potremmo voler creare un file di riassunto del capitolo vuoto o con un messaggio.
                # Per ora, se non ci sono lezioni, non creiamo il file di riassunto del capitolo.
                all_chapter_summary_files.append(None)


        # Creazione dell'indice principale
        # Filtra i None anche qui
        valid_chapter_summary_files = [path for path in all_chapter_summary_files if path is not None]
        if valid_chapter_summary_files:
            main_index_file = create_main_index(formatter, course_name, valid_chapter_summary_files, output_dir)
            if main_index_file:
                logger.info(f"Indice principale del corso creato: {main_index_file}")
            else:
                logger.error("Fallimento nella creazione dell'indice principale del corso.")
        else:
            logger.warning("Nessun riassunto di capitolo valido disponibile per creare l'indice principale.")
            # Crea un indice vuoto se non ci sono capitoli o riassunti di capitoli
            empty_index_file = create_main_index(formatter, course_name, [], output_dir)
            if empty_index_file:
                logger.info(f"Creato un indice principale vuoto o con intestazione: {empty_index_file}")
            else:
                logger.error("Fallimento anche nella creazione di un indice principale vuoto.")

        course_processing_time_s = time.time() - start_time_course # Calcola tempo totale
        logger.info(f"Elaborazione del corso completata in {course_processing_time_s:.2f} secondi. Token totali usati: {total_tokens_course}.")
        # if course_trace: course_trace.update(status_message="Course processing completed successfully.") # RIMOSSO, gestito da end_session o metriche

    except ValueError as e: # Ad esempio, da setup_output_directory o list_chapter_directories
        logger.error(f"Errore di configurazione o di I/O: {e}")
        # if 'course_trace' in locals() and course_trace: course_trace.update(level='ERROR', status_message=f"Configuration or I/O error: {e}") # RIMOSSO
    except Exception as e:
        logger.error(f"Errore imprevisto durante l'elaborazione del corso: {e}", exc_info=True) # Aggiunto exc_info per traceback
        # if 'course_trace' in locals() and course_trace: course_trace.update(level='ERROR', status_message=f"Unexpected error: {e}") # RIMOSSO
    finally:
        if langfuse_tracker:
            logger.info("Spegnimento di LangfuseTracker...")
            # Traccia le metriche finali del corso
            # Nota: lessons_failed_course è una stima. Potrebbe essere migliorata.
            # estimated_cost non viene calcolato qui come da discussione
            langfuse_tracker.track_processing_metrics(
                lessons_processed=lessons_processed_course,
                lessons_failed=lessons_failed_course, # Questo valore andrebbe calcolato più precisamente
                total_tokens_used=total_tokens_course,
                total_processing_time_s=course_processing_time_s 
            )
            
            # MODIFICATO: Chiamata a end_session() e flush()
            langfuse_tracker.end_session()
            langfuse_tracker.flush()
            logger.info("LangfuseTracker: sessione terminata e dati inviati.")

if __name__ == '__main__':
    main()