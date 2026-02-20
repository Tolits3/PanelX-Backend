# backend/api/routes/chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import requests
import time

router = APIRouter()

REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY")

class ChatRequest(BaseModel):
    message: str
    generate_image: bool = False

class ImageGenerationRequest(BaseModel):
    prompt: str
    style: Optional[str] = "comic book art"

# ─────────────────────────────────────────────────────
# REPLICATE REST API - No SDK needed!
# ─────────────────────────────────────────────────────
def call_replicate_api(model: str, input_data: dict):
    """Call Replicate API directly using HTTP requests"""
    
    if not REPLICATE_API_KEY:
        raise Exception("REPLICATE_API_KEY not set")
    
    headers = {
        "Authorization": f"Token {REPLICATE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Start prediction
    response = requests.post(
        "https://api.replicate.com/v1/predictions",
        headers=headers,
        json={
            "version": model,
            "input": input_data
        }
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


# ─────────────────────────────────────────────────────
# IMAGE GENERATION - SDXL (Fast, Good Quality)
# ─────────────────────────────────────────────────────
@router.post("/generate-image")
async def generate_image(req: ImageGenerationRequest):
    """Generate comic panel using SDXL"""
    
    if not REPLICATE_API_KEY:
        raise HTTPException(status_code=500, detail="REPLICATE_API_KEY not set")
    
    try:
        enhanced_prompt = f"{req.prompt}, {req.style}, highly detailed, professional comic book illustration, vibrant colors, dynamic composition"
        
        # SDXL model version
        model_version = "39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
        
        output = call_replicate_api(model_version, {
            "prompt": enhanced_prompt,
            "width": 896,
            "height": 1152,
            "num_outputs": 1,
            "guidance_scale": 7.5,
            "num_inference_steps": 30,
            "negative_prompt": "blurry, bad anatomy, ugly, distorted, low quality, pixelated"
        })
        
        if not output or len(output) == 0:
            raise Exception("No image generated")
        
        image_url = output[0] if isinstance(output, list) else output
        
        return {
            "success": True,
            "image_url": image_url,
            "prompt": req.prompt,
            "enhanced_prompt": enhanced_prompt,
            "model": "SDXL"
        }
        
    except Exception as e:
        print(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")


# ─────────────────────────────────────────────────────
# ALTERNATIVE: FLUX (Better quality, slower)
# ─────────────────────────────────────────────────────
@router.post("/generate-image-flux")
async def generate_image_flux(req: ImageGenerationRequest):
    """Generate using FLUX Schnell (premium quality)"""
    
    if not REPLICATE_API_KEY:
        raise HTTPException(status_code=500, detail="API key not set")
    
    try:
        enhanced_prompt = f"{req.prompt}, {req.style}, masterpiece, highly detailed comic art"
        
        # FLUX Schnell version
        model_version = "f2ab8a5569279bc6a362ac15e6ea9aaf3bcd1d6c2b90d20c3e2d6e96ba9e2c7a"
        
        output = call_replicate_api(model_version, {
            "prompt": enhanced_prompt,
            "num_outputs": 1,
            "aspect_ratio": "9:16",
            "output_format": "png"
        })
        
        if not output:
            raise Exception("No image generated")
        
        image_url = output[0] if isinstance(output, list) else output
        
        return {
            "success": True,
            "image_url": image_url,
            "prompt": req.prompt,
            "model": "FLUX Schnell"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")


# ─────────────────────────────────────────────────────
# CHAT ENDPOINT
# ─────────────────────────────────────────────────────
@router.post("/message")
async def chat_message(req: ChatRequest):
    """Simple chat - can trigger image generation"""
    
    if req.generate_image:
        prompt = req.message.replace("generate:", "").replace("create:", "").strip()
        
        try:
            result = await generate_image(ImageGenerationRequest(prompt=prompt))
            return {
                "success": True,
                "response": f"Generated image: {prompt}",
                "image_url": result["image_url"],
                "image_generated": True
            }
        except Exception as e:
            return {
                "success": False,
                "response": f"Generation failed: {str(e)}",
                "image_generated": False
            }
    
    return {
        "success": True,
        "response": "I'm your AI assistant! Describe an image and I'll generate it.",
        "image_generated": False
    }


@router.get("/health")
async def health_check():
    return {
        "status": "online",
        "replicate_configured": bool(REPLICATE_API_KEY),
        "api_method": "REST (no SDK)"
    }