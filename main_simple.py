# backend/main_simple.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os, logging
from dotenv import load_dotenv

from api.routes import chat
from api.routes import reading_progress
from api.routes import users
from api.routes import credits
from api.routes import series        # ← NEW

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

for d in ["generated", "data", "data/avatars"]:
    os.makedirs(d, exist_ok=True)

app = FastAPI(title="PanelX API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/generated", StaticFiles(directory="generated"), name="generated")
app.mount("/avatars",   StaticFiles(directory="data/avatars"), name="avatars")

# ─── Routers ───
app.include_router(chat.router,             prefix="/api/chat",             tags=["chat"])
app.include_router(reading_progress.router, prefix="/api/reading-progress", tags=["reading"])
app.include_router(users.router,            prefix="/api/users",            tags=["users"])
app.include_router(credits.router,          prefix="/api/credits",          tags=["credits"])
app.include_router(series.router,           prefix="/api/series",           tags=["series"])  # ← NEW

@app.get("/")
async def root():
    return {
        "status": "online",
        "version": "3.0.0",
        "endpoints": [
            "/api/chat", "/api/users", "/api/credits",
            "/api/series", "/api/reading-progress"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 PanelX Backend v3 — All systems online")
    uvicorn.run("main_simple:app", host="0.0.0.0", port=8000, reload=True)