from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Shuvo AI Portfolio Assistant API",
        "version": "1.0.0"
    }
