import os
import sqlite3

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "PokeDatabase.db"))
print(f"Migrando esquema de base de datos en: {db_path}")

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("PRAGMA foreign_keys=OFF")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS Cartas_temp (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            id_api VARCHAR NOT NULL,
            idioma VARCHAR NOT NULL DEFAULT 'es',
            nombre VARCHAR NOT NULL,
            type VARCHAR,
            price FLOAT,
            rarity VARCHAR,
            number VARCHAR,
            set_id VARCHAR,
            set_name VARCHAR,
            stage VARCHAR,
            especial_type VARCHAR,
            trainer VARCHAR,
            edition VARCHAR,
            UNIQUE(id_api, idioma)
        )
    """)

    # Copiar registros existentes
    cur.execute("""
        INSERT OR IGNORE INTO Cartas_temp (id, id_api, idioma, nombre, type, price, rarity, number, set_id, set_name, stage, especial_type, trainer, edition)
        SELECT id, id_api, 'es', nombre, type, price, rarity, number, set_id, set_name, stage, especial_type, trainer, edition
        FROM Cartas
    """)

    cur.execute("DROP TABLE Cartas")
    cur.execute("ALTER TABLE Cartas_temp RENAME TO Cartas")

    cur.execute("PRAGMA foreign_keys=ON")
    conn.commit()
    conn.close()
    print("Migracion completada: Restriccion unica id_api+idioma aplicada con exito!")
