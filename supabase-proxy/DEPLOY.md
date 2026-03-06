# Deploy Supabase proxy (5 min) — fix login from India

Deploy the `supabase-proxy` folder to **Render**, then point `SUPABASE_URL` in `backend/.env` at the proxy URL.

---

## Render

**Option A — Blueprint (easiest)**  
1. [render.com](https://render.com) → **New +** → **Blueprint** → connect `nexus-agent-hub` repo.  
2. Render reads `render.yaml` and creates the `supabase-proxy` service with the right root directory.  
3. Open the new service → **Environment** → set `SUPABASE_ORIGIN` = `https://bckwiupiefznkojxejbx.supabase.co`.  
4. Deploy runs; copy the service URL.

**Option B — Web Service (manual)**  
1. **New +** → **Web Service** → connect `nexus-agent-hub` repo.  
2. **Important:** In **Settings**, set **Root Directory** to `supabase-proxy` (otherwise you get `Cannot find module 'server.js'`).  
3. **Build Command:** leave empty. **Start Command:** `node server.js`.  
4. **Environment:** add `SUPABASE_ORIGIN` = `https://bckwiupiefznkojxejbx.supabase.co`.  
5. **Create Web Service** → copy the service URL.

6. **Backend .env:**  
   In `backend/.env` set (no trailing slash):
   ```env
   SUPABASE_URL=https://supabase-proxy-xxxx.onrender.com
   ```
   Restart the backend. Test login from India.

---

## Checklist

- [ ] Render Web Service created from `supabase-proxy` with `SUPABASE_ORIGIN` set
- [ ] `SUPABASE_URL` in `backend/.env` = Render URL (no trailing slash)
- [ ] Backend restarted
- [ ] Login works

---

## Alternative: Railway

**New Project** → Deploy from GitHub → **Settings → Root Directory** = `supabase-proxy` → **Variables:** `SUPABASE_ORIGIN` = `https://bckwiupiefznkojxejbx.supabase.co` → **Networking → Generate Domain**. Use that URL as `SUPABASE_URL` in `backend/.env`.
