import time
import requests
from PyQt6.QtCore import QThread, pyqtSignal
from MyQtApp.session import SessionLocal
from MyQtApp.models import Cartas


class PriceUpdaterThread(QThread):
    """
    Hilo de ejecución en segundo plano que sincroniza precios en tiempo real
    desde la API de Scrydex / Pokémon TCG / TCGPlayer / Cardmarket en lotes (batching).
    """
    progress = pyqtSignal(int, int)  # (actual, total)
    finished = pyqtSignal(int)      # (total_actualizadas)
    error = pyqtSignal(str)

    def __init__(self, id_apis=None, parent=None):
        super().__init__(parent)
        self.id_apis = id_apis
        self.is_running = True

    def stop(self):
        self.is_running = False

    def run(self):
        session = SessionLocal()
        try:
            # Si no se proveen IDs específicos, obtener todos los id_api de la BD
            if not self.id_apis:
                cartas_db = session.query(Cartas.id_api).all()
                target_ids = [c[0] for c in cartas_db if c[0]]
            else:
                target_ids = list(self.id_apis)

            total = len(target_ids)
            if total == 0:
                self.finished.emit(0)
                return

            self.progress.emit(0, total)

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
            }

            total_actualizadas = 0
            chunk_size = 35  # Procesar de a 35 cartas por llamada API

            for i in range(0, total, chunk_size):
                if not self.is_running:
                    break

                chunk = target_ids[i:i + chunk_size]
                # Construir consulta q=id:"id1" OR id:"id2" ...
                escaped_ids = [f'id:"{cid}"' for cid in chunk]
                query_str = " OR ".join(escaped_ids)
                url = f"https://api.pokemontcg.io/v2/cards?q={requests.utils.quote(query_str)}"

                try:
                    response = requests.get(url, headers=headers, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        cards_data = data.get("data", [])
                        
                        # Mapear precios actualizados
                        for c_info in cards_data:
                            cid = c_info.get("id")
                            if not cid:
                                continue

                            # 1. TCGPlayer prices
                            tcg_prices = c_info.get("tcgplayer", {}).get("prices", {})
                            nuevo_precio = 0.0
                            
                            if isinstance(tcg_prices, dict):
                                for variant_name, price_dict in tcg_prices.items():
                                    if isinstance(price_dict, dict):
                                        m_price = price_dict.get("market") or price_dict.get("mid") or price_dict.get("low")
                                        if m_price and float(m_price) > 0:
                                            nuevo_precio = float(m_price)
                                            break
                            
                            # 2. Fallback a Cardmarket si TCGPlayer no tiene market price
                            if nuevo_precio == 0.0:
                                cm = c_info.get("cardmarket", {}).get("prices", {})
                                if isinstance(cm, dict):
                                    if "averageSellPrice" in cm and cm["averageSellPrice"]:
                                        nuevo_precio = float(cm["averageSellPrice"])
                                    elif "trendPrice" in cm and cm["trendPrice"]:
                                        nuevo_precio = float(cm["trendPrice"])

                            # Actualizar BD local
                            if nuevo_precio > 0.0:
                                carta_obj = session.query(Cartas).filter(Cartas.id_api == cid).first()
                                if carta_obj:
                                    carta_obj.price = nuevo_precio
                                    total_actualizadas += 1

                        session.commit()

                except Exception as e:
                    print(f"Error al actualizar lote de precios: {e}")

                # Emitir progreso
                procesadas = min(i + chunk_size, total)
                self.progress.emit(procesadas, total)
                
                # Pausa ligera para no saturar rate limit
                time.sleep(0.25)

            self.finished.emit(total_actualizadas)

        except Exception as e:
            session.rollback()
            self.error.emit(str(e))
        finally:
            session.close()
