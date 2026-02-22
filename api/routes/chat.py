# backend/api/routes/chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import requests
import time

router = APIRouter()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY")

class ChatRequest(BaseModel):
    message: str
    generate_image: bool = False

class ImageGenerationRequest(BaseModel):
    prompt: str
    style: Optional[str] = "comic book art"

# ─────────────────────────────────────────────────────
# GROQ AI CHAT - Real AI Conversations!
# ─────────────────────────────────────────────────────
def chat_with_groq(message: str) -> str:
    """Chat with Groq's LLaMA model for natural conversations"""
    
    if not GROQ_API_KEY:
        return "⚠️ Groq API key not configured. Add GROQ_API_KEY to your environment variables to enable AI chat!"
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",  # Fast and smart!
                "messages": [
                    {
                        "role": "system",
                        "content": """You are a helpful AI assistant for PanelX, a comic creation platform. 
                        
Your role is to help comic creators with:
- Brainstorming story ideas and plot concepts
- Developing characters and their backgrounds
- Suggesting panel compositions and layouts
- Writing dialogue and captions
- Giving creative feedback on their work
- Providing comic creation tips and best practices

Be friendly, creative, and encouraging. Keep responses concise (2-3 sentences usually). 
When users mention generating images, remind them they can type "generate: description" to create comic panels.
Be enthusiastic about their comic ideas!"""
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
        
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            return f"⚠️ Groq API error: {response.status_code}. Please try again!"
            
    except requests.exceptions.Timeout:
        return "⚠️ Response timed out. Please try again!"
    except Exception as e:
        print(f"Groq error: {e}")
        return "⚠️ Something went wrong. Please try again!"


# ─────────────────────────────────────────────────────
# IMAGE GENERATION - REPLICATE (Optional)
# ─────────────────────────────────────────────────────
def call_replicate_api(model: str, input_data: dict):
    """Call Replicate API for image generation"""
    
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
    
    # Poll for result (max 60 seconds)
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
async def generate_image(req: ImageGenerationRequest):
    """Generate comic panel image using Replicate"""
    
    if not REPLICATE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Image generation unavailable. Replicate API key not configured."
        )
    
    try:
        enhanced_prompt = f"{req.prompt}, {req.style}, highly detailed, professional comic book illustration, vibrant colors"
        
        # SDXL model
        model_version = "39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
        
        output = call_replicate_api(model_version, {
            "prompt": enhanced_prompt,
            "width": 896,
            "height": 1152,
            "num_outputs": 1,
            "guidance_scale": 7.5,
            "num_inference_steps": 30,
            "negative_prompt": "blurry, bad anatomy, ugly, distorted, low quality"
        })
        
        if not output:
            raise Exception("No image generated")
        
        image_url = output[0] if isinstance(output, list) else output
        
        return {
            "success": True,
            "image_url": image_url,
            "prompt": req.prompt,
            "model": "SDXL"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────
# MAIN CHAT ENDPOINT
# ─────────────────────────────────────────────────────
@router.post("/message")
async def chat_message(req: ChatRequest):
    """AI chat assistant powered by Groq"""
    
    # Check if user wants image generation
    msg_lower = req.message.lower()
    is_image_request = (
        req.generate_image or 
        "generate:" in msg_lower or 
        "draw:" in msg_lower or 
        "create:" in msg_lower
    )
    
    if is_image_request:
        if not REPLICATE_API_KEY:
            ai_response = chat_with_groq(
                "The user wants to generate an image but Replicate credits aren't available. "
                "Politely let them know image generation is temporarily unavailable but you can still help them brainstorm and plan their comic."
            )
            return {
                "success": True,
                "response": ai_response,
                "image_generated": False
            }
        
        # Extract prompt and try to generate
        prompt = req.message
        for prefix in ["generate:", "draw:", "create:"]:
            if prefix in msg_lower:
                prompt = req.message[req.message.lower().index(prefix) + len(prefix):].strip()
                break
        
        try:
            result = await generate_image(ImageGenerationRequest(prompt=prompt))
            
            # Ask Groq to create a nice message about the generated image
            ai_comment = chat_with_groq(
                f"The user just generated a comic panel image with this prompt: '{prompt}'. "
                f"Give them a brief, enthusiastic response (1-2 sentences) about their image and maybe a quick tip."
            )
            
            return {
                "success": True,
                "response": ai_comment,
                "image_url": result["image_url"],
                "image_generated": True
            }
        except Exception as e:
            error_msg = chat_with_groq(
                f"Image generation failed with error: {str(e)}. "
                f"Politely let the user know and offer to help them brainstorm instead."
            )
            return {
                "success": False,
                "response": error_msg,
                "image_generated": False
            }
    
    # Regular chat - use Groq AI
    ai_response = chat_with_groq(req.message)
    
    return {
        "success": True,
        "response": ai_response,
        "image_generated": False
    }


@router.get("/health")
async def health_check():
    return {
        "status": "online",
        "groq_configured": bool(GROQ_API_KEY),
        "replicate_configured": bool(REPLICATE_API_KEY),
        "chat_available": bool(GROQ_API_KEY),
        "image_generation_available": bool(REPLICATE_API_KEY),
        "model": "llama-3.3-70b-versatile" if GROQ_API_KEY else None
    }