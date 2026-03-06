import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

key = os.environ.get("GOOGLE_API_KEY")
print(f"Checking Google API Key: {key[:10]}...{key[-5:]}")

client = genai.Client(api_key=key)

print("\n--- Testing gemini-1.5-flash ---")
try:
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents="Hello, are you working? Reply in one sentence."
    )
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Test Failed: {e}")
