import sys
import os
import json
import shutil

APP_VERSION = "1.5.0"

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
PERFIL_DIR = os.path.join(ASSETS_DIR, "perfil")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
STYLE_FILE = os.path.join(ASSETS_DIR, "style.qss")
STYLE_DARK_FILE = os.path.join(ASSETS_DIR, "style_dark.qss")

# Directorio persistente local de datos del usuario (sobrevive a actualizaciones del launcher)
def get_user_data_dir() -> str:
    override = os.environ.get("POKEBINDER_DATA_DIR")
    if override:
        os.makedirs(override, exist_ok=True)
        return override
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(base, "PokeBinder")
    else:
        path = os.path.join(os.path.expanduser("~"), ".pokebinder")
    os.makedirs(path, exist_ok=True)
    return path

USER_DATA_DIR = get_user_data_dir()
BACKUPS_DIR = os.path.join(USER_DATA_DIR, "backups")
os.makedirs(BACKUPS_DIR, exist_ok=True)

# Carpeta de imágenes descargadas (en la ruta del ejecutable para aprovechar assets-v1 del launcher)
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


# Base de datos y persistencia de usuario en AppData/Local/PokeBinder
SEED_DB_PATH = os.path.join(BUNDLE_DIR, "PokeDatabase.db")
DB_PATH = os.path.join(USER_DATA_DIR, "PokeDatabase.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Configuración y Persistencia de Carpetas/Binders
SETTINGS_FILE = os.path.join(USER_DATA_DIR, "settings.json")
BINDER_DATA_FILE = os.path.join(USER_DATA_DIR, "binder_data.json")


def ensure_user_data_initialized():
    """
    Inicializa los archivos persistentes del usuario en USER_DATA_DIR (%LOCALAPPDATA%\\PokeBinder)
    si aún no existen, migrando datos previos de la carpeta instalada/bundle cuando corresponda.
    Así el usuario jamás pierde sus sesiones, colecciones ni binders al actualizar la aplicación.
    """
    os.makedirs(USER_DATA_DIR, exist_ok=True)

    # 1. Base de datos SQLite
    if not os.path.exists(DB_PATH):
        legacy_candidates = [
            os.path.join(EXE_DIR, "PokeDatabase.db"),
            os.path.join(EXE_DIR, "_internal", "PokeDatabase.db"),
            SEED_DB_PATH,
        ]
        for cand in legacy_candidates:
            if cand and os.path.exists(cand) and os.path.abspath(cand) != os.path.abspath(DB_PATH):
                try:
                    shutil.copy2(cand, DB_PATH)
                    print(f"[Storage] Base de datos inicializada en {DB_PATH} desde {cand}")
                    break
                except Exception as e:
                    print(f"[Storage] Error copiando DB desde {cand}: {e}")

    # 2. Datos de Binders (binder_data.json)
    if not os.path.exists(BINDER_DATA_FILE):
        migrated = False
        legacy_binder_candidates = [
            os.path.join(EXE_DIR, "assets", "binder_data.json"),
            os.path.join(EXE_DIR, "_internal", "assets", "binder_data.json"),
            os.path.join(ASSETS_DIR, "binder_data.json"),
        ]
        for cand in legacy_binder_candidates:
            if cand and os.path.exists(cand) and os.path.abspath(cand) != os.path.abspath(BINDER_DATA_FILE):
                try:
                    with open(cand, "r", encoding="utf-8") as f:
                        content = json.load(f)
                    if isinstance(content, dict) and len(content) > 0:
                        shutil.copy2(cand, BINDER_DATA_FILE)
                        print(f"[Storage] binder_data.json migrado desde {cand}")
                        migrated = True
                        break
                except Exception:
                    pass
        if not migrated:
            try:
                with open(BINDER_DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump({}, f, indent=4)
            except Exception as e:
                print(f"[Storage] Error inicializando binder_data.json: {e}")

    # 3. Configuración (settings.json)
    if not os.path.exists(SETTINGS_FILE):
        legacy_settings_candidates = [
            os.path.join(EXE_DIR, "assets", "settings.json"),
            os.path.join(ASSETS_DIR, "settings.json"),
        ]
        for cand in legacy_settings_candidates:
            if cand and os.path.exists(cand) and os.path.abspath(cand) != os.path.abspath(SETTINGS_FILE):
                try:
                    shutil.copy2(cand, SETTINGS_FILE)
                    break
                except Exception:
                    pass


ensure_user_data_initialized()

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
