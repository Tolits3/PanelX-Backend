import os
import base64
import json
import asyncio
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# ---------------------------------------
# CONFIG
# ---------------------------------------
HF_ROUTER = os.getenv("HF_ROUTER", "https://router.huggingface.co/hf-inference")
HF_TOKEN = os.getenv("HF_TOKEN", "hf_CKlyvrwxptipsbigxjsKbyKnNKZuydHkb")
GENERATED_DIR = "generated/characters"

os.makedirs(GENERATED_DIR, exist_ok=True)

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# ---------------------------------------
# INPUT MODEL FROM FRONTEND
# ---------------------------------------
class CharacterTraits(BaseModel):
    name: str
    gender: str = "neutral"
    hair: str = "short"
    eyes: str = "normal"
    clothes: str = "casual"
    vibe: str = "anime"
    style: str = "manga"
    seed: int | None = None


# ---------------------------------------
# PROMPT TEMPLATES FOR DIFFERENT ANGLES
# ---------------------------------------
ANGLE_TEMPLATES = {
    "front": "{base_prompt}, front view, symmetrical, full body, neutral pose",
    "three_q_left": "{base_prompt}, 3/4 view left, dynamic lighting, full body",
    "three_q_right": "{base_prompt}, 3/4 view right, dynamic lighting, full body",
    "left_profile": "{base_prompt}, side profile left, full body",
    "back": "{base_prompt}, back view, full body"
}

def build_base_prompt(traits: CharacterTraits):
    parts = [
        f"{traits.name}, {traits.gender}",
        f"{traits.hair} hair",
        f"{traits.eyes} eyes",
        traits.clothes,
        traits.vibe,
        "consistent character, clean lineart, high detail"
    ]
    if traits.style:
        parts.append(f"art style: {traits.style}")

    return ", ".join(parts)


# ---------------------------------------
# HF GENERATION FUNCTION
# ---------------------------------------
async def hf_generate_image(model: str, prompt: str, width=768, height=1152, seed=None):
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": width,
            "height": height,
            "num_inference_steps": 20,
            "guidance_scale": 7.5,
        }
    }

    if seed is not None:
        payload["parameters"]["seed"] = seed

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{HF_ROUTER}/{model}",
            headers=HEADERS,
            json=payload
        )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=500, detail=f"HuggingFace Error: {str(e)}")

    result = response.json()

    if "generated_image" not in result:
        raise HTTPException(status_code=500, detail="HF missing 'generated_image'")

    return base64.b64decode(result["generated_image"])


# ---------------------------------------
# SAVE IN FILESYSTEM
# ---------------------------------------
def save_image_bytes(character_id: str, angle: str, img_bytes: bytes):
    folder = os.path.join(GENERATED_DIR, character_id)
    os.makedirs(folder, exist_ok=True)

    filename = f"{angle}_{os.urandom(3).hex()}.png"
    filepath = os.path.join(folder, filename)

    with open(filepath, "wb") as f:
        f.write(img_bytes)

    return f"/{filepath.replace(os.path.sep, '/')}"


# ---------------------------------------
# MAIN ENDPOINT
# ---------------------------------------
@router.post("/create-character")
async def create_character(traits: CharacterTraits):
    base_prompt = build_base_prompt(traits)

    prompts = {
        angle: template.format(base_prompt=base_prompt)
        for angle, template in ANGLE_TEMPLATES.items()
    }

    seed = traits.seed

    tasks = [
        hf_generate_image("stabilityai/sdxl-turbo", prompt, seed=seed)
        for prompt in prompts.values()
    ]

    try:
        results = await asyncio.gather(*tasks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    character_id = f"char_{os.urandom(4).hex()}"
    angle_keys = list(prompts.keys())

    urls = {}
    for angle_key, img_bytes in zip(angle_keys, results):
        url = save_image_bytes(character_id, angle_key, img_bytes)
        urls[angle_key] = url

    rig = {
        "character_id": character_id,
        "name": traits.name,
        "angles": urls,
        "attach_points": {
            "head": {"x": 0.5, "y": 0.15},
            "right_hand": {"x": 0.75, "y": 0.65},
            "left_hand": {"x": 0.25, "y": 0.65}
        }
    }

    # Save rig.json
    with open(os.path.join(GENERATED_DIR, character_id, "rig.json"), "w") as f:
        json.dump(rig, f)

    return {"status": "success", "character_id": character_id, "rig": rig}
