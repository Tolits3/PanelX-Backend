from fastapi import APIRouter
from database.memory_optimized import query_optimized, cleanup_connections

router = APIRouter()

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
            # Create user if not exists (for demo purposes)
            query_optimized(
                "INSERT IGNORE INTO users (uid, username, role, email) VALUES (:uid, :username, :role, :email)",
                {"uid": user_id, "username": f"User_{user_id[:8]}", "role": "reader", "email": f"{user_id}@demo.com"},
                fetch=None
            )
            return {"success": True, "user": {"uid": user_id, "username": f"User_{user_id[:8]}", "role": "reader"}}
            
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cleanup_connections()

@router.post("/create")
def create_user(data: dict):
    try:
        query_optimized(
            "INSERT INTO users (uid, email, username, role, avatar_url, bio) VALUES (:uid, :email, :username, :role, :avatar_url, :bio)",
            data,
            fetch=None
        )
        return {"success": True, "message": "User created", "user": data}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cleanup_connections()