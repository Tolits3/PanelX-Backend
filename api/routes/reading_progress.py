# backend/api/routes/reading_progress.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import json
import os

router = APIRouter()

# For now, we'll use a simple JSON file as database
# Later you can migrate to PostgreSQL/MongoDB
PROGRESS_FILE = "data/reading_progress.json"
os.makedirs("data", exist_ok=True)

# Initialize file if it doesn't exist
if not os.path.exists(PROGRESS_FILE):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({}, f)

# ========================================
# MODELS
# ========================================
class ReadingProgress(BaseModel):
    user_id: str
    comic_id: str
    chapter_id: str
    page_number: Optional[int] = 1
    completed: bool = False
    last_read: str

class ProgressResponse(BaseModel):
    success: bool
    message: str
    progress: Optional[dict] = None

# ========================================
# HELPER FUNCTIONS
# ========================================
def load_progress():
    """Load reading progress from file"""
    try:
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_progress(data):
    """Save reading progress to file"""
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ========================================
# ROUTES
# ========================================

@router.post("/update")
async def update_progress(progress: ReadingProgress):
    """Update user's reading progress for a chapter"""
    try:
        data = load_progress()
        
        # Create nested structure: user_id -> comic_id -> chapter_id
        if progress.user_id not in data:
            data[progress.user_id] = {}
        
        if progress.comic_id not in data[progress.user_id]:
            data[progress.user_id][progress.comic_id] = {}
        
        # Store chapter progress
        data[progress.user_id][progress.comic_id][progress.chapter_id] = {
            "page_number": progress.page_number,
            "completed": progress.completed,
            "last_read": progress.last_read
        }
        
        save_progress(data)
        
        return ProgressResponse(
            success=True,
            message="Progress updated successfully",
            progress=data[progress.user_id][progress.comic_id][progress.chapter_id]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{user_id}/comic/{comic_id}")
async def get_comic_progress(user_id: str, comic_id: str):
    """Get all reading progress for a specific comic"""
    try:
        data = load_progress()
        
        if user_id in data and comic_id in data[user_id]:
            return {
                "success": True,
                "progress": data[user_id][comic_id]
            }
        
        return {
            "success": True,
            "progress": {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{user_id}")
async def get_user_progress(user_id: str):
    """Get all reading progress for a user"""
    try:
        data = load_progress()
        
        if user_id in data:
            return {
                "success": True,
                "progress": data[user_id]
            }
        
        return {
            "success": True,
            "progress": {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/user/{user_id}/comic/{comic_id}/chapter/{chapter_id}")
async def clear_chapter_progress(user_id: str, comic_id: str, chapter_id: str):
    """Clear progress for a specific chapter"""
    try:
        data = load_progress()
        
        if (user_id in data and 
            comic_id in data[user_id] and 
            chapter_id in data[user_id][comic_id]):
            
            del data[user_id][comic_id][chapter_id]
            save_progress(data)
            
            return {
                "success": True,
                "message": "Progress cleared"
            }
        
        return {
            "success": False,
            "message": "No progress found"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))