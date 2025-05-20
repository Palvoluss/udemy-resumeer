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
import webvtt
import PyPDF2

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

def extract_text_from_vtt(vtt_file_path):
    """
    Estrae il testo parlato da un file VTT.
    
    Utilizza la libreria webvtt-py per analizzare il file VTT ed estrarre solo il contenuto
    testuale (escludendo timestamp, impostazioni dei sottotitoli e l'intestazione WEBVTT).
    
    Args:
        vtt_file_path (str o Path): Percorso del file VTT da processare.
            
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

def extract_text_from_pdf(pdf_file_path):
    """
    Estrae il testo da un file PDF.
    
    Utilizza la libreria PyPDF2 per estrarre il testo da tutte le pagine del documento PDF.
    
    Args:
        pdf_file_path (str o Path): Percorso del file PDF da processare.
            
    Returns:
        str: Il testo estratto dal file PDF.
        
    Raises:
        ValueError: Se il file non esiste o non è un file PDF valido.
        Exception: Per altri errori durante l'elaborazione del file PDF.
    """
    pdf_path = Path(pdf_file_path)
    
    if not pdf_path.exists() or not pdf_path.is_file():
        raise ValueError(f"Il file PDF '{pdf_file_path}' non esiste o non è un file.")
    
    if pdf_path.suffix.lower() != '.pdf':
        raise ValueError(f"Il file '{pdf_file_path}' non è un file PDF (estensione attesa: .pdf).")
    
    try:
        logging.debug(f"Estrazione del testo dal file PDF: {pdf_path}")
        
        # Apri il file PDF
        with open(pdf_path, 'rb') as pdf_file:
            # Crea un lettore PDF
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Estrai il testo da tutte le pagine
            all_text = []
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                all_text.append(page.extract_text())
            
            # Unisci il testo di tutte le pagine con interruzioni di riga
            extracted_text = "\n\n".join(all_text)
            
            logging.debug(f"Testo estratto dal PDF ({len(extracted_text)} caratteri).")
            return extracted_text
        
    except PyPDF2.errors.PdfReadError as e:
        raise ValueError(f"Errore durante la lettura del file PDF '{pdf_file_path}': {str(e)}")
    except Exception as e:
        raise Exception(f"Errore durante l'estrazione del testo dal file PDF '{pdf_file_path}': {str(e)}")

def main():
    """Funzione principale per orchestrare il processo di generazione dei riassunti."""
    # Configura il logging
    configure_logging()
    
    # Log dell'avvio dello script
    logging.info("Avvio di Resume Generator: Tool per riassumere corsi strutturati in cartelle")
    
    args = parse_arguments()
    
    try:
        logging.info(f"Processo avviato con directory del corso: {args.course_dir}")
        output_directory = setup_output_directory(args.course_dir, args.output_dir)
        logging.info(f"Directory di output configurata: {output_directory}")
        
        # Lista delle directory dei capitoli
        chapter_directories = list_chapter_directories(args.course_dir)
        logging.info(f"Capitoli trovati: {[chapter.name for chapter in chapter_directories]}")
        
    except Exception as e:
        logging.error(f"Si è verificato un errore: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code) 