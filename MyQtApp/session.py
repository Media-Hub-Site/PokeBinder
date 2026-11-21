from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from MyQtApp.config import DB_PATH, DATABASE_URL, ensure_user_data_initialized

ensure_user_data_initialized()
print(f"Usando base de datos en: {DB_PATH}")

engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

# Las tablas se crearán desde main.py
