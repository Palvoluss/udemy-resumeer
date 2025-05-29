import logging
# import openai # Rimosso import diretto del modulo, useremo OpenAI client
from openai import OpenAI, APIError # AGGIUNTO OpenAI e APIError
from typing import Optional, Dict, Any # Aggiunto Any per LangfuseTracker
import os
import time

# Assumiamo che LangfuseTracker sia importabile se si trova nello stesso livello o in PYTHONPATH
# from ..langfuse_tracker import LangfuseTracker # Esempio se fosse in un modulo genitore
# Per ora, ci aspettiamo che LangfuseTracker sia un tipo noto o usiamo Any

logger = logging.getLogger(__name__)

class ImageDescriber:
    def __init__(self, api_key: Optional[str] = None, langfuse_tracker: Optional[Any] = None): # Aggiunto langfuse_tracker
        """Inizializza ImageDescriber.

        Args:
            api_key: La chiave API di OpenAI. Se non fornita, si assume che 
                     la variabile d'ambiente OPENAI_API_KEY sia impostata.
            langfuse_tracker: Istanza opzionale di LangfuseTracker.
        """
        self.langfuse_tracker = langfuse_tracker # Memorizza il tracker
        try:
            if api_key:
                self.client = OpenAI(api_key=api_key)
            else:
                self.client = OpenAI() # Si affiderà a OPENAI_API_KEY variabile d'ambiente
            logger.info("ImageDescriber inizializzato con client OpenAI.")
        except Exception as e:
            logger.error(f"Errore durante l'inizializzazione del client OpenAI in ImageDescriber: {e}")
            self.client = None # Segnala che il client non è utilizzabile

    def describe_image_url(self, image_url: str, detail: str = "high", 
                           # Parametri aggiuntivi per il tracciamento Langfuse
                           chapter_name: Optional[str] = None, 
                           lesson_name: Optional[str] = None,
                           original_alt: Optional[str] = None) -> str:
        """Genera una descrizione per un'immagine fornita tramite URL.
        Traccia la chiamata con Langfuse se un tracker è fornito.

        Args:
            image_url: L'URL dell'immagine da descrivere.
            detail: Il livello di dettaglio per la descrizione ("low", "high", "auto").
                    "low" usa meno token, "high" ne usa di più per dettagli più fini.
            chapter_name: Il nome del capitolo associato alla descrizione.
            lesson_name: Il nome dell'attività associata alla descrizione.
            original_alt: Il testo alternativo originale dell'immagine.

        Returns:
            Una stringa contenente la descrizione dell'immagine, o una stringa di errore.
        """
        logger.info(f"Richiesta descrizione per l'URL: {image_url} con dettaglio: {detail}")
        # TODO: Implementare la logica per scaricare l'immagine se l'URL è remoto
        #       e passarla al modello di visione, o passare direttamente l'URL se supportato.

        # Esempio di chiamata API (da adattare per GPT-4V o altro modello multimodale)
        # Questa è una struttura Platzhalter e va sostituita con la chiamata API corretta
        # per i modelli di visione di OpenAI (GPT-4 con Vision).

        if not self.client:
            logger.error("Client OpenAI non inizializzato correttamente in ImageDescriber.")
            return "Errore: Client OpenAI non configurato."

        # Definisci il prompt e i messaggi per l'API e per il tracciamento
        # Potremmo voler rendere il prompt testuale più configurabile in futuro
        prompt_text_for_llm = "Descrivi questa immagine nel dettaglio."
        messages_for_llm = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text_for_llm},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url,
                            "detail": detail
                        },
                    },
                ],
            }
        ]
        
        # Input per Langfuse: una combinazione del prompt testuale e dell'URL dell'immagine
        # o potremmo serializzare `messages_for_llm` se preferito e se Langfuse lo gestisce bene.
        langfuse_input = f"{prompt_text_for_llm}\nImage URL: {image_url}"
        langfuse_metadata_prompt = {
            "image_url": image_url,
            "image_detail_level": detail,
            "original_alt_text": original_alt or "N/A"
        }

        start_time = time.time() # Per la latenza
        description = f"Errore sconosciuto nella descrizione dell'immagine: {image_url}" # Default in caso di fallimento imprevisto
        token_usage: Optional[Dict[str, int]] = None
        api_error: Optional[str] = None
        model_used = "gpt-4o" # Modello che stiamo usando

        try:
            response = self.client.chat.completions.create(
                model=model_used,
                messages=messages_for_llm, # type: ignore
                max_tokens=700 
            )
            description = response.choices[0].message.content
            if response.usage:
                token_usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            logger.info(f"Descrizione generata per {image_url}")
        
        except APIError as e:
            logger.error(f"Errore API OpenAI durante la descrizione dell'immagine {image_url}: {e}")
            description = f"Errore API OpenAI: {e}"
            api_error = str(e)
        except Exception as e:
            logger.error(f"Errore imprevisto durante la descrizione dell'immagine {image_url}: {str(e)}")
            description = f"Errore imprevisto: {str(e)}"
            api_error = str(e)
        
        latency_ms = (time.time() - start_time) * 1000

        if self.langfuse_tracker and hasattr(self.langfuse_tracker, 'track_llm_call'):
            self.langfuse_tracker.track_llm_call(
                input_text=langfuse_input, # O una rappresentazione dei messaggi
                output_text=description,
                model=model_used,
                chapter_name=chapter_name, # Passato come argomento
                lesson_name=lesson_name,   # Passato come argomento
                content_type="image_description", # Tipo specifico
                token_usage=token_usage,
                latency_ms=latency_ms,
                error=api_error,
                prompt_info=langfuse_metadata_prompt # Informazioni specifiche dell'immagine
            )
            
        return description

    def describe_image_data(self, image_data: bytes, detail: str = "high",
                            # Parametri aggiuntivi per il tracciamento Langfuse
                            chapter_name: Optional[str] = None, 
                            lesson_name: Optional[str] = None,
                            original_alt: Optional[str] = None) -> str:
        """Genera una descrizione per dati di immagine (bytes).
        Traccia la chiamata con Langfuse se un tracker è fornito.

        Args:
            image_data: I dati binari dell'immagine.
            detail: Il livello di dettaglio per la descrizione ("low", "high", "auto").
            chapter_name: Il nome del capitolo associato alla descrizione.
            lesson_name: Il nome dell'attività associata alla descrizione.
            original_alt: Il testo alternativo originale dell'immagine.

        Returns:
            Una stringa contenente la descrizione dell'immagine, o una stringa di errore.
        """
        logger.info(f"Richiesta descrizione per dati immagine (lunghezza: {len(image_data)} bytes) con dettaglio: {detail}")
        # TODO: Implementare la logica per inviare i dati dell'immagine (es. base64 encoded)
        #       al modello di visione.
        # Questo metodo sarà utile se le immagini sono locali o già scaricate.
        # La chiamata API sarà simile a describe_image_url ma con i dati dell'immagine
        # probabilmente codificati in base64.
        if not self.client:
            logger.error("Client OpenAI non inizializzato correttamente per describe_image_data.")
            return "Errore: Client OpenAI non configurato."

        # TODO: Implementare la logica per inviare i dati dell'immagine (es. base64 encoded)
        #       al modello di visione. La chiamata API sarà simile a describe_image_url
        #       ma con i dati dell'immagine probabilmente codificati in base64.
        #       Esempio di come potrebbe essere il payload per image_url con dati base64:
        #       {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_encoded_data}"}} 
        logger.warning("Funzionalità di descrizione da dati immagine non ancora implementata.")
        
        # Esempio di tracciamento (da adattare quando la funzione sarà implementata):
        # if self.langfuse_tracker and hasattr(self.langfuse_tracker, 'track_llm_call'):
        #     self.langfuse_tracker.track_llm_call(
        #         input_text="Richiesta descrizione dati immagine (base64)", 
        #         output_text="Descrizione mock per dati immagine", 
        #         model="gpt-4o", 
        #         chapter_name=chapter_name, 
        #         lesson_name=lesson_name, 
        #         content_type="image_description_data", 
        #         token_usage=None, 
        #         latency_ms=0,
        #         error=None, 
        #         prompt_info={"original_alt_text": original_alt or "N/A", "data_length": len(image_data)}
        #     )
        return "Funzionalità di descrizione da dati immagine non ancora implementata."

# Esempio di utilizzo (da adattare e testare quando le funzionalità saranno complete)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # Configura la tua chiave API OpenAI qui o tramite variabili d'ambiente
    # os.environ["OPENAI_API_KEY"] = "la_tua_chiave_api"
    
    # È necessario avere una chiave API valida e un modello come gpt-4-vision-preview abilitato.
    # Per testare realmente, decommenta e imposta la chiave.
    # api_key_manager = APIKeyManager() # Assumendo che esista e sia configurato
    # api_key = api_key_manager.get_api_key("OPENAI_API_KEY")
    # if not api_key:
    #     logger.error("Chiave API OpenAI non trovata. Impostare la variabile d'ambiente OPENAI_API_KEY.")
    # else:
    #     describer = ImageDescriber(api_key=api_key)
    #     image_url_test = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg" # URL di esempio
    #     # Nota: l'URL di test deve essere accessibile pubblicamente.
    #     description = describer.describe_image_url(image_url_test, detail="low")
    #     print(f"Descrizione per {image_url_test}: {description}")

    logger.warning("L'esempio di ImageDescriber non verrà eseguito attivamente senza una chiave API configurata e il modello GPT-4V.")
    logger.warning("Le chiamate API reali sono commentate per evitare costi/errori imprevisti.")

    # Importa LangfuseTracker per il test if __name__ == '__main__'
    # Questo potrebbe richiedere di aggiustare il path se i file sono in sottocartelle diverse
    try:
        from src.langfuse_tracker import LangfuseTracker 
        langfuse_enabled_for_test = True
    except ImportError:
        LangfuseTracker = None # type: ignore
        langfuse_enabled_for_test = False
        logger.warning("LangfuseTracker non trovato, tracciamento disabilitato per l'esempio.")

    # Inizializza il tracker per il test (se disponibile)
    tracker_instance = None
    if langfuse_enabled_for_test and LangfuseTracker and os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY"):
        tracker_instance = LangfuseTracker()
        # Potrebbe essere necessario avviare una sessione/trace se track_llm_call lo richiede
        if hasattr(tracker_instance, 'start_session'):
            tracker_instance.start_session(course_name="ImageDescriberTest")
        logger.info("LangfuseTracker inizializzato per il test.")

    describer = ImageDescriber(langfuse_tracker=tracker_instance)

    if describer.client: # Controlla se il client è stato inizializzato
        image_url_test = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
        description = describer.describe_image_url(
            image_url_test, 
            detail="low", 
            chapter_name="TestChapter", 
            lesson_name="TestLesson", 
            original_alt="Boardwalk example"
        )
        print(f"Descrizione per {image_url_test}")
        
        # Esempio (non funzionante) per describe_image_data
        # try:
        #     with open("path_to_your_test_image.jpg", "rb") as img_file:
        #         test_image_data = img_file.read()
        #     data_description = describer.describe_image_data(test_image_data)
        #     print(f"Descrizione per dati immagine: {data_description}")
        # except FileNotFoundError:
        #     logger.warning("File immagine di test non trovato per describe_image_data.")
    else:
        logger.error("Impossibile eseguire l'esempio: client ImageDescriber non inizializzato.")

    logger.warning("L'esempio di ImageDescriber potrebbe non funzionare completamente senza una chiave API valida e il modello GPT-4V abilitato.")
    if tracker_instance and hasattr(tracker_instance, 'flush'):
        tracker_instance.flush()
        logger.info("LangfuseTracker dati inviati (flush). ") 