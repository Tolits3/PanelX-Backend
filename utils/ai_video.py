import replicate
import os
from tempfile import NamedTemporaryFile

async def generate_ai_video(image, style, clothes, accessory, background, pose, emotion, prompt):
    with NamedTemporaryFile(delete=False, suffix=".png") as temp_img:
        temp_img.write(await image.read())
        img_path = temp_img.name

    full_prompt = (
        f"Generate a short {style}-style animated scene. "
        f"Character wearing {clothes} with {accessory}. "
        f"Background: {background}. Pose: {pose}. Emotion: {emotion}. "
        f"Prompt details: {prompt}"
    )

    # Example with a video model on Replicate (Pika or RunwayML)
    model = replicate.models.get("pika-labs/pika-video")
    output = model.predict(prompt=full_prompt, input_image=open(img_path, "rb"))

    return output[0] if isinstance(output, list) else output
