import requests

def generate_story(prompt: str, genre: str = "fantasy") -> str:
    combined_prompt = f"Create a {genre} comic story: {prompt}"

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "tinyllama", "prompt": combined_prompt},
            timeout=60
        )
        if response.status_code == 200:
            return response.json().get("response", "No story generated.")
        else:
            return f"Story generation failed: {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"
