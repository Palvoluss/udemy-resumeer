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
from api_key_manager import APIKeyManager # IMPORT AGGIUNTO
# from dotenv import load_dotenv
# import hashlib
import openai # type: ignore
import re # Necessario per find_related_pdf
from dotenv import load_dotenv # IMPORT AGGIUNTO

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

    if system_prompt_content is None:
        system_prompt_content = (
            "Sei un assistente AI specializzato nel creare riassunti estremamente precisi, dettagliati e ben strutturati. "
            "Il tuo obiettivo è mantenere tutti i concetti chiave, le informazioni cruciali e le sfumature del testo originale. "
            "Quando appropriato, utilizza rappresentazioni schematiche come liste puntate, numerate o tabelle per organizzare le informazioni in modo chiaro e logico. "
            "Non abbreviare eccessivamente; la completezza e l'accuratezza sono prioritarie rispetto alla brevità. "
            "Assicurati che il riassunto sia scritto in italiano fluente e grammaticalmente corretto. "
            "Evita interpretazioni personali o l'aggiunta di informazioni non presenti nel testo originale. "
            "Il riassunto deve essere autosufficiente e comprensibile senza fare riferimento al testo sorgente."
        )
        logger.debug("Utilizzo del prompt di sistema di default per il riassunto.")
    else:
        logger.debug(f"Utilizzo del prompt di sistema personalizzato: \"{system_prompt_content[:100]}...\"")

    try:
        client = openai.OpenAI(api_key=api_key)
        logger.info("Chiamata all'API Chat Completions di OpenAI con il modello gpt-3.5-turbo.")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt_content},
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
    for i, chunk in enumerate(chunks):
        logger.info(f"Riassumo chunk {i+1}/{len(chunks)}...")
        try:
            chunk_summary = summarize_with_openai(chunk, api_key, system_prompt_content="You are an assistant that creates precise and detailed summaries of text chunks. Focus on extracting key information and concepts.")
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
    meta_summary_prompt = (
        "You are a highly skilled summarization assistant. "
        "The following text consists of multiple summaries of consecutive text chunks from a single document. "
        "Your task is to synthesize these individual summaries into a single, coherent, and comprehensive summary of the entire original document. "
        "Ensure that all key information and concepts from the individual summaries are retained and integrated smoothly. "
        "The final summary should be detailed and precise. Use schematic representations (bullet points, tables) where appropriate to organize information clearly. "
        "Focus on accuracy and completeness rather than brevity. The user is expecting a detailed summary of the original content, not a summary of summaries."
        "Do not explicitly mention that you are summarizing summaries or chunks."
    )
    final_summary = summarize_with_openai(combined_summaries_text, api_key, system_prompt_content=meta_summary_prompt)
    logger.info("Meta-riassunto completato.")
    return final_summary

def write_lesson_summary(lesson_title: str, summary_text: str, output_file_path: Path) -> None: # Ripristinato None
    """
    Scrive il riassunto di una lezione in un file Markdown.
    # Ripristino docstring e logica interna se alterata
    Il file creato (o sovrascritto) avrà il seguente contenuto:
    ## [lesson_title]

    [summary_text]

    Args:
        lesson_title (str): Il titolo della lezione, sanitizzato per l'uso come nome file se necessario.
        summary_text (str): Il testo del riassunto della lezione.
        output_file_path (Path): Il percorso completo del file Markdown di output.
                                 La directory genitore verrà creata se non esiste.
                                 
    Raises:
        IOError: Se si verifica un errore durante la scrittura del file.
        Exception: Per altri errori imprevisti.
    """
    logger.debug(f"Tentativo di scrivere il riassunto della lezione '{lesson_title}' su '{output_file_path}'.")

    try:
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Assicurata la directory genitore: {output_file_path.parent}")

        cleaned_lesson_title = lesson_title.replace("[", "").replace("]", "")

        markdown_content = f"## {cleaned_lesson_title}\n\n{summary_text.strip()}\n"
        
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.info(f"Riassunto della lezione '{cleaned_lesson_title}' scritto con successo su '{output_file_path}'.")

    except IOError as e:
        logger.error(f"Errore di I/O durante la scrittura del file '{output_file_path}': {e}")
        raise
    except Exception as e:
        logger.error(f"Errore imprevisto durante la scrittura del riassunto della lezione su '{output_file_path}': {e}")
        raise

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

def process_lesson(vtt_file: Path, chapter_dir: Path, base_output_dir: Path, api_key: str) -> Optional[Path]:
    """
    Processa una singola lezione (file VTT) e i suoi PDF correlati.

    Estrae il testo dal VTT e dai PDF, li riassume e scrive i riassunti
    in un unico file Markdown nella directory di output appropriata.

    Args:
        vtt_file (Path): Percorso del file VTT della lezione.
        chapter_dir (Path): Percorso della directory del capitolo che contiene la lezione.
        base_output_dir (Path): Directory di output principale per tutti i riassunti del corso.
        api_key (str): Chiave API di OpenAI.

    Returns:
        Optional[Path]: Il percorso del file Markdown generato se il processo ha successo,
                        None altrimenti.
    """
    logger.info(f"Inizio elaborazione lezione: {vtt_file.name} nel capitolo {chapter_dir.name}")
    try:
        # 1. Estrarre testo dal VTT
        vtt_text = extract_text_from_vtt(vtt_file)
        if not vtt_text.strip():
            logger.warning(f"Testo vuoto estratto da VTT: {vtt_file.name}. Salto il riassunto VTT.")
            vtt_summary = "Nessun contenuto testuale trovato nel file VTT."
        else:
            logger.info(f"Testo estratto da VTT: {vtt_file.name} ({len(vtt_text)} caratteri). Inizio riassunto...")
            vtt_summary = summarize_long_text(vtt_text, api_key)
            logger.info(f"Riassunto VTT per {vtt_file.name} completato.")

        # 2. Trovare PDF correlati
        related_pdfs = find_related_pdf(vtt_file, chapter_dir)
        pdf_summaries_content = []

        if related_pdfs:
            logger.info(f"Trovati {len(related_pdfs)} PDF correlati per {vtt_file.name}: {[pdf.name for pdf in related_pdfs]}")
            for pdf_file in related_pdfs:
                logger.info(f"Elaborazione PDF correlato: {pdf_file.name}")
                try:
                    pdf_text = extract_text_from_pdf(pdf_file)
                    if not pdf_text.strip():
                        logger.warning(f"Testo vuoto estratto da PDF: {pdf_file.name}. Salto il riassunto PDF.")
                        pdf_summary = f"Nessun contenuto testuale trovato nel file PDF: {pdf_file.name}."
                    else:
                        logger.info(f"Testo estratto da PDF: {pdf_file.name} ({len(pdf_text)} caratteri). Inizio riassunto...")
                        pdf_summary = summarize_long_text(pdf_text, api_key)
                        logger.info(f"Riassunto PDF per {pdf_file.name} completato.")
                    
                    pdf_summaries_content.append(f"### Riassunto del PDF: {pdf_file.name}\\n\\n{pdf_summary}")
                except Exception as e_pdf:
                    logger.error(f"Errore durante l'elaborazione del PDF {pdf_file.name}: {e_pdf}")
                    pdf_summaries_content.append(f"### Errore nel processare il PDF: {pdf_file.name}\\n\\nSi è verificato un errore: {e_pdf}")
        else:
            logger.info(f"Nessun PDF correlato trovato per {vtt_file.name}.")

        # 3. Costruire titolo della lezione
        lesson_title_base = vtt_file.stem
        lesson_title_base = re.sub(r"^\\d+[-_.\s]*", "", lesson_title_base)
        lesson_title = lesson_title_base.replace("_", " ").replace("-", " ").title()
        logger.info(f"Titolo della lezione derivato: '{lesson_title}' da '{vtt_file.name}'")

        # 4. Costruire il contenuto Markdown finale
        full_summary_content = f"## Riassunto Trascrizione Lezione: {lesson_title} (da {vtt_file.name})\\n\\n{vtt_summary}\\n"
        if pdf_summaries_content:
            full_summary_content += "\\n---\\n\\n" 
            full_summary_content += "\\n\\n".join(pdf_summaries_content)
        
        # 5. Creare struttura di output e scrivere il file
        chapter_name_for_path = chapter_dir.name
        lesson_filename_stem = re.sub(r"^\\d+[-_.\s]*", "", vtt_file.stem) 
        lesson_filename_stem = lesson_filename_stem.replace(" ", "_") 
        
        prefix_match = re.match(r"^(\\d+[-_.\s]*)", vtt_file.stem)
        if prefix_match:
            prefix = prefix_match.group(1).rstrip('-_.\s') 
            lesson_filename = f"{prefix}_{lesson_filename_stem}_summary.md"
        else:
            lesson_filename = f"{lesson_filename_stem}_summary.md"
            
        lesson_filename = "".join(c if c.isalnum() or c in ('.', '_', '-') else '_' for c in lesson_filename)


        lesson_output_dir = base_output_dir / chapter_name_for_path
        output_file_path = lesson_output_dir / lesson_filename

        write_lesson_summary(lesson_title, full_summary_content, output_file_path)
        logger.info(f"Riassunto completo della lezione '{lesson_title}' scritto in: {output_file_path}")
        return output_file_path

    except Exception as e:
        logger.error(f"Errore grave durante l'elaborazione della lezione {vtt_file.name}: {e}")
        return None

def process_chapter(chapter_dir: Path, base_output_dir: Path, api_key: str) -> List[Optional[Path]]:
    """
    Processa tutti i file VTT all'interno di una directory di capitolo.

    Per ogni file VTT, chiama process_lesson per generare il riassunto.

    Args:
        chapter_dir (Path): Percorso della directory del capitolo.
        base_output_dir (Path): Directory di output principale per tutti i riassunti del corso.
        api_key (str): Chiave API di OpenAI.

    Returns:
        List[Optional[Path]]: Una lista di percorsi ai file Markdown generati per ogni lezione.
                              Contiene None per le lezioni che hanno fallito l'elaborazione.
    """
    logger.info(f"Inizio elaborazione del capitolo: {chapter_dir.name}")
    
    if not chapter_dir.exists() or not chapter_dir.is_dir():
        logger.error(f"La directory del capitolo '{chapter_dir}' non esiste o non è una directory.")
        return []

    vtt_files = list_vtt_files(chapter_dir)
    if not vtt_files:
        logger.warning(f"Nessun file VTT trovato nel capitolo '{chapter_dir.name}'. Salto l'elaborazione del capitolo.")
        return []

    processed_lesson_paths: List[Optional[Path]] = []
    for vtt_file in vtt_files:
        logger.info(f"Avvio elaborazione per il file VTT: {vtt_file.name} nel capitolo {chapter_dir.name}")
        # Nota: base_output_dir viene passato a process_lesson, che creerà la sottocartella del capitolo
        # se non esiste già.
        lesson_summary_path = process_lesson(vtt_file, chapter_dir, base_output_dir, api_key)
        processed_lesson_paths.append(lesson_summary_path)
        if lesson_summary_path:
            logger.info(f"File VTT {vtt_file.name} elaborato con successo. Riassunto salvato in: {lesson_summary_path}")
        else:
            logger.error(f"Fallita l'elaborazione del file VTT: {vtt_file.name} nel capitolo {chapter_dir.name}")
            
    logger.info(f"Elaborazione del capitolo '{chapter_dir.name}' completata. {len(processed_lesson_paths)} lezioni elaborate.")
    return processed_lesson_paths

def create_chapter_summary(chapter_dir: Path, lesson_summary_files: List[Optional[Path]], base_output_dir: Path) -> Optional[Path]:
    """
    Crea un file Markdown di riassunto per un capitolo.

    Il file conterrà un titolo per il capitolo e una lista di link
    ai file di riassunto delle singole lezioni.

    Args:
        chapter_dir (Path): Percorso della directory del capitolo.
        lesson_summary_files (List[Optional[Path]]): Lista dei percorsi ai file Markdown
                                                     dei riassunti delle lezioni.
                                                     Può contenere None per lezioni non processate.
        base_output_dir (Path): Directory di output principale per tutti i riassunti del corso.

    Returns:
        Optional[Path]: Il percorso del file Markdown del riassunto del capitolo generato
                        o None in caso di errore.
    """
    try:
        chapter_name = chapter_dir.name
        chapter_title = chapter_name.replace("_", " ").replace("-", " ")
        # Tentativo di rendere il titolo più leggibile, es. rimuovendo prefissi numerici
        chapter_title = re.sub(r"^\d+\s*[-_]*\s*", "", chapter_title).title()

        chapter_summary_file_name = f"{chapter_name}_summary.md"
        chapter_summary_output_path = base_output_dir / chapter_summary_file_name

        logging.info(f"Creazione del file di riassunto per il capitolo '{chapter_title}' in '{chapter_summary_output_path}'")

        with open(chapter_summary_output_path, "w", encoding="utf-8") as f:
            f.write(f"# {chapter_title}\\n\\n")
            f.write("## Lezioni\\n\\n")

            valid_lesson_files = [Path(file) for file in lesson_summary_files if file is not None]

            if not valid_lesson_files:
                f.write("Nessuna lezione processata per questo capitolo.\\n")
            else:
                for lesson_file_abs_path in valid_lesson_files:
                    # Crea un percorso relativo dal file di riassunto del capitolo al file della lezione
                    try:
                        # Assicurati che entrambi i percorsi siano assoluti prima di calcolare il relativo
                        if not chapter_summary_output_path.is_absolute():
                            # Fallback se il percorso di output non è assoluto (improbabile con Path)
                            chapter_summary_abs_path = Path.cwd() / chapter_summary_output_path
                        else:
                            chapter_summary_abs_path = chapter_summary_output_path
                        
                        # Il percorso del file della lezione dovrebbe già essere assoluto o relativo corretto
                        # Se lesson_file_abs_path non è assoluto, rendilo relativo a base_output_dir
                        if not lesson_file_abs_path.is_absolute():
                             lesson_file_to_link = lesson_file_abs_path # è già relativo a base_output_dir
                        else:
                             # Se è assoluto, rendilo relativo alla directory che contiene il chapter_summary_file
                             lesson_file_to_link = lesson_file_abs_path.relative_to(chapter_summary_abs_path.parent)


                        lesson_title = lesson_file_abs_path.stem.replace("_summary", "").replace("_", " ").replace("-", " ")
                        lesson_title = re.sub(r"^\d+\s*[-_]*\s*", "", lesson_title).title()
                        
                        f.write(f"- [{lesson_title}]({lesson_file_to_link})\\n")
                    except ValueError as ve:
                        logging.warning(f"Impossibile creare il link relativo per {lesson_file_abs_path} da {chapter_summary_abs_path.parent}: {ve}")
                        # Fallback: usa il nome del file se il link relativo non può essere creato
                        lesson_title = lesson_file_abs_path.stem.replace("_summary", "").replace("_", " ").replace("-", " ").title()
                        f.write(f"- {lesson_title} (file: {lesson_file_abs_path.name})\\n")


            logging.info(f"File di riassunto del capitolo '{chapter_summary_output_path}' creato con successo.")
            return chapter_summary_output_path

    except IOError as e:
        logging.error(f"Errore di I/O durante la creazione del riassunto del capitolo per '{chapter_dir.name}': {e}")
        return None
    except Exception as e:
        logging.error(f"Errore imprevisto durante la creazione del riassunto del capitolo per '{chapter_dir.name}': {e}")
        return None

def create_main_index(course_name: str, chapter_summary_files: List[Optional[Path]], base_output_dir: Path) -> Optional[Path]:
    """
    Crea il file README.md principale per il corso.

    Il file README.md conterrà un titolo per il corso e una lista di link
    ai file di riassunto di ciascun capitolo.

    Args:
        course_name (str): Il nome del corso.
        chapter_summary_files (List[Optional[Path]]): Lista dei percorsi ai file Markdown
                                                     dei riassunti dei capitoli.
        base_output_dir (Path): Directory di output principale per tutti i riassunti.

    Returns:
        Optional[Path]: Il percorso del file README.md generato o None in caso di errore.
    """
    logging.info(f"Creazione del file README.md principale per il corso '{course_name}'.")
    readme_file_path = base_output_dir / "README.md"
    valid_chapter_summaries = [f for f in chapter_summary_files if f is not None]

    try:
        with open(readme_file_path, 'w', encoding='utf-8') as f:
            f.write(f"# Riepilogo del Corso: {course_name}\\n\\n")

            if not valid_chapter_summaries:
                f.write("Nessun capitolo è stato processato con successo.\\n")
                logging.warning("Nessun file di riassunto di capitolo fornito per creare il README.md principale.")
            else:
                f.write("## Capitoli\\n\\n")
                for chapter_summary_file in valid_chapter_summaries:
                    # chapter_title = chapter_summary_file.stem.replace('_summary', '').replace('_', ' ').title()
                    # Assumiamo che il nome del file di riassunto del capitolo sia tipo 'NomeCapitolo_summary.md'
                    # Vogliamo che il link sia al file, e il testo del link sia il nome del capitolo.
                    # Il nome del file è già relativo a base_output_dir se salvato come 'NomeCapitolo_summary.md'
                    # Il link relativo dal README.md (che è in base_output_dir) al file del capitolo (anch'esso in base_output_dir)
                    # sarà semplicemente il nome del file.
                    
                    # Estrai il titolo del capitolo dal nome del file del riassunto del capitolo
                    # E.g., da "01 - Introduzione_summary.md" a "01 - Introduzione"
                    chapter_link_text = chapter_summary_file.stem.replace('_summary', '')
                    # Rimuovi eventuali prefissi numerici per il testo del link se desiderato,
                    # ma per ora usiamo il nome del file come base per il testo del link.
                    # Esempio di pulizia del titolo:
                    # match = re.match(r"\\d*\\s*[-_]?\\s*(.*)", chapter_link_text)
                    # if match:
                    #    chapter_display_name = match.group(1).replace('_', ' ').replace('-', ' ').title()
                    # else:
                    #    chapter_display_name = chapter_link_text.replace('_', ' ').replace('-', ' ').title()
                    
                    # Per ora, usiamo una versione più semplice per il testo del link, basata sul nome del file
                    chapter_display_name = chapter_link_text.replace('_', ' ').replace('-', ' ').title()


                    # Il link deve essere relativo al README.md. Poiché entrambi sono in base_output_dir,
                    # il percorso relativo è solo il nome del file del riassunto del capitolo.
                    relative_link = chapter_summary_file.name
                    f.write(f"- [{chapter_display_name}]({relative_link})\\n")
                logging.info(f"Elenco dei capitoli aggiunto al README.md.")

        logging.info(f"File README.md principale creato con successo: {readme_file_path}")
        return readme_file_path
    except IOError as e:
        logging.error(f"Errore di I/O durante la scrittura del file README.md principale: {e}")
        return None
    except Exception as e:
        logging.error(f"Errore imprevisto durante la creazione del file README.md principale: {e}")
        return None

def main():
    """
    Funzione principale per orchestrare il processo di generazione dei riassunti del corso.
    """
    configure_logging()
    logging.info("Avvio dell'agente di riassunto corsi.")

    try:
        args = parse_arguments()
        logging.info(f"Argomenti ricevuti: course_dir='{args.course_dir}', output_dir='{args.output_dir}'")

        # 1. Inizializza API Key Manager e ottieni la chiave
        key_manager = APIKeyManager()
        api_key = key_manager.get_key()
        logging.info(f"Chiave API OpenAI caricata correttamente (hash: {key_manager._hash_key(api_key)}).")

        # 2. Configura la directory di output
        base_output_dir = setup_output_directory(args.course_dir, args.output_dir)
        logging.info(f"Directory di output configurata: {base_output_dir}")
        
        course_name = Path(args.course_dir).name


        # 3. Elenca le directory dei capitoli
        chapter_dirs = list_chapter_directories(args.course_dir)
        if not chapter_dirs:
            logging.warning("Nessun capitolo trovato nella directory del corso. Uscita.")
            return

        total_lessons_processed = 0
        total_lessons_failed = 0
        all_chapter_summary_files: List[Optional[Path]] = []

        # 4. Processa ogni capitolo
        for chapter_dir in chapter_dirs:
            logging.info(f"Inizio elaborazione capitolo: {chapter_dir.name}")
            # La funzione process_chapter restituisce una lista di Path ai riassunti delle lezioni
            lesson_summary_files_paths = process_chapter(chapter_dir, base_output_dir, api_key)
            
            processed_in_chapter = sum(1 for p in lesson_summary_files_paths if p is not None)
            failed_in_chapter = len(lesson_summary_files_paths) - processed_in_chapter
            total_lessons_processed += processed_in_chapter
            total_lessons_failed += failed_in_chapter
            
            logging.info(f"Elaborazione capitolo '{chapter_dir.name}' completata. "
                         f"Lezioni elaborate con successo: {processed_in_chapter}, Lezioni fallite: {failed_in_chapter}")

            if any(p is not None for p in lesson_summary_files_paths): # Crea il riassunto del capitolo solo se almeno una lezione è stata processata
                chapter_summary_file = create_chapter_summary(chapter_dir, lesson_summary_files_paths, base_output_dir)
                all_chapter_summary_files.append(chapter_summary_file)
            else:
                logging.warning(f"Nessuna lezione elaborata con successo per il capitolo '{chapter_dir.name}'. "
                                f"Il file di riassunto del capitolo non sarà creato.")
                all_chapter_summary_files.append(None)


        # 5. Crea il file README.md principale
        if any(cs_path is not None for cs_path in all_chapter_summary_files):
            main_index_path = create_main_index(course_name, all_chapter_summary_files, base_output_dir)
            if main_index_path:
                logging.info(f"File README.md principale creato con successo: {main_index_path}")
            else:
                logging.error("Creazione del file README.md principale fallita.")
        else:
            logging.warning("Nessun riassunto di capitolo creato. Il README.md principale non sarà generato.")


        # 6. Logga statistiche finali
        logging.info("Elaborazione del corso completata.")
        logging.info(f"Totale lezioni elaborate con successo: {total_lessons_processed}")
        logging.info(f"Totale lezioni fallite: {total_lessons_failed}")
        logging.info(f"I riassunti sono stati salvati in: {base_output_dir.resolve()}")

    except ValueError as ve:
        logging.error(f"Errore di validazione: {ve}")
    except Exception as e:
        logging.error(f"Errore imprevisto durante l'esecuzione: {e}", exc_info=True)
    finally:
        logging.info("Termine dell'agente di riassunto corsi.")


if __name__ == "__main__":
    main()