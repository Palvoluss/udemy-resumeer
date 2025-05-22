#!/usr/bin/env python3
"""
Script di test per la funzione extract_text_from_vtt.

Questo script esegue test sulla funzione extract_text_from_vtt implementata in resume_generator.py.
"""
import sys
import logging
from pathlib import Path
from resume_generator import extract_text_from_vtt

# Configura logging per il test
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def test_extract_text_from_vtt():
    """
    Esegue test sulla funzione extract_text_from_vtt.
    
    Verifica che la funzione:
    1. Estragga correttamente il testo da un file VTT valido
    2. Rimuova timestamp, metadata e intestazione WEBVTT
    3. Gestisca correttamente errori come file inesistenti o invalidi
    
    Returns:
        bool: True se tutti i test passano, False altrimenti.
    """
    logging.info("Iniziando i test per extract_text_from_vtt...")
    
    # Test 1: File VTT valido
    test_file = Path("test_data/course_A/Chapter1_Intro/01_Welcome.vtt")
    if not test_file.exists():
        logging.error(f"File di test non trovato: {test_file}")
        return False
    
    try:
        logging.info(f"Test 1: Estrazione testo da file VTT valido: {test_file}")
        extracted_text = extract_text_from_vtt(test_file)
        
        # Verifica che il testo estratto contenga frasi chiave dal file VTT
        expected_phrases = [
            "Benvenuti al nostro corso di programmazione Python!",
            "fondamenti della programmazione in Python",
            "linguaggio di programmazione molto potente e versatile"
        ]
        
        all_phrases_found = all(phrase in extracted_text for phrase in expected_phrases)
        
        if all_phrases_found:
            logging.info("Test 1: PASSATO - Il testo estratto contiene tutte le frasi chiave attese.")
        else:
            logging.error("Test 1: FALLITO - Il testo estratto non contiene tutte le frasi chiave attese.")
            logging.error(f"Testo estratto:\n{extracted_text}")
            return False
        
        # Verifica che i timestamp e l'intestazione WEBVTT non siano presenti
        unwanted_phrases = [
            "WEBVTT",
            "00:00:",
            "-->"
        ]
        
        no_unwanted_phrases = all(phrase not in extracted_text for phrase in unwanted_phrases)
        
        if no_unwanted_phrases:
            logging.info("Test 2: PASSATO - Il testo estratto non contiene timestamp o intestazione WEBVTT.")
        else:
            logging.error("Test 2: FALLITO - Il testo estratto contiene timestamp o intestazione WEBVTT.")
            logging.error(f"Testo estratto:\n{extracted_text}")
            return False
            
    except Exception as e:
        logging.error(f"Test 1: FALLITO - Si è verificata un'eccezione durante l'estrazione: {e}")
        return False
    
    # Test 2: File inesistente
    nonexistent_file = Path("test_data/nonexistent_file.vtt")
    try:
        logging.info(f"Test 3: Gestione file inesistente: {nonexistent_file}")
        extract_text_from_vtt(nonexistent_file)
        logging.error("Test 3: FALLITO - Nessuna eccezione lanciata per file inesistente")
        return False
    except ValueError as e:
        logging.info(f"Test 3: PASSATO - Eccezione corretta per file inesistente: {e}")
    except Exception as e:
        logging.error(f"Test 3: FALLITO - Eccezione inattesa per file inesistente: {e}")
        return False
    
    # Test 3: File non VTT
    try:
        logging.info("Test 4: Creazione file di test non-VTT...")
        non_vtt_file = Path("test_data/not_a_vtt_file.txt")
        with open(non_vtt_file, "w") as f:
            f.write("Questo non è un file VTT")
        
        logging.info(f"Test 4: Gestione file non VTT: {non_vtt_file}")
        extract_text_from_vtt(non_vtt_file)
        logging.error("Test 4: FALLITO - Nessuna eccezione lanciata per file non VTT")
        non_vtt_file.unlink()  # Pulizia
        return False
    except ValueError as e:
        logging.info(f"Test 4: PASSATO - Eccezione corretta per file non VTT: {e}")
        if non_vtt_file.exists():
            non_vtt_file.unlink()  # Pulizia
    except Exception as e:
        logging.error(f"Test 4: FALLITO - Eccezione inattesa per file non VTT: {e}")
        if non_vtt_file.exists():
            non_vtt_file.unlink()  # Pulizia
        return False
    
    logging.info("Tutti i test sono stati completati con successo!")
    return True

if __name__ == "__main__":
    success = test_extract_text_from_vtt()
    if success:
        logging.info("SUCCESSO: Tutti i test sono stati superati.")
        sys.exit(0)
    else:
        logging.error("FALLIMENTO: Almeno un test è fallito.")
        sys.exit(1) 