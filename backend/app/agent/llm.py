"""
LLM Configuration for Nexus Agent.
"""
import os
from langchain_core.rate_limiters import InMemoryRateLimiter

def get_llm():
    """
    Get Google Gemini LLM with professional rate limit handling.
    
    Implements:
    1. Client-side rate limiting via InMemoryRateLimiter (prevents 429s proactively)
    2. Built-in retry with exponential backoff via max_retries
    3. Appropriate timeout configuration
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_openai import ChatOpenAI
    
    # CHECK FOR LOCAL LLM OVERRIDE
    use_local = os.environ.get("USE_LOCAL_LLM", "false").lower() == "true"
    
    if use_local:
        print("[LLM] 🏠 Using LOCAL LLM via LM Studio (http://localhost:1234/v1)", flush=True)
        return ChatOpenAI(
            base_url="http://localhost:1234/v1",
            api_key="lm-studio",
            model="local-model", # LM Studio usually ignores this, or use the loaded model name
            temperature=0,
            timeout=120, # Local generation can be slower
        )
    
    # FALLBACK TO GEMINI
    gemini_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not gemini_key:
        raise ValueError(
            "GOOGLE_API_KEY not set. Get a FREE key at https://aistudio.google.com/apikey"
        )

    # Client-side rate limiter: 10 requests/second, max burst of 20
    # This prevents hitting API limits proactively
    rate_limiter = InMemoryRateLimiter(
        requests_per_second=10,      # Conservative limit (API allows 2000/min = 33/sec)
        check_every_n_seconds=0.1,   # Check frequently for smooth rate limiting
        max_bucket_size=20,          # Allow small bursts
    )
    
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        max_retries=5,
        timeout=120, # Gemini can be slow sometimes
        rate_limiter=rate_limiter,  # Proactive client-side rate limiting
    )
