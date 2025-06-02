#!/usr/bin/env python3
"""
Test per la classe ImageDescriber in src/image_describer.py.
"""

import unittest
from unittest.mock import patch, MagicMock # Rimosso create_autospec perché non più usato direttamente nei test modificati
import logging
import os
import httpx # Richiesto per APIError e per respx
import respx # Aggiunto per mockare le chiamate HTTP
import json # Per costruire risposte JSON

# Importa la classe da testare
from src.image_describer import ImageDescriber
from openai import APIError, OpenAI, APIConnectionError # Aggiunto APIConnectionError

# Disabilita i log di info e warning durante i test per pulire l'output,
# a meno che non si stia specificamente testando il logging.
# logging.disable(logging.INFO)
# logging.disable(logging.WARNING)

class TestImageDescriber(unittest.TestCase):
    """Classe di test per ImageDescriber."""

    def setUp(self):
        """Configura l'ambiente per ogni test."""
        self.mock_api_key = "test_api_key"
        # Pulisci le variabili d'ambiente che potrebbero interferire
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        # Assicurati che OPENAI_API_BASE_URL non sia impostata, altrimenti respx potrebbe avere problemi
        # a intercettare le chiamate se il client OpenAI è inizializzato con un base_url custom non mockato.
        # Per i test di unità con respx, vogliamo che il client punti all'URL di default di OpenAI
        # che respx andrà a intercettare.
        if "OPENAI_API_BASE_URL" in os.environ:
            del os.environ["OPENAI_API_BASE_URL"]

    @patch('src.image_describer.OpenAI')
    def test_initialization_with_api_key(self, mock_openai_constructor):
        """Testa l'inizializzazione con una API key fornita."""
        mock_client_instance = MagicMock(spec=OpenAI) # Usiamo MagicMock base per il costruttore
        mock_openai_constructor.return_value = mock_client_instance
        
        describer = ImageDescriber(api_key=self.mock_api_key)
        
        mock_openai_constructor.assert_called_once_with(api_key=self.mock_api_key)
        self.assertIsNotNone(describer.client)
        self.assertEqual(describer.client, mock_client_instance)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "env_api_key"})
    @patch('src.image_describer.OpenAI')
    def test_initialization_with_env_variable(self, mock_openai_constructor):
        """Testa l'inizializzazione usando la variabile d'ambiente OPENAI_API_KEY."""
        mock_client_instance = MagicMock(spec=OpenAI)
        mock_openai_constructor.return_value = mock_client_instance

        describer = ImageDescriber() # Nessuna api_key fornita esplicitamente
        
        # La libreria OpenAI potrebbe essere chiamata con argomenti di default o vuoti
        # quando si affida alle variabili d'ambiente. Verifichiamo che sia chiamata.
        mock_openai_constructor.assert_called_once()
        self.assertIsNotNone(describer.client)
        self.assertEqual(describer.client, mock_client_instance)

    @patch('src.image_describer.OpenAI')
    def test_initialization_failure(self, mock_openai_constructor):
        """Testa l'inizializzazione quando la creazione del client OpenAI fallisce."""
        mock_openai_constructor.side_effect = Exception("Connection error")
        
        with self.assertLogs(logger='src.image_describer', level='ERROR') as cm:
            describer = ImageDescriber(api_key=self.mock_api_key)
        
        self.assertIsNone(describer.client)
        self.assertIn("Errore durante l'inizializzazione del client OpenAI in ImageDescriber: Connection error", cm.output[0])

    def test_initialization_with_langfuse_tracker(self):
        """Testa che LangfuseTracker sia memorizzato correttamente."""
        mock_tracker = MagicMock()
        # Per questo test, non ci interessa mockare OpenAI, quindi lo lasciamo creare un client reale
        # (o fallire se non c'è una chiave, ma il test si concentra sul tracker)
        describer = ImageDescriber(api_key=self.mock_api_key, langfuse_tracker=mock_tracker)
        self.assertEqual(describer.langfuse_tracker, mock_tracker)

    @patch.object(ImageDescriber, '__init__', lambda self, api_key=None, langfuse_tracker=None: None) # Evita __init__ reale
    def test_describe_image_url_client_not_initialized(self):
        """Testa describe_image_url quando il client non è inizializzato."""
        describer = ImageDescriber()
        describer.client = None # Simula client non inizializzato
        describer.langfuse_tracker = None # Assicura che non ci sia tracker per questo test

        result = describer.describe_image_url("http://example.com/image.jpg")
        self.assertEqual(result, "Errore: Client OpenAI non configurato.")

    @respx.mock
    def test_describe_image_url_success(self, respx_mock):
        """Testa describe_image_url in caso di successo della chiamata API usando respx."""
        expected_description = "Una bella descrizione dell\\'immagine."
        prompt_tokens = 10
        completion_tokens = 20
        total_tokens = 30

        respx_mock.post("https://api.openai.com/v1/chat/completions").respond(
            status_code=200,
            json={
                "choices": [{
                    "message": {"content": expected_description}
                }],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                }
            }
        )
        
        mock_langfuse_tracker = MagicMock()
        describer = ImageDescriber(api_key=self.mock_api_key, langfuse_tracker=mock_langfuse_tracker)
        
        image_url = "http://example.com/image.jpg"
        detail = "high"
        chapter = "Cap1"
        lesson = "Lez1"
        alt = "Alt text"

        result = describer.describe_image_url(image_url, detail=detail, chapter_name=chapter, lesson_name=lesson, original_alt=alt)
        
        self.assertEqual(result, expected_description)
        
        mock_langfuse_tracker.track_llm_call.assert_called_once()
        langfuse_args, langfuse_kwargs = mock_langfuse_tracker.track_llm_call.call_args
        self.assertEqual(langfuse_kwargs['output_text'], expected_description)
        self.assertEqual(langfuse_kwargs['model'], "gpt-4o") 
        self.assertEqual(langfuse_kwargs['chapter_name'], chapter)
        self.assertEqual(langfuse_kwargs['lesson_name'], lesson)
        self.assertEqual(langfuse_kwargs['content_type'], "image_description")
        self.assertIsNotNone(langfuse_kwargs['token_usage'])
        self.assertEqual(langfuse_kwargs['token_usage']['total_tokens'], total_tokens)
        self.assertEqual(langfuse_kwargs['token_usage']['prompt_tokens'], prompt_tokens)
        self.assertEqual(langfuse_kwargs['token_usage']['completion_tokens'], completion_tokens)
        self.assertIsNone(langfuse_kwargs['error'])
        self.assertEqual(langfuse_kwargs['prompt_info']['image_url'], image_url) 
        self.assertEqual(langfuse_kwargs['prompt_info']['original_alt_text'], alt)

    @respx.mock
    def test_describe_image_url_api_error(self, respx_mock):
        """Testa describe_image_url quando OpenAI solleva un APIError, usando respx."""
        api_error_message_detail = "Invalid API key."
        api_error_type = "invalid_request_error"
        status_code = 401

        error_body_dict = {"error": {"message": api_error_message_detail, "type": api_error_type}}
        # La rappresentazione stringa di un dict Python usa virgolette singole.
        # Questa è la stringa che ci aspettiamo nel messaggio di errore da str(APIError).
        error_body_repr_string = str(error_body_dict) 
        
        # Mock della risposta HTTP: passiamo il dizionario, httpx/openai lo gestiranno.
        # La libreria OpenAI poi, nel creare APIError, userà una rappresentazione stringa del corpo
        # che assomiglia a str(dict) piuttosto che a json.dumps(dict).
        respx_mock.post("https://api.openai.com/v1/chat/completions").respond(
            status_code=status_code, 
            json=error_body_dict # Passiamo il dict direttamente, sarà serializzato da httpx/respx
        )
        
        mock_langfuse_tracker = MagicMock()
        describer = ImageDescriber(api_key="invalid_key", langfuse_tracker=mock_langfuse_tracker)
        
        image_url = "http://example.com/image.jpg"
        result = describer.describe_image_url(image_url)
        
        expected_error_str_from_api_error = f"Error code: {status_code} - {error_body_repr_string}"
        expected_returned_message = f"Errore API OpenAI: {expected_error_str_from_api_error}"
        self.assertEqual(result, expected_returned_message)
        
        mock_langfuse_tracker.track_llm_call.assert_called_once()
        langfuse_args, langfuse_kwargs = mock_langfuse_tracker.track_llm_call.call_args
        self.assertEqual(langfuse_kwargs['error'], expected_error_str_from_api_error)

    @respx.mock
    def test_describe_image_url_generic_exception(self, respx_mock):
        """Testa describe_image_url quando si verifica un'eccezione di connessione (wrappata come APIConnectionError)."""
        original_httpx_message = "Simulated network error from httpx"
        # Questo è il messaggio che la libreria OpenAI tipicamente usa per APIConnectionError generiche
        expected_openai_connection_error_message = "Connection error."

        respx_mock.post("https://api.openai.com/v1/chat/completions").mock(side_effect=httpx.ConnectError(original_httpx_message))
        
        mock_langfuse_tracker = MagicMock()
        describer = ImageDescriber(api_key=self.mock_api_key, langfuse_tracker=mock_langfuse_tracker)
        
        image_url = "http://example.com/image.jpg"
        result = describer.describe_image_url(image_url)
        
        self.assertTrue(result.startswith("Errore API OpenAI:"), f"Risultato attuale: {result}")
        # Verifica che il messaggio generico di APIConnectionError sia presente
        self.assertIn(expected_openai_connection_error_message, result)
        # Il messaggio originale di httpx potrebbe non essere sempre presente, quindi questa asserzione è meno robusta:
        # self.assertIn(original_httpx_message, result)
        
        mock_langfuse_tracker.track_llm_call.assert_called_once()
        langfuse_args, langfuse_kwargs = mock_langfuse_tracker.track_llm_call.call_args
        # L'errore tracciato dovrebbe contenere il messaggio generico di APIConnectionError
        self.assertIn(expected_openai_connection_error_message, langfuse_kwargs['error'])
        # E potrebbe anche contenere il messaggio originale di httpx, ma ci concentriamo su quello di OpenAI
        # self.assertIn(original_httpx_message, langfuse_kwargs['error'])

    def test_describe_image_data_not_implemented(self):
        """Testa che describe_image_data restituisca il messaggio di non implementato."""
        describer = ImageDescriber(api_key=self.mock_api_key) # Non serve mockare OpenAI qui se non lo usa
        
        with self.assertLogs(logger='src.image_describer', level='WARNING') as cm:
            result = describer.describe_image_data(b"imagedata")
        
        self.assertEqual(result, "Funzionalità di descrizione da dati immagine non ancora implementata.")
        self.assertIn("Funzionalità di descrizione da dati immagine non ancora implementata.", cm.output[0])

    @patch.object(ImageDescriber, '__init__', lambda self, api_key=None, langfuse_tracker=None: None) # Evita __init__ reale
    def test_describe_image_data_client_not_initialized(self):
        """Testa describe_image_data quando il client non è inizializzato."""
        describer = ImageDescriber()
        describer.client = None # Simula client non inizializzato
        describer.langfuse_tracker = None

        result = describer.describe_image_data(b"imagedata")
        self.assertEqual(result, "Errore: Client OpenAI non configurato.")


if __name__ == '__main__':
    unittest.main() 