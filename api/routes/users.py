# backend/api/routes/users.py

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import json
import os
import shutil

router = APIRouter()

# User profiles stored in JSON file (can migrate to DB later)
USERS_FILE = "data/users.json"
AVATARS_DIR = "data/avatars"
os.makedirs("data", exist_ok=True)
os.makedirs(AVATARS_DIR, exist_ok=True)

# Initialize file if it doesn't exist
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

# ========================================
# MODELS
# ========================================
class UserProfile(BaseModel):
    uid: str
    email: str
    username: Optional[str] = None
    role: str  # "creator" or "reader"
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

class UpdateProfile(BaseModel):
    username: Optional[str] = None
    bio: Optional[str] = None

class UserResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict] = None

# ========================================
# HELPER FUNCTIONS
# ========================================
def load_users():
    """Load users from file"""
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    """Save users to file"""
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def generate_username_from_email(email: str) -> str:
    """Generate default username from email"""
    return email.split("@")[0]

# ========================================
# ROUTES
# ========================================

@router.post("/create")
async def create_user(profile: UserProfile):
    """Create new user profile after Firebase signup"""
    try:
        users = load_users()
        
        # Check if user already exists
        if profile.uid in users:
            return UserResponse(
                success=False,
                message="User already exists"
            )
        
        # Generate username if not provided
        if not profile.username:
            profile.username = generate_username_from_email(profile.email)
        
        # Check if username is taken
        for uid, user_data in users.items():
            if user_data.get("username") == profile.username:
                profile.username = f"{profile.username}_{profile.uid[:4]}"
                break
        
        # Store user profile
        users[profile.uid] = {
            "uid": profile.uid,
            "email": profile.email,
            "username": profile.username,
            "role": profile.role,
            "avatar_url": profile.avatar_url,
            "bio": profile.bio,
            "created_at": profile.created_at,
            "updated_at": datetime.now().isoformat()
        }
        
        save_users(users)
        
        return UserResponse(
            success=True,
            message="User profile created successfully",
            user=users[profile.uid]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{uid}")
async def get_user(uid: str):
    """Get user profile by UID"""
    try:
        users = load_users()
        
        if uid not in users:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            success=True,
            message="User found",
            user=users[uid]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{uid}")
async def update_user(uid: str, updates: UpdateProfile):
    """Update user profile"""
    try:
        users = load_users()
        
        if uid not in users:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if new username is taken
        if updates.username:
            for user_uid, user_data in users.items():
                if user_uid != uid and user_data.get("username") == updates.username:
                    raise HTTPException(status_code=400, detail="Username already taken")
            
            users[uid]["username"] = updates.username
        
        if updates.bio is not None:
            users[uid]["bio"] = updates.bio
        
        users[uid]["updated_at"] = datetime.now().isoformat()
        
        save_users(users)
        
        return UserResponse(
            success=True,
            message="Profile updated successfully",
            user=users[uid]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{uid}/avatar")
async def upload_avatar(uid: str, file: UploadFile = File(...)):
    """Upload user avatar"""
    try:
        users = load_users()
        
        if uid not in users:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type. Only images allowed.")
        
        # Generate filename
        extension = file.filename.split(".")[-1]
        filename = f"{uid}.{extension}"
        filepath = os.path.join(AVATARS_DIR, filename)
        
        # Save file
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Update user profile
        avatar_url = f"http://localhost:8000/avatars/{filename}"
        users[uid]["avatar_url"] = avatar_url
        users[uid]["updated_at"] = datetime.now().isoformat()
        
        save_users(users)
        
        return UserResponse(
            success=True,
            message="Avatar uploaded successfully",
            user=users[uid]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/username/{username}")
async def check_username(username: str):
    """Check if username is available"""
    try:
        users = load_users()
        
        for uid, user_data in users.items():
            if user_data.get("username") == username:
                return {
                    "available": False,
                    "message": "Username is taken"
                }
        
        return {
            "available": True,
            "message": "Username is available"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{uid}")
async def delete_user(uid: str):
    """Delete user profile"""
    try:
        users = load_users()
        
        if uid not in users:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete avatar if exists
        if users[uid].get("avatar_url"):
            filename = users[uid]["avatar_url"].split("/")[-1]
            filepath = os.path.join(AVATARS_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        
        del users[uid]
        save_users(users)
        
        return {
            "success": True,
            "message": "User deleted successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))