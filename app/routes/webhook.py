from fastapi import APIRouter

router = APIRouter()

@router.post("/webhook/cloudinary")
def cloudinary_webhook():
    return {
        "status": "success",
        "message": "Cloudinary webhook listener active"
    }
