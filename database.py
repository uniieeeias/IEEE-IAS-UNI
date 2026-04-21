from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# 🔥 Obtener variable de entorno desde Render
DATABASE_URL = os.getenv("DATABASE_URL")

# 🚨 Validación para evitar crash silencioso
if not DATABASE_URL:
    raise Exception("❌ DATABASE_URL no está configurada en el entorno (Render)")

# 🔗 Crear engine de conexión a PostgreSQL
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # evita conexiones muertas en deploy
    pool_recycle=300      # recicla conexiones cada cierto tiempo
)

# 🧠 Sesión de base de datos
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
