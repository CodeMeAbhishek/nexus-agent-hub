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

## Connecting MongoDB (fresh Atlas)

1. **Create a free cluster** at [cloud.mongodb.com](https://cloud.mongodb.com). Sign up or log in → Build a Database → choose **M0 Free** → pick a region → Create.
2. **Create a DB user**: Database Access → Add New User → set username/password → Add User.
3. **Allow network access**: Network Access → Add IP Address → Add Current IP (or `0.0.0.0/0` for testing).
4. **Get the connection string**: Database → Connect → Drivers → copy the **connection string** (e.g. `mongodb+srv://user:password@cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority`). Replace `<password>` with your DB user password.
5. **In the app**: Open Nexus Agent Hub → **Settings** (or **Limbs**) → find **MongoDB** → **Connect** → paste the connection string → Connect.
6. **Backend (Windows + Atlas)**: If you see an SSL handshake error, run in the backend folder: `pip install "pymongo[tls]"` then restart the server.

## Scripts

- `npm run dev` — Start dev server with hot reload
- `npm run build` — Production build
- `npm run preview` — Preview production build
- `npm run lint` — Run ESLint
- `npm run test` — Run tests
