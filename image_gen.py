import os
import time
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from huggingface_hub import InferenceClient, HfApi
from PIL import Image
import io

# -------------------------------------------------------
# 🌍 SETUP
# -------------------------------------------------------
load_dotenv()

app = FastAPI(title="PanelX Image Generation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL = "black-forest-labs/FLUX.1-dev"
GENERATED_DIR = os.path.join(os.path.dirname(__file__), "generated")
os.makedirs(GENERATED_DIR, exist_ok=True)
app.mount("/generated", StaticFiles(directory=GENERATED_DIR), name="generated")

# -------------------------------------------------------
# 🔑 CHECK TOKEN
# -------------------------------------------------------
@app.get("/check-hf-token")
def check_hf_token():
    try:
        api = HfApi()
        info = api.whoami(token=HF_TOKEN)
        return {"valid": True, "user": info.get("name")}
    except Exception as e:
        return {"valid": False, "error": str(e)}

# -------------------------------------------------------
# 📸 IMAGE GENERATION
# -------------------------------------------------------
@app.post("/generate-image")
async def generate_image(request: Request):
    """
    POST JSON: {"prompt": "A swordsman under the moonlight, manhwa style"}
    Returns: {"image_url": ".../generated/panel_123.png"}
    """
    data = await request.json()
    prompt = data.get("prompt", "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt required")

    full_prompt = (
        f"{prompt}, full color, highly detailed, cinematic lighting, "
        "vertical webtoon panel, sharp lines, expressive faces"
    )

    print(f"🧠 Using model: {HF_MODEL}")
    print(f"📝 Prompt: {full_prompt}")

    try:
        # Generate filename BEFORE using it
        timestamp = int(time.time() * 1000)
        filename = f"panel_{timestamp}.png"
        filepath = os.path.join(GENERATED_DIR, filename)
        
        # Create Hugging Face client
        client = InferenceClient(model=HF_MODEL, token=HF_TOKEN)
        
        print(f"🎨 Generating image...")
        
        # Generate image
        image = client.text_to_image(full_prompt)
        
        # Save the image
        if isinstance(image, Image.Image):
            image.save(filepath)
            print(f"✅ Image saved to: {filepath}")
        else:
            # If it's bytes, convert to PIL Image first
            image_pil = Image.open(io.BytesIO(image))
            image_pil.save(filepath)
            print(f"✅ Image saved to: {filepath}")
        
        return {
            "image_url": f"http://localhost:8000/generated/{filename}",  # Use port 8000 (main server)
            "meta": {"prompt": full_prompt},
        }
        
    except Exception as e:
        print(f"⚠️ Hugging Face generation error: {e}")
        raise HTTPException(status_code=502, detail=f"HF generation failed: {e}")

# -------------------------------------------------------
# 🎬 VIDEO GENERATION PLACEHOLDER
# -------------------------------------------------------
@app.post("/generate-video")
async def generate_video(request: Request):
    """
    Placeholder route until HF exposes unified video generation through InferenceClient.
    """
    raise HTTPException(
        status_code=501,
        detail="Video generation not yet implemented with new Hugging Face router.",
    )

if __name__ == "__main__":
    from multiprocessing import freeze_support
    
    # Required for Windows multiprocessing
    freeze_support()
    
    print("🎨 Starting Image Generation Service...")
    print("📍 Running on http://localhost:8001")
    
    uvicorn.run(
        "image_gen:app",
        host="0.0.0.0",
        port=8001,
        reload=False  # Set to False to avoid Windows multiprocessing issues
    )