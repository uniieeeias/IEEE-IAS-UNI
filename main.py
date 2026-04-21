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
def generate_certificate(data: CertificateRequest):

    db = SessionLocal()

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

    # ========================
    # CASO: NO EXISTE
    # ========================
    if not cert:
        status_title = "❌ Certificado no encontrado"
        status_type = "error"
        name = "No disponible"
        event = "No registrado"
        event_type = "No registrado"
        fecha_html = ""
        qr_html = ""

    # ========================
    # CASO: INVÁLIDO
    # ========================
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

    # ========================
    # CASO: VÁLIDO
    # ========================
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

    # ========================
    # COLORES
    # ========================
    if status_type == "success":
        bg_color = "#e6f4ea"
        text_color = "#1B9943"
    elif status_type == "warning":
        bg_color = "#fff4e5"
        text_color = "#e67e22"
    else:
        bg_color = "#fdecea"
        text_color = "#c0392b"


    # ========================
    # HTML FINAL
    # ========================
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

<table width="100%">
<tr>
<td width="48%" style="background:#f4f9fc;padding:20px;border-radius:12px;">
<div style="font-size:13px;color:#7a8793;">Evento</div>
<div style="font-size:15px;font-weight:bold;">{event}</div>
</td>

<td width="4%"></td>

<td width="48%" style="background:#f4fbf6;padding:20px;border-radius:12px;">
<div style="font-size:13px;color:#7a8793;">Tipo</div>
<div style="font-size:15px;font-weight:bold;">{event_type}</div>
</td>
</tr>
</table>

<div style="margin-top:25px;padding:15px;background:#f8fafc;border-radius:10px;text-align:center;">
<div style="font-size:12px;color:#7a8793;">Código de verificación</div>
<div style="font-size:14px;color:#16679E;font-weight:bold;">{serial}</div>
{fecha_html}
{qr_html}
</div>

<p style="text-align:center;margin-top:25px;color:#555;">
<strong>IEEE IAS UNI - UNI</strong>
</p>

</td>
</tr>

<tr>
<td style="background:#101820;padding:25px;text-align:center;">
<div style="color:white;font-size:17px;font-weight:bold;">IEEE IAS UNI</div>
<div style="color:#a5b0bb;font-size:12px;">Sistema de Certificación Digital</div>
</td>
</tr>

</table>

</td>
</tr>
</table>

</body>
</html>
"""
