import os
import sys
import requests

# Agregar el directorio raíz del proyecto al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from MyQtApp.session import SessionLocal
from MyQtApp.models import Cartas
from MyQtApp.config import IMAGES_WEBP_DIR, TCGDEX_LANG_MAP
from MyQtApp.app.getImgs import save_bytes_as_webp


def sync_all_tcgdex_metadata(languages=None):
    """Sincroniza masivamente el catálogo completo de cartas para todos los idiomas en la BD."""
    if languages is None:
        languages = ["es", "ja", "en", "fr", "pt", "zh"]

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    for lang_code in languages:
        tcgdex_lang = TCGDEX_LANG_MAP.get(lang_code, "en")
        print(f"\nSincronizando catalogo TCGDex para [{lang_code}] ({tcgdex_lang})...")

        url = f"https://api.tcgdex.net/v2/{tcgdex_lang}/cards"
        try:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code != 200:
                print(f"Error consultando TCGDex para [{lang_code}] (HTTP {r.status_code})")
                continue
            data = r.json()
        except Exception as e:
            print(f"Error de conexión con TCGDex [{lang_code}]: {e}")
            continue

        print(f"Recibidas {len(data)} cartas en TCGDex para [{lang_code}]. Insertando en BD...")

        session = SessionLocal()
        existing_ids = set(
            r[0] for r in session.query(Cartas.id_api).filter(Cartas.idioma == lang_code).all()
        )

        new_objects = []
        for item in data:
            card_id = item.get("id")
            nombre = item.get("name")
            local_id = item.get("localId")

            if not card_id or not nombre or card_id in existing_ids:
                continue

            new_objects.append(
                Cartas(
                    id_api=card_id,
                    idioma=lang_code,
                    nombre=nombre,
                    type="Desconocido",
                    price=0.0,
                    rarity="Desconocida",
                    number=str(local_id) if local_id else "N/A",
                    set_id=card_id.split("-")[0] if "-" in card_id else "N/A",
                    set_name="TCGDex",
                    stage="Ninguno",
                    especial_type="Normal",
                    trainer="Ninguno",
                    edition="Ninguno"
                )
            )

        if new_objects:
            session.bulk_save_objects(new_objects)
            session.commit()
            print(f"Insertadas {len(new_objects)} cartas nuevas para [{lang_code}] con exito!")
        else:
            print(f"[{lang_code}] ya tiene todas sus cartas en la BD.")

        session.close()


if __name__ == "__main__":
    sync_all_tcgdex_metadata(["es", "ja", "en", "fr", "pt", "zh"])
