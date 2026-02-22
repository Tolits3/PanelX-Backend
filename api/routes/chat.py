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
# SIMPLE AI CHAT RESPONSES (No API needed!)
# ─────────────────────────────────────────────────────
def get_ai_response(message: str) -> str:
    """Simple rule-based chatbot responses"""
    
    msg = message.lower().strip()
    
    # Introduction/creator
    if any(word in msg for word in ["i'm", "i am", "my name", "creator", "made this", "built this"]):
        return "Nice to meet you! 👋 Awesome that you're the creator of PanelX! I'm here to help you and your users brainstorm comic ideas. What kind of story are you working on today?"
    
    # Greetings (only for simple greetings, not full sentences)
    if msg in ["hello", "hi", "hey", "greetings", "yo", "sup", "what's up"]:
        return "Hello! 👋 I'm your AI comic assistant. I can help you brainstorm ideas for your comic panels! Try asking me to 'generate: a hero in space' or just chat about your story ideas."
    
    # Help
    if "help" in msg:
        return """Here's what I can do:
        
🎨 **Image Generation**: Type 'generate: your idea' (needs Replicate credits)
💭 **Brainstorming**: Ask me about story ideas, character concepts, or plot suggestions
📖 **Comic Tips**: Ask me about panel composition, pacing, or dialogue

What would you like help with?"""
    
    # Story/character ideas
    if any(word in msg for word in ["story", "plot", "character", "idea", "brainstorm"]):
        return """Great! Let's brainstorm! Some popular comic themes:

🦸 **Superhero**: Origin stories, powers, villains
🐉 **Fantasy**: Magic, quests, mythical creatures  
🚀 **Sci-Fi**: Space exploration, future tech, aliens
😂 **Comedy**: Slice of life, funny situations
💀 **Horror**: Suspense, supernatural, mystery

What genre interests you? Or tell me about your idea!"""
    
    # Panel/composition
    if any(word in msg for word in ["panel", "composition", "layout"]):
        return """Panel composition tips:

📐 **Rule of thirds**: Place key elements at intersection points
👁️ **Eye direction**: Guide readers left-to-right, top-to-bottom  
💥 **Action panels**: Use diagonal lines for dynamic movement
🔇 **Quiet moments**: Simple, centered compositions
📏 **Panel size**: Bigger panels = more important moments

Need specific advice for a scene?"""
    
    # Dialogue
    if "dialogue" in msg or "speech" in msg:
        return """Dialogue tips for comics:

💬 **Keep it short**: 2-3 sentences max per bubble
🎭 **Show, don't tell**: Use expressions and actions
⚡ **Pace it**: Break long speeches into multiple panels
🎨 **Bubble placement**: Top-left first, natural reading flow

Want examples for a specific scene?"""
    
    # Genre-specific
    if "superhero" in msg:
        return "Superhero story! Think about: What's their power? What's their weakness? Who's their nemesis? What drives them to be a hero?"
    
    if "fantasy" in msg:
        return "Fantasy epic! Consider: What's the magic system? What's the quest? Who are the companions? What's the ancient evil?"
    
    if "sci-fi" in msg or "space" in msg:
        return "Sci-fi adventure! Think about: What's the technology level? What planet/station? What's the conflict? First contact or space war?"
    
    # Generate request (without credits)
    if "generate" in msg or "draw" in msg or "create" in msg:
        if not REPLICATE_API_KEY:
            return "🎨 Image generation is currently disabled (Replicate API key not set). For now, try uploading your own images or using placeholder images while testing!"
        else:
            return "🎨 To generate an image, type: 'generate: your description' (e.g., 'generate: a dragon breathing fire'). Note: This requires Replicate credits."
    
    # Default conversational response
    responses = [
        f"Interesting! You mentioned '{message[:40]}{'...' if len(message) > 40 else ''}'. I'm here to help with your comic! Want to brainstorm a character, work on a scene, or get tips on composition?",
        f"I see! Tell me more about that. Are you working on a specific comic scene right now? I can help with story ideas, character concepts, or panel layout tips.",
        f"Got it! I'm your comic creation assistant. I can help you: 💡 Brainstorm story ideas | 🎨 Plan panel compositions | 💬 Write dialogue | 📖 Develop characters. What interests you?",
    ]
    
    # Pick response based on message length
    if len(message) < 20:
        return responses[2]
    elif "?" in message:
        return responses[1]
    else:
        return responses[0]


# ─────────────────────────────────────────────────────
# IMAGE GENERATION - REPLICATE (Optional)
# ─────────────────────────────────────────────────────
def call_replicate_api(model: str, input_data: dict):
    """Call Replicate API - only if key is available"""
    
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
    
    # Poll for result
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
    """Generate image using Replicate (requires API key)"""
    
    if not REPLICATE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Image generation unavailable. Replicate API key not configured."
        )
    
    try:
        enhanced_prompt = f"{req.prompt}, {req.style}, highly detailed, professional comic book illustration"
        
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
# CHAT ENDPOINT - Works WITHOUT Replicate!
# ─────────────────────────────────────────────────────
@router.post("/message")
async def chat_message(req: ChatRequest):
    """AI chat assistant - works with or without Replicate"""
    
    # Check if user wants image generation
    if req.generate_image or any(word in req.message.lower() for word in ["generate:", "draw:", "create:"]):
        if not REPLICATE_API_KEY:
            return {
                "success": False,
                "response": "🎨 Image generation is temporarily unavailable (Replicate credits needed). But I can still help you brainstorm ideas, give comic tips, and chat about your story!",
                "image_generated": False
            }
        
        # Try to generate image
        prompt = req.message.replace("generate:", "").replace("draw:", "").replace("create:", "").strip()
        
        try:
            result = await generate_image(ImageGenerationRequest(prompt=prompt))
            return {
                "success": True,
                "response": f"✨ Generated image for: {prompt}",
                "image_url": result["image_url"],
                "image_generated": True
            }
        except Exception as e:
            return {
                "success": False,
                "response": f"⚠️ Image generation failed: {str(e)}\n\nBut I can still chat and help with ideas!",
                "image_generated": False
            }
    
    # Regular chat - no API needed!
    response_text = get_ai_response(req.message)
    
    return {
        "success": True,
        "response": response_text,
        "image_generated": False
    }


@router.get("/health")
async def health_check():
    return {
        "status": "online",
        "replicate_configured": bool(REPLICATE_API_KEY),
        "chat_available": True,
        "image_generation_available": bool(REPLICATE_API_KEY)
    }