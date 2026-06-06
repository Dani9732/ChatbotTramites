import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import google.generativeai as genai


load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

modelo = genai.GenerativeModel("gemini-2.5-flash")

app = FastAPI()


with open("tramites.json", "r", encoding="utf-8") as f:
    TRAMITES = json.load(f)

with open("pasos.json", "r", encoding="utf-8") as f:
    PASOS = json.load(f)


class ChatRequest(BaseModel):
    mensaje: str


@app.post("/chat")
def chat(req: ChatRequest):
    mensaje = req.mensaje.lower()

    negocio_encontrado = None
    tramite_encontrado = None

    # 1. Buscar si el usuario mencionó un trámite
    for tramite in PASOS.keys():
        if tramite.lower() in mensaje:
            tramite_encontrado = tramite
            break

    # 2. Buscar si el usuario mencionó un negocio
    for clave, info in TRAMITES.items():
        if clave.lower() in mensaje or info["nombre"].lower() in mensaje:
            negocio_encontrado = info
            break

    # 3. Crear contexto según lo detectado
    if tramite_encontrado:
        contexto = f"""
El usuario quiere información sobre el trámite: {tramite_encontrado}

Pasos para realizarlo:
{json.dumps(PASOS[tramite_encontrado], ensure_ascii=False, indent=2)}
"""
    elif negocio_encontrado:
        contexto = f"""
Negocio detectado: {negocio_encontrado["nombre"]}

Trámites necesarios:
{json.dumps(negocio_encontrado["tramites"], ensure_ascii=False, indent=2)}
"""
    else:
        contexto = """
No se detectó un negocio ni un trámite específico.
Pide al usuario que indique qué negocio quiere abrir o sobre qué trámite quiere información.
"""

    respuesta = modelo.generate_content(
        f"""
Eres un asesor para apertura de negocios en México.

Reglas:
- Responde de forma breve y clara.
- No muestres todos los pasos de golpe.
- Si detectas un negocio, muestra solo la lista de trámites necesarios.
- Si detectas un trámite, muestra solo los pasos para realizar ese trámite.
- Usa únicamente la información proporcionada.
- No inventes requisitos.
- No pidas el negocio si el usuario ya preguntó por un trámite específico.

Información disponible:
{contexto}

Mensaje del usuario:
{req.mensaje}
"""
    )

    return {
        "respuesta": respuesta.text
    }


app.mount("/", StaticFiles(directory="static", html=True), name="static")