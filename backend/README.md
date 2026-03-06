# Nexus Agent Hub — Backend

FastAPI service for orchestration, MCP connectivity, and (later) SSE streaming.

## Setup

**PowerShell (Windows):**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # set NOTION_TOKEN for Notion limb (see Notion limb section)
```

**Bash (macOS/Linux):**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run

From `backend/` with venv activated:
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: http://localhost:8000/health  
- List tools (limbs): http://localhost:8000/api/tools  
- Docs: http://localhost:8000/docs  

## LLM (Gemini)

- **Use GCP billing/credits** (e.g. $300 free trial): set `GOOGLE_CLOUD_PROJECT` to your GCP project ID in `.env`. Enable the [Generative Language API](https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com) in that project. Then run `gcloud auth application-default login` once. Requests will use Vertex AI and your project’s billing.
- **Use AI Studio free tier**: set `GOOGLE_API_KEY` in `.env` (key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)). Subject to free-tier limits; when exhausted you get 429 / limit: 0.

See `.env.example` for all options.

## Notion limb (first MCP integration)

1. **Node.js** must be on PATH (backend spawns `npx @notionhq/notion-mcp-server`).
2. Create an [internal integration](https://www.notion.so/profile/integrations), copy the **Internal Integration Secret** (starts with `ntn_`).
3. In backend `.env`: `NOTION_TOKEN=ntn_your_secret_here`.
4. Restart the backend; `/api/tools` will show Notion as **active** with tool count. Frontend Limb Dashboard will show Notion as Active.

## Frontend

From repo root, frontend expects backend at `http://localhost:8000` or set `VITE_API_URL` in `.env`.

## Architecture & scaling

- **Limb registry** (`app/core/limbs.py`): Single source of truth for routes, keywords, and tool counts. Add a new limb by editing the registry and the corresponding loader in `app/agent/graph.py`.
- **Config** (`app/core/config.py`): Pydantic Settings for `CORS_ORIGINS`, `RATE_LIMIT_PER_MINUTE` (0 = disabled), and server options.
- **Rate limiting**: In-memory per IP/user; set `RATE_LIMIT_PER_MINUTE=0` to disable. For multi-worker deployments, replace with a Redis-backed limiter.
- **Request ID**: Every response includes `X-Request-ID` for tracing; use in logs for production debugging.
- **Chat history**: Shared helper in `app/db/chat_history.py` used by both chat and stream endpoints.
- **Health**: Use `/health` for liveness; extend with DB/LLM checks for readiness if needed.
