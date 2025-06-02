#!/usr/bin/env python3
"""
Test per la funzionalità di chunking del testo con dati reali.

Questo script verifica che la funzione chunk_text funzioni correttamente con dati reali
estratti da file VTT e PDF del corso di esempio.
"""
import unittest
import os
from pathlib import Path
import shutil
import logging

from src.resume_generator import chunk_text, extract_text_from_vtt, extract_text_from_pdf

class TestRealDataChunking(unittest.TestCase):
    """Classe di test per la funzionalità di chunking con dati reali."""
    
    @classmethod
    def setUpClass(cls):
        """Configura l'ambiente di test prima di tutti i test."""
        # Configura il logging per i test
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Percorso al corso di esempio
        cls.course_dir = Path("../udemy-downloader/out_dir/web-marketing-corso-completo")
        if not cls.course_dir.exists():
            logging.warning(f"La directory del corso di esempio non esiste: {cls.course_dir}")
            cls.course_available = False
        else:
            cls.course_available = True
            
            # Trova un file VTT di esempio
            intro_chapter = cls.course_dir / "01 - Introduzione al corso"
            vtt_files = list(intro_chapter.glob("*.vtt"))
            if vtt_files:
                cls.sample_vtt = vtt_files[0]
                logging.info(f"File VTT di esempio: {cls.sample_vtt}")
            else:
                cls.sample_vtt = None
                logging.warning("Nessun file VTT trovato nel capitolo di introduzione.")
                
            # Trova un file PDF di esempio
            pdf_files = list(intro_chapter.glob("*.pdf"))
            if pdf_files:
                cls.sample_pdf = pdf_files[0]
                logging.info(f"File PDF di esempio: {cls.sample_pdf}")
            else:
                cls.sample_pdf = None
                logging.warning("Nessun file PDF trovato nel capitolo di introduzione.")
    
    def setUp(self):
        """Setup eseguito prima di ogni test."""
        if not self.course_available:
            self.skipTest("La directory del corso di esempio non è disponibile.")
    
    def test_chunk_vtt_content(self):
        """Testa il chunking del testo estratto da un file VTT reale."""
        if not self.sample_vtt:
            self.skipTest("Nessun file VTT di esempio disponibile.")
            
        # Estrai il testo dal file VTT
        vtt_text = extract_text_from_vtt(self.sample_vtt)
        self.assertTrue(len(vtt_text) > 0, "Il testo estratto dal file VTT è vuoto.")
        logging.info(f"Testo estratto dal file VTT: {len(vtt_text)} caratteri.")
        
        # Testa il chunking con diverse dimensioni massime
        chunk_sizes = [1000, 2000, 4000]
        for size in chunk_sizes:
            chunks = chunk_text(vtt_text, size)
            
            # Verifica che ci siano chunks
            self.assertTrue(len(chunks) > 0, f"Il testo dovrebbe essere suddiviso in almeno un chunk (size={size})")
            
            # Verifica che ciascun chunk non superi la dimensione massima
            for i, chunk in enumerate(chunks):
                self.assertLessEqual(len(chunk), size, 
                                    f"Il chunk {i+1} supera la dimensione massima di {size} caratteri")
                
            logging.info(f"Chunking con max_size={size}: {len(chunks)} chunks creati.")
    
    def test_chunk_pdf_content(self):
        """Testa il chunking del testo estratto da un file PDF reale."""
        if not self.sample_pdf:
            self.skipTest("Nessun file PDF di esempio disponibile.")
            
        # Estrai il testo dal file PDF
        pdf_text = extract_text_from_pdf(self.sample_pdf)
        self.assertTrue(len(pdf_text) > 0, "Il testo estratto dal file PDF è vuoto.")
        logging.info(f"Testo estratto dal file PDF: {len(pdf_text)} caratteri.")
        
        # Testa il chunking con diverse dimensioni massime
        chunk_sizes = [1000, 2000, 4000]
        for size in chunk_sizes:
            chunks = chunk_text(pdf_text, size)
            
            # Verifica che ci siano chunks
            self.assertTrue(len(chunks) > 0, f"Il testo dovrebbe essere suddiviso in almeno un chunk (size={size})")
            
            # Verifica che ciascun chunk non superi la dimensione massima
            for i, chunk in enumerate(chunks):
                self.assertLessEqual(len(chunk), size, 
                                    f"Il chunk {i+1} supera la dimensione massima di {size} caratteri")
                
            logging.info(f"Chunking con max_size={size}: {len(chunks)} chunks creati.")
    
    def test_combined_content_chunking(self):
        """Testa il chunking di contenuto combinato da VTT e PDF."""
        if not self.sample_vtt or not self.sample_pdf:
            self.skipTest("File VTT o PDF di esempio non disponibili.")
            
        # Estrai il testo dai file
        vtt_text = extract_text_from_vtt(self.sample_vtt)
        pdf_text = extract_text_from_pdf(self.sample_pdf)
        
        # Combina i testi
        combined_text = f"{vtt_text}\n\n--- MATERIALE ALLEGATO ---\n\n{pdf_text}"
        logging.info(f"Testo combinato: {len(combined_text)} caratteri.")
        
        # Chunking del testo combinato
        max_size = 3000
        chunks = chunk_text(combined_text, max_size)
        
        # Verifica che ci siano chunks
        self.assertTrue(len(chunks) > 0, "Il testo dovrebbe essere suddiviso in almeno un chunk")
        
        # Verifica che ciascun chunk non superi la dimensione massima
        for i, chunk in enumerate(chunks):
            self.assertLessEqual(len(chunk), max_size, 
                                f"Il chunk {i+1} supera la dimensione massima di {max_size} caratteri")
            
        logging.info(f"Testo combinato diviso in {len(chunks)} chunks.")
        
        # Verifica che i chunks contengano sia contenuto VTT che PDF
        vtt_marker_found = False
        pdf_marker_found = False
        
        # Cerca frasi caratteristiche del VTT e del PDF
        for chunk in chunks:
            if "MATERIALE ALLEGATO" in chunk:
                pdf_marker_found = True
            # Cerca le prime parole del VTT
            if vtt_text[:30] in chunk:
                vtt_marker_found = True
                
        # Potrebbe non essere vero se i chunks sono molto piccoli, ma con 3000 dovrebbe essere ok
        self.assertTrue(vtt_marker_found, "Nessun chunk contiene l'inizio del contenuto VTT")
        self.assertTrue(pdf_marker_found, "Nessun chunk contiene il marker del PDF")
            
if __name__ == "__main__":
    unittest.main() 