import os

APP_VERSION = "1.0"

# Rutas absolutas del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")

STYLE_FILE = os.path.join(ASSETS_DIR, "style.qss")
STYLE_DARK_FILE = os.path.join(ASSETS_DIR, "style_dark.qss")

import json

# Base de datos
DB_PATH = os.path.join(BASE_DIR, "PokeDatabase.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Configuración y Persistencia
SETTINGS_FILE = os.path.join(ASSETS_DIR, "settings.json")

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
