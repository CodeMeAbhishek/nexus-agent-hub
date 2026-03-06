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
  const target = SUPABASE_ORIGIN + url.pathname + url.search;

  const headers = { ...req.headers, host: HOST };
  delete headers['host'];
  headers['host'] = HOST;

  const opts = { method: req.method, headers };
  if (!['GET', 'HEAD'].includes(req.method)) opts.body = await readBody(req);

  try {
    const r = await fetch(target, opts);
    const outHeaders = Object.fromEntries(r.headers.entries());
    res.writeHead(r.status, outHeaders);
    const buf = await r.arrayBuffer();
    res.end(Buffer.from(buf));
  } catch (e) {
    res.writeHead(502, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Proxy failed', detail: String(e.message) }));
  }
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => console.log('Supabase proxy listening on', PORT, '→', SUPABASE_ORIGIN));
