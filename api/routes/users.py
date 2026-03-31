from fastapi import APIRouter
from pydantic import BaseModel
from database.memory_optimized import query_optimized, cleanup_connections

router = APIRouter()

class UserCreate(BaseModel):
    uid: str
    email: str
    username: str
    role: str
    avatar_url: str = None
    bio: str = None

@router.get("/profile/{firebase_uid}")
def get_user_profile(firebase_uid: str):
    """Get user profile after Firebase login"""
    try:
        user = query_optimized(
            "SELECT uid, username, role, avatar_url, bio, credit_balance FROM users WHERE uid = :uid",
            {"uid": firebase_uid},
            fetch="one"
        )
        
        if user:
            return {"success": True, "user": user}
        else:
            # User doesn't exist in our DB yet, return empty profile
            return {"success": True, "user": None, "needs_setup": True}
            
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cleanup_connections()

@router.get("/{user_id}")
def get_user(user_id: str):
    try:
        user = query_optimized(
            "SELECT uid, username, role, avatar_url, bio, credit_balance FROM users WHERE uid = :uid",
            {"uid": user_id},
            fetch="one"
        )
        
        if user:
            return {"success": True, "user": user}
        else:
            return {"success": False, "error": "User not found"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cleanup_connections()

@router.post("/create")
def create_user(user_data: UserCreate):
    try:
        # Check if user already exists
        existing = query_optimized(
            "SELECT uid FROM users WHERE uid = :uid OR email = :email",
            {"uid": user_data.uid, "email": user_data.email},
            fetch="one"
        )
        
        if existing:
            return {"success": False, "error": "User already exists"}
        
        # Create new user
        query_optimized(
            "INSERT INTO users (uid, email, username, role) VALUES (:uid, :email, :username, :role)",
            {
                "uid": user_data.uid,
                "email": user_data.email,
                "username": user_data.username,
                "role": user_data.role
            },
            fetch=None
        )
        
        return {"success": True, "message": "User created successfully", "user": {"uid": user_data.uid, "username": user_data.username, "role": user_data.role}}
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cleanup_connections()