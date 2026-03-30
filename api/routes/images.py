from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def test_images():
    return {"message": "Images route working 🎨"}