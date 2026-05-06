from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import os
import httpx
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════
# IMPORT ROUTERS
# ═══════════════════════════════════════════
from api.routes.users import router as users_router
from api.routes.series import router as series_router

app = FastAPI(title="PanelX API", version="3.0.0")

# ✅ FIXED: viewer_store at module level (NOT inside a function)
viewer_store = {}

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
    generate_image: Optional[bool] = True

class CreditRequest(BaseModel):
    user_uid: str
    package_id: Optional[str] = "free"

class ImageGenerateRequest(BaseModel):
    prompt: str
    panel_id: Optional[str] = None
    style: Optional[str] = "manga, black and white, detailed"
    width: Optional[int] = 768
    height: Optional[int] = 1024

class StripGenerateRequest(BaseModel):
    prompt: str
    panels: Optional[int] = 4
    style: Optional[str] = "manga, black and white, detailed"

class ViewerSession(BaseModel):
    session: int

class CommentCreate(BaseModel):
    user_uid: str
    username: str
    content: str

# ═══════════════════════════════════════════
# ROOT
# ═══════════════════════════════════════════
@app.get("/")
def root():
    return {
        "status": "online",
        "message": "PanelX API is running!",
        "version": "3.0.0",
    }

# ═══════════════════════════════════════════
# AI CHAT
# ═══════════════════════════════════════════
@app.post("/api/chat/message")
async def chat_message(body: ChatMessage):
    try:
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")

        client = Groq(api_key=groq_api_key)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert AI assistant for PanelX, a comic creation platform. Help creators with story ideas, character development, panel composition, dialogue, and art style."},
                {"role": "user", "content": body.message}
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        return {
            "success": True,
            "response": completion.choices[0].message.content,
            "model": "llama-3.3-70b-versatile"
        }
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════
# CREDITS
# ═══════════════════════════════════════════
@app.get("/api/credits/packages")
async def get_credit_packages():
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
                "features": ["1000 free credits", "AI chat assistant", "Full studio access", "Unlimited reading", "Cloud storage"],
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
                "features": ["5000 credits/month", "Priority generation", "Advanced analytics", "Premium templates", "Creator badge"],
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
                "features": ["Unlimited credits", "Team collaboration", "API access", "White-label options", "1-on-1 support"],
                "badge": "💎 Coming Soon",
                "active": False
            }
        ]
    }

@app.get("/api/credits/balance/{user_uid}")
async def get_credit_balance(user_uid: str):
    return {"success": True, "user_uid": user_uid, "balance": 1000, "beta": True}

@app.post("/api/credits/purchase")
async def purchase_credits(body: CreditRequest):
    return {"success": False, "beta": True, "message": "PanelX is in beta - all features are FREE!"}

# ═══════════════════════════════════════════
# SERIES - TRENDING (must be before /{series_id} routes)
# ═══════════════════════════════════════════
@app.get("/api/series/trending")
async def get_trending_series():
    try:
        from database import get_db
        from sqlalchemy import text
        db = next(get_db())
        result = db.execute(text("""
            SELECT * FROM series
            WHERE is_published = 1
            ORDER BY view_count DESC
            LIMIT 10
        """))
        series = [dict(row._mapping) for row in result]
        return {"success": True, "series": series}
    except Exception as e:
        print(f"Trending error: {e}")
        return {"success": True, "series": []}

# ═══════════════════════════════════════════
# READING PROGRESS
# ═══════════════════════════════════════════
@app.get("/api/reading-progress/user/{user_uid}")
async def get_reading_progress(user_uid: str):
    try:
        from database import get_db
        from sqlalchemy import text
        db = next(get_db())
        result = db.execute(
            text("SELECT * FROM reading_progress WHERE user_uid = :uid ORDER BY updated_at DESC"),
            {"uid": user_uid}
        )
        progress = [dict(row._mapping) for row in result]
        return {"success": True, "progress": progress}
    except Exception as e:
        print(f"Reading progress error: {e}")
        return {"success": True, "progress": []}

@app.post("/api/reading-progress/update")
async def update_reading_progress(request: Request):
    try:
        from database import get_db
        from sqlalchemy import text
        import uuid
        body = await request.json()
        db = next(get_db())
        db.execute(text("""
            INSERT INTO reading_progress (id, user_uid, comic_id, chapter_id, page_number, completed, last_read)
            VALUES (:id, :user_uid, :comic_id, :chapter_id, :page_number, :completed, :last_read)
            ON DUPLICATE KEY UPDATE
                page_number = VALUES(page_number),
                completed = VALUES(completed),
                last_read = VALUES(last_read)
        """), {
            "id": str(uuid.uuid4()),
            "user_uid": body.get("user_id"),
            "comic_id": body.get("comic_id"),
            "chapter_id": body.get("chapter_id"),
            "page_number": body.get("page_number", 1),
            "completed": body.get("completed", False),
            "last_read": body.get("last_read"),
        })
        db.commit()
        return {"success": True}
    except Exception as e:
        print(f"Update progress error: {e}")
        return {"success": True}

# ═══════════════════════════════════════════
# EPISODES
# ═══════════════════════════════════════════
@app.get("/api/series/episode/creator/{user_uid}")
async def get_creator_episodes(user_uid: str):
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
        return {"success": True, "episodes": [dict(row._mapping) for row in result]}
    except Exception as e:
        print(f"Error fetching episodes: {e}")
        return {"success": True, "episodes": []}


@app.get("/api/mangadex/popular")
async def mangadex_popular(limit: int = 20):
    """Proxy MangaDex popular manga"""
    try:
        url = f"https://api.mangadex.org/manga?limit={limit}&contentRating%5B%5D=safe&includes%5B%5D=cover_art&availableTranslatedLanguage%5B%5D=en&order%5BfollowedCount%5D=desc"
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=10)
            return res.json()
    except Exception as e:
        print(f"MangaDex proxy error: {e}")
        return {"data": []}

@app.get("/api/mangadex/latest")
async def mangadex_latest(limit: int = 20):
    """Proxy MangaDex latest manga"""
    try:
        url = f"https://api.mangadex.org/manga?limit={limit}&contentRating%5B%5D=safe&includes%5B%5D=cover_art&availableTranslatedLanguage%5B%5D=en&order%5BlatestUploadedChapter%5D=desc"
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=10)
            return res.json()
    except Exception as e:
        print(f"MangaDex proxy error: {e}")
        return {"data": []}

@app.get("/api/mangadex/search")
async def mangadex_search(title: str = "", limit: int = 10):
    """Proxy MangaDex search"""
    try:
        url = f"https://api.mangadex.org/manga?limit={limit}&contentRating%5B%5D=safe&includes%5B%5D=cover_art&availableTranslatedLanguage%5B%5D=en&title={title}"
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=10)
            return res.json()
    except Exception as e:
        return {"data": []}

@app.get("/api/mangadex/genre/{tag_id}")
async def mangadex_by_genre(tag_id: str, limit: int = 20):
    """Proxy MangaDex genre filter"""
    try:
        url = f"https://api.mangadex.org/manga?limit={limit}&contentRating%5B%5D=safe&includes%5B%5D=cover_art&availableTranslatedLanguage%5B%5D=en&includedTags%5B%5D={tag_id}"
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=10)
            return res.json()
    except Exception as e:
        return {"data": []}

@app.get("/api/mangadex/manga/{manga_id}")
async def mangadex_manga(manga_id: str):
    """Proxy MangaDex manga details"""
    try:
        url = f"https://api.mangadex.org/manga/{manga_id}?includes%5B%5D=cover_art&includes%5B%5D=author&includes%5B%5D=artist"
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=10)
            return res.json()
    except Exception as e:
        return {"data": None}

@app.get("/api/mangadex/manga/{manga_id}/chapters")
async def mangadex_chapters(manga_id: str):
    """Proxy MangaDex chapter list"""
    try:
        url = f"https://api.mangadex.org/manga/{manga_id}/feed?limit=100&translatedLanguage%5B%5D=en&order%5Bchapter%5D=desc&includes%5B%5D=scanlation_group&contentRating%5B%5D=safe"
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=10)
            return res.json()
    except Exception as e:
        return {"data": []}

@app.get("/api/mangadex/chapter/{chapter_id}/pages")
async def mangadex_pages(chapter_id: str):
    """Proxy MangaDex chapter pages"""
    try:
        url = f"https://api.mangadex.org/at-home/server/{chapter_id}"
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=10)
            return res.json()
    except Exception as e:
        return {"result": "error"}

@app.get("/api/mangadex/chapter/{chapter_id}/info")
async def mangadex_chapter_info(chapter_id: str):
    """Proxy MangaDex chapter info"""
    try:
        url = f"https://api.mangadex.org/chapter/{chapter_id}?includes%5B%5D=manga"
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=10)
            return res.json()
    except Exception as e:
        return {"data": None}

@app.get("/api/episodes/{episode_id}")
async def get_episode(episode_id: str):
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
# STUDIO
# ═══════════════════════════════════════════
@app.get("/api/studio/{episode_id}")
async def get_studio_project(episode_id: str):
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
        return {"success": False, "error": str(e)}

@app.put("/api/studio/{episode_id}/save")
async def save_studio_project(episode_id: str, request: Request):
    try:
        from database import get_db
        from sqlalchemy import text
        import json
        body = await request.json()
        db = next(get_db())
        db.execute(
            text("UPDATE episodes SET title = :title, panels_data = :panels_data WHERE id = :id"),
            {
                "id": episode_id,
                "title": body.get("title", "Untitled"),
                "panels_data": json.dumps(body.get("panels_data", []))
            }
        )
        db.commit()
        return {"success": True, "message": "Project saved!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════
# IMAGE GENERATION
# ═══════════════════════════════════════════
@app.post("/api/generate/image")
async def generate_image(body: ImageGenerateRequest):
    try:
        import replicate
        replicate_key = os.getenv("REPLICATE_API_KEY")
        if not replicate_key:
            raise HTTPException(status_code=500, detail="REPLICATE_API_KEY not configured")
        client = replicate.Client(api_token=replicate_key)
        full_prompt = f"{body.prompt}, {body.style}, high quality, comic art"
        output = client.run(
            "stability-ai/sdxl:39ed52f2319f9f8a56de0dc05aeb00e6c2d8bfdc",
            input={
                "prompt": full_prompt,
                "negative_prompt": "blurry, low quality, ugly, distorted, bad anatomy",
                "width": body.width or 768,
                "height": body.height or 1024,
                "num_inference_steps": 25,
                "guidance_scale": 7.5,
            }
        )
        image_url = output[0] if isinstance(output, list) else str(output)
        return {"success": True, "image_url": image_url, "prompt": body.prompt, "panel_id": body.panel_id}
    except Exception as e:
        print(f"Image generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate/strip")
async def generate_strip(body: StripGenerateRequest):
    try:
        import replicate
        import json
        replicate_key = os.getenv("REPLICATE_API_KEY")
        if not replicate_key:
            raise HTTPException(status_code=500, detail="REPLICATE_API_KEY not configured")
        client = replicate.Client(api_token=replicate_key)
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        panel_count = body.panels or 4
        breakdown = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": f"Break this story into {panel_count} comic panel descriptions. Story: {body.prompt}. Return ONLY a JSON array of {panel_count} strings. No extra text."}],
            max_tokens=500,
        )
        panel_prompts_raw = breakdown.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
        panel_prompts = json.loads(panel_prompts_raw)
        if not isinstance(panel_prompts, list):
            panel_prompts = [body.prompt] * panel_count
        images = []
        for prompt in panel_prompts[:panel_count]:
            try:
                output = client.run(
                    "stability-ai/sdxl:39ed52f2319f9f8a56de0dc05aeb00e6c2d8bfdc",
                    input={"prompt": f"{prompt}, {body.style}, high quality, comic art", "width": 768, "height": 1024, "num_inference_steps": 20}
                )
                images.append(output[0] if isinstance(output, list) else str(output))
            except Exception as img_err:
                print(f"Panel generation error: {img_err}")
        return {"success": True, "images": images, "prompts": panel_prompts, "count": len(images)}
    except Exception as e:
        print(f"Strip generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════
# VIEWER COUNT
# ═══════════════════════════════════════════
@app.post("/api/viewers/{chapter_id}/join")
async def viewer_join(chapter_id: str, body: ViewerSession):
    if chapter_id not in viewer_store:
        viewer_store[chapter_id] = set()
    viewer_store[chapter_id].add(str(body.session))
    if len(viewer_store[chapter_id]) > 200:
        sessions = list(viewer_store[chapter_id])
        viewer_store[chapter_id] = set(sessions[-200:])
    return {"success": True, "count": len(viewer_store[chapter_id])}

@app.get("/api/viewers/{chapter_id}/count")
async def viewer_count(chapter_id: str):
    count = len(viewer_store.get(chapter_id, set()))
    return {"success": True, "count": max(count, 1)}

@app.post("/api/viewers/{chapter_id}/leave")
async def viewer_leave(chapter_id: str, body: ViewerSession):
    if chapter_id in viewer_store:
        viewer_store[chapter_id].discard(str(body.session))
    return {"success": True}

# ═══════════════════════════════════════════
# COMMENTS
# ═══════════════════════════════════════════
@app.get("/api/comments/{chapter_id}")
async def get_comments(chapter_id: str):
    try:
        from database import get_db
        from sqlalchemy import text
        db = next(get_db())
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS comments (
                id VARCHAR(50) PRIMARY KEY,
                chapter_id VARCHAR(200) NOT NULL,
                user_uid VARCHAR(128) NOT NULL,
                username VARCHAR(100) NOT NULL,
                content TEXT NOT NULL,
                likes INT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.commit()
        result = db.execute(
            text("SELECT * FROM comments WHERE chapter_id = :chapter_id ORDER BY created_at DESC LIMIT 100"),
            {"chapter_id": chapter_id}
        )
        return {"success": True, "comments": [dict(row._mapping) for row in result]}
    except Exception as e:
        print(f"Get comments error: {e}")
        return {"success": True, "comments": []}

@app.post("/api/comments/{chapter_id}")
async def post_comment(chapter_id: str, body: CommentCreate):
    try:
        from database import get_db
        from sqlalchemy import text
        import uuid
        from datetime import datetime
        if not body.content.strip():
            raise HTTPException(status_code=400, detail="Comment cannot be empty")
        if len(body.content) > 500:
            raise HTTPException(status_code=400, detail="Comment too long")
        db = next(get_db())
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS comments (
                id VARCHAR(50) PRIMARY KEY,
                chapter_id VARCHAR(200) NOT NULL,
                user_uid VARCHAR(128) NOT NULL,
                username VARCHAR(100) NOT NULL,
                content TEXT NOT NULL,
                likes INT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        comment_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        db.execute(
            text("INSERT INTO comments (id, chapter_id, user_uid, username, content, created_at) VALUES (:id, :chapter_id, :user_uid, :username, :content, :created_at)"),
            {"id": comment_id, "chapter_id": chapter_id, "user_uid": body.user_uid, "username": body.username, "content": body.content.strip(), "created_at": now}
        )
        db.commit()
        return {"success": True, "comment": {"id": comment_id, "chapter_id": chapter_id, "user_uid": body.user_uid, "username": body.username, "content": body.content.strip(), "likes": 0, "created_at": now}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Post comment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/comments/{comment_id}")
async def delete_comment(comment_id: str, user_uid: str):
    try:
        from database import get_db
        from sqlalchemy import text
        db = next(get_db())
        db.execute(text("DELETE FROM comments WHERE id = :id AND user_uid = :uid"), {"id": comment_id, "uid": user_uid})
        db.commit()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════
# EXCEPTION HANDLERS
# ═══════════════════════════════════════════
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.detail})

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"success": False, "error": "Internal server error"})