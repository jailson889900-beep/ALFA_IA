import os
import random
import re
import difflib
import datetime
import math
from flask import Flask, request

# 🔥 FIREBASE
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

app = Flask(__name__)

# -------------------
# FUNÇÕES
# -------------------

def limpar(txt):
    txt = txt.lower().strip()
    txt = re.sub(r"[^\w\s]", "", txt)
    return txt

def pegar(valor):
    if isinstance(valor, list):
        return random.choice(valor)
    return valor

# -------------------
# FIREBASE MEMÓRIA
# -------------------

def salvar_memoria(pergunta, resposta):
    doc_ref = db.collection("memoria").document(pergunta)
    doc = doc_ref.get()

    if doc.exists:
        dados = doc.to_dict()
        respostas = dados.get("respostas", [])
        respostas.append(resposta)
    else:
        respostas = [resposta]

    doc_ref.set({
        "respostas": respostas
    })


def buscar_memoria(pergunta):
    doc = db.collection("memoria").document(pergunta).get()

    if doc.exists:
        dados = doc.to_dict()
        return random.choice(dados.get("respostas", []))

    return None

# -------------------
# CORREÇÕES
# -------------------

def corrigir_termo(txt):
    correcoes = {
        "pedro alves cabral": "pedro álvares cabral",
        "donald trunp": "donald trump",
        "capitar da franca": "capital da frança"
    }
    return correcoes.get(txt, txt)

# -------------------
# CAPITAL
# -------------------

def responder_capital(pergunta):
    capitais = {
        "brasil": "Brasília",
        "frança": "Paris",
        "estados unidos": "Washington, D.C.",
        "japão": "Tóquio",
        "argentina": "Buenos Aires",
        "portugal": "Lisboa",
        "inglaterra": "Londres",
        "reino unido": "Londres"
    }

    if "capital" in pergunta:
        for pais, capital in capitais.items():
            if pais in pergunta:
                return f"A capital de {pais.title()} é {capital}."
    return None

# -------------------
# SENTIMENTOS
# -------------------

def responder_sentimento(pergunta):

    if "triste" in pergunta:
        return "Sinto muito. Quer conversar comigo?"

    if "feliz" in pergunta:
        return "Que bom ouvir isso."

    if "raiva" in pergunta:
        return "Entendo sua raiva."

    if "ansioso" in pergunta:
        return "Respire fundo. Estou aqui."

    return None

# -------------------
# BASE INICIAL (Firebase)
# -------------------

base = {
    "oi": ["Olá!", "Oi!"],
    "ola": ["Olá!"],
    "quem e voce": ["Sou a Alfa IA."],
    "seu nome": ["Meu nome é Alfa IA."]
}

for pergunta, respostas in base.items():
    doc = db.collection("memoria").document(pergunta).get()
    if not doc.exists:
        db.collection("memoria").document(pergunta).set({
            "respostas": respostas
        })

# -------------------
# IA
# -------------------

def responder(user):

    pergunta = limpar(user)
    pergunta = corrigir_termo(pergunta)

    r = responder_capital(pergunta)
    if r:
        return r

    r = responder_sentimento(pergunta)
    if r:
        return r

    if "hora" in pergunta:
        agora = datetime.datetime.now().strftime("%H:%M")
        return f"Agora são {agora}"

    if pergunta == "pi":
        return str(math.pi)

    try:
        if any(x in pergunta for x in ["+", "-", "*", "/"]):
            return str(eval(pergunta))
    except:
        pass

    res = buscar_memoria(pergunta)
    if res:
        return res

    return "__APRENDER__"

# -------------------
# SITE
# -------------------

@app.route("/")
def home():
    return """
    <html>
    <body style='font-family:Arial;text-align:center;margin-top:80px;background:#111;color:white;'>

    <h1>ALFA IA</h1>

    <form action='/chat'>
        <input name='msg' placeholder='Digite sua pergunta'
        style='width:300px;height:45px;font-size:18px;border-radius:10px;padding:10px;'>
        <br><br>
        <button style='width:160px;height:45px;border:none;
        border-radius:10px;background:#00cc66;color:white;font-size:18px;'>
        Enviar
        </button>
    </form>

    </body>
    </html>
    """

@app.route("/chat")
def chat():

    msg = request.args.get("msg")
    ensinar = request.args.get("ensinar")

    pergunta = limpar(msg)

    if ensinar:
        salvar_memoria(pergunta, ensinar)

        return """
        <html>
        <body style='font-family:Arial;text-align:center;margin-top:80px;background:#111;color:white;'>

        <h1>ALFA IA</h1>

        <p style='font-size:24px;'>Aprendi.</p>

        <a href='/'>Voltar</a>

        </body>
        </html>
        """

    resposta = responder(msg)

    if resposta == "__APRENDER__":
        return f"""
        <html>
        <body style='font-family:Arial;text-align:center;margin-top:80px;background:#111;color:white;'>

        <h1>ALFA IA</h1>

        <p>Não sei responder isso.</p>
        <p>Me ensine:</p>

        <form action='/chat'>
            <input type='hidden' name='msg' value='{msg}'>

            <input name='ensinar'
            placeholder='Digite a resposta'
            style='width:300px;height:45px;font-size:18px;border-radius:10px;padding:10px;'>

            <br><br>

            <button style='width:160px;height:45px;border:none;
            border-radius:10px;background:#00cc66;color:white;font-size:18px;'>
            Ensinar
            </button>
        </form>

        </body>
        </html>
        """

    return f"""
    <html>
    <body style='font-family:Arial;text-align:center;margin-top:80px;background:#111;color:white;'>

    <h1>ALFA IA</h1>

    <p style='font-size:24px;'>{resposta}</p>

    <a href='/'>Voltar</a>

    </body>
    </html>
    """

# -------------------
# RODAR (SÓ NO PC)
# -------------------

app.run(host="127.0.0.1", port=5000)	