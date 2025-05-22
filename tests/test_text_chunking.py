#!/usr/bin/env python3
"""
Test per la funzionalità di chunking del testo.

Questo script verifica che la funzione chunk_text divida correttamente un testo lungo
in chunks più piccoli preservando il significato semantico e rispettando il limite di dimensione.
"""
import unittest
import sys
import os
import logging
from pathlib import Path

# Aggiunge la directory principale al path per poter importare i moduli
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resume_generator import chunk_text

class TestTextChunking(unittest.TestCase):
    """Classe di test per la funzionalità di chunking del testo."""
    
    def setUp(self):
        """Configura l'ambiente di test."""
        # Configura il logging per i test
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Crea un testo di esempio di circa 10.000 caratteri
        self.create_sample_text()

    def create_sample_text(self):
        """Crea un testo di esempio di circa 10.000 caratteri per i test."""
        # Paragrafo base di circa 500 caratteri
        base_paragraph = (
            "Questo è un paragrafo di esempio che verrà utilizzato per testare la funzione di chunking. "
            "Contiene frasi di varia lunghezza per simulare un testo reale. "
            "La funzione di chunking dovrebbe dividere il testo in modo da preservare il significato semantico, "
            "preferibilmente non interrompendo frasi o paragrafi quando possibile. "
            "Il testo dovrebbe essere diviso in chunks che non superino la dimensione massima specificata. "
            "Questo permette di ottimizzare l'utilizzo dell'API di OpenAI, che ha limiti sul numero di token che possono essere processati in una singola richiesta. "
            "Una buona strategia di chunking è fondamentale per un'applicazione efficace di Natural Language Processing."
        )
        
        # Replica il paragrafo con piccole variazioni per creare un testo di circa 10.000 caratteri
        paragraphs = []
        for i in range(20):
            # Aggiungi un numero all'inizio per rendere ogni paragrafo leggermente diverso
            modified_paragraph = f"Paragrafo {i+1}: {base_paragraph}"
            paragraphs.append(modified_paragraph)
        
        # Unisci i paragrafi con doppio newline per creare un testo completo
        self.sample_text = "\n\n".join(paragraphs)
        self.sample_text_length = len(self.sample_text)
        
        logging.info(f"Creato testo di esempio di {self.sample_text_length} caratteri.")

    def test_chunk_text_basic(self):
        """Test base: verifica che la funzione divida il testo in chunks di dimensione appropriata."""
        max_chunk_size = 2000
        chunks = chunk_text(self.sample_text, max_chunk_size)
        
        # Verifica che ci siano chunks
        self.assertTrue(len(chunks) > 0, "Il testo dovrebbe essere suddiviso in almeno un chunk")
        
        # Verifica che ciascun chunk non superi la dimensione massima
        for i, chunk in enumerate(chunks):
            self.assertLessEqual(len(chunk), max_chunk_size, 
                                f"Il chunk {i+1} supera la dimensione massima di {max_chunk_size} caratteri")
            
        logging.info(f"Test base superato: {len(chunks)} chunks creati, tutti entro il limite di {max_chunk_size} caratteri.")

    def test_chunk_text_content_preservation(self):
        """Test di preservazione del contenuto: verifica che tutto il contenuto originale sia preservato."""
        max_chunk_size = 2000
        chunks = chunk_text(self.sample_text, max_chunk_size)
        
        # Unisci i chunks (ignorando le sovrapposizioni)
        # Nota: questo è un test approssimativo, poiché la sovrapposizione dei chunks rende difficile
        # una verifica esatta. Controlliamo che tutti i paragrafi originali siano presenti.
        
        # Estrattore di paragrafi: divide il testo in paragrafi
        def extract_paragraphs(text):
            return [p for p in text.split("\n\n") if p.strip()]
        
        original_paragraphs = extract_paragraphs(self.sample_text)
        
        # Per ogni paragrafo originale, verifica che sia contenuto in almeno un chunk
        for para in original_paragraphs:
            is_contained = False
            for chunk in chunks:
                if para in chunk:
                    is_contained = True
                    break
            
            self.assertTrue(is_contained, f"Il paragrafo '{para[:50]}...' non è stato preservato nei chunks")
        
        logging.info("Test di preservazione del contenuto superato: tutti i paragrafi originali sono presenti nei chunks.")

    def test_chunk_text_empty_input(self):
        """Test con input vuoto: verifica che la funzione sollevi un'eccezione appropriata."""
        with self.assertRaises(ValueError):
            chunk_text("", 2000)
        with self.assertRaises(ValueError):
            chunk_text("   ", 2000)
            
        logging.info("Test con input vuoto superato: sollevata eccezione appropriata.")

    def test_chunk_text_small_max_size(self):
        """Test con dimensione massima troppo piccola: verifica che la funzione sollevi un'eccezione appropriata."""
        with self.assertRaises(ValueError):
            chunk_text(self.sample_text, 50)
            
        logging.info("Test con dimensione massima troppo piccola superato: sollevata eccezione appropriata.")

    def test_chunk_text_overlap(self):
        """Test sovrapposizione: verifica che ci sia una sovrapposizione tra i chunks adiacenti."""
        max_chunk_size = 2000
        chunks = chunk_text(self.sample_text, max_chunk_size)
        
        # Verifica la sovrapposizione solo se ci sono almeno 2 chunks
        if len(chunks) >= 2:
            # Per verificare la sovrapposizione, un approccio più robusto è controllare
            # se ci sono frasi o porzioni di testo significative che appaiono in entrambi i chunks
            
            overlap_found = False
            
            for i in range(len(chunks) - 1):
                current_chunk = chunks[i]
                next_chunk = chunks[i+1]
                
                # Estrai frasi dal chunk corrente (in modo approssimativo)
                sentences = [s.strip() + "." for s in current_chunk.split(".") if len(s.strip()) > 20]
                
                # Verifica se una qualsiasi di queste frasi appare anche nel chunk successivo
                for sentence in sentences:
                    if sentence in next_chunk:
                        overlap_found = True
                        logging.info(f"Trovata sovrapposizione: '{sentence[:50]}...'")
                        break
                
                if overlap_found:
                    break
            
            # Se non troviamo frasi complete che si sovrappongono, proviamo con porzioni di testo più piccole
            if not overlap_found:
                for i in range(len(chunks) - 1):
                    # Prendiamo gli ultimi 200 caratteri del chunk corrente
                    end_of_current = chunks[i][-200:] if len(chunks[i]) > 200 else chunks[i]
                    # E i primi 200 caratteri del chunk successivo
                    start_of_next = chunks[i+1][:200] if len(chunks[i+1]) > 200 else chunks[i+1]
                    
                    # Cerchiamo sovrapposizioni di almeno 50 caratteri
                    for j in range(50, len(end_of_current) - 10):
                        fragment = end_of_current[-j:]
                        if fragment in start_of_next:
                            overlap_found = True
                            logging.info(f"Trovata sovrapposizione: '{fragment[:30]}...'")
                            break
                    
                    if overlap_found:
                        break
            
            self.assertTrue(overlap_found, "Non è stata trovata sovrapposizione tra chunks adiacenti")
            logging.info("Test di sovrapposizione superato: rilevata sovrapposizione tra chunks adiacenti.")
        else:
            logging.info("Test di sovrapposizione saltato: ci sono meno di 2 chunks.")

if __name__ == "__main__":
    unittest.main() 