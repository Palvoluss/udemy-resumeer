#!/usr/bin/env python3
"""
Test della funzionalità di estrazione testo da PDF.

Questo script testa la funzione extract_text_from_pdf che estrae il testo da file PDF.
"""
import os
import logging
import unittest
import tempfile
from pathlib import Path
import PyPDF2
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from resume_generator import extract_text_from_pdf, configure_logging

class TestPDFExtraction(unittest.TestCase):
    """Classe per i test della funzionalità di estrazione testo da PDF."""

    def setUp(self):
        """Configurazione per i test."""
        configure_logging()
        # Crea una directory temporanea per i test
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.test_dir.name)
        
        # Crea un file PDF di test
        self.sample_text = "Sample PDF content for testing."
        self.sample_pdf_path = self.test_path / "sample.pdf"
        self.create_sample_pdf(self.sample_pdf_path, self.sample_text)
        
        # Crea anche un file non-PDF per i test negativi
        self.non_pdf_path = self.test_path / "not_pdf.txt"
        with open(self.non_pdf_path, 'w', encoding='utf-8') as f:
            f.write("This is not a PDF file.")

    def tearDown(self):
        """Pulizia dopo i test."""
        self.test_dir.cleanup()

    def create_sample_pdf(self, path, text):
        """
        Crea un file PDF di esempio con il testo specificato.
        
        Args:
            path (Path): percorso dove salvare il PDF
            text (str): testo da inserire nel PDF
        """
        c = canvas.Canvas(str(path), pagesize=letter)
        c.drawString(100, 750, text)
        c.save()

    def test_extract_text_from_valid_pdf(self):
        """Test dell'estrazione di testo da un file PDF valido."""
        extracted_text = extract_text_from_pdf(self.sample_pdf_path)
        # Dato che PyPDF2 e reportlab potrebbero gestire il testo in modi leggermente diversi,
        # verifichiamo solo che il testo originale sia contenuto nell'estratto
        self.assertIn(self.sample_text, extracted_text)
        logging.info(f"Test estrazione da PDF valido completato: testo estratto contiene '{self.sample_text}'")

    def test_extract_text_from_nonexistent_file(self):
        """Test del comportamento con un file inesistente."""
        nonexistent_path = self.test_path / "nonexistent.pdf"
        with self.assertRaises(ValueError):
            extract_text_from_pdf(nonexistent_path)
        logging.info("Test con file inesistente completato: ValueError sollevato come previsto")

    def test_extract_text_from_non_pdf_file(self):
        """Test del comportamento con un file che non è un PDF."""
        with self.assertRaises(ValueError):
            extract_text_from_pdf(self.non_pdf_path)
        logging.info("Test con file non-PDF completato: ValueError sollevato come previsto")

if __name__ == "__main__":
    unittest.main() 