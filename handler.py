import runpod

def handler(event):
    input_data = event["input"]

    return {
        "response": "ALFA IA online",
        "input_recebido": input_data
    }

runpod.serverless.start({
    "handler": handler
})