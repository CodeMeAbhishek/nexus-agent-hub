# Deploy Supabase proxy (5 min) — fix login from India

Deploy the `supabase-proxy` folder to **Render**, then point `SUPABASE_URL` in `backend/.env` at the proxy URL.

---

## Render

1. **Sign in:** [render.com](https://render.com) → Login with GitHub.

2. **New Web Service:**  
   **New +** → **Web Service** → connect the `nexus-agent-hub` repo (or your fork).

3. **Configure:**
   - **Root Directory:** `supabase-proxy`
   - **Build Command:** leave empty
   - **Start Command:** `node server.js`
   - **Instance type:** Free

4. **Environment:**  
   **Environment** tab → **Add Environment Variable**:
   - Key: `SUPABASE_ORIGIN`
   - Value: `https://bckwiupiefznkojxejbx.supabase.co`  
   (use your Supabase project URL if different.)

5. **Create Web Service.**  
   Wait for deploy, then copy the service URL (e.g. `https://supabase-proxy-xxxx.onrender.com`).

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
