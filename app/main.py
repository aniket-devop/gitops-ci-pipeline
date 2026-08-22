from fastapi import FastAPI

app = FastAPI()

APP_VERSION = "1.0.0"

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/version")
def version():
    return {"version": APP_VERSION, "message": "Hello from GitOps demo app v1"}

@app.get("/")
def root():
    return {"service": "gitops-demo-app", "status": "running"}