import json
import os

locales_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'locales')
translations = {}

SUPPORTED_LANGUAGES = ['en', 'de', 'es', 'fr', 'it']

def load_locales():
    if not os.path.exists(locales_dir):
        os.makedirs(locales_dir, exist_ok=True)
    
    for lang in SUPPORTED_LANGUAGES:
        file_path = os.path.join(locales_dir, f"{lang}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                translations[lang] = json.load(f)
        else:
            translations[lang] = {}

# Initial load
load_locales()

def t(key: str, lang: str = 'en') -> str:
    """Translate a dot-separated key, e.g. 'home.title'"""
    if lang not in translations:
        lang = 'en'
    
    keys = key.split('.')
    val = translations[lang]
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return key # fallback to key name if not found
    
    return str(val) if not isinstance(val, dict) else key
