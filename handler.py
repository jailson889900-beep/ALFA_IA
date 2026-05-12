from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "ALFA IA ONLINE"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    pergunta = data.get("message", "")

    resposta = f"ALFA respondeu: {pergunta}"

    return jsonify({
        "response": resposta
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)