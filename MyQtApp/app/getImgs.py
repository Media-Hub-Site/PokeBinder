import os
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from MyQtApp.config import IMAGES_DIR

os.makedirs(IMAGES_DIR, exist_ok=True)

# Caché en memoria para evitar os.walk e hilos de carga pesados
_image_cache = {}
_cache_initialized = False
_pixmap_cache = {}
def _init_cache():
    global _cache_initialized
    if _cache_initialized:
        return
    print("Inicializando caché de imágenes...")
    dirs_to_scan = [IMAGES_DIR, IMAGES_WEBP_DIR]
    for d in dirs_to_scan:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for f in files:
                    full_path = os.path.join(root, f)
                    f_lower = f.lower()
                    # Guardar por nombre de archivo
                    _image_cache[f_lower] = full_path
                    # Guardar por ruta relativa respecto a d
                    try:
                        rel = os.path.relpath(full_path, d).replace('\\', '/').lower()
                        _image_cache[rel] = full_path
                    except Exception:
                        pass
    _cache_initialized = True
    print(f"Caché de imágenes listo con {len(_image_cache)} archivos registrados.")

def get_pixmap_from_zip(relative_path, size=None, id_api=None):
    """
    Carga una imagen desde la carpeta assets/images y la retorna como QPixmap,
    utilizando un caché en memoria para evitar recargas costosas de disco.
    """
    cache_key = (relative_path, size, id_api)
    if cache_key in _pixmap_cache:
        return _pixmap_cache[cache_key]

    try:
        # Asegurar caché listo
        _init_cache()
        
        rel_path = relative_path.replace('\\\\', '/').lstrip('/')
        base_name = os.path.basename(rel_path)
        name_no_ext, ext = os.path.splitext(base_name)
        
        raw_name = name_no_ext.lower().replace(' ', '_')
        alnum_name = "".join([c for c in raw_name if c.isalnum() or c == '_'])
        
        name_variants = [raw_name]
        if alnum_name != raw_name:
            name_variants.append(alnum_name)
            
        clean_id = str(id_api).lower() if id_api else None
        
        found = None
        candidates_keys = []
        extensions = ['.webp', '.png', '.jpg', '.jpeg']
        
        for n in name_variants:
            if clean_id:
                for e in extensions:
                    candidates_keys.append(f"{n}_{clean_id}{e}")
            if ext:
                candidates_keys.append(f"{n}{ext.lower()}")
            for e in extensions:
                candidates_keys.append(f"{n}{e}")
                
        if ext and base_name.lower() not in candidates_keys:
            candidates_keys.append(base_name.lower())
            
        for key in candidates_keys:
            if key in _image_cache:
                found = _image_cache[key]
                break
                
        # 2. Si no se encontró en las llaves exactas, buscar si alguna llave empieza con algún prefijo
        if not found:
            for key, path in _image_cache.items():
                for n in name_variants:
                    prefix = f"{n}_{clean_id}." if clean_id else f"{n}."
                    if key.startswith(prefix):
                        found = path
                        break
                if found:
                    break

        if not found:
            # Si a pesar de todo no está en caché, buscamos directamente en disco
            for search_dir in [IMAGES_DIR, IMAGES_WEBP_DIR]:
                for n in name_variants:
                    if clean_id:
                        for e in extensions:
                            for target_id in [id_api, clean_id]:
                                posible = os.path.join(search_dir, f"{n}_{target_id}{e}")
                                if os.path.exists(posible):
                                    found = posible
                                    _image_cache[os.path.basename(posible).lower()] = posible
                                    break
                            if found:
                                break
                    if found:
                        break
                if found:
                    break

        if not found:
            print(f"❌ No se encontró imagen para: {raw_name}")
            return None

        pix = QPixmap(found)
        
        if pix.isNull():
            print(f"❌ Error al cargar la imagen en QPixmap: {found}")
            return None
            
        if size:
            pix = pix.scaled(
                size[0], size[1], 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            
        _pixmap_cache[cache_key] = pix
        return pix
        
    except Exception as e:
        print(f"❌ Error al procesar la imagen: {str(e)}")
        return None


import io
import requests
from PIL import Image
from PyQt6.QtCore import QThread, pyqtSignal
from MyQtApp.config import IMAGES_DIR, IMAGES_HD_DIR, IMAGES_WEBP_DIR, TCGDEX_LANG_MAP, normalize_lang_code


def save_bytes_as_webp(image_bytes: bytes, target_path: str, quality=85) -> bool:
    """Convierte cualquier byte de imagen (PNG/JPG) a formato .webp comprimido."""
    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")
        img.save(target_path, "WEBP", quality=quality, optimize=True)
        return True
    except Exception as e:
        print(f"❌ Error convirtiendo a WebP: {e}")
        return False


def save_bytes_as_png(image_bytes: bytes, target_path: str) -> bool:
    """Guarda cualquier byte de imagen (PNG/WebP/JPG) en alta definición en formato .png en assets/images_hd."""
    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        img.save(target_path, "PNG", optimize=True)
        return True
    except Exception as e:
        print(f"❌ Error guardando PNG HD: {e}")
        return False


def get_hd_pixmap(id_api, nombre_archivo=None, idioma="es", size=None):
    """Busca y retorna la versión en alta definición (.png) guardada localmente en assets/images_hd."""
    if not id_api:
        return None

    lang_code = normalize_lang_code(idioma)
    clean_id = str(id_api).lower()
    clean_name = str(nombre_archivo or "card").lower().replace(" ", "_")
    clean_name = "".join([c for c in clean_name if c.isalnum() or c == '_'])

    candidates = [
        os.path.join(IMAGES_HD_DIR, lang_code, f"{clean_name}_{clean_id}_hires.png"),
        os.path.join(IMAGES_HD_DIR, lang_code, f"{clean_name}_{clean_id}.png"),
        os.path.join(IMAGES_HD_DIR, f"{clean_name}_{clean_id}_hires.png"),
        os.path.join(IMAGES_HD_DIR, f"{clean_name}_{clean_id}.png"),
    ]

    for path in candidates:
        if os.path.exists(path):
            pix = QPixmap(path)
            if pix and not pix.isNull():
                if size:
                    pix = pix.scaled(
                        size[0], size[1],
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                return pix
    return None


def get_webp_pixmap(id_api, nombre_archivo=None, idioma="es", size=None):
    """Busca y retorna la versión comprimida en .webp/png/jpg de la carta según idioma."""
    if not id_api:
        return None

    lang_code = normalize_lang_code(idioma)
    clean_id = str(id_api).lower()
    clean_name = str(nombre_archivo or "card").lower().replace(" ", "_")
    clean_name = "".join([c for c in clean_name if c.isalnum() or c == '_'])

    # 1. Probar primero si ya tenemos versión HD guardada localmente
    hd_pix = get_hd_pixmap(id_api, nombre_archivo, idioma, size)
    if hd_pix and not hd_pix.isNull():
        return hd_pix

    _init_cache()

    # Combinaciones directas de búsqueda (subcarpeta idioma o directorio raíz)
    possible_keys = [
        f"{lang_code}/{clean_name}_{clean_id}.webp",
        f"{lang_code}/{clean_name}_{clean_id}.png",
        f"en/{clean_name}_{clean_id}.webp",
        f"es/{clean_name}_{clean_id}.webp",
        f"{clean_name}_{clean_id}.webp",
        f"{clean_name}_{clean_id}.png",
    ]

    for k in possible_keys:
        if k in _image_cache and os.path.exists(_image_cache[k]):
            pix = QPixmap(_image_cache[k])
            if pix and not pix.isNull():
                if size:
                    pix = pix.scaled(
                        size[0], size[1],
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                return pix

    # Fallback general a get_pixmap_from_zip (busca recursivo en assets/images)
    pix = get_pixmap_from_zip(clean_name, size=size, id_api=clean_id)
    if pix and not pix.isNull():
        return pix

    return None


class HDImageDownloaderThread(QThread):
    """Hilo en segundo plano para obtener e integrar la imagen Full HD en formato .png desde TCGDex o PokéAPI."""
    image_loaded = pyqtSignal(QPixmap, str)  # (pixmap, id_api)

    def __init__(self, id_api, set_id=None, number=None, nombre_archivo=None, idioma="es", parent=None):
        super().__init__(parent)
        self.id_api = id_api
        self.set_id = set_id
        self.number = number
        self.nombre_archivo = nombre_archivo or (id_api or "card")
        self.idioma = normalize_lang_code(idioma)

    def run(self):
        if not self.id_api:
            return

        clean_id = str(self.id_api).lower()
        clean_name = str(self.nombre_archivo).lower().replace(" ", "_")
        clean_name = "".join([c for c in clean_name if c.isalnum() or c == '_'])

        lang_dir = os.path.join(IMAGES_HD_DIR, self.idioma)
        os.makedirs(lang_dir, exist_ok=True)

        hd_png_target = os.path.join(lang_dir, f"{clean_name}_{clean_id}_hires.png")
        root_hd_png_target = os.path.join(IMAGES_HD_DIR, f"{clean_name}_{clean_id}_hires.png")

        # 1. Si la imagen HD PNG ya existe localmente, cargarla directamente
        for target in [hd_png_target, root_hd_png_target]:
            if os.path.exists(target):
                pix = QPixmap(target)
                if pix and not pix.isNull():
                    self.image_loaded.emit(pix, self.id_api)
                    return

        # 2. Si no existe, descargar la imagen Full HD desde TCGDex o PokéAPI
        tcgdex_lang = TCGDEX_LANG_MAP.get(self.idioma, "en")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        urls_to_try = []

        try:
            api_card_url = f"https://api.tcgdex.net/v2/{tcgdex_lang}/cards/{self.id_api}"
            api_resp = requests.get(api_card_url, headers=headers, timeout=6)
            if api_resp.status_code == 200:
                card_data = api_resp.json()
                base_img = card_data.get("image")
                if base_img:
                    urls_to_try.append(f"{base_img}/high.png")
                    urls_to_try.append(f"{base_img}/high.webp")
                    urls_to_try.append(f"{base_img}/low.png")
        except Exception:
            pass

        set_id = self.set_id
        number = self.number
        if not set_id or not number:
            if "-" in self.id_api:
                parts = self.id_api.split("-")
                set_id = parts[0]
                number = "-".join(parts[1:])

        if set_id and number:
            urls_to_try.append(f"https://assets.tcgdex.net/{tcgdex_lang}/{set_id}/{number}/high.png")
            urls_to_try.append(f"https://assets.tcgdex.net/{tcgdex_lang}/{set_id}/{number}/high.webp")
            if self.idioma == "en":
                num_clean = str(number).lstrip('0') if str(number).isdigit() else str(number)
                urls_to_try.append(f"https://images.pokemontcg.io/{set_id}/{number}_hires.png")
                urls_to_try.append(f"https://images.pokemontcg.io/{set_id}/{number}.png")
                if num_clean and num_clean != str(number):
                    urls_to_try.append(f"https://images.pokemontcg.io/{set_id}/{num_clean}_hires.png")
                    urls_to_try.append(f"https://images.pokemontcg.io/{set_id}/{num_clean}.png")

        for url in urls_to_try:
            try:
                resp = requests.get(url, headers=headers, timeout=12)
                if resp.status_code == 200 and len(resp.content) > 100:
                    if save_bytes_as_png(resp.content, hd_png_target):
                        pix = QPixmap(hd_png_target)
                        if pix and not pix.isNull():
                            self.image_loaded.emit(pix, self.id_api)
                            return
            except Exception as e:
                print(f"Error descargando imagen HD desde {url}: {e}")




