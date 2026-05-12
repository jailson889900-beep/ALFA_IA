import runpod

def handler(job):
    return {
        "message": "ALFA IA online"
    }

runpod.serverless.start({
    "handler": handler
})