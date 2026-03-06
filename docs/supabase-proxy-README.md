# Supabase proxy when *.supabase.co is blocked (e.g. India)

## Why use a proxy?

In some regions (e.g. India), `*.supabase.co` can be blocked or unreachable. The app can still work by pointing `SUPABASE_URL` to a proxy that forwards requests to your real Supabase project.

## Option 1: Cloudflare Worker (simple, but 530 in India)

- Deploy `supabase-proxy-worker.js` as a Cloudflare Worker.
- Set the Worker URL as `SUPABASE_URL` in backend `.env` (no trailing slash):
  - `SUPABASE_URL=https://supabase-proxy.YOUR_ACCOUNT.workers.dev`

**If you get HTTP 530:**  
530 is Cloudflare’s “Origin DNS Error”. The Worker runs on the edge; when that edge is in a region where Supabase is blocked, it cannot resolve `*.supabase.co`, so the Worker’s `fetch()` to Supabase fails. Cloudflare Workers cannot override the `Host` header to use a different hostname, so this cannot be fixed by DNS tricks inside Workers. Use **Option 2** instead.

## Option 2: External proxy (recommended when 530 happens)

A ready-made proxy lives in **`supabase-proxy/`**. Deploy it to Railway or Render (5 min).

**→ Fast guide: [supabase-proxy/DEPLOY.md](../supabase-proxy/DEPLOY.md)**

1. Deploy the `supabase-proxy` folder to Railway or Render (see DEPLOY.md).
2. Set env `SUPABASE_ORIGIN=https://bckwiupiefznkojxejbx.supabase.co` on the proxy service.
3. In `backend/.env` set `SUPABASE_URL=https://your-proxy-url` (no trailing slash). Restart backend.

### Backend .env

- Use the proxy URL **without** a trailing slash to avoid double slashes:
  - `SUPABASE_URL=https://your-proxy.railway.app`
  - or `SUPABASE_URL=https://supabase-proxy.YOUR_ACCOUNT.workers.dev` (if Worker works in your region)

Keep `SUPABASE_ANON_KEY` and `SUPABASE_SERVICE_ROLE_KEY` unchanged (they are for your Supabase project, not the proxy).
