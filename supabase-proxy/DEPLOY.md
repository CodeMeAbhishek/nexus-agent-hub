# Deploy Supabase proxy (5 min) — fix login from India

Deploy the `supabase-proxy` folder to **Railway**, **Fly.io**, or **Render**, then set `SUPABASE_URL` in `backend/.env` to the proxy URL (no trailing slash).

---

## Railway (recommended)

1. **[railway.app](https://railway.app)** → **Login with GitHub**.

2. **New Project** → **Deploy from GitHub repo** → select **`nexus-agent-hub`**.  
   - If the repo doesn’t appear: click **Configure GitHub App**, then on GitHub add `nexus-agent-hub` to the repos Railway can access. Refresh Railway and try again.

3. After the service is created, open it and configure:
   - **Settings** → **Root Directory** → set to **`supabase-proxy`** → **Save**.
   - **Variables** → **New Variable** → name **`SUPABASE_ORIGIN`**, value **`https://bckwiupiefznkojxejbx.supabase.co`** (use your Supabase project URL if different).
   - **Settings** → **Networking** → **Generate Domain** → copy the URL (e.g. `https://nexus-agent-hub-production-xxxx.up.railway.app`).

4. In **`backend/.env`** set (no trailing slash):
   ```env
   SUPABASE_URL=https://YOUR-RAILWAY-URL
   ```
   Restart the backend and test login.

   **If the build fails** with "context canceled" or "copy /mise/installs": the repo now includes `railway.json` so Railway uses the **Dockerfile** builder. Commit and push, then trigger a new deploy.

---

## Fly.io

*Requires a payment method on file (free tier usage is not charged).*

1. Install [flyctl](https://fly.io/docs/hub/quickstart/) and run `fly auth login` (or `& "$env:USERPROFILE\.fly\bin\flyctl.exe" auth login` on Windows if `fly` isn’t in PATH).
2. `cd supabase-proxy` → `fly launch --no-deploy --name supabase-proxy` (use existing `fly.toml` when asked).
3. `fly secrets set SUPABASE_ORIGIN=https://bckwiupiefznkojxejbx.supabase.co`
4. `fly deploy` → copy the app URL.
5. In `backend/.env`: `SUPABASE_URL=https://supabase-proxy.fly.dev` (no trailing slash). Restart backend.

---

## Render

**Blueprint:** **New +** → **Blueprint** → connect repo. Render uses `render.yaml`; set **Environment** → `SUPABASE_ORIGIN` = `https://bckwiupiefznkojxejbx.supabase.co` → copy service URL.

**Manual:** **New +** → **Web Service** → connect repo → **Root Directory** = `supabase-proxy`, **Start Command** = `node server.js`, **Environment** = `SUPABASE_ORIGIN` = your Supabase URL → copy service URL.

Then in `backend/.env`: `SUPABASE_URL=https://your-service.onrender.com` (no trailing slash). Restart backend.

---

## Checklist (any platform)

- [ ] Proxy deployed with **Root Directory** (or equivalent) = `supabase-proxy`
- [ ] `SUPABASE_ORIGIN` set on the proxy service
- [ ] `SUPABASE_URL` in `backend/.env` = proxy URL, no trailing slash
- [ ] Backend restarted → test login
