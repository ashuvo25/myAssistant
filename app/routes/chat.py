from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
def chat_endpoint(request: ChatRequest):
    return {
        "answer": f"Received: '{request.message}'. Context retrieval and LLM inference ready.",
        "sources": []
    }
