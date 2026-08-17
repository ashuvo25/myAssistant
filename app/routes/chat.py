import sys
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

# Add scripts directory to path so imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from source_manager import SourceManager
from context_processor import process_context
from llm_client import generate_answer

router = APIRouter()

# Initialize source manager once at startup
_source_manager = None


def get_source_manager():
    global _source_manager
    if _source_manager is None:
        _source_manager = SourceManager()
    return _source_manager


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    route: str
    sources: list
    reason: str


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    Full RAG pipeline:
      1. Route the query to the right sources
      2. Fetch data from those sources
      3. Build context
      4. Generate answer with GPT-4o-mini
    """

    manager = get_source_manager()

    # Step 1+2: Route + Fetch
    source_response = manager.execute_route(
        request.message
    )

    # Step 3: Build context
    context = process_context(source_response)

    # Step 4: Generate answer
    answer = generate_answer(
        question=request.message,
        context=context,
    )

    return ChatResponse(
        answer=answer,
        route=source_response.get("route", "unknown"),
        sources=source_response.get("sources", []),
        reason=source_response.get("reason", ""),
    )
