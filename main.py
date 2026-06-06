import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
import google.generativeai as genai

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

modelo = genai.GenerativeModel("gemini-2.5-flash")

app = FastAPI()

with open("tramites.json", "r", encoding="utf-8") as f:
    TRAMITES = json.load(f)

with open("pasos.json", "r", encoding="utf-8") as f:
    PASOS = json.load(f)


class ChatRequest(BaseModel):
    mensaje: str


estado_usuario = {
    "fase": "seleccion_negocio",
    "negocio": None
}


def buscar_negocio(mensaje):
    mensaje = mensaje.lower()

    for clave, info in TRAMITES.items():
        nombre = info["nombre"].lower()

        if clave.lower() in mensaje or nombre in mensaje:
            return clave

    return None


def buscar_tramite(mensaje, negocio):
    mensaje = mensaje.lower()
    tramites = TRAMITES[negocio]["tramites"]

    for tramite in tramites:
        if tramite.lower() in mensaje:
            return tramite

    return None


def listar_tramites(negocio):
    info = TRAMITES[negocio]

    texto = f"Para abrir una {info['nombre']} necesitas estos trámites:\n\n"

    for i, tramite in enumerate(info["tramites"], start=1):
        texto += f"{i}. {tramite}\n"

    texto += "\n¿Sobre cuál trámite quieres que te explique los pasos?"

    return texto


def explicar_pasos(tramite):
    pasos = PASOS.get(tramite)

    if not pasos:
        return "No tengo pasos registrados para ese trámite."

    texto = f"Pasos para {tramite}:\n\n"

    for i, paso in enumerate(pasos, start=1):
        texto += f"{i}. {paso}\n"

    texto += "\n¿Quieres consultar otro trámite de este negocio?"

    return texto


@app.post("/chat")
def chat(req: ChatRequest):
    mensaje = req.mensaje.strip()
    mensaje_lower = mensaje.lower()

    fase = estado_usuario["fase"]
    negocio_actual = estado_usuario["negocio"]

    if mensaje_lower in ["reiniciar", "empezar de nuevo", "reset"]:
        estado_usuario["fase"] = "seleccion_negocio"
        estado_usuario["negocio"] = None

        return {
            "respuesta": "Listo. ¿Qué tipo de negocio quieres abrir?"
        }

    if fase == "seleccion_negocio":
        negocio = buscar_negocio(mensaje)

        if negocio:
            estado_usuario["negocio"] = negocio
            estado_usuario["fase"] = "seleccion_tramite"

            return {
                "respuesta": listar_tramites(negocio)
            }

        return {
            "respuesta": "Claro. Primero dime qué tipo de negocio quieres abrir. Por ejemplo: cafetería, abarrotes, papelería o restaurante."
        }

    if fase == "seleccion_tramite":
        tramite = buscar_tramite(mensaje, negocio_actual)

        if tramite:
            estado_usuario["fase"] = "viendo_pasos"

            return {
                "respuesta": explicar_pasos(tramite)
            }

        return {
            "respuesta": "No encontré ese trámite en la lista. Escribe uno de estos:\n\n" + listar_tramites(negocio_actual)
        }

    if fase == "viendo_pasos":
        if mensaje_lower in ["si", "sí", "simon", "claro", "quiero otro", "otro"]:
            estado_usuario["fase"] = "seleccion_tramite"

            return {
                "respuesta": listar_tramites(negocio_actual)
            }

        if mensaje_lower in ["no", "gracias", "ya no"]:
            estado_usuario["fase"] = "seleccion_negocio"
            estado_usuario["negocio"] = None

            return {
                "respuesta": "Perfecto. Si quieres consultar otro negocio, dime cuál quieres abrir."
            }

        tramite = buscar_tramite(mensaje, negocio_actual)

        if tramite:
            return {
                "respuesta": explicar_pasos(tramite)
            }

        return {
            "respuesta": "Puedes escribir el nombre de otro trámite o responder 'sí' para ver la lista otra vez."
        }


app.mount("/", StaticFiles(directory="static", html=True), name="static")