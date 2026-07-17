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
    if os.path.exists(IMAGES_DIR):
        for root, _, files in os.walk(IMAGES_DIR):
            for f in files:
                # Guardamos la llave en minúsculas para búsquedas insensibles a mayúsculas
                _image_cache[f.lower()] = os.path.join(root, f)
    _cache_initialized = True
    print(f"Caché de imágenes listo con {len(_image_cache)} archivos.")

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
        
        clean_name = name_no_ext.lower().replace(' ', '_')
        
        found = None
        
        # 1. Intentar construir nombres probables y chequear en caché (O(1))
        candidates_keys = []
        if id_api:
            for e in ['.webp', '.png', '.jpg', '.jpeg']:
                candidates_keys.append(f"{clean_name}_{id_api}{e}")
        
        if ext:
            candidates_keys.append(base_name.lower())
            
        for e in ['.webp', '.png', '.jpg', '.jpeg']:
            candidates_keys.append(f"{clean_name}{e}")
            
        for key in candidates_keys:
            if key in _image_cache:
                found = _image_cache[key]
                break
                
        # 2. Si no se encontró en las llaves exactas, buscar si alguna llave empieza con clean_name (O(N) en diccionario pero mucho más rápido que filesystem)
        if not found:
            for key, path in _image_cache.items():
                if key.startswith(clean_name + '.'):
                    found = path
                    break
 
        if not found:
            # Si a pesar de todo no está, puede que sea nueva, buscamos en disco directamente
            # Construir posible ruta
            if id_api:
                posible = os.path.join(IMAGES_DIR, f"{clean_name}_{id_api}.webp")
                if os.path.exists(posible):
                    found = posible
                    _image_cache[f"{clean_name}_{id_api}.webp"] = posible
 
        if not found:
            print(f"❌ No se encontró imagen para: {clean_name}")
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

