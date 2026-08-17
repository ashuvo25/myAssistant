import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routes import health, chat, webhook

# Load .env variables
load_dotenv()

app = FastAPI(
    title="Shuvo AI Portfolio Assistant API",
    description="Self-Hosted RAG Backend for Portfolio Assistant",
    version="1.0.0"
)

# Configure CORS
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(webhook.router)

@app.get("/")
def root():
    return {
        "service": "Shuvo AI Portfolio Assistant API",
        "status": "online",
        "docs_url": "/docs",
        "health_url": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
