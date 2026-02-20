import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if api_key:
    print(f"✅ API Key found!")
    print(f"   First 10 chars: {api_key[:10]}...")
    print(f"   Length: {len(api_key)} characters")
    print(f"   Starts with 'AIza': {api_key.startswith('AIza')}")
else:
    print("❌ GOOGLE_API_KEY not found in environment!")
    print("\nMake sure your .env file contains:")
    print("GOOGLE_API_KEY=your_key_here")