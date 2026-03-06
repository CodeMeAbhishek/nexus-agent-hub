/**
 * Cloudflare Worker: reverse proxy for Supabase when *.supabase.co is blocked (e.g. India).
 * Deploy at Workers & Pages → Create Worker → paste this, set SUPABASE_ORIGIN, then Deploy.
 * Use the Worker URL (e.g. https://supabase-proxy.YOUR_ACCOUNT.workers.dev) as SUPABASE_URL in .env.
 *
 * If you get 530 (Origin DNS Error): the edge running this Worker cannot resolve *.supabase.co.
 * Use the external proxy instead: see docs/supabase-proxy-README.md.
 */

const SUPABASE_ORIGIN = 'https://bckwiupiefznkojxejbx.supabase.co';

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const pathname = url.pathname.replace(/^\/+/, '').replace(/\/+/g, '/');
    const path = pathname.startsWith('/') ? pathname : '/' + pathname;
    const targetUrl = SUPABASE_ORIGIN.replace(/\/+$/, '') + path + url.search;

    const headers = new Headers(request.headers);
    headers.set('Host', new URL(SUPABASE_ORIGIN).host);

    if (request.headers.get('Upgrade') === 'websocket') {
      try {
        return await fetch(targetUrl, { headers, method: request.method });
      } catch (e) {
        return new Response(JSON.stringify({ error: 'Proxy upstream failed', detail: String(e.message) }), {
          status: 502,
          headers: { 'Content-Type': 'application/json' },
        });
      }
    }

    try {
      const res = await fetch(targetUrl, {
        method: request.method,
        headers,
        body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
        redirect: 'follow',
      });
      return res;
    } catch (e) {
      return new Response(
        JSON.stringify({
          error: 'Proxy upstream failed (often 530 in India: edge cannot resolve Supabase). Use external proxy; see docs/supabase-proxy-README.md.',
          detail: String(e.message),
        }),
        { status: 502, headers: { 'Content-Type': 'application/json' } }
      );
    }
  },
};
