from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="Chat API", version="1.0.0")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat() + "Z"}

@app.post("/api/chat")
async def chat():
    return {"message": "ok"}
