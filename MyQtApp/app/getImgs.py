import os
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt


# Backwards-compatible utility name.
# Previously images were inside a zip named `imagenes_cartas.zip`.
# Now images live in the folder assets/images relative to the repo root.
IMAGES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "images"))


def get_pixmap_from_zip(relative_path, size=None):
    """
    Backwards-compatible loader: given a relative filename (formerly inside the zip),
    try to load it from the `assets/images` folder and return a QPixmap.

    relative_path: e.g. 'pikachu.jpg' or 'folder/img.webp'
    size: optional tuple (width, height) to scale the pixmap while keeping aspect ratio.
    Returns QPixmap or None if not found/failed.
    """
    try:
        if not os.path.isdir(IMAGES_DIR):
            return None

        # Normalize input
        rel = relative_path.replace('\\', '/').lstrip('/')
        base_name = os.path.basename(rel)
        name_no_ext, ext = os.path.splitext(base_name)

        # Build candidate paths (prefer webp, then png, then jpg)
        candidates = []
        candidates.append(os.path.normpath(os.path.join(IMAGES_DIR, rel)))
        candidates.append(os.path.normpath(os.path.join(IMAGES_DIR, base_name)))

        if not ext:
            for e in ('.webp', '.png', '.jpg', '.jpeg'):
                candidates.append(os.path.join(IMAGES_DIR, name_no_ext + e))
        else:
            for e in ('.webp', '.png', '.jpg', '.jpeg'):
                if e != ext.lower():
                    candidates.append(os.path.join(IMAGES_DIR, name_no_ext + e))

        # Fast path: check candidates
        found = None
        for cand in candidates:
            if os.path.exists(cand) and os.path.isfile(cand):
                found = cand
                break

        # Case-insensitive fallback
        if not found:
            lower_target = base_name.lower()
            for root, _, files in os.walk(IMAGES_DIR):
                for f in files:
                    if f.lower() == lower_target or f.lower().startswith(name_no_ext.lower() + '.'):
                        found = os.path.join(root, f)
                        break
                if found:
                    break

        if not found:
            return None

        pix = QPixmap(found)
        if pix.isNull():
            return None
        if size:
            return pix.scaled(size[0], size[1], Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return pix
    except Exception:
        return None
