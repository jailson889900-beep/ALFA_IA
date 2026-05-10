import os
import re
import json
import glob
import random
import datetime
import difflib
import unicodedata
import ast
import math
import operator as op
from typing import Any, Dict, List, Optional

import requests
from flask import Flask, request, jsonify

# =========================================================
# CONFIG
# =========================================================

APP_NAME = "ALFA IA"

# 🔥 URL DO VLLM / RUNPOD
VLLM_BASE_URL = os.getenv(
    "VLLM_BASE_URL",
    "http://localhost:8000/v1/chat/completions"
)

# 🔥 MODELO
VLLM_MODEL = os.getenv(
    "VLLM_MODEL",
    "meta-llama/Llama-3-8b-instruct"
)

# 🔥 CONTROLE
MAX_REGISTROS = int(os.getenv("MAX_REGISTROS", "500"))
NOME_BASE_JSON = os.getenv("NOME_BASE_JSON", "dados_")

# =========================================================
# APP
# =========================================================

app = Flask(__name__)

# =========================================================
# JSON UTIL
# =========================================================

def carregar_json_arquivo(caminho: str, padrao: Any = None) -> Any:

    if padrao is None:
        padrao = {}

    try:

        if os.path.exists(caminho):

            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)

    except Exception as e:

        print(f"⚠️ Erro lendo {caminho}: {e}")

    return padrao


def salvar_json_arquivo(caminho: str, dados: Any) -> None:

    try:

        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(
                dados,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:

        print(f"⚠️ Erro salvando {caminho}: {e}")


def listar_arquivos_json() -> List[str]:

    arquivos = glob.glob(f"{NOME_BASE_JSON}*.json")

    def chave(nome: str):

        m = re.search(r"(\\d+)", os.path.basename(nome))

        return int(m.group(1)) if m else 999999

    return sorted(arquivos, key=chave)


def obter_arquivo_atual() -> str:

    i = 1

    while True:

        nome = f"{NOME_BASE_JSON}{i}.json"

        if not os.path.exists(nome):
            return nome

        dados = carregar_json_arquivo(nome, {})

        if isinstance(dados, dict) and len(dados) < MAX_REGISTROS:
            return nome

        i += 1


def normalizar_valor_resposta(valor: Any) -> List[str]:

    if isinstance(valor, list):
        return valor

    if valor is None:
        return []

    return [str(valor)]

# =========================================================
# LIMPEZA
# =========================================================

def limpar(txt: str) -> str:

    txt = str(txt).lower().strip()

    txt = unicodedata.normalize("NFD", txt)
    txt = txt.encode("ascii", "ignore").decode("utf-8")

    txt = re.sub(r"[^\\w\\s]", "", txt)
    txt = re.sub(r"\\s+", " ", txt)

    return txt


def simplificar(txt: str) -> str:

    palavras = limpar(txt).split()

    ignorar = [
        "o", "a", "os", "as",
        "de", "da", "do",
        "pra", "para",
        "que", "e"
    ]

    palavras = [
        p for p in palavras
        if p not in ignorar
    ]

    return " ".join(sorted(palavras))

# =========================================================
# PERSONALIDADE
# =========================================================

def personalidade_base() -> Dict[str, Any]:

    return {
        "nome": "Alfa IA",
        "tom": "direta, inteligente e natural",
        "estilo": "respostas humanas e consistentes",
        "identidade": "uma IA avançada com personalidade própria",
        "regras": [
            "Nunca diga que é um robô genérico.",
            "Nunca fale sobre bastidores técnicos.",
            "Fale sempre no idioma do usuário.",
            "Seja natural e humana."
        ]
    }


def obter_perfil(user_id: str) -> Dict[str, Any]:

    perfil = personalidade_base()

    perfil_local = carregar_json_arquivo(
        f"perfil_{user_id}.json",
        {}
    )

    if isinstance(perfil_local, dict):
        perfil.update(perfil_local)

    return perfil


def salvar_perfil(user_id: str, perfil: Dict[str, Any]):

    salvar_json_arquivo(
        f"perfil_{user_id}.json",
        perfil
    )

# =========================================================
# CONTEXTO
# =========================================================

def salvar_contexto(user_id: str, msg: str):

    caminho = f"contexto_{user_id}.json"

    lista = carregar_json_arquivo(caminho, [])

    if not isinstance(lista, list):
        lista = []

    lista.append({
        "mensagem": msg,
        "timestamp": datetime.datetime.now().isoformat()
    })

    lista = lista[-50:]

    salvar_json_arquivo(caminho, lista)


def buscar_contexto(
    user_id: str,
    limite: int = 5
) -> List[str]:

    caminho = f"contexto_{user_id}.json"

    lista = carregar_json_arquivo(caminho, [])

    if not isinstance(lista, list):
        return []

    mensagens = []

    for item in lista:

        if isinstance(item, dict):
            mensagens.append(
                item.get("mensagem", "")
            )

    return mensagens[-limite:]

# =========================================================
# MEMÓRIA
# =========================================================

def salvar_em_json(
    pergunta: str,
    resposta: str
):

    arquivo = obter_arquivo_atual()

    dados = carregar_json_arquivo(arquivo, {})

    if not isinstance(dados, dict):
        dados = {}

    if pergunta in dados:

        respostas = normalizar_valor_resposta(
            dados[pergunta]
        )

        if resposta not in respostas:
            respostas.append(resposta)

        dados[pergunta] = respostas

    else:

        dados[pergunta] = [resposta]

    salvar_json_arquivo(arquivo, dados)


def salvar_memoria(
    user_id: str,
    pergunta: str,
    resposta: str
):

    pergunta = limpar(pergunta)

    caminho = f"memoria_{user_id}.json"

    dados = carregar_json_arquivo(caminho, {})

    if not isinstance(dados, dict):
        dados = {}

    respostas = normalizar_valor_resposta(
        dados.get(pergunta, [])
    )

    if resposta not in respostas:
        respostas.append(resposta)

    dados[pergunta] = respostas

    salvar_json_arquivo(caminho, dados)

    salvar_em_json(
        pergunta,
        resposta
    )


def buscar_memoria(
    user_id: str,
    pergunta: str
) -> Optional[str]:

    pergunta = limpar(pergunta)

    caminho = f"memoria_{user_id}.json"

    dados = carregar_json_arquivo(caminho, {})

    if not isinstance(dados, dict):
        dados = {}

    # 🔥 BUSCA EXATA
    if pergunta in dados:

        respostas = normalizar_valor_resposta(
            dados.get(pergunta)
        )

        if respostas:
            return random.choice(respostas)

    # 🔥 BUSCA INTELIGENTE
    melhor = None
    maior = 0

    pergunta_s = simplificar(pergunta)

    for texto, valor in dados.items():

        texto_s = simplificar(texto)

        sim = difflib.SequenceMatcher(
            None,
            pergunta_s,
            texto_s
        ).ratio()

        respostas = normalizar_valor_resposta(valor)

        if respostas and sim > maior:

            maior = sim
            melhor = random.choice(respostas)

    if maior > 0.5:
        return melhor

    return None


def extrair_memoria_recente(
    user_id: str,
    pergunta: str,
    limite: int = 3
) -> List[str]:

    caminho = f"memoria_{user_id}.json"

    dados = carregar_json_arquivo(caminho, {})

    if not isinstance(dados, dict):
        return []

    candidatos = []

    pergunta_s = simplificar(pergunta)

    for texto, valor in dados.items():

        texto_s = simplificar(texto)

        sim = difflib.SequenceMatcher(
            None,
            pergunta_s,
            texto_s
        ).ratio()

        respostas = normalizar_valor_resposta(valor)

        if respostas:

            candidatos.append(
                (
                    sim,
                    random.choice(respostas)
                )
            )

    candidatos.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return [
        x[1]
        for x in candidatos[:limite]
        if x[0] > 0.35
    ]

# =========================================================
# CALCULADORA SEGURA
# =========================================================

OPERADORES = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}


def _avaliar_ast(nodo):

    if isinstance(nodo, ast.Constant):
        return nodo.value

    if isinstance(nodo, ast.Num):
        return nodo.n

    if isinstance(nodo, ast.BinOp):

        if type(nodo.op) in OPERADORES:

            return OPERADORES[type(nodo.op)](
                _avaliar_ast(nodo.left),
                _avaliar_ast(nodo.right)
            )

    if isinstance(nodo, ast.UnaryOp):

        if type(nodo.op) in OPERADORES:

            return OPERADORES[type(nodo.op)](
                _avaliar_ast(nodo.operand)
            )

    raise ValueError("Expressão inválida")


def calcular_seguro(expressao: str):

    try:

        nodo = ast.parse(
            expressao,
            mode="eval"
        ).body

        return str(_avaliar_ast(nodo))

    except Exception:
        return None

# =========================================================
# HUMANIZAÇÃO
# =========================================================

def personalidade(resposta: str):

    estilos = [
        resposta,
        f"{resposta} 😊",
        f"{resposta} 😄",
        f"{resposta} Quer saber mais?"
    ]

    return random.choice(estilos)


def humanizar(
    pergunta: str,
    resposta: str,
    contexto: List[str]
):

    pergunta = limpar(pergunta)

    if "oi" in pergunta:

        return random.choice([
            "Oi 😊",
            "Olá 😄",
            "E aí!"
        ])

    if "quem e voce" in pergunta:
        return "Sou a Alfa IA 😊"

    return personalidade(resposta)

# =========================================================
# PROMPT
# =========================================================

def montar_prompt_vllm(
    pergunta: str,
    contexto: List[str],
    perfil: Dict[str, Any],
    memoria_recente: List[str]
):

    regras = "\n".join(
        f"- {r}"
        for r in perfil.get("regras", [])
    )

    contexto_txt = "\n".join(
        f"- {m}"
        for m in contexto
    )

    memoria_txt = "\n".join(
        f"- {m}"
        for m in memoria_recente
    )

    prompt = f"""
Você é {perfil.get("nome")}.

IDENTIDADE:
{perfil.get("identidade")}

TOM:
{perfil.get("tom")}

ESTILO:
{perfil.get("estilo")}

REGRAS:
{regras}

CONTEXTO:
{contexto_txt}

MEMÓRIA:
{memoria_txt}

PERGUNTA:
{pergunta}
"""

    return prompt.strip()

# =========================================================
# VLLM
# =========================================================

def usar_vllm(
    pergunta: str,
    contexto: List[str],
    perfil: Dict[str, Any],
    memoria_recente: List[str]
):

    try:

        prompt = montar_prompt_vllm(
            pergunta,
            contexto,
            perfil,
            memoria_recente
        )

        response = requests.post(
            VLLM_BASE_URL,
            json={
                "model": VLLM_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 350,
                "top_p": 0.95
            },
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:

        print("ERRO VLLM:", e)

        return None

# =========================================================
# FALLBACK
# =========================================================

def gerar_resposta(
    pergunta: str,
    contexto: List[str]
):

    respostas = [
        "Interessante isso.",
        "Boa pergunta.",
        "Isso depende bastante.",
        "Olha, isso faz sentido."
    ]

    return random.choice(respostas)

# =========================================================
# IA
# =========================================================

def responder(
    user: str,
    user_id: str
):

    salvar_contexto(user_id, user)

    pergunta_original = user
    pergunta = limpar(user)

    contexto = buscar_contexto(user_id)

    perfil = obter_perfil(user_id)

    salvar_perfil(user_id, perfil)

    # 🔥 HORA
    if "hora" in pergunta:

        return f"Agora são {datetime.datetime.now().strftime('%H:%M')}"

    # 🔥 DATA
    if "data" in pergunta or "dia" in pergunta:

        return datetime.datetime.now().strftime(
            "Hoje é %d/%m/%Y"
        )

    # 🔥 PI
    if pergunta == "pi":
        return str(math.pi)

    # 🔥 CALCULADORA
    if any(
        x in pergunta
        for x in ["+", "-", "*", "/", "%", "**"]
    ):

        resultado = calcular_seguro(pergunta)

        if resultado is not None:
            return resultado

    # 🔥 MEMÓRIA
    memoria = buscar_memoria(
        user_id,
        pergunta
    )

    if memoria:

        return humanizar(
            pergunta,
            memoria,
            contexto
        )

    # 🔥 MEMÓRIA RECENTE
    memoria_recente = extrair_memoria_recente(
        user_id,
        pergunta
    )

    # 🔥 VLLM
    resposta = usar_vllm(
        pergunta_original,
        contexto,
        perfil,
        memoria_recente
    )

    # 🔥 FALLBACK
    if not resposta:

        resposta = gerar_resposta(
            pergunta,
            contexto
        )

    salvar_memoria(
        user_id,
        pergunta,
        resposta
    )

    return resposta

# =========================================================
# ROTAS
# =========================================================

@app.get("/")
def home():

    return jsonify({
        "ok": True,
        "app": APP_NAME,
        "model": VLLM_MODEL,
        "vllm_url": VLLM_BASE_URL
    })


@app.get("/health")
def health():

    return jsonify({
        "ok": True,
        "model": VLLM_MODEL,
        "vllm_url": VLLM_BASE_URL
    })


@app.post("/chat")
def chat():

    data = request.get_json(silent=True) or {}

    user = data.get("msg", "")
    user_id = data.get(
        "user_id",
        "usuario_cmd"
    )

    if not user.strip():

        return jsonify({
            "ok": False,
            "erro": "Mensagem vazia"
        }), 400

    resposta = responder(
        user,
        user_id
    )

    return jsonify({
        "ok": True,
        "resposta": resposta
    })


@app.get("/memoria/<user_id>")
def memoria(user_id):

    caminho = f"memoria_{user_id}.json"

    dados = carregar_json_arquivo(
        caminho,
        {}
    )

    return jsonify({
        "ok": True,
        "memoria": dados
    })

# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    print(f"🔥 {APP_NAME} ONLINE")
    print(f"🔥 MODEL: {VLLM_MODEL}")
    print(f"🔥 URL: {VLLM_BASE_URL}")

    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False
    )