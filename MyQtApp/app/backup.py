import os
import shutil
import sqlite3
from datetime import datetime
from MyQtApp.config import DB_PATH, EXE_DIR

BACKUPS_DIR = os.path.join(EXE_DIR, "backups")


def get_backups_dir() -> str:
    """Asegura que exista la carpeta de respaldos y devuelve la ruta."""
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    return BACKUPS_DIR


def create_database_backup(tag: str = "manual") -> str:
    """
    Crea una copia de seguridad consistente de PokeDatabase.db.
    Retorna la ruta absoluta del archivo de respaldo creado o None si la base de datos no existe.
    """
    if not os.path.exists(DB_PATH):
        print(f"[Backup] No se encontró la base de datos en: {DB_PATH}")
        return None

    backups_dir = get_backups_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"PokeDatabase_backup_{tag}_{ts}.db"
    backup_path = os.path.join(backups_dir, backup_filename)

    try:
        # Usar la API de backup nativa de SQLite3 para garantizar una copia segura aun si la DB está abierta
        src_conn = sqlite3.connect(DB_PATH)
        dst_conn = sqlite3.connect(backup_path)
        with dst_conn:
            src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
        print(f"[Backup] Copia de seguridad creada exitosamente: {backup_path}")

        # Limpiar respaldos antiguos mantención máxima
        cleanup_old_backups()
        return backup_path
    except Exception as e:
        print(f"[Backup] Error creando copia de seguridad con sqlite backup, usando fallback shutil: {e}")
        try:
            shutil.copy2(DB_PATH, backup_path)
            cleanup_old_backups()
            return backup_path
        except Exception as err:
            print(f"[Backup] Error en copia fallback: {err}")
            return None


def list_backups() -> list:
    """Devuelve una lista de tuplas (filename, filepath, timestamp_formatted) ordenada de más reciente a más antigua."""
    backups_dir = get_backups_dir()
    if not os.path.exists(backups_dir):
        return []

    items = []
    for f in os.listdir(backups_dir):
        if f.startswith("PokeDatabase_backup_") and f.endswith(".db"):
            full_path = os.path.join(backups_dir, f)
            mtime = os.path.getmtime(full_path)
            dt_str = datetime.fromtimestamp(mtime).strftime("%d/%m/%Y %H:%M:%S")
            items.append((f, full_path, mtime, dt_str))

    items.sort(key=lambda x: x[2], reverse=True)
    return [(item[0], item[1], item[3]) for item in items]


def restore_database_backup(backup_path: str) -> bool:
    """
    Restaura la base de datos desde un archivo de respaldo especificado.
    Antes de sobrescribir, realiza un respaldo de emergencia de la DB actual.
    """
    if not os.path.exists(backup_path):
        print(f"[Backup] El archivo de respaldo no existe: {backup_path}")
        return False

    try:
        # Crear respaldo preventivo de la DB actual antes de restaurar
        if os.path.exists(DB_PATH):
            pre_restore_tag = f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            create_database_backup(tag=pre_restore_tag)

        # Restaurar copia
        dst_conn = sqlite3.connect(DB_PATH)
        src_conn = sqlite3.connect(backup_path)
        with dst_conn:
            src_conn.backup(dst_conn)
        src_conn.close()
        dst_conn.close()
        print(f"[Backup] Base de datos restaurada correctamente desde: {backup_path}")
        return True
    except Exception as e:
        print(f"[Backup] Error restaurando base de datos: {e}")
        try:
            shutil.copy2(backup_path, DB_PATH)
            return True
        except Exception as err:
            print(f"[Backup] Error en restore fallback: {err}")
            return False


def cleanup_old_backups(keep_count: int = 15):
    """Mantiene solo las últimas `keep_count` copias de seguridad para evitar uso excesivo de disco."""
    backups_dir = get_backups_dir()
    items = []
    for f in os.listdir(backups_dir):
        if f.startswith("PokeDatabase_backup_") and f.endswith(".db"):
            full_path = os.path.join(backups_dir, f)
            mtime = os.path.getmtime(full_path)
            items.append((full_path, mtime))

    items.sort(key=lambda x: x[1], reverse=True)
    if len(items) > keep_count:
        for full_path, _ in items[keep_count:]:
            try:
                os.remove(full_path)
                print(f"[Backup] Limpieza de respaldo antiguo: {full_path}")
            except Exception as e:
                print(f"[Backup] No se pudo eliminar respaldo antiguo {full_path}: {e}")
