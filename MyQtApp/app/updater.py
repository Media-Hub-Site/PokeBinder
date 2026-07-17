import os
import urllib.request
import json
import tempfile
from PyQt6.QtCore import QThread, pyqtSignal
from MyQtApp.config import APP_VERSION

class UpdateCheckerThread(QThread):
    update_available = pyqtSignal(str, str, str)  # new_version, release_notes, download_url

    def run(self):
        try:
            url = "https://api.github.com/repos/Alan-Dave/TCG-Inventory/releases/latest"
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'TCG-Inventory-Updater'}
            )
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                
            tag = data.get("tag_name", "").strip()
            # Limpiar la versión de letras no numéricas
            remote_version = tag.lower().replace("v", "")
            local_version = APP_VERSION.lower().replace("v", "")
            
            # Comparación semántica
            if self.is_newer_version(local_version, remote_version):
                # Buscar el instalador (.exe) en los assets
                download_url = None
                assets = data.get("assets", [])
                for asset in assets:
                    name = asset.get("name", "").lower()
                    if name.endswith(".exe"):
                        download_url = asset.get("browser_download_url")
                        break
                
                # Si no hay instalador .exe, usar el html_url de la release como fallback
                if not download_url:
                    download_url = data.get("html_url")
                    
                notes = data.get("body", "No hay descripción disponible para esta versión.")
                self.update_available.emit(remote_version, notes, download_url)
        except Exception as e:
            # Silenciar errores si el usuario no tiene internet en ese momento
            print(f"Error checking updates: {e}")

    def is_newer_version(self, local, remote):
        try:
            l_parts = [int(x) for x in local.split(".")]
            r_parts = [int(x) for x in remote.split(".")]
            max_len = max(len(l_parts), len(r_parts))
            l_parts += [0] * (max_len - len(l_parts))
            r_parts += [0] * (max_len - len(r_parts))
            return r_parts > l_parts
        except Exception:
            return remote != local


class FileDownloaderThread(QThread):
    progress_changed = pyqtSignal(int)
    finished = pyqtSignal(str, bool)

    def __init__(self, download_url):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            req = urllib.request.Request(
                self.download_url,
                headers={'User-Agent': 'TCG-Inventory-Updater'}
            )
            
            dest_dir = tempfile.gettempdir()
            dest_path = os.path.join(dest_dir, "TCG_Inventory_Update_Setup.exe")
            
            with urllib.request.urlopen(req) as response:
                meta = response.info()
                total_size = int(meta.get("Content-Length", 0))
                
                block_size = 8192
                downloaded = 0
                
                with open(dest_path, "wb") as f:
                    while True:
                         buffer = response.read(block_size)
                         if not buffer:
                             break
                         downloaded += len(buffer)
                         f.write(buffer)
                         
                         if total_size > 0:
                             percent = int((downloaded / total_size) * 100)
                             self.progress_changed.emit(percent)
                             
            self.finished.emit(dest_path, True)
        except Exception as e:
            print(f"Error downloading update: {e}")
            self.finished.emit("", False)
