// api/proxy/fetch.js
// Vercel serverless function for strwatch.io (vanilla Node, not Next.js)
// Proxies .gov page fetches from DigitalOcean scraper

const crypto = require('crypto');

const ALLOWED_DOMAINS = [
  'charleston-sc.gov',
  'www.charleston-sc.gov',
  'savannahga.gov',
  'www.savannahga.gov',
  'sandiego.gov',
  'www.sandiego.gov',
  'seshat.datasd.org',
  'data.sandiego.gov',
  'austintexas.gov',
  'www.austintexas.gov',
  'palmspringsca.gov',
  'www.palmspringsca.gov',
];

function isAuthorized(provided) {
  const expected = process.env.PROXY_SECRET;
  if (!expected || typeof provided !== 'string') return false;
  const a = Buffer.from(provided, 'utf8');
  const b = Buffer.from(expected, 'utf8');
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

module.exports = async (req, res) => {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Shared secret is accepted from the x-proxy-secret header only (never the
  // query string, which ends up in access logs). Constant-time comparison.
  if (!isAuthorized(req.headers['x-proxy-secret'])) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const targetUrl = req.query.url;
  if (!targetUrl) {
    return res.status(400).json({ error: 'Missing url parameter' });
  }

  let parsed;
  try {
    parsed = new URL(targetUrl);
  } catch {
    return res.status(400).json({ error: 'Invalid URL' });
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return res.status(400).json({ error: 'Only http(s) URLs are allowed' });
  }
  if (parsed.port !== '') {
    return res.status(400).json({ error: 'Explicit ports are not allowed' });
  }
  const hostname = parsed.hostname;

  if (!ALLOWED_DOMAINS.includes(hostname)) {
    return res.status(403).json({ error: `Domain not allowed: ${hostname}` });
  }

  try {
    const response = await fetch(targetUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
      },
      signal: AbortSignal.timeout(30000),
      redirect: 'follow',
    });

    // Government sites redirect freely (http->https, trailing slashes, CMS moves),
    // so follow them — but never serve a response that ended up off the allowlist.
    let finalHost;
    try {
      finalHost = new URL(response.url || targetUrl).hostname;
    } catch {
      finalHost = '';
    }
    if (!ALLOWED_DOMAINS.includes(finalHost)) {
      console.error(`Proxy refused off-allowlist redirect for ${targetUrl}: landed on ${finalHost || '?'}`);
      return res.status(502).json({ error: 'Upstream redirected off allowlist' });
    }

    if (!response.ok) {
      return res.status(response.status).json({
        error: `Upstream returned ${response.status}`,
      });
    }

    const body = await response.text();
    const contentType = response.headers.get('content-type') || 'text/html';

    res.setHeader('Content-Type', contentType);
    res.setHeader('X-Proxied-From', hostname);
    res.setHeader('Cache-Control', 'no-store');
    return res.status(200).send(body);

  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error(`Proxy fetch error for ${targetUrl}:`, message);
    return res.status(502).json({ error: 'Proxy fetch failed' });
  }
};
