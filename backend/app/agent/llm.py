"""
LLM Configuration for Nexus Agent.

Two backends for Gemini:
- Vertex AI (GCP): Set GOOGLE_CLOUD_PROJECT to use your GCP project's billing and credits.
  Uses Application Default Credentials (gcloud auth application-default login).
- Gemini Developer API (AI Studio): Set GOOGLE_API_KEY for the free-tier API key.
  Subject to free-tier limits; does NOT use GCP billing/credits.
"""
import os
import logging
from langchain_core.rate_limiters import InMemoryRateLimiter

logger = logging.getLogger(__name__)


def get_llm():
    """
    Get Google Gemini LLM. Uses Vertex AI (GCP billing/credits) if GOOGLE_CLOUD_PROJECT
    is set; otherwise uses Gemini Developer API (AI Studio key) with GOOGLE_API_KEY.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_openai import ChatOpenAI

    # CHECK FOR LOCAL LLM OVERRIDE
    use_local = os.environ.get("USE_LOCAL_LLM", "false").lower() == "true"

    if use_local:
        logger.info("[LLM] Using LOCAL LLM via LM Studio (http://localhost:1234/v1)")
        return ChatOpenAI(
            base_url="http://localhost:1234/v1",
            api_key="lm-studio",
            model="local-model",
            temperature=0,
            timeout=120,
        )

    # VERTEX AI (GCP): uses project billing and credits — no AI Studio free-tier limit
    gcp_project = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    if gcp_project:
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1").strip()
        logger.info(
            "[LLM] Using Vertex AI (GCP billing/credits) project=%s location=%s",
            gcp_project,
            location,
        )
        rate_limiter = InMemoryRateLimiter(
            requests_per_second=10,
            check_every_n_seconds=0.1,
            max_bucket_size=20,
        )
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0,
            max_retries=5,
            timeout=120,
            rate_limiter=rate_limiter,
            vertexai=True,
            project=gcp_project,
            location=location,
        )

    # GEMINI DEVELOPER API (AI Studio): free-tier key — subject to free-tier quotas (limit: 0 when exhausted)
    gemini_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not gemini_key:
        raise ValueError(
            "Set GOOGLE_API_KEY (AI Studio key at https://aistudio.google.com/apikey) "
            "OR set GOOGLE_CLOUD_PROJECT to your GCP project ID to use Vertex AI and your GCP billing/credits."
        )
    logger.info("[LLM] Using Gemini Developer API (AI Studio key)")
    rate_limiter = InMemoryRateLimiter(
        requests_per_second=10,
        check_every_n_seconds=0.1,
        max_bucket_size=20,
    )
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        max_retries=5,
        timeout=120,
        rate_limiter=rate_limiter,
    )
