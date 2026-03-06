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

## Notion limb (first MCP integration)

1. **Node.js** must be on PATH (backend spawns `npx @notionhq/notion-mcp-server`).
2. Create an [internal integration](https://www.notion.so/profile/integrations), copy the **Internal Integration Secret** (starts with `ntn_`).
3. In backend `.env`: `NOTION_TOKEN=ntn_your_secret_here`.
4. Restart the backend; `/api/tools` will show Notion as **active** with tool count. Frontend Limb Dashboard will show Notion as Active.

## Frontend

From repo root, frontend expects backend at `http://localhost:8000` or set `VITE_API_URL` in `.env`.
