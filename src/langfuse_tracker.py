"""
Modulo per la gestione del tracciamento delle chiamate LLM tramite Langfuse.

Questo modulo fornisce la classe LangfuseTracker per inizializzare, configurare
e utilizzare Langfuse per monitorare le interazioni con i modelli LLM.
"""

import os
import logging
import time
from typing import Optional, Dict, Any
from langfuse import Langfuse


class LangfuseTracker:
    """
    Classe per gestire il tracciamento delle chiamate LLM con Langfuse.
    
    Questa classe si occupa di:
    - Configurare la connessione a Langfuse
    - Creare e gestire le trace per il monitoraggio
    - Registrare input, output, metadati e metriche delle chiamate LLM
    - Gestire sessioni distinte per diversi corsi
    """
    
    def __init__(self):
        """
        Inizializza il tracker Langfuse.
        
        Carica le chiavi API dalle variabili d'ambiente e configura la connessione.
        """
        self.logger = logging.getLogger(__name__)
        self.langfuse = None
        self.current_trace = None
        self.current_session_id = None
        self.current_chapter_span: Optional[Any] = None
        self._initialize_langfuse()
    
    def _initialize_langfuse(self) -> None:
        """
        Inizializza la connessione a Langfuse utilizzando le variabili d'ambiente.
        
        Cerca le chiavi LANGFUSE_SECRET_KEY e LANGFUSE_PUBLIC_KEY nelle variabili
        d'ambiente. Se non le trova, registra un warning e disabilita il tracciamento.
        """
        secret_key = os.getenv('LANGFUSE_SECRET_KEY')
        public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
        host = os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')
        
        if not secret_key or not public_key:
            self.logger.warning(
                "Chiavi Langfuse non trovate nelle variabili d'ambiente. "
                "Impostare LANGFUSE_SECRET_KEY e LANGFUSE_PUBLIC_KEY per abilitare il tracciamento."
            )
            return
        
        try:
            self.langfuse = Langfuse(
                secret_key=secret_key,
                public_key=public_key,
                host=host
            )
            self.logger.info("Langfuse inizializzato correttamente")
        except Exception as e:
            self.logger.error(f"Errore nell'inizializzazione di Langfuse: {str(e)}")
            self.langfuse = None
    
    def is_enabled(self) -> bool:
        """
        Verifica se il tracciamento Langfuse è abilitato.
        
        Returns:
            bool: True se Langfuse è configurato e pronto, False altrimenti
        """
        return self.langfuse is not None
    
    def start_session(self, course_name: str, session_metadata: Optional[Dict[str, Any]] = None, prompt_info: Optional[Dict[str, Any]] = None) -> None:
        """
        Inizia una nuova sessione di tracciamento per un corso specifico.
        
        Args:
            course_name (str): Nome del corso da elaborare
            session_metadata (Optional[Dict]): Metadati aggiuntivi per la sessione
            prompt_info (Optional[Dict]): Informazioni sul prompt utilizzato (es. versione)
        """
        if not self.is_enabled():
            return
        
        self.current_session_id = f"course_{course_name}_{int(time.time())}"
        
        metadata = {
            "course_name": course_name,
            "session_type": "course_processing",
            "timestamp": time.time()
        }
        
        if session_metadata:
            metadata.update(session_metadata)
        
        if prompt_info:
            metadata["prompt_info"] = prompt_info
        
        try:
            self.current_trace = self.langfuse.trace(
                name=f"Course Processing: {course_name}",
                session_id=self.current_session_id,
                metadata=metadata
            )
            self.logger.info(f"Sessione Langfuse iniziata per il corso: {course_name}")
        except Exception as e:
            self.logger.error(f"Errore nell'avvio della sessione Langfuse: {str(e)}")
    
    def track_llm_call(
        self,
        input_text: str,
        output_text: str,
        model: str,
        chapter_name: Optional[str] = None,
        lesson_name: Optional[str] = None,
        content_type: str = "vtt",
        token_usage: Optional[Dict[str, int]] = None,
        latency_ms: Optional[float] = None,
        error: Optional[str] = None,
        prompt_info: Optional[Dict[str, Any]] = None,
        cost_usd: Optional[float] = None
    ) -> None:
        """
        Traccia una chiamata LLM con tutti i metadati rilevanti.
        
        Args:
            input_text (str): Testo di input inviato al modello
            output_text (str): Testo di output ricevuto dal modello
            model (str): Nome del modello utilizzato
            chapter_name (Optional[str]): Nome del capitolo processato
            lesson_name (Optional[str]): Nome della lezione processata
            content_type (str): Tipo di contenuto ("vtt", "pdf", "meta_summary")
            token_usage (Optional[Dict]): Informazioni sui token utilizzati
            latency_ms (Optional[float]): Latenza della chiamata in millisecondi
            error (Optional[str]): Messaggio di errore se la chiamata è fallita
            prompt_info (Optional[Dict]): Informazioni sul prompt utilizzato (es. versione)
            cost_usd (Optional[float]): Costo stimato della chiamata LLM in USD
        """
        if not self.is_enabled() or not self.current_trace:
            return
        
        metadata = {
            "model": model,
            "content_type": content_type,
            "chapter_name": chapter_name,
            "lesson_name": lesson_name,
            "input_length": len(input_text),
            "output_length": len(output_text) if output_text else 0,
            "timestamp": time.time()
        }
        
        if token_usage:
            metadata.update({
                "prompt_tokens": token_usage.get("prompt_tokens", 0),
                "completion_tokens": token_usage.get("completion_tokens", 0),
                "total_tokens": token_usage.get("total_tokens", 0)
            })
        
        if latency_ms:
            metadata["latency_ms"] = latency_ms
        
        if prompt_info:
            metadata["prompt_info"] = prompt_info
            
        if cost_usd is not None:
            metadata["cost_usd"] = cost_usd
        
        try:
            generation_name = f"LLM_Summary_{content_type}"
            if chapter_name:
                generation_name += f"_{chapter_name}"
            if lesson_name:
                generation_name += f"_{lesson_name}"
            
            self.current_trace.generation(
                name=generation_name,
                model=model,
                input=input_text,
                output=output_text if not error else None,
                metadata=metadata,
                level="ERROR" if error else "DEFAULT"
            )
            
            if error:
                self.logger.warning(f"Chiamata LLM fallita tracciata: {error}")
            else:
                self.logger.debug(f"Chiamata LLM tracciata: {generation_name}")
                
        except Exception as e:
            self.logger.error(f"Errore nel tracciamento della chiamata LLM: {str(e)}")
    
    def track_processing_metrics(
        self,
        lessons_processed: int,
        lessons_failed: int,
        total_tokens_used: int,
        estimated_cost: Optional[float] = None,
        total_processing_time_s: Optional[float] = None
    ) -> None:
        """
        Traccia le metriche di elaborazione complessive per una sessione.
        
        Args:
            lessons_processed (int): Numero di lezioni elaborate con successo
            lessons_failed (int): Numero di lezioni che hanno fallito l'elaborazione
            total_tokens_used (int): Totale dei token utilizzati nella sessione
            estimated_cost (Optional[float]): Costo stimato della sessione
            total_processing_time_s (Optional[float]): Tempo totale di elaborazione in secondi
        """
        if not self.is_enabled() or not self.current_trace:
            return
        
        metrics = {
            "lessons_processed": lessons_processed,
            "lessons_failed": lessons_failed,
            "total_lessons": lessons_processed + lessons_failed,
            "success_rate": lessons_processed / (lessons_processed + lessons_failed) if (lessons_processed + lessons_failed) > 0 else 0,
            "total_tokens_used": total_tokens_used
        }
        
        if estimated_cost:
            metrics["estimated_cost_usd"] = estimated_cost
        
        if total_processing_time_s is not None:
            metrics["total_processing_time_s"] = total_processing_time_s
        
        try:
            self.current_trace.score(
                name="processing_metrics",
                value=lessons_processed,
                comment=f"Elaborate {lessons_processed} lezioni su {lessons_processed + lessons_failed}",
                metadata=metrics
            )
            self.logger.info(f"Metriche di elaborazione tracciate: {metrics}")
        except Exception as e:
            self.logger.error(f"Errore nel tracciamento delle metriche: {str(e)}")
    
    def end_session(self) -> None:
        """
        Termina la sessione di tracciamento corrente.
        """
        if not self.is_enabled():
            return
        
        try:
            if self.current_trace:
                if self.current_chapter_span:
                    self.logger.warning(f"Chiusura forzata dello span del capitolo non terminato durante end_session.")
                    try:
                        self.current_chapter_span.end()
                    except Exception as e_span:
                        self.logger.error(f"Errore nella chiusura forzata dello span del capitolo: {e_span}")
                    self.current_chapter_span = None
                self.logger.info(f"Preparazione per terminare la sessione Langfuse: {self.current_session_id}")
            
            self.current_trace = None
            self.current_session_id = None
            self.logger.info(f"Sessione Langfuse marcata come terminata localmente.")
        except Exception as e:
            self.logger.error(f"Errore durante la terminazione locale della sessione Langfuse: {str(e)}")
    
    def flush(self) -> None:
        """
        Forza l'invio di tutti i dati in sospeso a Langfuse.
        """
        if self.langfuse:
            try:
                self.langfuse.flush()
                self.logger.debug("Dati Langfuse inviati")
            except Exception as e:
                self.logger.error(f"Errore nell'invio dei dati Langfuse: {str(e)}")

    def start_chapter_span(self, chapter_name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Inizia uno span per tracciare l'elaborazione di un capitolo.

        Args:
            chapter_name (str): Nome del capitolo.
            metadata (Optional[Dict[str, Any]]): Metadati aggiuntivi per lo span del capitolo.
        """
        if not self.is_enabled() or not self.current_trace:
            self.logger.debug("Langfuse non abilitato o nessuna trace attiva, salto start_chapter_span.")
            return

        if self.current_chapter_span:
            self.logger.warning(f"Tentativo di avviare un nuovo span per il capitolo '{chapter_name}' mentre uno span è già attivo. Chiudo il precedente.")
            try:
                self.current_chapter_span.end()
            except Exception as e:
                self.logger.error(f"Errore chiudendo lo span del capitolo precedente: {e}")
            self.current_chapter_span = None

        try:
            span_metadata = metadata if metadata else {}
            span_metadata["chapter_name"] = chapter_name
            
            self.current_chapter_span = self.current_trace.span(
                name=f"Chapter Processing: {chapter_name}",
                metadata=span_metadata,
            )
            self.logger.info(f"Span Langfuse avviato per il capitolo: {chapter_name}")
        except Exception as e:
            self.logger.error(f"Errore nell'avvio dello span Langfuse per il capitolo '{chapter_name}': {str(e)}")
            self.current_chapter_span = None

    def end_chapter_span(self, output: Optional[Dict[str, Any]] = None, status: str = "OK") -> None:
        """
        Termina lo span corrente del capitolo.

        Args:
            output (Optional[Dict[str, Any]]): Output o metriche aggregate per lo span del capitolo.
            status (str): Stato finale dello span del capitolo (es. "OK", "ERROR").
        """
        if not self.current_chapter_span:
            self.logger.debug("Nessuno span capitolo attivo da terminare.")
            return

        try:
            update_args = {}
            if output:
                update_args["output"] = output
            if status == "ERROR":
                update_args["level"] = "ERROR"
                update_args["status_message"] = output.get("error_message", "Errore durante l'elaborazione del capitolo") if output else "Errore sconosciuto"

            self.current_chapter_span.end(**update_args)
            self.logger.info(f"Span Langfuse terminato per il capitolo. Output: {output}")
        except Exception as e:
            self.logger.error(f"Errore nella terminazione dello span Langfuse per il capitolo: {str(e)}")
        finally:
            self.current_chapter_span = None 