#!/usr/bin/env python3
"""
Test per il modulo api_key_manager.py.

Questo script esegue test sulla classe APIKeyManager per verificare
il corretto caricamento delle chiavi API da diverse fonti.
"""

import os
import unittest
import tempfile
from pathlib import Path
from api_key_manager import APIKeyManager

class TestAPIKeyManager(unittest.TestCase):
    """Classe di test per APIKeyManager."""
    
    def setUp(self):
        """Configurazione comune per tutti i test."""
        # Salva lo stato originale delle variabili d'ambiente
        self.original_env = os.environ.copy()
        
        # Ripulisci la variabile d'ambiente per i test
        if "TEST_API_KEY" in os.environ:
            del os.environ["TEST_API_KEY"]
            
    def tearDown(self):
        """Pulizia dopo ogni test."""
        # Ripristina lo stato originale delle variabili d'ambiente
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_missing_key_raises_error(self):
        """Verifica che venga sollevato un errore quando la chiave API è mancante."""
        # Crea un manager con un nome di chiave che sicuramente non esiste
        manager = APIKeyManager(key_name="NON_EXISTENT_KEY")
        
        # Verifica che venga sollevato un ValueError quando si tenta di ottenere la chiave
        with self.assertRaises(ValueError):
            manager.get_key()
    
    def test_key_from_env_variable(self):
        """Verifica che la chiave API venga caricata correttamente dalle variabili d'ambiente."""
        # Imposta una variabile d'ambiente di test
        os.environ["TEST_API_KEY"] = "test_key_from_env"
        
        # Crea un manager che utilizza questa variabile
        manager = APIKeyManager(key_name="TEST_API_KEY")
        
        # Verifica che la chiave venga caricata correttamente
        self.assertEqual(manager.get_key(), "test_key_from_env")
    
    def test_key_from_dotenv_file(self):
        """Verifica che la chiave API venga caricata correttamente dal file .env."""
        # Crea un file .env temporaneo con una chiave API di test
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_env:
            temp_env.write("TEST_API_KEY=test_key_from_dotenv\n")
            dotenv_path = temp_env.name
        
        try:
            # Crea un backup del file .env esistente se presente
            original_dotenv = None
            if Path(".env").exists():
                with open(".env", "r") as f:
                    original_dotenv = f.read()
                os.rename(".env", ".env.backup")
            
            # Copia il file temporaneo come .env
            with open(dotenv_path, "r") as source:
                with open(".env", "w") as dest:
                    dest.write(source.read())
            
            # Crea un manager che utilizzi questa chiave
            manager = APIKeyManager(key_name="TEST_API_KEY")
            
            # Verifica che la chiave venga caricata correttamente
            self.assertEqual(manager.get_key(), "test_key_from_dotenv")
            
        finally:
            # Pulizia: rimuovi il file .env temporaneo e ripristina quello originale se presente
            if Path(".env").exists():
                os.remove(".env")
            
            if Path(".env.backup").exists():
                os.rename(".env.backup", ".env")
            
            # Rimuovi il file temporaneo
            if Path(dotenv_path).exists():
                os.remove(dotenv_path)
    
    def test_env_variable_precedence(self):
        """Verifica che la variabile d'ambiente abbia la precedenza sul file .env."""
        # Crea un file .env temporaneo con una chiave API di test
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_env:
            temp_env.write("TEST_API_KEY=test_key_from_dotenv\n")
            dotenv_path = temp_env.name
        
        try:
            # Crea un backup del file .env esistente se presente
            original_dotenv = None
            if Path(".env").exists():
                with open(".env", "r") as f:
                    original_dotenv = f.read()
                os.rename(".env", ".env.backup")
            
            # Copia il file temporaneo come .env
            with open(dotenv_path, "r") as source:
                with open(".env", "w") as dest:
                    dest.write(source.read())
            
            # Imposta anche una variabile d'ambiente con lo stesso nome ma valore diverso
            os.environ["TEST_API_KEY"] = "test_key_from_env_override"
            
            # Crea un manager che utilizzi questa chiave
            manager = APIKeyManager(key_name="TEST_API_KEY")
            
            # Verifica che venga utilizzata la chiave dalla variabile d'ambiente
            self.assertEqual(manager.get_key(), "test_key_from_env_override")
            
        finally:
            # Pulizia: rimuovi il file .env temporaneo e ripristina quello originale se presente
            if Path(".env").exists():
                os.remove(".env")
            
            if Path(".env.backup").exists():
                os.rename(".env.backup", ".env")
            
            # Rimuovi il file temporaneo
            if Path(dotenv_path).exists():
                os.remove(dotenv_path)
    
    def test_hash_key(self):
        """Verifica che l'hashing della chiave funzioni correttamente."""
        manager = APIKeyManager()
        
        # Verifica che l'hash di una chiave sia sempre lo stesso
        test_key = "test_key_for_hashing"
        hash1 = manager._hash_key(test_key)
        hash2 = manager._hash_key(test_key)
        self.assertEqual(hash1, hash2)
        
        # Verifica che l'hash di chiavi diverse sia diverso
        different_key = "different_test_key"
        different_hash = manager._hash_key(different_key)
        self.assertNotEqual(hash1, different_hash)
        
        # Verifica che l'hash sia troncato a 8 caratteri
        self.assertEqual(len(hash1), 8)

if __name__ == "__main__":
    unittest.main() 