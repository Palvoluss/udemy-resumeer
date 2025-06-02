from typing import Optional, List

class MarkdownFormatter:
    """
    Una classe per aiutare nella formattazione del testo in Markdown.
    """

    def __init__(self):
        pass

    def format_header(self, text: str, level: int = 1) -> str:
        """
        Formatta una stringa come un'intestazione Markdown.
        Esempio: format_header('Titolo', 1) -> '# Titolo'
        """
        if not 1 <= level <= 6:
            raise ValueError("Il livello dell'header deve essere tra 1 e 6.")
        return f"{'#' * level} {text}"

    def format_bold(self, text: str) -> str:
        """
        Formatta una stringa in grassetto.
        Esempio: format_bold('testo') -> '**testo**'
        """
        return f"**{text}**"

    def format_italic(self, text: str) -> str:
        """
        Formatta una stringa in corsivo.
        Esempio: format_italic('testo') -> '*testo*'
        """
        return f"*{text}*"

    def format_list_item(self, text: str, ordered: bool = False, indent_level: int = 0) -> str:
        """
        Formatta una stringa come un elemento di una lista Markdown.
        Esempio: format_list_item('Voce 1') -> '- Voce 1'
        Esempio: format_list_item('Voce 1', ordered=True) -> '1. Voce 1'
        """
        indent = "  " * indent_level
        marker = "1." if ordered else "-"
        return f"{indent}{marker} {text}"

    def format_link(self, text: str, url: str) -> str:
        """
        Formatta un link Markdown.
        Esempio: format_link('Google', 'https://www.google.com') -> '[Google](https://www.google.com)'
        """
        return f"[{text}]({url})"

    def format_code_block(self, code: str, language: str = "") -> str:
        """
        Formatta una stringa come un blocco di codice Markdown.
        Esempio: format_code_block("print('hello')", "python") -> "```python\nprint('hello')\n```"
        """
        return f"```{language}\n{code}\n```"

    def new_line(self, count: int = 1) -> str:
        """
        Restituisce un carattere di nuova riga.
        """
        return "\n" * count

    def horizontal_rule(self) -> str:
        """
        Restituisce una linea orizzontale Markdown.
        """
        return "---"

    def format_frontmatter(self, data: dict) -> str:
        """
        Formatta un dizionario come frontmatter YAML.
        Esempio: format_frontmatter({'title': 'Mio Titolo', 'tags': ['a', 'b']})
                 -> ---
                    title: Mio Titolo
                    tags:
                      - a
                      - b
                    ---
        """
        if not isinstance(data, dict):
            raise ValueError("I dati per il frontmatter devono essere un dizionario.")
        
        yaml_lines = ["---"]
        for key, value in data.items():
            if isinstance(value, list):
                yaml_lines.append(f"{key}:")
                for item in value:
                    yaml_lines.append(f"  - {item}")
            else:
                if value == "":
                    yaml_lines.append(f"{key}:")
                else:
                    yaml_lines.append(f"{key}: {value}")
        yaml_lines.append("---")
        return "\n".join(yaml_lines) + "\n"

    def format_lesson_summary(
        self,
        lesson_title: str,
        vtt_summary: Optional[str],
        pdf_summary: Optional[str],
        html_summary: Optional[str],
        orphan_summary: Optional[str]
    ) -> str:
        """Formatta il contenuto completo del riassunto di una lezione.

        Args:
            lesson_title (str): Il titolo della lezione.
            vtt_summary (Optional[str]): Il riassunto del contenuto VTT.
            pdf_summary (Optional[str]): Il riassunto del contenuto PDF.
            html_summary (Optional[str]): Il riassunto del contenuto HTML (arricchito).
            orphan_summary (Optional[str]): Il riassunto del contenuto dei file orfani associati.

        Returns:
            str: Il contenuto Markdown formattato per il riassunto della lezione.
        """
        parts: List[str] = []

        if vtt_summary and vtt_summary.strip() and not vtt_summary.startswith("Errore") and not vtt_summary.startswith("Nessun contenuto") :
            parts.append(self.format_header("Riassunto Video (Trascrizione VTT)", 2))
            parts.append(self.new_line())
            parts.append(vtt_summary.strip())
            parts.append(self.new_line(count=2))
        elif vtt_summary:
            parts.append(self.format_header("Riassunto Video (Trascrizione VTT)", 2))
            parts.append(self.new_line())
            parts.append(self.format_blockquote(vtt_summary.strip()))
            parts.append(self.new_line(count=2))

        if pdf_summary and pdf_summary.strip() and not pdf_summary.startswith("Errore") and not pdf_summary.startswith("Nessun contenuto"):
            parts.append(self.format_header("Riassunto Documenti (PDF)", 2))
            parts.append(self.new_line())
            parts.append(pdf_summary.strip())
            parts.append(self.new_line(count=2))
        elif pdf_summary:
            parts.append(self.format_header("Riassunto Documenti (PDF)", 2))
            parts.append(self.new_line())
            parts.append(self.format_blockquote(pdf_summary.strip()))
            parts.append(self.new_line(count=2))

        if html_summary and html_summary.strip() and not html_summary.startswith("Errore") and not html_summary.startswith("Nessun contenuto"):
            parts.append(self.format_header("Riassunto Contenuti Web (HTML)", 2))
            parts.append(self.new_line())
            parts.append(html_summary.strip())
            parts.append(self.new_line(count=2))
        elif html_summary:
            parts.append(self.format_header("Riassunto Contenuti Web (HTML)", 2))
            parts.append(self.new_line())
            parts.append(self.format_blockquote(html_summary.strip()))
            parts.append(self.new_line(count=2))
        
        if orphan_summary and orphan_summary.strip() and not orphan_summary.startswith("Errore") and not orphan_summary.startswith("Nessun contenuto"):
            parts.append(self.format_header("Materiale Aggiuntivo (File Orfani)", 2))
            parts.append(self.new_line())
            parts.append(orphan_summary.strip())
            parts.append(self.new_line(count=2))
        elif orphan_summary:
            parts.append(self.format_header("Materiale Aggiuntivo (File Orfani)", 2))
            parts.append(self.new_line())
            parts.append(self.format_blockquote(orphan_summary.strip()))
            parts.append(self.new_line(count=2))

        return "".join(parts)

    def format_chapter_summary(self, summary: str) -> str:
        """
        Formatta una stringa come riassunto di un capitolo.
        Esempio: format_chapter_summary('Questo è il riassunto del capitolo.')
        """
        return f"## {summary}"

    def format_blockquote(self, text: str) -> str:
        """
        Formatta una stringa come blocco di citazione Markdown.
        Esempio: format_blockquote('Questo è un esempio di citazione.') -> '> Questo è un esempio di citazione.'
        """
        return f"> {text}" 