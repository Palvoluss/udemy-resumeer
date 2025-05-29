from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def extract_text_and_images_from_html(html_content: str) -> tuple[str, list[dict[str, str]]]:
    """Estrae testo pulito e informazioni sulle immagini da contenuto HTML.

    Args:
        html_content: Stringa contenente l'HTML da processare.

    Returns:
        Una tupla contenente:
            - Il testo estratto dall'HTML, con elementi non rilevanti rimossi.
            - Una lista di dizionari, ognuno rappresentante un'immagine 
              (con chiavi 'src' e 'alt').
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Rimuove script, style, nav, footer, header (elementi comuni non di contenuto)
    for element_type in ['script', 'style', 'nav', 'footer', 'header', 'aside']:
        for element in soup.find_all(element_type):
            element.decompose()

    # Estrae tutto il testo rimanente
    text_parts = [text for text in soup.stripped_strings]
    extracted_text = "\n".join(text_parts)

    images = []
    for img_tag in soup.find_all('img'):
        src = img_tag.get('src')
        alt = img_tag.get('alt', '') # Default a stringa vuota se alt non presente
        if src:
            images.append({'src': src, 'alt': alt})
            logger.info(f"Immagine trovata: src='{src}', alt='{alt}'")
        else:
            logger.warning(f"Trovato tag img senza attributo src: {img_tag}")

    return extracted_text, images

# Esempio di utilizzo (può essere rimosso o messo sotto if __name__ == '__main__'):
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    sample_html_content = """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <header><h1>Test Header</h1></header>
            <nav><a href="#">Home</a></nav>
            <p>Questo è il primo paragrafo di testo.</p>
            <img src="image1.jpg" alt="Descrizione immagine 1">
            <p>Questo è un altro paragrafo con un'altra immagine.</p>
            <img src="/path/to/image2.png" alt="Un gatto carino">
            <img src="data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==" alt="Pixel trasparente">
            <img alt="Immagine senza src">
            <script>console.log('questo non si vede')</script>
            <footer>Copyright 2024</footer>
        </body>
    </html>
    """
    text, image_info = extract_text_and_images_from_html(sample_html_content)
    print("--- Testo Estratto ---")
    print(text)
    print("\n--- Immagini Trovate ---")
    for img in image_info:
        print(img) 