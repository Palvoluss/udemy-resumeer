class PromptManager:
    """
    Gestisce e fornisce i template dei prompt per la generazione dei riassunti.
    """

    # Al momento, questo è l'unico prompt, ma la struttura è pronta per aggiungerne altri.
    LESSON_PRACTICAL_THEORETICAL_FACE_TO_FACE = """Sei un assistente AI specializzato nel riassumere trascrizioni di lezioni.
La lezione che stai per analizzare è di tipo "pratico teorica faccia a faccia".
Questo significa che il contenuto potrebbe includere spiegazioni concettuali, seguite da esempi pratici, dimostrazioni o discussioni interattive.
Il tuo obiettivo è creare un riassunto chiaro, conciso e ben strutturato che catturi:
1.  I principali concetti teorici presentati.
2.  Gli esempi pratici o le dimostrazioni chiave e cosa illustrano.
3.  Eventuali conclusioni o punti salienti della lezione.
Mantieni un tono formale ed educativo. Evita informazioni superflue o dettagli troppo specifici che non sono cruciali per la comprensione generale.
Organizza il riassunto in modo logico, usando elenchi puntati o numerati se appropriato per migliorare la leggibilità.
Assicurati di estrarre e riformulare le informazioni essenziali dalla trascrizione fornita. Non aggiungere informazioni non presenti nel testo.

Trascrizione della lezione:
---
{lesson_transcript}
---

Fornisci il riassunto:
"""

    def get_lesson_prompt(self, lesson_type: str = "practical_theoretical_face_to_face") -> str:
        """
        Restituisce il template del prompt per un dato tipo di lezione.

        Args:
            lesson_type: Il tipo di lezione per cui ottenere il prompt. 
                         Attualmente supporta solo "practical_theoretical_face_to_face".

        Returns:
            Il template del prompt come stringa.
            
        Raises:
            ValueError: Se il tipo di lezione non è supportato.
        """
        if lesson_type == "practical_theoretical_face_to_face":
            return self.LESSON_PRACTICAL_THEORETICAL_FACE_TO_FACE
        else:
            # In futuro, si potranno aggiungere altri tipi di prompt qui
            raise ValueError(f"Tipo di lezione non supportato: {lesson_type}")

    def format_prompt(self, prompt_template: str, **kwargs) -> str:
        """
        Formatta un template di prompt con i valori forniti.

        Args:
            prompt_template: La stringa del template del prompt.
            **kwargs: Le coppie chiave-valore da sostituire nel template.

        Returns:
            Il prompt formattato.
        """
        return prompt_template.format(**kwargs)

if __name__ == '__main__':
    # Esempio di utilizzo (per testare rapidamente)
    manager = PromptManager()
    
    # Ottenere il prompt per una lezione
    lesson_prompt_template = manager.get_lesson_prompt()
    print("--- Template del Prompt per Lezione ---")
    print(lesson_prompt_template)
    print("\n-------------------------------------\n")

    # Formattare il prompt con una trascrizione di esempio
    example_transcript = "Questa è una trascrizione di esempio della lezione. Si parla di Python e AI."
    formatted_prompt = manager.format_prompt(lesson_prompt_template, lesson_transcript=example_transcript)
    print("--- Prompt Formattato ---")
    print(formatted_prompt)
    print("\n--------------------------\n")

    # Esempio di gestione di un tipo di lezione non supportato
    try:
        manager.get_lesson_prompt("tipo_sconosciuto")
    except ValueError as e:
        print(f"Errore atteso: {e}") 