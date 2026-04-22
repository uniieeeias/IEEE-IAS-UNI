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

# 🔥 IMPORTANTE: en Render usa /tmp para evitar problemas de filesystem
QR_FOLDER = os.path.join("/tmp", "qrs")
os.makedirs(QR_FOLDER, exist_ok=True)

app = FastAPI()

# servir carpeta QR
app.mount("/qrs", StaticFiles(directory=QR_FOLDER), name="qrs")

# API KEY
API_KEY = os.getenv("API_KEY")


# ========================
# MODELO
# ========================

class CertificateRequest(BaseModel):
    event_code: str
    event_name: str
    event_type: str
    participant: str


# ========================
# SERIAL
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
def generate_certificate(data: CertificateRequest, x_api_key: str = Header(None)):

    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="No autorizado")

    db = SessionLocal()

    existing = db.query(Certificate).filter(
        Certificate.event_name == data.event_name,
        Certificate.participant == data.participant
    ).first()

    if existing:
        db.close()
        return {"message": "Este certificado ya existe", "serial": existing.serial}

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

    # ========================
    # QR GENERATION (FIX)
    # ========================
    qr = qrcode.make(verification_url)

    qr_filename = f"{serial}.png"
    qr_path = os.path.join(QR_FOLDER, qr_filename)

    qr.save(qr_path)

    # 🔥 validación real
    if not os.path.exists(qr_path):
        raise HTTPException(status_code=500, detail="No se pudo generar el QR")

    return {
        "serial": serial,
        "qr_url": f"{BASE_URL}/qrs/{qr_filename}",
        "verification_url": verification_url
    }


# ========================
# VERIFICACIÓN (TU DISEÑO ORIGINAL)
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verificación de Certificado</title>
    </head>

    <body style="margin:0;padding:0;background-color:#edf3f7;font-family:Arial,Helvetica,sans-serif;">

    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="padding:30px 10px;">
    <tr>
    <td align="center">

    <table width="620" cellpadding="0" cellspacing="0" border="0" style="background-color:#ffffff;border-radius:18px;overflow:hidden;box-shadow:0px 8px 25px rgba(0,0,0,0.08);">

    <tr>
    <td style="background:linear-gradient(90deg,#16679E,#1B9943);height:8px;"></td>
    </tr>

    <tr>
    <td align="center" style="padding:25px 20px 10px 20px;">
    <div style="background-color:{bg_color};color:{text_color};padding:12px 20px;border-radius:10px;font-weight:bold;font-size:16px;display:inline-block;">
    {status_title}
    </div>
    </td>
    </tr>

    <tr>
    <td align="center" style="padding:20px 30px 10px 30px;">

    <div style="font-size:12px;color:#1B9943;font-weight:bold;letter-spacing:1px;">
    IEEE IAS UNI · CERTIFICACIÓN
    </div>

    <h2 style="margin:15px 0 5px 0;color:#101820;">
    {name}
    </h2>

    <p style="margin:0;font-size:14px;color:#6b7785;">
    Verificación de autenticidad del certificado
    </p>

    </td>
    </tr>

    <tr>
    <td style="padding:25px 35px;">

    <div style="text-align:center;">
        <div style="font-size:13px;">Evento: <b>{event}</b></div>
        <div style="font-size:13px;">Tipo: <b>{event_type}</b></div>
    </div>

    <div style="margin-top:20px;text-align:center;">
        <b>{serial}</b>
        {fecha_html}
        {qr_html}
    </div>

    </td>
    </tr>

    </table>

    </td>
    </tr>
    </table>

    </body>
    </html>
    """
