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

    def new_line(self) -> str:
        """
        Restituisce un carattere di nuova riga.
        """
        return "\n"

    def horizontal_rule(self) -> str:
        """
        Restituisce una linea orizzontale Markdown.
        """
        return "---" 