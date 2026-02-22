# backend/api/routes/users.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import os

router = APIRouter()

# Check if using MySQL or JSON
DATABASE_URL = os.getenv("DATABASE_URL")
USE_DB = bool(DATABASE_URL)

if USE_DB:
    from sqlalchemy import create_engine, text
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    
    def query(sql: str, params: dict = None, fetch: str = "all"):
        with engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            conn.commit()
            if fetch == "one":
                row = result.fetchone()
                return dict(row._mapping) if row else None
            elif fetch == "all":
                rows = result.fetchall()
                return [dict(r._mapping) for r in rows]
            return None
else:
    import json
    DATA_DIR = "data"
    os.makedirs(DATA_DIR, exist_ok=True)
    
    def load_json(filename):
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump({}, f)
        with open(path, "r") as f:
            return json.load(f)
    
    def save_json(filename, data):
        path = os.path.join(DATA_DIR, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

# ─────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────
class UserProfile(BaseModel):
    uid: str
    email: str
    username: Optional[str] = None
    role: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    created_at: Optional[str] = None

class UpdateProfile(BaseModel):
    username: Optional[str] = None
    bio: Optional[str] = None

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@router.post("/create")
async def create_user(profile: UserProfile):
    """Create new user account"""
    try:
        # Generate username if not provided
        if not profile.username:
            profile.username = profile.email.split("@")[0]
        
        # Set created_at if not provided
        if not profile.created_at:
            profile.created_at = datetime.now().isoformat()

        if USE_DB:
            # Check if user already exists
            existing = query(
                "SELECT uid FROM users WHERE uid = :uid",
                {"uid": profile.uid},
                fetch="one"
            )
            
            if existing:
                # User exists, just return success
                user = query(
                    "SELECT * FROM users WHERE uid = :uid",
                    {"uid": profile.uid},
                    fetch="one"
                )
                return {
                    "success": True,
                    "message": "User already exists",
                    "user": user
                }
            
            # Check if username is taken
            username_taken = query(
                "SELECT uid FROM users WHERE username = :username",
                {"username": profile.username},
                fetch="one"
            )
            
            if username_taken:
                profile.username = f"{profile.username}_{profile.uid[:4]}"
            
            # Create new user
            query("""
                INSERT INTO users (uid, email, username, role, avatar_url, bio, credit_balance, created_at, updated_at)
                VALUES (:uid, :email, :username, :role, :avatar_url, :bio, 1000, :created_at, :updated_at)
            """, {
                "uid": profile.uid,
                "email": profile.email,
                "username": profile.username,
                "role": profile.role,
                "avatar_url": profile.avatar_url,
                "bio": profile.bio,
                "created_at": profile.created_at,
                "updated_at": datetime.now().isoformat()
            }, fetch=None)
            
            # Get the created user
            user = query(
                "SELECT * FROM users WHERE uid = :uid",
                {"uid": profile.uid},
                fetch="one"
            )
            
            # Give free credits
            import uuid
            query("""
                INSERT INTO credit_transactions (id, user_uid, transaction_type, amount, balance_after, description, created_at)
                VALUES (:id, :user_uid, 'free', 1000, 1000, '🎉 Welcome! 1000 free credits', :created_at)
            """, {
                "id": str(uuid.uuid4()),
                "user_uid": profile.uid,
                "created_at": datetime.now().isoformat()
            }, fetch=None)
            
            return {
                "success": True,
                "message": "User created successfully",
                "user": user
            }
        
        else:
            # JSON fallback
            users = load_json("users.json")
            
            if profile.uid in users:
                return {
                    "success": True,
                    "message": "User already exists",
                    "user": users[profile.uid]
                }
            
            users[profile.uid] = {
                "uid": profile.uid,
                "email": profile.email,
                "username": profile.username,
                "role": profile.role,
                "avatar_url": profile.avatar_url,
                "bio": profile.bio,
                "credit_balance": 1000,
                "created_at": profile.created_at,
                "updated_at": datetime.now().isoformat()
            }
            
            save_json("users.json", users)
            
            return {
                "success": True,
                "message": "User created successfully",
                "user": users[profile.uid]
            }
    
    except Exception as e:
        print(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{uid}")
async def get_user(uid: str):
    """Get user by UID"""
    try:
        if USE_DB:
            user = query(
                "SELECT * FROM users WHERE uid = :uid",
                {"uid": uid},
                fetch="one"
            )
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {
                "success": True,
                "user": user
            }
        else:
            users = load_json("users.json")
            
            if uid not in users:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {
                "success": True,
                "user": users[uid]
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{uid}")
async def update_user(uid: str, updates: UpdateProfile):
    """Update user profile"""
    try:
        if USE_DB:
            # Check if username is taken
            if updates.username:
                taken = query(
                    "SELECT uid FROM users WHERE username = :username AND uid != :uid",
                    {"username": updates.username, "uid": uid},
                    fetch="one"
                )
                
                if taken:
                    raise HTTPException(status_code=400, detail="Username already taken")
            
            # Update user
            query("""
                UPDATE users
                SET username = COALESCE(:username, username),
                    bio = COALESCE(:bio, bio),
                    updated_at = :updated_at
                WHERE uid = :uid
            """, {
                "username": updates.username,
                "bio": updates.bio,
                "updated_at": datetime.now().isoformat(),
                "uid": uid
            }, fetch=None)
            
            # Get updated user
            user = query(
                "SELECT * FROM users WHERE uid = :uid",
                {"uid": uid},
                fetch="one"
            )
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {
                "success": True,
                "message": "Profile updated",
                "user": user
            }
        
        else:
            users = load_json("users.json")
            
            if uid not in users:
                raise HTTPException(status_code=404, detail="User not found")
            
            if updates.username:
                users[uid]["username"] = updates.username
            
            if updates.bio is not None:
                users[uid]["bio"] = updates.bio
            
            users[uid]["updated_at"] = datetime.now().isoformat()
            
            save_json("users.json", users)
            
            return {
                "success": True,
                "message": "Profile updated",
                "user": users[uid]
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check/username/{username}")
async def check_username(username: str):
    """Check if username is available"""
    try:
        if USE_DB:
            taken = query(
                "SELECT uid FROM users WHERE username = :username",
                {"username": username},
                fetch="one"
            )
            
            return {"available": not taken}
        else:
            users = load_json("users.json")
            taken = any(u.get("username") == username for u in users.values())
            return {"available": not taken}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))