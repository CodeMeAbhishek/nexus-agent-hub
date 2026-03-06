/**
 * Supabase reverse proxy — run outside India (e.g. Railway/Render) so login works.
 * Set SUPABASE_ORIGIN to your project URL; clients use this server's URL as SUPABASE_URL.
 */
const SUPABASE_ORIGIN = (process.env.SUPABASE_ORIGIN || 'https://bckwiupiefznkojxejbx.supabase.co').replace(/\/+$/, '');
const HOST = new URL(SUPABASE_ORIGIN).host;

async function readBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return Buffer.concat(chunks);
}

const server = require('http').createServer(async (req, res) => {
  const url = new URL(req.url || '/', `http://${req.headers.host}`);

  // Health check: GET / or /health
  if (req.method === 'GET' && (url.pathname === '/' || url.pathname === '/health')) {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({
      ok: true,
      supabase_origin_set: !!process.env.SUPABASE_ORIGIN,
      target: SUPABASE_ORIGIN,
    }));
  }

  const target = SUPABASE_ORIGIN + url.pathname + url.search;

  // Forward only safe headers; let fetch set Content-Length for body
  const skip = new Set(['host', 'connection', 'content-length', 'transfer-encoding']);
  const headers = { host: HOST };
  for (const [k, v] of Object.entries(req.headers)) {
    if (v != null && !skip.has(k.toLowerCase())) headers[k] = v;
  }

  const opts = { method: req.method, headers };
  if (!['GET', 'HEAD'].includes(req.method)) opts.body = await readBody(req);

  try {
    const r = await fetch(target, opts);
    const outHeaders = Object.fromEntries(r.headers.entries());
    res.writeHead(r.status, outHeaders);
    const buf = await r.arrayBuffer();
    res.end(Buffer.from(buf));
  } catch (e) {
    const detail = e.cause ? `${e.message} (${e.cause.message || e.cause})` : e.message;
    res.writeHead(502, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Proxy failed', detail: String(detail) }));
  }
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => console.log('Supabase proxy listening on', PORT, '→', SUPABASE_ORIGIN));
