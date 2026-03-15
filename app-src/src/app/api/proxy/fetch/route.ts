import { NextRequest, NextResponse } from 'next/server'

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
]

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl
  const key = searchParams.get('key') || request.headers.get('x-proxy-key')
  const targetUrl = searchParams.get('url')

  // Auth check
  if (key !== process.env.PROXY_SECRET) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  if (!targetUrl) {
    return NextResponse.json({ error: 'Missing url parameter' }, { status: 400 })
  }

  // Validate domain whitelist
  let hostname: string
  try {
    hostname = new URL(targetUrl).hostname
  } catch {
    return NextResponse.json({ error: 'Invalid URL' }, { status: 400 })
  }

  if (!ALLOWED_DOMAINS.includes(hostname)) {
    return NextResponse.json({ error: `Domain not allowed: ${hostname}` }, { status: 403 })
  }

  try {
    const response = await fetch(targetUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
      },
      signal: AbortSignal.timeout(30000),
    })

    if (!response.ok) {
      return NextResponse.json(
        { error: `Upstream returned ${response.status}` },
        { status: response.status }
      )
    }

    const body = await response.text()
    const contentType = response.headers.get('content-type') || 'text/html'

    return new NextResponse(body, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'X-Proxied-From': hostname,
        'Cache-Control': 'no-store',
      },
    })

  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err)
    console.error(`Proxy fetch error for ${targetUrl}:`, message)
    return NextResponse.json(
      { error: 'Proxy fetch failed', detail: message },
      { status: 502 }
    )
  }
}
