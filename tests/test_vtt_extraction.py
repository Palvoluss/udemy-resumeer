#!/usr/bin/env python3
"""
Test per la funzione extract_text_from_vtt del modulo resume_generator.
"""

import unittest
import logging
from pathlib import Path
import tempfile
from src.resume_generator import extract_text_from_vtt

# Configura logging per il test (opzionale, ma utile per il debug)
# Rimosso il logging di base, unittest ha il suo sistema di verbosità.

class TestVTTExtraction(unittest.TestCase):
    """Classe di test per la funzione extract_text_from_vtt."""

    def setUp(self):
        """Crea una directory temporanea per i file di test."""
        self.test_data_dir = Path("test_data_vtt_temp")
        self.test_data_dir.mkdir(parents=True, exist_ok=True)

        self.valid_vtt_content = """WEBVTT

00:00:01.000 --> 00:00:05.000
Benvenuti al nostro corso di programmazione Python!

00:00:06.000 --> 00:00:10.000
Imparerete i fondamenti della programmazione in Python. E' un linguaggio di programmazione molto potente e versatile.
"""
        self.valid_vtt_file = self.test_data_dir / "valid.vtt"
        with open(self.valid_vtt_file, "w", encoding="utf-8") as f:
            f.write(self.valid_vtt_content)

        self.not_vtt_content = "Questo non è un file VTT."
        self.not_vtt_file = self.test_data_dir / "not_a_vtt.txt"
        with open(self.not_vtt_file, "w", encoding="utf-8") as f:
            f.write(self.not_vtt_content)

    def tearDown(self):
        """Rimuove la directory temporanea e i suoi contenuti."""
        if self.valid_vtt_file.exists():
            self.valid_vtt_file.unlink()
        if self.not_vtt_file.exists():
            self.not_vtt_file.unlink()
        if self.test_data_dir.exists():
            # Prova a rimuovere i file rimanenti prima della directory
            for item in self.test_data_dir.iterdir():
                if item.is_file():
                    item.unlink()
            self.test_data_dir.rmdir()


    def test_extract_from_valid_vtt(self):
        """Testa l'estrazione da un file VTT valido."""
        extracted_text = extract_text_from_vtt(self.valid_vtt_file)
        
        # Il testo atteso è esattamente come viene prodotto da webvtt.read().caption_text(),
        # che unisce le linee di una caption con spazio e le diverse caption con newline.
        expected_text = "Benvenuti al nostro corso di programmazione Python!\nImparerete i fondamenti della programmazione in Python. E' un linguaggio di programmazione molto potente e versatile."

        self.assertEqual(extracted_text.strip(), expected_text.strip())
        
        # Verifica che i timestamp e l'intestazione WEBVTT non siano presenti
        unwanted_patterns = ["WEBVTT", "00:", "-->"]
        for pattern in unwanted_patterns:
            self.assertNotIn(pattern, extracted_text)

    def test_extract_from_nonexistent_file(self):
        """Testa il comportamento con un file VTT inesistente."""
        non_existent_file = self.test_data_dir / "non_existent.vtt"
        # Usa str(path) per il messaggio atteso, come fa la funzione.
        expected_error_message = f"Il file VTT '{str(non_existent_file)}' non esiste o non è un file."
        with self.assertRaisesRegex(ValueError, expected_error_message):
            extract_text_from_vtt(non_existent_file)

    def test_extract_from_not_a_vtt_file(self):
        """Testa il comportamento con un file che non è un VTT (basato sul contenuto)."""
        malformed_vtt_file = self.test_data_dir / "malformed.vtt"
        with open(malformed_vtt_file, "w", encoding="utf-8") as f:
            f.write("Questo non è un contenuto VTT valido anche se l'estensione è .vtt")
        
        # Usa str(path) per il messaggio atteso.
        expected_error_message = f"Il file VTT '{str(malformed_vtt_file)}' è malformato: Invalid format"
        with self.assertRaisesRegex(ValueError, expected_error_message):
             extract_text_from_vtt(malformed_vtt_file)
        if malformed_vtt_file.exists():
            malformed_vtt_file.unlink()


    def test_extract_from_text_file_spoofed_as_vtt(self):
        """Testa il comportamento con un file .txt rinominato .vtt ma con contenuto non VTT."""
        spoofed_vtt_file = self.not_vtt_file.rename(self.test_data_dir / "spoofed.vtt")
        # Usa str(path) per il messaggio atteso.
        expected_error_message = f"Il file VTT '{str(spoofed_vtt_file)}' è malformato: Invalid format"
        with self.assertRaisesRegex(ValueError, expected_error_message):
            extract_text_from_vtt(spoofed_vtt_file)


if __name__ == "__main__":
    unittest.main() 