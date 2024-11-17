import os
from google.cloud import translate_v2 as translate
from django.conf import settings


def translate_text(text, target_language='en'):
    """
    Translates text into the target language using Google Cloud Translate API.
    :param text: The text to translate.
    :param target_language: Target language code (e.g., 'en', 'es').
    :return: Translated text.
    """
    # Fetch the API key from settings or environment
    api_key = getattr(settings, 'GOOGLE_TRANSLATE_API_KEY', os.getenv('GOOGLE_TRANSLATE_API_KEY'))
    if not api_key:
        raise ValueError("API key not found in settings or environment variables.")

    # Initialize the translation client
    client = translate.Client(client_options={"api_key": api_key})

    # Translate the text
    result = client.translate(text, target_language=target_language)
    return result['translatedText']