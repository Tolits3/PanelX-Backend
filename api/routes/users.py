from fastapi import APIRouter

router = APIRouter()

@router.get("/{user_id}")
def get_user(user_id: str):
    return {
        "uid": user_id,
        "username": "TestUser",
        "role": "creator"
    }

@router.post("/create")
def create_user(data: dict):
    return {
        "message": "User created",
        "user": data
    }