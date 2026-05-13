import runpod

def handler(event):
    input_data = event["input"]
    return {
        "response": f"ALFA recebeu: {input_data}"
    }

runpod.serverless.start({"handler": handler})