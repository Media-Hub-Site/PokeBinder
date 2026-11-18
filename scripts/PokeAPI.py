import os
import requests
import time
from MyQtApp.session import SessionLocal
from MyQtApp.models import Cartas
from MyQtApp.config import IMAGES_DIR

# Ensure images directory exists
os.makedirs(IMAGES_DIR, exist_ok=True)

session = SessionLocal()

page = 125  # Inicia desde la página 125 (carta 12,401 en adelante)
total_guardadas = 12400  # Contador inicial de cartas guardadas

print("Iniciando recopilación de datos de Pokémon TCG...")
print(f"Las imágenes se guardarán en: {IMAGES_DIR}")

while True:
    url = f"https://api.pokemontcg.io/v2/cards?page={page}&pageSize=100"
    print(f"\nConsultando página {page}...")
    
    # Wait 2 seconds before API call (as requested, basic limit)
    time.sleep(2)
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error consultando la API en la página {page}: {e}")
        # Wait longer if there's an error (e.g. Rate Limit or 500 Server Error)
        print("Esperando 30 segundos antes de reintentar...")
        time.sleep(30)
        continue

    cartas = data.get("data", [])
    if not cartas:
        print("No se encontraron más cartas. Finalizando.")
        break

    for i, carta in enumerate(cartas):
        id_api = carta.get("id")
        nombre = carta.get("name")
        tipos = carta.get("types", [])
        tipo = tipos[0] if tipos else "Desconocido"
        rareza = carta.get("rarity", "Desconocida")

        precios = carta.get("tcgplayer", {}).get("prices", {})
        precio = precios.get("market", precios.get("normal", {})).get("market", 0.0)

        numero = carta.get("number", "N/A")
        set_info = carta.get("set", {})
        set_id = set_info.get("id", "N/A")
        set_nombre = set_info.get("name", "N/A")

        subtipos = carta.get("subtypes", [])
        stage = subtipos[0] if subtipos else "Ninguno"
        especial_type = subtipos[1] if len(subtipos) > 1 else "Normal"
        trainer = subtipos[2] if len(subtipos) > 2 else "Desconocido"
        edition = subtipos[3] if len(subtipos) > 3 else "Ninguno"

        # Image URL (we use small to save space, but it has good enough quality)
        img_url = carta.get("images", {}).get("small")
        
        # Format image name: lowercase name, replace spaces with underscores, append id_api
        clean_name = str(nombre).lower().replace(' ', '_')
        # Removing any other weird characters like slashes or colons that are invalid in Windows files
        clean_name = "".join([c for c in clean_name if c.isalnum() or c == '_'])
        
        img_filename = f"{clean_name}_{id_api}.png"
        img_path = os.path.join(IMAGES_DIR, img_filename)

        # 1. Download image if it doesn't exist
        if img_url and not os.path.exists(img_path):
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                img_response = requests.get(img_url, headers=headers, timeout=10)
                if img_response.status_code == 200:
                    with open(img_path, 'wb') as f:
                        f.write(img_response.content)
                # Small delay to avoid overloading image CDN
                time.sleep(0.1)
            except Exception as e:
                print(f"Error descargando imagen de {nombre} ({id_api}): {e}")

        # 2. Save into Database
        try:
            existe = session.query(Cartas).filter_by(id_api=id_api).first()
            if not existe:
                nueva_carta = Cartas(
                    id_api=id_api, nombre=nombre, type=tipo, price=precio,
                    rarity=rareza, number=numero, set_id=set_id,
                    set_name=set_nombre, stage=stage, especial_type=especial_type,
                    trainer=trainer, edition=edition
                )
                session.add(nueva_carta)
                session.commit()
                total_guardadas += 1
                
                # Print progress for every inserted card
                print(f"[{total_guardadas}] Guardada: {nombre} ({id_api}) -> {img_filename}")
        except Exception as e:
            session.rollback()
            print(f"Error guardando {id_api} en BD: {e}")

    print(f"Página {page} procesada [OK] | Cartas totales guardadas: {total_guardadas}")
    page += 1

session.close()
print(f"IMPORTACIÓN FINALIZADA [OK] Total insertadas: {total_guardadas}")
