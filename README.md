# Nexus Agent Hub

Agentic AI for Tinkerthon 4.0 (TEC-4): internal knowledge access and action across Slack, Notion, GitHub, Stripe, MongoDB, and more. MCP + LangGraph backend; Vite + React frontend.

## Repo layout

- **Frontend** (this root): Vite, React, TypeScript, shadcn/ui — chat, Reasoning Trace, Limb dashboard.
- **Backend** (`backend/`): FastAPI — health, `/api/tools` (limb handshake), SSE and LangGraph in later phases.

## Getting started

```sh
# Frontend
npm i
npm run dev          # http://localhost:8080

# Backend (separate terminal; PowerShell use ; instead of &&)
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Set `VITE_API_URL=http://localhost:8000` in frontend `.env` if needed. See `backend/README.md` for env and API tokens.

**Login from India:** Supabase can be blocked there. Deploy the proxy in `supabase-proxy/` (see [supabase-proxy/DEPLOY.md](supabase-proxy/DEPLOY.md)) and set `SUPABASE_URL` to the proxy URL in `backend/.env`.

## Scripts

- `npm run dev` — Start dev server with hot reload
- `npm run build` — Production build
- `npm run preview` — Preview production build
- `npm run lint` — Run ESLint
- `npm run test` — Run tests
