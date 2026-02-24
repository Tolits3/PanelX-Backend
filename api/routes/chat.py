# backend/api/routes/chat.py
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import os
import requests
import time
import uuid
from datetime import datetime

router = APIRouter()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# Database connection (if available)
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

class ChatRequest(BaseModel):
    message: str
    generate_image: bool = False
    user_uid: Optional[str] = None
    session_id: Optional[str] = None

class ImageGenerationRequest(BaseModel):
    prompt: str
    style: Optional[str] = "comic book art"

# ─────────────────────────────────────────────────────
# CONTENT MODERATION - Basic keyword filtering
# ─────────────────────────────────────────────────────
HARMFUL_KEYWORDS = [
    # Add your moderation keywords here
    "violence", "nsfw", "explicit", "harmful", "illegal",
    # This is a basic example - use a proper moderation API for production
]

def check_content_safety(text: str) -> tuple[bool, str]:
    """Basic content moderation - returns (is_safe, reason)"""
    text_lower = text.lower()
    
    for keyword in HARMFUL_KEYWORDS:
        if keyword in text_lower:
            return False, f"Contains inappropriate content: {keyword}"
    
    return True, ""

# ─────────────────────────────────────────────────────
# CHAT LOGGING
# ─────────────────────────────────────────────────────
def log_chat(
    user_uid: str,
    session_id: str,
    message_type: str,
    message_content: str,
    image_generated: bool = False,
    image_url: str = None,
    image_prompt: str = None,
    model_used: str = None,
    response_time_ms: int = None,
    flagged: bool = False,
    flag_reason: str = None,
    ip_address: str = None,
    user_agent: str = None
):
    """Log chat message to database"""
    
    if not USE_DB:
        # Fallback: log to file or just print
        print(f"[CHAT LOG] {user_uid}: {message_content[:50]}...")
        return
    
    try:
        log_id = str(uuid.uuid4())
        query("""
            INSERT INTO chat_logs (
                id, user_uid, session_id, message_type, message_content,
                image_generated, image_url, image_prompt, model_used,
                response_time_ms, flagged, flag_reason, ip_address, user_agent,
                created_at
            ) VALUES (
                :id, :user_uid, :session_id, :message_type, :message_content,
                :image_generated, :image_url, :image_prompt, :model_used,
                :response_time_ms, :flagged, :flag_reason, :ip_address, :user_agent,
                :created_at
            )
        """, {
            "id": log_id,
            "user_uid": user_uid,
            "session_id": session_id,
            "message_type": message_type,
            "message_content": message_content,
            "image_generated": image_generated,
            "image_url": image_url,
            "image_prompt": image_prompt,
            "model_used": model_used,
            "response_time_ms": response_time_ms,
            "flagged": flagged,
            "flag_reason": flag_reason,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.now().isoformat()
        }, fetch=None)
        
        # If flagged, create a moderation entry
        if flagged:
            query("""
                INSERT INTO flagged_content (
                    chat_log_id, user_uid, reason, severity, created_at
                ) VALUES (
                    :chat_log_id, :user_uid, :reason, :severity, :created_at
                )
            """, {
                "chat_log_id": log_id,
                "user_uid": user_uid,
                "reason": flag_reason,
                "severity": "medium",  # Can be determined by severity of keywords
                "created_at": datetime.now().isoformat()
            }, fetch=None)
            
    except Exception as e:
        print(f"Error logging chat: {e}")

# ─────────────────────────────────────────────────────
# GROQ AI CHAT
# ─────────────────────────────────────────────────────
def chat_with_groq(message: str) -> str:
    """Chat with Groq's LLaMA model"""
    
    if not GROQ_API_KEY:
        return "⚠️ AI chat unavailable. Please contact support."
    
    try:
        start_time = time.time()
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {
                        "role": "system",
                        "content": """You are a helpful AI assistant for PanelX, a comic creation platform. 

Your role is to help comic creators with:
- Brainstorming story ideas and plot concepts
- Developing characters and their backgrounds
- Suggesting panel compositions and layouts
- Writing dialogue and captions
- Giving creative feedback

Be friendly, creative, and encouraging. Keep responses concise (2-3 sentences).
IMPORTANT: Never generate, suggest, or engage with harmful, violent, NSFW, or illegal content.
If asked for inappropriate content, politely decline and redirect to creative comic ideas."""
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 300,
                "top_p": 1
            },
            timeout=30
        )
        
        response_time = int((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"], response_time
        else:
            return f"⚠️ AI temporarily unavailable. Please try again!", 0
            
    except Exception as e:
        print(f"Groq error: {e}")
        return "⚠️ Something went wrong. Please try again!", 0

# ─────────────────────────────────────────────────────
# IMAGE GENERATION (with logging)
# ─────────────────────────────────────────────────────
def call_replicate_api(model: str, input_data: dict):
    """Call Replicate API"""
    
    if not REPLICATE_API_KEY:
        raise Exception("Replicate API key not configured")
    
    headers = {
        "Authorization": f"Token {REPLICATE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        "https://api.replicate.com/v1/predictions",
        headers=headers,
        json={"version": model, "input": input_data}
    )
    
    if response.status_code != 201:
        raise Exception(f"Replicate API error: {response.text}")
    
    prediction = response.json()
    prediction_id = prediction["id"]
    
    for _ in range(60):
        time.sleep(1)
        status_response = requests.get(
            f"https://api.replicate.com/v1/predictions/{prediction_id}",
            headers=headers
        )
        result = status_response.json()
        status = result.get("status")
        
        if status == "succeeded":
            return result.get("output")
        elif status == "failed":
            raise Exception(f"Generation failed: {result.get('error')}")
    
    raise Exception("Generation timed out")

@router.post("/generate-image")
async def generate_image(req: ImageGenerationRequest, request: Request):
    """Generate image with logging"""
    
    if not REPLICATE_API_KEY:
        raise HTTPException(status_code=503, detail="Image generation unavailable")
    
    # Content safety check
    is_safe, reason = check_content_safety(req.prompt)
    if not is_safe:
        raise HTTPException(status_code=400, detail=f"Inappropriate prompt: {reason}")
    
    try:
        start_time = time.time()
        enhanced_prompt = f"{req.prompt}, {req.style}, highly detailed, professional comic art"
        
        model_version = "39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
        output = call_replicate_api(model_version, {
            "prompt": enhanced_prompt,
            "width": 896,
            "height": 1152,
            "num_outputs": 1,
            "guidance_scale": 7.5,
            "num_inference_steps": 30,
            "negative_prompt": "blurry, bad anatomy, ugly"
        })
        
        response_time = int((time.time() - start_time) * 1000)
        
        if not output:
            raise Exception("No image generated")
        
        image_url = output[0] if isinstance(output, list) else output
        
        return {
            "success": True,
            "image_url": image_url,
            "prompt": req.prompt,
            "model": "SDXL",
            "response_time_ms": response_time
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────────────
# MAIN CHAT ENDPOINT (with logging)
# ─────────────────────────────────────────────────────
@router.post("/message")
async def chat_message(req: ChatRequest, request: Request):
    """AI chat with comprehensive logging"""
    
    # Get request metadata
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    session_id = req.session_id or str(uuid.uuid4())
    
    # Content safety check
    is_safe, flag_reason = check_content_safety(req.message)
    
    # Log user message
    if req.user_uid:
        log_chat(
            user_uid=req.user_uid,
            session_id=session_id,
            message_type="user",
            message_content=req.message,
            flagged=not is_safe,
            flag_reason=flag_reason if not is_safe else None,
            ip_address=client_ip,
            user_agent=user_agent
        )
    
    if not is_safe:
        warning_response = "⚠️ Your message contains inappropriate content. Let's keep our conversations creative and respectful! How about we focus on your comic ideas instead?"
        
        # Log warning response
        if req.user_uid:
            log_chat(
                user_uid=req.user_uid,
                session_id=session_id,
                message_type="system",
                message_content=warning_response,
                ip_address=client_ip
            )
        
        return {
            "success": False,
            "response": warning_response,
            "image_generated": False,
            "flagged": True
        }
    
    # Check for image generation
    msg_lower = req.message.lower()
    is_image_request = (
        req.generate_image or 
        "generate:" in msg_lower or 
        "draw:" in msg_lower or 
        "create:" in msg_lower
    )
    
    if is_image_request:
        # Extract prompt
        prompt = req.message
        for prefix in ["generate:", "draw:", "create:"]:
            if prefix in msg_lower:
                prompt = req.message[req.message.lower().index(prefix) + len(prefix):].strip()
                break
        
        if not REPLICATE_API_KEY:
            response_text = "🎨 Image generation is temporarily unavailable. But I can help you plan and brainstorm your comic ideas!"
            
            if req.user_uid:
                log_chat(
                    user_uid=req.user_uid,
                    session_id=session_id,
                    message_type="system",
                    message_content=response_text,
                    model_used="none"
                )
            
            return {
                "success": True,
                "response": response_text,
                "image_generated": False
            }
    
    # Regular chat with Groq
    ai_response, response_time = chat_with_groq(req.message)
    
    # Log AI response
    if req.user_uid:
        log_chat(
            user_uid=req.user_uid,
            session_id=session_id,
            message_type="ai",
            message_content=ai_response,
            model_used="groq-llama-3.3-70b",
            response_time_ms=response_time,
            ip_address=client_ip
        )
    
    return {
        "success": True,
        "response": ai_response,
        "image_generated": False,
        "session_id": session_id
    }

# ─────────────────────────────────────────────────────
# ADMIN: View chat logs
# ─────────────────────────────────────────────────────
@router.get("/admin/logs")
async def get_chat_logs(limit: int = 100, flagged_only: bool = False):
    """Get recent chat logs (admin only - add auth later)"""
    
    if not USE_DB:
        return {"error": "Database not configured"}
    
    try:
        if flagged_only:
            logs = query("""
                SELECT * FROM chat_logs 
                WHERE flagged = 1 
                ORDER BY created_at DESC 
                LIMIT :limit
            """, {"limit": limit}, fetch="all")
        else:
            logs = query("""
                SELECT * FROM chat_logs 
                ORDER BY created_at DESC 
                LIMIT :limit
            """, {"limit": limit}, fetch="all")
        
        return {
            "success": True,
            "logs": logs,
            "count": len(logs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/flagged")
async def get_flagged_content():
    """Get flagged content for review (admin only)"""
    
    if not USE_DB:
        return {"error": "Database not configured"}
    
    try:
        flagged = query("""
            SELECT fc.*, cl.message_content, u.username, u.email
            FROM flagged_content fc
            JOIN chat_logs cl ON fc.chat_log_id = cl.id
            JOIN users u ON fc.user_uid = u.uid
            WHERE fc.reviewed = 0
            ORDER BY fc.created_at DESC
        """, fetch="all")
        
        return {
            "success": True,
            "flagged": flagged,
            "count": len(flagged)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    return {
        "status": "online",
        "groq_configured": bool(GROQ_API_KEY),
        "replicate_configured": bool(REPLICATE_API_KEY),
        "logging_enabled": USE_DB,
        "chat_available": bool(GROQ_API_KEY),
        "image_generation_available": bool(REPLICATE_API_KEY),
        "model": "llama-3.3-70b-versatile" if GROQ_API_KEY else None
    }