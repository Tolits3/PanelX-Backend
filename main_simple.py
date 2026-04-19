from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════
# IMPORT ROUTERS
# ═══════════════════════════════════════════
from api.routes.users import router as users_router
from api.routes.series import router as series_router

app = FastAPI(title="PanelX API", version="3.0.0")

# ═══════════════════════════════════════════
# CORS
# ═══════════════════════════════════════════
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://panelsx.netlify.app",
        "https://panel-x-frontend.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════
# INCLUDE ROUTERS
# ═══════════════════════════════════════════
app.include_router(users_router, prefix="/api/users")
app.include_router(series_router, prefix="/api/series")

# ═══════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════
class ChatMessage(BaseModel):
    message: str
    user_uid: Optional[str] = None
    context: Optional[str] = "comic creation"
    generate_image: Optional[bool] = False

class CreditRequest(BaseModel):
    user_uid: str
    package_id: Optional[str] = "free"

# ═══════════════════════════════════════════
# ROOT
# ═══════════════════════════════════════════
@app.get("/")
def root():
    return {
        "status": "online",
        "message": "PanelX API is running!",
        "version": "3.0.0",
        "endpoints": [
            "/api/users",
            "/api/series",
            "/api/chat/message",
            "/api/credits",
        ]
    }

# ═══════════════════════════════════════════
# AI CHAT ENDPOINT
# ═══════════════════════════════════════════
@app.post("/api/chat/message")
async def chat_message(body: ChatMessage):
    try:
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")

        client = Groq(api_key=groq_api_key)

        system_prompt = """You are an expert AI assistant for PanelX, a comic creation platform. 
        You help creators with:
        - Comic story ideas and plot suggestions
        - Character development and design descriptions
        - Panel composition and layout advice
        - Dialogue writing tips
        - Art style recommendations
        - Manga/webtoon creation techniques
        
        Be creative, encouraging, and specific. Keep responses concise but helpful.
        If asked to generate an image prompt, create a detailed, vivid description."""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": body.message}
            ],
            temperature=0.7,
            max_tokens=1000,
        )

        response_text = completion.choices[0].message.content

        return {
            "success": True,
            "response": response_text,
            "model": "llama-3.3-70b-versatile"
        }

    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════
# CREDITS ENDPOINTS
# ═══════════════════════════════════════════
@app.get("/api/credits/packages")
async def get_credit_packages():
    """Returns available credit packages - currently all free during beta"""
    return {
        "success": True,
        "beta": True,
        "message": "PanelX is currently in development - use it for free!",
        "packages": [
            {
                "id": "free_beta",
                "name": "Free Beta",
                "credits": 1000,
                "price": 0,
                "currency": "USD",
                "description": "Everything free during beta!",
                "features": [
                    "1000 free credits",
                    "AI chat assistant",
                    "Full studio access",
                    "Unlimited reading",
                    "Cloud storage"
                ],
                "badge": "🎉 FREE",
                "active": True
            },
            {
                "id": "creator_pro",
                "name": "Creator Pro",
                "credits": 5000,
                "price": 9.99,
                "currency": "USD",
                "description": "Coming soon!",
                "features": [
                    "5000 credits/month",
                    "Priority generation",
                    "Advanced analytics",
                    "Premium templates",
                    "Creator badge"
                ],
                "badge": "🚀 Coming Soon",
                "active": False
            },
            {
                "id": "studio",
                "name": "Studio",
                "credits": -1,
                "price": 29.99,
                "currency": "USD",
                "description": "Coming soon!",
                "features": [
                    "Unlimited credits",
                    "Team collaboration",
                    "API access",
                    "White-label options",
                    "1-on-1 support"
                ],
                "badge": "💎 Coming Soon",
                "active": False
            }
        ]
    }

@app.get("/api/credits/balance/{user_uid}")
async def get_credit_balance(user_uid: str):
    """Get user credit balance"""
    return {
        "success": True,
        "user_uid": user_uid,
        "balance": 1000,
        "beta": True,
        "message": "Free credits during beta!"
    }

@app.post("/api/credits/purchase")
async def purchase_credits(body: CreditRequest):
    """Purchase credits - disabled during beta"""
    return {
        "success": False,
        "beta": True,
        "message": "💡 PanelX is currently in development - all features are FREE! Paid plans coming soon.",
    }

# ═══════════════════════════════════════════
# EPISODES ENDPOINTS (Missing from series router)
# ═══════════════════════════════════════════
@app.get("/api/series/episode/creator/{user_uid}")
async def get_creator_episodes(user_uid: str):
    """Get all episodes by creator"""
    try:
        from database import get_db
        from sqlalchemy import text

        db = next(get_db())
        result = db.execute(
            text("""
                SELECT e.*, s.title as series_title 
                FROM episodes e
                JOIN series s ON e.series_id = s.id
                WHERE s.user_uid = :uid
                ORDER BY e.created_at DESC
            """),
            {"uid": user_uid}
        )

        episodes = []
        for row in result:
            episodes.append(dict(row._mapping))

        return {"success": True, "episodes": episodes}

    except Exception as e:
        print(f"Error fetching episodes: {e}")
        return {"success": True, "episodes": []}

@app.get("/api/episodes/{episode_id}")
async def get_episode(episode_id: str):
    """Get single episode"""
    try:
        from database import get_db
        from sqlalchemy import text

        db = next(get_db())
        result = db.execute(
            text("SELECT * FROM episodes WHERE id = :id"),
            {"id": episode_id}
        ).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Episode not found")

        return {"success": True, "episode": dict(result._mapping)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/episodes/create")
async def create_episode(request: Request):
    """Create new episode"""
    try:
        from database import get_db
        from sqlalchemy import text
        import uuid

        body = await request.json()
        db = next(get_db())

        episode_id = str(uuid.uuid4())

        db.execute(
            text("""
                INSERT INTO episodes (id, series_id, episode_number, title, script_content, status)
                VALUES (:id, :series_id, :episode_number, :title, :script_content, :status)
            """),
            {
                "id": episode_id,
                "series_id": body.get("series_id"),
                "episode_number": body.get("episode_number", 1),
                "title": body.get("title", "Untitled Episode"),
                "script_content": body.get("script_content", ""),
                "status": body.get("status", "draft")
            }
        )
        db.commit()

        return {"success": True, "episode_id": episode_id}

    except Exception as e:
        print(f"Error creating episode: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════
# STUDIO ENDPOINTS
# ═══════════════════════════════════════════
@app.get("/api/studio/{episode_id}")
async def get_studio_project(episode_id: str):
    """Load studio project"""
    try:
        from database import get_db
        from sqlalchemy import text

        db = next(get_db())
        result = db.execute(
            text("SELECT * FROM episodes WHERE id = :id"),
            {"id": episode_id}
        ).fetchone()

        if not result:
            return {"success": False, "error": "Episode not found"}

        episode = dict(result._mapping)

        return {
            "success": True,
            "project": {
                "id": episode_id,
                "title": episode.get("title", "Untitled"),
                "panels_data": episode.get("panels_data", []),
                "script_content": episode.get("script_content", "")
            }
        }

    except Exception as e:
        print(f"Error loading studio: {e}")
        return {"success": False, "error": str(e)}

@app.put("/api/studio/{episode_id}/save")
async def save_studio_project(episode_id: str, request: Request):
    """Save studio project"""
    try:
        from database import get_db
        from sqlalchemy import text
        import json

        body = await request.json()
        db = next(get_db())

        db.execute(
            text("""
                UPDATE episodes 
                SET title = :title, panels_data = :panels_data, updated_at = NOW()
                WHERE id = :id
            """),
            {
                "id": episode_id,
                "title": body.get("title", "Untitled"),
                "panels_data": json.dumps(body.get("panels_data", []))
            }
        )
        db.commit()

        return {"success": True, "message": "Project saved!"}

    except Exception as e:
        print(f"Error saving studio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════
# EXCEPTION HANDLERS
# ═══════════════════════════════════════════
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"},
    )