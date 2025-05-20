#!/usr/bin/env python3
"""
Resume Generator: Tool per riassumere corsi strutturati in cartelle.

Questo script analizza una struttura di cartelle del corso, estrae testo da file VTT e PDF,
e genera riassunti intelligenti utilizzando l'API di OpenAI.
"""

import os
import re
import shutil
import glob
from pathlib import Path
import subprocess
import logging
from typing import List, Dict, Tuple
import requests
import json
import time
import argparse
import dotenv
import secrets
import hashlib
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from collections import Counter
import math
import PyPDF2

# Carica le variabili d'ambiente dal file .env se presente
dotenv.load_dotenv()

# Configurazione del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class APIKeyManager:
    """
    Classe per gestire le chiavi API in modo sicuro.
    """
    def __init__(self, key_name: str = "OPENAI_API_KEY"):
        self.key_name = key_name
        self.key_hash = None
        self.api_key = None
        
    def get_key(self) -> str:
        """
        Ottiene la chiave API da varie fonti in modo sicuro.
        Cerca prima nelle variabili d'ambiente, poi nel file .env.
        
        Returns:
            La chiave API se trovata, altrimenti None
        """
        # Ottieni la chiave API dall'ambiente
        api_key = os.environ.get(self.key_name)
        
        # Se la chiave non è trovata, cerca nel file .env
        if not api_key and os.path.exists(".env"):
            try:
                with open(".env", "r") as f:
                    for line in f:
                        if line.startswith(f"{self.key_name}="):
                            api_key = line.strip().split("=", 1)[1].strip()
                            # Rimuovi eventuali virgolette
                            api_key = api_key.strip('"\'')
                            break
            except Exception as e:
                logger.error(f"Errore nella lettura del file .env: {e}")
        
        if api_key:
            # Crea un hash della chiave per logging sicuro
            self.key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:8]
            self.api_key = api_key
            logger.info(f"Chiave API {self.key_name} trovata (hash: {self.key_hash})")
            return api_key
        else:
            logger.warning(f"Chiave API {self.key_name} non trovata")
            return None

class SimpleResumeGenerator:
    def __init__(self, course_dir: str, output_dir: str = None, lesson: int = None, lesson_range: str = None, use_ai: bool = True, api_key: str = None):
        """
        Inizializza il generatore di riassunti.
        
        Args:
            course_dir: La directory del corso Udemy scaricato
            output_dir: La directory di output (default: resume_[nome_corso])
            lesson: Numero della singola lezione da processare
            lesson_range: Range di lezioni da processare (es. "1-5" o "1,3,5")
            use_ai: Se True, usa OpenAI per generare riassunti
            api_key: Chiave API di OpenAI (opzionale)
        """
        self.course_dir = Path(course_dir)
        self.course_name = self.course_dir.name
        self.lesson = lesson
        self.lesson_range = lesson_range
        self.use_ai = use_ai
        
        # Gestione della chiave API
        self.key_manager = APIKeyManager("OPENAI_API_KEY")
        self.api_key = api_key or self.key_manager.get_key()
        
        if output_dir is None:
            self.output_dir = Path(f"resume_{self.course_name}")
        else:
            self.output_dir = Path(output_dir)
            
        # Assicuriamoci che la directory di output esista
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Scarica le risorse NLTK necessarie
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
            
        self.stop_words = set(stopwords.words('italian'))
        
        logger.info(f"Corso: {self.course_name}")
        logger.info(f"Directory di output: {self.output_dir}")
        logger.info(f"Utilizzo riassunto AI: {self.use_ai}")

    def extract_text_from_vtt(self, vtt_file: Path) -> str:
        """
        Estrae il testo da un file VTT rimuovendo i timestamp e altri metadati.
        
        Args:
            vtt_file: Percorso del file VTT
            
        Returns:
            Il testo estratto dal file VTT
        """
        try:
            with open(vtt_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Rimuovi l'intestazione WEBVTT
            content = re.sub(r'^WEBVTT\n\n', '', content)
            
            # Rimuovi i timestamp
            content = re.sub(r'\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}\.\d{3}\n', '', content)
            
            # Elimina righe vuote multiple
            content = re.sub(r'\n\n+', '\n\n', content)
            
            return content.strip()
        except Exception as e:
            logger.error(f"Errore nell'estrazione del testo da {vtt_file}: {e}")
            return ""

    def extract_text_from_pdf(self, pdf_file: Path) -> str:
        """
        Estrae il testo da un file PDF.
        
        Args:
            pdf_file: Percorso del file PDF
            
        Returns:
            Il testo estratto dal PDF
        """
        try:
            text = ""
            with open(pdf_file, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Errore nell'estrazione del testo da {pdf_file}: {e}")
            return ""

    def calculate_sentence_scores(self, sentences: List[str]) -> Dict[str, float]:
        """
        Calcola il punteggio per ogni frase basato sulla frequenza delle parole.
        
        Args:
            sentences: Lista di frasi
            
        Returns:
            Dizionario con frasi e relativi punteggi
        """
        # Calcola la frequenza delle parole
        word_frequencies = Counter()
        for sentence in sentences:
            words = [word.lower() for word in sentence.split() if word.lower() not in self.stop_words]
            word_frequencies.update(words)
            
        # Normalizza le frequenze
        max_frequency = max(word_frequencies.values()) if word_frequencies else 1
        for word in word_frequencies:
            word_frequencies[word] = word_frequencies[word] / max_frequency
            
        # Calcola il punteggio per ogni frase
        sentence_scores = {}
        for sentence in sentences:
            words = [word.lower() for word in sentence.split() if word.lower() not in self.stop_words]
            if words:
                score = sum(word_frequencies[word] for word in words) / len(words)
                sentence_scores[sentence] = score
                
        return sentence_scores

    def summarize_with_openai(self, text: str, max_tokens: int = 500) -> str:
        """
        Utilizza l'API di OpenAI per generare un riassunto.
        Gestisce testi lunghi dividendoli in chunk.
        
        Args:
            text: Testo da riassumere
            max_tokens: Lunghezza massima del riassunto in token
            
        Returns:
            Testo riassunto
        """
        if not self.api_key:
            logger.warning("Chiave API OpenAI non trovata. Utilizzo il metodo di riassunto semplice.")
            return self.summarize_text_simple(text)
            
        try:
            # Stima approssimativa dei token (4 caratteri = ~1 token)
            estimated_tokens = len(text) // 4
            
            # Se il testo è troppo lungo, dividi in chunk
            if estimated_tokens > 12000:  # Limite sicuro per GPT-3.5
                logger.info(f"Testo troppo lungo (circa {estimated_tokens} token), suddivisione in chunk...")
                return self.process_long_text(text)
                
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "Sei un assistente esperto nel campo del digital marketing. Il tuo compito è riassumere il contenuto delle lezioni di un corso in modo chiaro e conciso, mantenendo tutti i concetti chiave."},
                    {"role": "user", "content": f"Riassumi il seguente testo di una lezione di un corso di web marketing, mantenendo tutti i concetti chiave e le informazioni importanti: \n\n{text}"}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.5
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"Errore nella chiamata API OpenAI: {response.status_code} - {response.text}")
                return self.summarize_text_simple(text)
                
        except Exception as e:
            logger.error(f"Errore durante il riassunto con OpenAI: {e}")
            return self.summarize_text_simple(text)

    def process_long_text(self, text: str) -> str:
        """
        Elabora testi lunghi suddividendoli in chunk e riassumendo ogni parte.
        
        Args:
            text: Testo lungo da elaborare
            
        Returns:
            Riassunto combinato
        """
        try:
            # Dividi il testo in paragrafi
            paragraphs = text.split("\n\n")
            
            # Crea chunk di dimensioni gestibili
            chunks = []
            current_chunk = []
            current_length = 0
            
            for para in paragraphs:
                para_length = len(para)
                
                # Se il paragrafo è già troppo grande da solo, suddividilo
                if para_length > 4000:
                    # Dividi il paragrafo in frasi
                    try:
                        sentences = [s + "." for s in para.split(".") if s.strip()]
                    except Exception:
                        # Fallback: dividi il paragrafo in porzioni di testo
                        sentences = [para[i:i+1000] for i in range(0, len(para), 1000)]
                    
                    for sentence in sentences:
                        if current_length + len(sentence) > 8000:
                            chunks.append("\n\n".join(current_chunk))
                            current_chunk = [sentence]
                            current_length = len(sentence)
                        else:
                            current_chunk.append(sentence)
                            current_length += len(sentence)
                            
                # Altrimenti, gestisci il paragrafo normalmente
                elif current_length + para_length > 8000:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = [para]
                    current_length = para_length
                else:
                    current_chunk.append(para)
                    current_length += para_length
                    
            # Aggiungi l'ultimo chunk se non è vuoto
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                
            logger.info(f"Testo diviso in {len(chunks)} chunk")
            
            # Riassumi ogni chunk
            summaries = []
            for i, chunk in enumerate(chunks):
                logger.info(f"Riassunto del chunk {i+1}/{len(chunks)}")
                if i < len(chunks) - 1:
                    summaries.append(self.summarize_with_openai(chunk, 300))
                else:
                    summaries.append(self.summarize_with_openai(chunk, 400))
                    
            # Combina i riassunti
            combined_summary = "\n\n".join(summaries)
            
            # Se il riassunto combinato è ancora troppo lungo, riassumilo ulteriormente
            if len(combined_summary) > 8000:
                logger.info("Riassunto finale dei chunks...")
                return self.summarize_with_openai(combined_summary, 800)
                
            return combined_summary
            
        except Exception as e:
            logger.error(f"Errore durante l'elaborazione del testo lungo: {e}")
            return self.summarize_text_simple(text)

    def summarize_text_simple(self, text: str, ratio: float = 0.3) -> str:
        """
        Genera un riassunto del testo utilizzando un approccio basato su estrazione.
        
        Args:
            text: Testo da riassumere
            ratio: Rapporto tra lunghezza del riassunto e testo originale
            
        Returns:
            Testo riassunto
        """
        try:
            # Tokenizza il testo in frasi usando metodo semplice per evitare errori con il tokenizer italiano
            sentences = self.simple_sentence_tokenize(text)
            
            if not sentences:
                return ""
                
            # Calcola i punteggi delle frasi
            sentence_scores = self.calculate_sentence_scores(sentences)
            
            # Seleziona le frasi con punteggio più alto
            num_sentences = max(1, int(len(sentences) * ratio))
            summary_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:num_sentences]
            
            # Riordina le frasi nell'ordine originale
            summary_sentences = sorted(summary_sentences, key=lambda x: sentences.index(x[0]))
            
            return " ".join(sentence for sentence, _ in summary_sentences)
        except Exception as e:
            logger.error(f"Errore durante il riassunto semplice: {e}")
            # Fallback estremo: restituisci le prime frasi
            sentences = self.simple_sentence_tokenize(text)
            num_sentences = max(1, int(len(sentences) * ratio))
            return " ".join(sentences[:num_sentences])
    
    def simple_sentence_tokenize(self, text: str) -> List[str]:
        """
        Tokenizzatore di frasi semplice che non dipende da nltk punkt per l'italiano.
        
        Args:
            text: Testo da dividere in frasi
            
        Returns:
            Lista di frasi
        """
        # Dividi il testo in base a caratteri standard di fine frase
        raw_sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Filtra frasi vuote e normalizza
        sentences = [s.strip() for s in raw_sentences if s.strip()]
        
        return sentences

    def summarize_text(self, text: str) -> str:
        """
        Riassume il testo utilizzando il metodo appropriato.
        
        Args:
            text: Testo da riassumere
            
        Returns:
            Testo riassunto
        """
        if self.use_ai and self.api_key:
            return self.summarize_with_openai(text)
        else:
            return self.summarize_text_simple(text)

    def _should_process_lesson(self, lesson_num: int) -> bool:
        """
        Determina se una lezione dovrebbe essere processata in base ai parametri specificati.
        
        Args:
            lesson_num: Numero della lezione
            
        Returns:
            True se la lezione dovrebbe essere processata, False altrimenti
        """
        if self.lesson is not None:
            return lesson_num == self.lesson
            
        if self.lesson_range:
            # Gestisce il formato "1-5"
            if '-' in self.lesson_range:
                start, end = map(int, self.lesson_range.split('-'))
                return start <= lesson_num <= end
            # Gestisce il formato "1,3,5"
            elif ',' in self.lesson_range:
                return lesson_num in map(int, self.lesson_range.split(','))
                
        return True

    def process_chapter(self, chapter_dir: Path) -> Dict:
        """
        Processa un singolo capitolo del corso.
        
        Args:
            chapter_dir: Directory del capitolo
            
        Returns:
            Dizionario con informazioni sul capitolo
        """
        chapter_name = chapter_dir.name
        logger.info(f"Elaborazione capitolo: {chapter_name}")
        
        # Estrai numero e titolo del capitolo
        chapter_match = re.match(r'(\d+)\s*-\s*(.*)', chapter_name)
        if chapter_match:
            chapter_num = chapter_match.group(1).zfill(3)  # Aggiunge zeri iniziali
            chapter_title = chapter_match.group(2).strip()
            formatted_name = f"{chapter_num} - {chapter_title}"
        else:
            formatted_name = chapter_name
        
        # Trova tutti i file VTT e PDF nel capitolo
        vtt_files = list(chapter_dir.glob("**/*.vtt"))
        pdf_files = list(chapter_dir.glob("**/*.pdf"))
        
        if not vtt_files and not pdf_files:
            logger.warning(f"Nessun file VTT o PDF trovato in {chapter_name}")
            return None
            
        # Estrai e combina il testo da tutti i file
        lessons_text = ""
        pdf_texts = []
        pdf_names = []
        
        # Processa i file VTT
        for vtt_file in vtt_files:
            # Estrai il numero della lezione dal nome del file
            lesson_match = re.match(r'(\d+)', vtt_file.stem)
            if lesson_match:
                lesson_num = int(lesson_match.group(1))
                if not self._should_process_lesson(lesson_num):
                    continue
                    
            text = self.extract_text_from_vtt(vtt_file)
            lessons_text += text + "\n\n"
            
        # Processa i file PDF
        for pdf_file in pdf_files:
            text = self.extract_text_from_pdf(pdf_file)
            if text:
                pdf_texts.append(text)
                pdf_names.append(pdf_file.stem)
                
                # Copia il PDF nella directory di output
                try:
                    shutil.copy2(pdf_file, self.output_dir / pdf_file.name)
                except Exception as e:
                    logger.error(f"Errore nella copia del file PDF {pdf_file}: {e}")
            
        if not lessons_text and not pdf_texts:
            logger.warning(f"Nessun testo da processare in {chapter_name}")
            return None
            
        # Genera i riassunti
        chapter_summary = ""
        
        # Riassunto delle lezioni
        if lessons_text:
            lessons_summary = self.summarize_text(lessons_text)
            chapter_summary += "## Riassunto delle Lezioni\n\n"
            chapter_summary += lessons_summary + "\n\n"
            
        # Riassunto dei PDF
        if pdf_texts:
            chapter_summary += "## Materiali PDF\n\n"
            for pdf_text, pdf_name in zip(pdf_texts, pdf_names):
                pdf_summary = self.summarize_text(pdf_text)
                chapter_summary += f"### {pdf_name}\n\n"
                chapter_summary += pdf_summary + "\n\n"
        
        return {
            "name": formatted_name,
            "original_name": chapter_name,
            "summary": chapter_summary,
            "full_text": lessons_text
        }

    def generate_resume(self) -> None:
        """
        Genera i riassunti per tutti i capitoli del corso.
        """
        # Trova tutte le directory dei capitoli
        chapter_dirs = [d for d in self.course_dir.iterdir() if d.is_dir()]
        
        # Processa ogni capitolo
        chapters = []
        for chapter_dir in sorted(chapter_dirs):
            chapter_info = self.process_chapter(chapter_dir)
            if chapter_info:
                chapters.append(chapter_info)
                
                # Crea il file markdown per il capitolo
                chapter_file = self.output_dir / f"{chapter_info['name']}.md"
                with open(chapter_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {chapter_info['name']}\n\n")
                    f.write(chapter_info['summary'])
                    
        # Crea l'indice
        self.create_index(chapters)

    def create_index(self, chapters: List[Dict]) -> None:
        """
        Crea un file indice con i link a tutti i capitoli.
        
        Args:
            chapters: Lista delle informazioni sui capitoli
        """
        index_file = self.output_dir / "README.md"
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(f"# Riassunto del Corso: {self.course_name}\n\n")
            f.write("## Indice dei Capitoli\n\n")
            
            # Ordina i capitoli per numero
            sorted_chapters = sorted(chapters, key=lambda x: x['name'])
            
            for chapter in sorted_chapters:
                f.write(f"- [{chapter['name']}](./{chapter['name']}.md)\n")

def parse_arguments():
    """
    Analizza gli argomenti della riga di comando.
    """
    parser = argparse.ArgumentParser(description='Genera riassunti per un corso Udemy')
    parser.add_argument('course_dir', help='Directory del corso Udemy')
    parser.add_argument('--output-dir', help='Directory di output (opzionale)')
    parser.add_argument('--lesson', type=int, help='Numero della singola lezione da processare')
    parser.add_argument('--range', type=str, help='Range di lezioni da processare (es. "1-5" o "1,3,5")')
    parser.add_argument('--skip-pdf', action='store_true', help='Salta l\'elaborazione dei file PDF')
    parser.add_argument('--no-ai', action='store_true', help='Non utilizzare l\'API di OpenAI per i riassunti')
    parser.add_argument('--api-key', help='Chiave API di OpenAI')
    
    return parser.parse_args()

def main():
    """Funzione principale per orchestrare il processo di generazione dei riassunti."""
    print("Resume Generator: Tool per riassumere corsi strutturati in cartelle")

if __name__ == "__main__":
    main() 