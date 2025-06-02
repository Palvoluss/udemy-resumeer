#!/usr/bin/env python3
"""
Test per il modulo html_parser.py.

Questo script esegue test sulla funzione extract_text_and_images_from_html
per verificare la corretta estrazione di testo e informazioni sulle immagini
da diverse stringhe HTML.
"""

import unittest
from src.html_parser import extract_text_and_images_from_html

class TestHTMLParser(unittest.TestCase):
    """Classe di test per le funzioni di parsing HTML."""

    def test_extract_basic_text_and_images(self):
        """Verifica l'estrazione da HTML semplice con testo e immagini."""
        html_content = ("<html><head><title>Titolo</title></head><body>" +
                        "<p>Paragrafo 1.</p><img src=\"img1.png\" alt=\"Alt1\">" +
                        "<div>Altro testo.</div><img src=\"img2.jpeg\" alt=\"Alt2\"></body></html>")
        text, images = extract_text_and_images_from_html(html_content)
        self.assertEqual(text, "Titolo\nParagrafo 1.\nAltro testo.")
        self.assertEqual(len(images), 2)
        self.assertIn({'src': 'img1.png', 'alt': 'Alt1'}, images)
        self.assertIn({'src': 'img2.jpeg', 'alt': 'Alt2'}, images)

    def test_remove_scripts_and_styles(self):
        """Verifica che script, style e altri tag non contenutistici vengano rimossi."""
        html_content = ("<body><script>alert('ciao');</script>" +
                        "<style>p {color: red;}</style><nav>Link</nav>" +
                        "<p>Testo visibile</p><footer>Copyright</footer>" +
                        "<header>Header</header><aside>Aside</aside></body>")
        text, images = extract_text_and_images_from_html(html_content)
        self.assertEqual(text, "Testo visibile")
        self.assertEqual(len(images), 0)

    def test_empty_html(self):
        """Verifica il comportamento con una stringa HTML vuota."""
        html_content = ""
        text, images = extract_text_and_images_from_html(html_content)
        self.assertEqual(text, "")
        self.assertEqual(len(images), 0)

    def test_html_with_no_text(self):
        """Verifica il comportamento con HTML che contiene solo tag (nessun testo)."""
        html_content = "<html><body><img src=\"test.gif\"></body></html>"
        text, images = extract_text_and_images_from_html(html_content)
        self.assertEqual(text, "") # BeautifulSoup potrebbe estrarre stringhe vuote dai tag
        self.assertEqual(len(images), 1)
        self.assertIn({'src': 'test.gif', 'alt': ''}, images)

    def test_html_with_no_images(self):
        """Verifica il comportamento con HTML che non contiene immagini."""
        html_content = "<p>Solo testo qui.</p><div>Altro testo.</div>"
        text, images = extract_text_and_images_from_html(html_content)
        self.assertEqual(text, "Solo testo qui.\nAltro testo.")
        self.assertEqual(len(images), 0)

    def test_image_with_no_alt_attribute(self):
        """Verifica che le immagini senza attributo 'alt' vengano gestite (alt='')."""
        html_content = "<img src=\"no_alt.jpg\">"
        text, images = extract_text_and_images_from_html(html_content)
        self.assertEqual(len(images), 1)
        self.assertIn({'src': 'no_alt.jpg', 'alt': ''}, images)

    def test_image_with_empty_alt_attribute(self):
        """Verifica che le immagini con attributo 'alt' vuoto vengano gestite."""
        html_content = "<img src=\"empty_alt.png\" alt=\"\">"
        text, images = extract_text_and_images_from_html(html_content)
        self.assertEqual(len(images), 1)
        self.assertIn({'src': 'empty_alt.png', 'alt': ''}, images)

    def test_image_tag_without_src(self):
        """Verifica che i tag <img> senza attributo 'src' vengano ignorati."""
        html_content = "<img alt=\"Senza SRC\"><p>Testo</p>"
        text, images = extract_text_and_images_from_html(html_content)
        self.assertEqual(text, "Testo")
        self.assertEqual(len(images), 0)

    def test_complex_html_structure(self):
        """Verifica l'estrazione da una struttura HTML più complessa e nidificata."""
        html_content = ("<div><p><span>Testo</span> importante.</p>" +
                        "<section><img src=\"image.gif\" alt=\"Animazione\"></section></div>")
        text, images = extract_text_and_images_from_html(html_content)
        self.assertEqual(text, "Testo\nimportante.")
        self.assertEqual(len(images), 1)
        self.assertIn({'src': 'image.gif', 'alt': 'Animazione'}, images)
    
    def test_text_extraction_with_line_breaks(self):
        """Verifica la corretta gestione degli a capo nel testo estratto."""
        html_content = "<p>Riga 1</p><p>Riga 2</p><div>Riga 3</div>"
        text, images = extract_text_and_images_from_html(html_content)
        self.assertEqual(text, "Riga 1\nRiga 2\nRiga 3")
        self.assertEqual(len(images), 0)

    def test_text_extraction_with_stripped_strings(self):
        """Verifica che gli spazi bianchi extra vengano rimossi correttamente."""
        html_content = "<body>   <p>   Testo con spazi   </p>   <div>   Altro testo   </div>   </body>"
        text, images = extract_text_and_images_from_html(html_content)
        self.assertEqual(text, "Testo con spazi\nAltro testo")
        self.assertEqual(len(images), 0)

if __name__ == "__main__":
    unittest.main() 