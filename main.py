import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from core.config import settings
from core.database import init_db
from api.routes import images, stories, characters, auth
from api.routes import images, stories, characters, auth, chat
from api.routes import chat


app = FastAPI()

app.include_router(chat.router)

@app.get("/")
def home():
    return {"status": "PanelX API is running"}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure generated directory exists
os.makedirs(settings.GENERATED_DIR, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting PanelX Backend...")
    await init_db()
    logger.info("✅ Database initialized")
    yield
    logger.info("👋 Shutting down PanelX Backend...")

# Initialize FastAPI app
app = FastAPI(
    title="PanelX API",
    description="Backend API for PanelX Comic Generation Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
# Mount static files for generated images
app.mount("/generated", StaticFiles(directory=settings.GENERATED_DIR), name="generated")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(images.router, prefix="/api/images", tags=["Images"])
app.include_router(stories.router, prefix="/api/stories", tags=["Stories"])
app.include_router(characters.router, prefix="/api/characters", tags=["Characters"])

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "PanelX API",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "storage": "available"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )