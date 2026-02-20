from huggingface_hub import InferenceClient
from PIL import Image
import io, os, traceback
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("HF_TOKEN")
prompt = "a samurai under the moonlight, manhwa style"

try:
    client = InferenceClient(
    model="stabilityai/sdxl-turbo",
    token=token,
    provider="hf-inference"
   )
    result = client.text_to_image(prompt)
    if isinstance(result, (bytes, bytearray)):
        img = Image.open(io.BytesIO(result))
    else:
        img = result
    img.save("test_result.png")
    print("✅ Saved test_result.png successfully.")
except Exception as e:
    traceback.print_exc()
