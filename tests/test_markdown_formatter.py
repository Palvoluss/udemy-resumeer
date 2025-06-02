#!/usr/bin/env python3
"""
Test per il modulo markdown_formatter.py.

Questo script esegue test sulla classe MarkdownFormatter per verificare
la corretta formattazione del testo in vari stili Markdown.
"""

import unittest
from src.markdown_formatter import MarkdownFormatter

class TestMarkdownFormatter(unittest.TestCase):
    """Classe di test per MarkdownFormatter."""

    def setUp(self):
        """Configurazione comune per tutti i test."""
        self.formatter = MarkdownFormatter()

    def test_format_header_level_1(self):
        """Verifica la formattazione di un header di livello 1."""
        self.assertEqual(self.formatter.format_header("Test Header", 1), "# Test Header")

    def test_format_header_level_3(self):
        """Verifica la formattazione di un header di livello 3."""
        self.assertEqual(self.formatter.format_header("Subtitle", 3), "### Subtitle")

    def test_format_header_level_6(self):
        """Verifica la formattazione di un header di livello 6."""
        self.assertEqual(self.formatter.format_header("Smallest Header", 6), "###### Smallest Header")

    def test_format_header_invalid_level_too_low(self):
        """Verifica che un livello di header troppo basso sollevi un ValueError."""
        with self.assertRaises(ValueError):
            self.formatter.format_header("Invalid Header", 0)

    def test_format_header_invalid_level_too_high(self):
        """Verifica che un livello di header troppo alto sollevi un ValueError."""
        with self.assertRaises(ValueError):
            self.formatter.format_header("Invalid Header", 7)

    def test_format_bold(self):
        """Verifica la formattazione del testo in grassetto."""
        self.assertEqual(self.formatter.format_bold("bold text"), "**bold text**")

    def test_format_italic(self):
        """Verifica la formattazione del testo in corsivo."""
        self.assertEqual(self.formatter.format_italic("italic text"), "*italic text*")

    def test_format_list_item_unordered(self):
        """Verifica la formattazione di un elemento di lista non ordinato."""
        self.assertEqual(self.formatter.format_list_item("Item 1"), "- Item 1")

    def test_format_list_item_ordered(self):
        """Verifica la formattazione di un elemento di lista ordinato."""
        self.assertEqual(self.formatter.format_list_item("Item A", ordered=True), "1. Item A")

    def test_format_list_item_unordered_indented(self):
        """Verifica la formattazione di un elemento di lista non ordinato e indentato."""
        self.assertEqual(self.formatter.format_list_item("SubItem", indent_level=1), "  - SubItem")

    def test_format_list_item_ordered_indented(self):
        """Verifica la formattazione di un elemento di lista ordinato e indentato."""
        self.assertEqual(self.formatter.format_list_item("SubItem B", ordered=True, indent_level=2), "    1. SubItem B")

    def test_format_link(self):
        """Verifica la formattazione di un link Markdown."""
        self.assertEqual(self.formatter.format_link("Visit Example", "http://example.com"), "[Visit Example](http://example.com)")

    def test_format_code_block_no_language(self):
        """Verifica la formattazione di un blocco di codice senza linguaggio specificato."""
        code = "print(\"Hello, World!\")"
        expected = "```\nprint(\"Hello, World!\")\n```"
        self.assertEqual(self.formatter.format_code_block(code), expected)

    def test_format_code_block_with_language(self):
        """Verifica la formattazione di un blocco di codice con linguaggio specificato."""
        code = "def greet():\n    return \"Hello\""
        expected = "```python\ndef greet():\n    return \"Hello\"\n```"
        self.assertEqual(self.formatter.format_code_block(code, "python"), expected)

    def test_new_line(self):
        """Verifica che il metodo new_line restituisca un carattere di nuova riga."""
        self.assertEqual(self.formatter.new_line(), "\n")

    def test_horizontal_rule(self):
        """Verifica che il metodo horizontal_rule restituisca una linea orizzontale Markdown."""
        self.assertEqual(self.formatter.horizontal_rule(), "---")

if __name__ == "__main__":
    unittest.main() 