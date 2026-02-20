import replicate
import os
from tempfile import NamedTemporaryFile

async def generate_ai_image(image, style, clothes, accessory, background, pose, emotion, prompt):
    # Save uploaded image temporarily
    with NamedTemporaryFile(delete=False, suffix=".png") as temp_img:
        temp_img.write(await image.read())
        img_path = temp_img.name

    # Build natural prompt
    full_prompt = (
        f"Generate a {style}-style comic scene. "
        f"Character wearing {clothes} with {accessory}. "
        f"Background: {background}. Pose: {pose}. Emotion: {emotion}. "
        f"Extra details: {prompt}"
    )

    # Call Replicate model (example: stable-diffusion or anime model)
    model = replicate.models.get("stability-ai/stable-diffusion")
    output = model.predict(prompt=full_prompt, image=open(img_path, "rb"))

    return output[0] if isinstance(output, list) else output
