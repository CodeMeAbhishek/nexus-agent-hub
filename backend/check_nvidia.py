import os
import sys
from dotenv import load_dotenv

load_dotenv()

nvidia_key = os.environ.get("NVIDIA_API_KEY", "").strip()
print(f"Reading NVIDIA_KEY: {nvidia_key[:10]}...{nvidia_key[-4:]}")

from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="meta/llama-3.1-70b-instruct",
    api_key=nvidia_key,
    base_url="https://integrate.api.nvidia.com/v1",
    temperature=0,
)

print("Invoking NVIDIA NIM (OpenAI Compatible)...")
try:
    res = llm.invoke("Hello, are you working?")
    print("Response:", res.content)
except Exception as e:
    print("Error:", e)
