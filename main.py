import os
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import uuid
import qrcode

from database import SessionLocal, engine
from models import Base, Certificate

# ========================
# CONFIGURACIÓN BASE
# ========================

Base.metadata.create_all(bind=engine)

QR_FOLDER = "qrs"
os.makedirs(QR_FOLDER, exist_ok=True)

app = FastAPI()

app.mount("/qrs", StaticFiles(directory=QR_FOLDER), name="qrs")

# 🔐 API KEY (Render -> Environment Variable)
API_KEY = os.getenv("API_KEY")


# ========================
# MODELO REQUEST
# ========================

class CertificateRequest(BaseModel):
    event_code: str
    event_name: str
    event_type: str
    participant: str


# ========================
# SERIAL GENERATOR
# ========================

def generate_serial(event_type: str):
    type_code = event_type[:3].upper()
    unique = uuid.uuid4().hex[:8].upper()
    return f"IAS-UNI-2026-{type_code}-{unique}"


# ========================
# HOME
# ========================

@app.get("/")
def home():
    return {"message": "API de certificados funcionando 🚀"}


# ========================
# GENERAR CERTIFICADO
# ========================

@app.post("/certificates/generate")
def generate_certificate(
    data: CertificateRequest,
    x_api_key: str = Header(None)
):

    # 🔐 validación API KEY (opcional pero recomendado)
    if API_KEY:
        if x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail="No autorizado")

    db = SessionLocal()

    # evitar duplicados
    existing = db.query(Certificate).filter(
        Certificate.event_name == data.event_name,
        Certificate.participant == data.participant
    ).first()

    if existing:
        db.close()
        return {
            "message": "Este certificado ya existe",
            "serial": existing.serial
        }

    serial = generate_serial(data.event_type)

    BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
    verification_url = f"{BASE_URL}/verify/{serial}"

    cert = Certificate(
        serial=serial,
        event_code=data.event_code,
        event_name=data.event_name,
        event_type=data.event_type,
        participant=data.participant,
        status="valid"
    )

    db.add(cert)
    db.commit()
    db.close()

    # QR
    qr = qrcode.make(verification_url)
    qr_path = f"{QR_FOLDER}/{serial}.png"
    qr.save(qr_path)

    return {
        "serial": serial,
        "qr_url": f"{BASE_URL}/qrs/{serial}.png",
        "verification_url": verification_url
    }


# ========================
# VERIFICACIÓN
# ========================

@app.get("/verify/{serial}", response_class=HTMLResponse)
def verify_certificate(serial: str):

    db = SessionLocal()
    cert = db.query(Certificate).filter(Certificate.serial == serial).first()
    db.close()

    if not cert:
        status_title = "❌ Certificado no encontrado"
        status_type = "error"
        name = "No disponible"
        event = "No registrado"
        event_type = "No registrado"
        fecha_html = ""
        qr_html = ""

    elif cert.status != "valid":
        status_title = "⚠️ Certificado inválido"
        status_type = "warning"
        name = cert.participant
        event = cert.event_name
        event_type = cert.event_type

        fecha_html = f"""
        <p style="text-align:center;font-size:13px;color:#7a8793;margin-top:10px;">
        Emitido el: {cert.created_at.strftime("%d/%m/%Y") if cert.created_at else ''}
        </p>
        """

        qr_html = f"""
        <img src="/qrs/{serial}.png" width="120" style="margin-top:15px;">
        """

    else:
        status_title = "✅ Certificado válido"
        status_type = "success"
        name = cert.participant
        event = cert.event_name
        event_type = cert.event_type

        fecha_html = f"""
        <p style="text-align:center;font-size:13px;color:#7a8793;margin-top:10px;">
        Emitido el: {cert.created_at.strftime("%d/%m/%Y") if cert.created_at else ''}
        </p>
        """

        qr_html = f"""
        <img src="/qrs/{serial}.png" width="120" style="margin-top:15px;">
        """

    if status_type == "success":
        bg_color = "#e6f4ea"
        text_color = "#1B9943"
    elif status_type == "warning":
        bg_color = "#fff4e5"
        text_color = "#e67e22"
    else:
        bg_color = "#fdecea"
        text_color = "#c0392b"

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
    <meta charset="UTF-8">
    <title>Certificado</title>
    </head>

    <body style="font-family:Arial;background:#edf3f7;margin:0;">

    <div style="max-width:620px;margin:40px auto;background:white;border-radius:18px;padding:30px;">

        <div style="background:{bg_color};color:{text_color};padding:10px;border-radius:10px;text-align:center;font-weight:bold;">
        {status_title}
        </div>

        <h2 style="text-align:center;margin-top:20px;">{name}</h2>

        <p style="text-align:center;">{event} - {event_type}</p>

        <div style="text-align:center;margin-top:20px;">
            <b>{serial}</b>
            {fecha_html}
            {qr_html}
        </div>

    </div>

    </body>
    </html>
    """
