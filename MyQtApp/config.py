import sys
import os

APP_VERSION = "1.1.0"

# Rutas absolutas del proyecto
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = sys._MEIPASS
    EXE_DIR = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    EXE_DIR = BUNDLE_DIR

PROJECT_ROOT = BUNDLE_DIR

# Carpetas de assets estáticos (empaquetados con el exe)
ASSETS_DIR = os.path.join(BUNDLE_DIR, "assets")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
STYLE_FILE = os.path.join(ASSETS_DIR, "style.qss")
STYLE_DARK_FILE = os.path.join(ASSETS_DIR, "style_dark.qss")

import json

# Carpeta de imágenes descargadas y Base de datos (en la ruta del ejecutable)
IMAGES_DIR = os.path.join(EXE_DIR, "assets", "images")
IMAGES_HD_DIR = os.path.join(EXE_DIR, "assets", "images_hd")
IMAGES_WEBP_DIR = os.path.join(EXE_DIR, "assets", "images_webp")
os.makedirs(IMAGES_HD_DIR, exist_ok=True)
os.makedirs(IMAGES_WEBP_DIR, exist_ok=True)

TCGDEX_LANG_MAP = {
    "es": "es",
    "en": "en",
    "ja": "ja",
    "fr": "fr",
    "pt": "pt",
    "zh": "zh-tw"
}

LANG_NORMALIZE_MAP = {
    "es": "es", "español": "es", "espanol": "es", "spanish": "es",
    "en": "en", "inglés": "en", "ingles": "en", "english": "en",
    "ja": "ja", "japonés": "ja", "japones": "ja", "japanese": "ja",
    "fr": "fr", "francés": "fr", "frances": "fr", "french": "fr",
    "pt": "pt", "portugués": "pt", "portugues": "pt", "portuguese": "pt",
    "zh": "zh", "chino": "zh", "chinese": "zh", "zh-tw": "zh", "tw": "zh"
}

def normalize_lang_code(lang: str) -> str:
    if not lang:
        return "es"
    clean = str(lang).strip().lower()
    return LANG_NORMALIZE_MAP.get(clean, clean[:2] if len(clean) >= 2 else "es")

VARIANT_COLOR_MAP = {
    "Holo": {"name": "Holográfica", "color": "#a855f7", "icon": "🟣", "border": "#c084fc"},
    "Reverse": {"name": "Reverse Holo", "color": "#22c55e", "icon": "🟢", "border": "#4ade80"},
    "1st Edition": {"name": "1ª Edición", "color": "#eab308", "icon": "🟡", "border": "#fde047"},
    "Proxy": {"name": "Proxy / Copia", "color": "#f97316", "icon": "🟠", "border": "#fb923c"},
    "Normal": {"name": "Normal / Base", "color": "#0284c7", "icon": "🔵", "border": "#38bdf8"},
}


DB_PATH = os.path.join(EXE_DIR, "PokeDatabase.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Configuración y Persistencia
SETTINGS_FILE = os.path.join(EXE_DIR, "assets", "settings.json")

DEFAULT_SETTINGS = {
    "volumen_musica": 20,
    "volumen_sonido": 80,
    "pista_musica": 1,
    "animaciones": True,
    "tema_oscuro": False,
    "tamano_fuente": 14,
    "idioma": "Español",
    "tamano_cartas": "Normal"
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {**DEFAULT_SETTINGS, **data}
    except Exception:
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Error guardando settings: {e}")

def apply_global_style(app):
    import re
    settings = load_settings()
    es_oscuro = settings.get("tema_oscuro", False)
    font_size = settings.get("tamano_fuente", 14)
    
    path = STYLE_DARK_FILE if es_oscuro else STYLE_FILE
    if not os.path.exists(path):
        return
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        scale = font_size / 14.0
        
        def repl(match):
            orig_val = int(match.group(1))
            new_val = max(6, int(orig_val * scale))
            return f"font-size: {new_val}px;"
            
        new_content = re.sub(r"font-size\s*:\s*(\d+)px\s*;", repl, content)
        app.setStyleSheet(new_content)
    except Exception as e:
        print(f"Error applying stylesheet: {e}")

def get_music_track_path(pista: int) -> str:
    """Retorna la ruta completa al archivo de música de la pista dada, probando extensiones mp3, m4a, wav, ogg."""
    for ext in [".mp3", ".m4a", ".wav", ".ogg"]:
        filename = f"musica_fondo_{pista}{ext}"
        path = os.path.join(SOUNDS_DIR, filename)
        if os.path.exists(path):
            return path
    return os.path.join(SOUNDS_DIR, f"musica_fondo_{pista}.mp3")

def get_available_music_tracks() -> list:
    """Retorna la lista ordenada de números de pista musicales presentes en assets/sounds."""
    tracks = set()
    if os.path.exists(SOUNDS_DIR):
        for fname in os.listdir(SOUNDS_DIR):
            if fname.startswith("musica_fondo_"):
                base = fname.replace("musica_fondo_", "")
                parts = base.split(".")
                if parts[0].isdigit():
                    tracks.add(int(parts[0]))
    return sorted(list(tracks)) if tracks else [1, 2, 3]
