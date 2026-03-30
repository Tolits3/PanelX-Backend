from fastapi import APIRouter

router = APIRouter()

@router.get("/all")
def get_all_series():
    return [
        {"id": 1, "title": "Demo Series"}
    ]