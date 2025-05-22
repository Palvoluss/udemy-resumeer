#!/usr/bin/env python3
"""
API Key Manager: Modulo per la gestione sicura delle chiavi API.

Questo modulo fornisce una classe per caricare, verificare e gestire in modo sicuro
le chiavi API, con supporto per diverse fonti (file .env, variabili d'ambiente).
"""

import os
import logging
import hashlib
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

class APIKeyManager:
    """
    Classe per la gestione sicura delle chiavi API.
    
    Gestisce il caricamento di chiavi API da file .env o variabili d'ambiente,
    e fornisce funzionalità per l'hashing delle chiavi per il logging sicuro.
    """
    
    def __init__(self, key_name: str = "OPENAI_API_KEY"):
        """
        Inizializza il gestore delle chiavi API.
        
        Args:
            key_name (str, optional): Nome della chiave API da caricare.
                Default a "OPENAI_API_KEY".
        """
        self.key_name = key_name
        self.api_key: Optional[str] = None
        
        # Carica le variabili d'ambiente dal file .env se esiste
        dotenv_path = Path('.env')
        if dotenv_path.exists():
            load_dotenv(dotenv_path=dotenv_path)
            logging.debug(f"Caricato file .env da {dotenv_path.absolute()}")
    
    def get_key(self) -> str:
        """
        Ottiene la chiave API.
        
        Cerca la chiave API prima nel file .env (già caricato nel costruttore),
        poi nelle variabili d'ambiente del sistema.
        
        Returns:
            str: La chiave API.
            
        Raises:
            ValueError: Se la chiave API non è stata trovata.
        """
        # Cerca la chiave nelle variabili d'ambiente
        api_key = os.getenv(self.key_name)
        
        if not api_key:
            raise ValueError(
                f"Chiave API '{self.key_name}' non trovata. "
                f"Assicurati di averla definita nel file .env o nelle variabili d'ambiente del sistema."
            )
        
        self.api_key = api_key
        
        # Log con hash per verificare senza esporre la chiave completa
        logging.info(f"Chiave API '{self.key_name}' caricata con successo. "
                    f"Hash: {self._hash_key(api_key)}")
        
        return api_key
    
    def _hash_key(self, key: str) -> str:
        """
        Crea un hash della chiave per scopi di logging sicuro.
        
        Args:
            key (str): La chiave API da hashare.
            
        Returns:
            str: Un hash SHA-256 troncato della chiave (primi 8 caratteri).
        """
        # Crea un hash SHA-256 della chiave e restituisce i primi 8 caratteri
        hash_obj = hashlib.sha256(key.encode())
        return hash_obj.hexdigest()[:8] 