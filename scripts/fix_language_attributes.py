import os
import sqlite3

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "PokeDatabase.db"))
print(f"Actualizando atributos de idioma en: {db_path}")

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Eliminar duplicados TCGDex en inglés si ya existen en pokemontcg.io
    cur.execute("""
        DELETE FROM Cartas 
        WHERE set_name = 'TCGDex' 
        AND idioma = 'en' 
        AND id_api IN (SELECT id_api FROM Cartas WHERE set_name != 'TCGDex')
    """)

    # 2. Actualizar cartas pokemontcg.io a idioma = 'en'
    cur.execute("UPDATE OR IGNORE Cartas SET idioma = 'en' WHERE set_name != 'TCGDex' OR set_name IS NULL")
    updated_count = cur.rowcount

    conn.commit()
    conn.close()
    print(f"Se actualizaron {updated_count} cartas de pokemontcg.io asignando idioma = 'en' (Inglés).")
