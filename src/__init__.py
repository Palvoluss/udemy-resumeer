"""
Package per la generazione di riassunti da corsi didattici.

Questo package contiene tutti i moduli necessari per:
- Estrarre testo da file VTT e PDF
- Generare riassunti usando OpenAI
- Formattare output in Markdown
- Tracciare chiamate LLM con Langfuse
- Gestire chiavi API in modo sicuro
"""

from .api_key_manager import APIKeyManager
from .markdown_formatter import MarkdownFormatter
from .langfuse_tracker import LangfuseTracker

__version__ = "1.0.0"
__all__ = ["APIKeyManager", "MarkdownFormatter", "LangfuseTracker"] 