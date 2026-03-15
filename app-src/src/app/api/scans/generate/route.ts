import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY || ''
const MODEL = 'claude-sonnet-4-5-20250929'

const BETA_MARKETS: Record<string, string> = {
  'Nashville, TN': `Nashville STR data from STRWatch scrapers:
- Legislation source: Legistar API (webapi.legistar.com/v1/nashville)
- Permit types: Type 1 (owner-occupied), Type 2 (non-owner-occupied), Type 3 (multi-unit)
- Non-owner-occupied permits subject to density caps per neighborhood
- Permit cap enforced via overlay district system
- Annual permit renewal required
- Fines: $500/day for operating without a valid permit
- Metro Codes enforcement: 615-862-6590
- STR overlay district expansion under review for Q2 2026
- Key regulation: properties in R/RS zones restricted for non-owner-occupied
- Recent activity: Resolution RS2025-1172 granted STR distance requirement exemption`,

  'Austin, TX': `Austin STR data from STRWatch scrapers:
- License source: Austin Open Data SODA API (2,750 active licenses)
- License types: Type 1 (767), Type 1-A (109), Type 1-Secondary (221), Type 2 Commercial (33), Type 2 Residential (983), Type 3 (637)
- CRITICAL: July 1, 2026 enforcement deadline — unlicensed STRs will be removed from Airbnb/VRBO
- Type 1: owner-occupied, allowed in all residential zones
- Type 2: non-owner-occupied, restricted to commercial zoning
- Type 3: part of a multi-family property
- Hotel Occupancy Tax: 9% state + 7% city = 16% total
- Annual license renewal required
- Council monitors via austintexas.gov/department/city-council agendas`,

  'Denver, CO': `Denver STR data from STRWatch scrapers:
- License source: Colorado SODA API (7,449 total licenses, 6,870 active)
- Primary residence requirement — must be owner's primary home
- Annual license renewal: $100 fee
- Night cap enforced — exceeding limit = $1,000/night fine
- Lodger's tax: 10.75%
- Short-term rental = less than 30 consecutive days
- Active enforcement — revocations detected in scraper data
- License types tracked: Primary, Secondary
- Denver Business Licensing: denvergov.org`,

  'Scottsdale, AZ': `Scottsdale STR data from STRWatch scrapers:
- License source: ArcGIS REST API (2,999 active licenses)
- Annual license fee: $250/property
- Enforcement: $1,000/violation, active monitoring of listings
- Fields tracked: license number, address, owner, management company, emergency contact, property score
- Arizona state law limits city regulation of STRs but Scottsdale enforces licensing and nuisance ordinances
- Transaction Privilege Tax applies
- Emergency contact required on file with city`,

  'Palm Springs, CA': `Palm Springs STR data from STRWatch scrapers:
- One of the strictest STR regimes in the US
- 20% neighborhood density cap (10 of 66 neighborhoods already at cap)
- 26 rental contracts/year max (reduced from 36 as of Jan 1, 2026)
- Registration fee: $1,072/year per property
- Fines: $5,000 + permanent disqualification for violations
- TOT: 11.5% + city tax = ~19.75% total tax burden
- City publicly lists suspended properties
- Monitored via PrimeGov council portal (palmsprings.primegov.com)
- Vacation rental density page tracks neighborhood cap status`,
}

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { city } = await req.json()
  if (!city || typeof city !== 'string' || city.length > 100) {
    return NextResponse.json({ error: 'Invalid city' }, { status: 400 })
  }

  // Check tier — must be pro or on trial
  const supabase = createClient()
  const { data: tierData } = await supabase
    .from('user_tiers')
    .select('tier, trial_ends_at')
    .eq('user_id', userId)
    .single()

  const now = new Date()
  const tier = tierData?.tier || 'free'
  const trialEndsAt = tierData?.trial_ends_at ? new Date(tierData.trial_ends_at) : null
  const isTrialActive = trialEndsAt && trialEndsAt > now && tier === 'pro'
  const isPaid = tier === 'pro' && !trialEndsAt
  const isAgency = tier === 'agency'

  if (tier === 'free' && !isTrialActive) {
    return NextResponse.json({ error: 'Upgrade to Pro for market scans' }, { status: 403 })
  }

  // Check if this is a beta market (enriched data available)
  const betaContext = BETA_MARKETS[city] || null
  const isEnriched = !!betaContext

  const systemPrompt = `You are a short-term rental (STR) regulation analyst. Generate a comprehensive pre-investment market scan report for a city.

Your report must be structured as JSON with the following sections. Be specific — include actual dollar amounts, percentages, permit types, and enforcement details. When you are confident about a fact, state it directly. When you are less certain, note "verify with local government."

${betaContext ? `You have access to real-time scraped data for this market:\n${betaContext}\n\nUse this data to make the report as specific and current as possible.` : 'Use your knowledge of US STR regulations. Note that details should be verified with local government as they may have changed.'}

Respond ONLY with valid JSON, no markdown fences, no preamble.`

  const userPrompt = `Generate a pre-investment STR market scan for: ${city}

Return this exact JSON structure:
{
  "city": "${city}",
  "generated_at": "${new Date().toISOString().split('T')[0]}",
  "summary": "2-3 sentence executive summary of the STR regulatory environment",
  "risk_level": "low" | "medium" | "high" (based on regulatory burden),
  "sections": {
    "permit_requirements": {
      "title": "Permit & License Requirements",
      "items": [
        {"label": "...", "value": "...", "detail": "..."}
      ]
    },
    "fees_and_taxes": {
      "title": "Fees & Tax Obligations",
      "items": [{"label": "...", "value": "...", "detail": "..."}]
    },
    "restrictions": {
      "title": "Operating Restrictions",
      "items": [{"label": "...", "value": "...", "detail": "..."}]
    },
    "enforcement": {
      "title": "Enforcement & Penalties",
      "items": [{"label": "...", "value": "...", "detail": "..."}]
    },
    "upcoming_changes": {
      "title": "Upcoming Changes & Deadlines",
      "items": [{"label": "...", "value": "...", "detail": "..."}]
    },
    "market_notes": {
      "title": "Market Notes",
      "items": [{"label": "...", "value": "...", "detail": "..."}]
    }
  },
  "key_contacts": [
    {"name": "...", "phone": "...", "url": "..."}
  ],
  "disclaimer": "This report is for informational purposes only and does not constitute legal advice. Verify all details with local government before making investment decisions."
}`

  if (!ANTHROPIC_API_KEY) {
    return NextResponse.json({ error: 'API not configured' }, { status: 500 })
  }

  try {
    const apiRes = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: 3000,
        system: systemPrompt,
        messages: [{ role: 'user', content: userPrompt }],
      }),
    })

    if (!apiRes.ok) {
      const err = await apiRes.text()
      console.error('Anthropic API error:', apiRes.status, err)
      return NextResponse.json({ error: 'Report generation failed' }, { status: 502 })
    }

    const data = await apiRes.json()
    let responseText = ''
    for (const block of data.content) {
      if (block.type === 'text') responseText += block.text
    }

    // Parse JSON — handle markdown fences, preamble text, etc.
    let clean = responseText.trim()
    
    // Strip markdown code fences (```json ... ``` or ``` ... ```)
    const fenceMatch = clean.match(/```(?:json)?\s*\n?([\s\S]*?)\n?\s*```/)
    if (fenceMatch) {
      clean = fenceMatch[1].trim()
    }
    
    // If still not starting with {, try to find the JSON object
    if (!clean.startsWith('{')) {
      const jsonStart = clean.indexOf('{')
      const jsonEnd = clean.lastIndexOf('}')
      if (jsonStart !== -1 && jsonEnd !== -1) {
        clean = clean.substring(jsonStart, jsonEnd + 1)
      }
    }

    let report
    try {
      report = JSON.parse(clean)
    } catch (parseErr) {
      console.error('JSON parse failed. Raw response:', responseText.substring(0, 500))
      return NextResponse.json({ error: 'Report generation failed — invalid response format' }, { status: 502 })
    }

    // Save to Supabase
    const { data: saved, error: saveErr } = await supabase
      .from('scans')
      .insert({
        user_id: userId,
        city,
        report,
        is_enriched: isEnriched,
      })
      .select('id')
      .single()

    if (saveErr) {
      console.error('Scan save error:', saveErr)
    }

    return NextResponse.json({
      id: saved?.id || null,
      report,
      is_enriched: isEnriched,
    })

  } catch (err) {
    console.error('Scan generation error:', err)
    return NextResponse.json({ error: 'Report generation failed' }, { status: 500 })
  }
}
