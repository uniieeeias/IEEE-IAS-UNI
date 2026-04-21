from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL")

# 🔥 VALIDACIÓN IMPORTANTE (evita crash en Render)
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL no está configurada en las variables de entorno")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
