// api/proxy/fetch.js
// Vercel serverless function — proxies page fetches for .gov sites
// that block datacenter IPs (DigitalOcean, AWS, etc.)
//
// Usage: GET /api/proxy/fetch?url=https://www.charleston-sc.gov/1840/...&key=YOUR_SECRET
//
// Deploy in your strwatch.io Vercel project.

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

export default async function handler(req, res) {
  // Only allow GET
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Auth check — simple shared secret
  const key = req.query.key || req.headers['x-proxy-key'];
  if (key !== process.env.PROXY_SECRET) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const targetUrl = req.query.url;
  if (!targetUrl) {
    return res.status(400).json({ error: 'Missing url parameter' });
  }

  // Validate domain whitelist
  let hostname;
  try {
    hostname = new URL(targetUrl).hostname;
  } catch {
    return res.status(400).json({ error: 'Invalid URL' });
  }

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
    });

    if (!response.ok) {
      return res.status(response.status).json({
        error: `Upstream returned ${response.status}`,
        status: response.status,
      });
    }

    const contentType = response.headers.get('content-type') || 'text/html';
    const body = await response.text();

    res.setHeader('Content-Type', contentType);
    res.setHeader('X-Proxied-From', hostname);
    res.setHeader('Cache-Control', 'no-store');
    return res.status(200).send(body);

  } catch (err) {
    console.error(`Proxy fetch error for ${targetUrl}:`, err.message);
    return res.status(502).json({
      error: 'Proxy fetch failed',
      detail: err.message,
    });
  }
}
