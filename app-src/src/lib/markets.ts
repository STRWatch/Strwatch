// Server-side source of truth for the monitored markets. Imported by both the
// markets UI (search/aliases) and server actions (city validation).

export type Market = { city: string; zips: string[]; aliases: string[]; desc: string }

export const MARKETS: Market[] = [
  { city: 'Nashville, TN',       zips: ['370','371','372','373','374','375','376','377','378','379'], aliases: ['nashville','music city'], desc: 'Legistar API · Permit tiers · Active enforcement' },
  { city: 'Austin, TX',          zips: ['737','786','787','788','789'], aliases: ['austin'], desc: 'July 1 deadline · 2,744 licenses · Council agenda scanning' },
  { city: 'Denver, CO',          zips: ['800','801','802','803','804','805'], aliases: ['denver','mile high'], desc: '7,449 licenses · SODA API · Legistar council monitoring' },
  { city: 'Scottsdale, AZ',      zips: ['852'], aliases: ['scottsdale'], desc: '2,999 licenses · ArcGIS API · TPT lodging tax' },
  { city: 'Palm Springs, CA',    zips: ['922'], aliases: ['palm springs','coachella valley'], desc: 'PrimeGov portal · Active enforcement · TOT' },
  { city: 'New Orleans, LA',     zips: ['700','701'], aliases: ['new orleans','nola'], desc: '1,300 licenses · Legistar + SODA API' },
  { city: 'San Diego, CA',       zips: ['919','920','921'], aliases: ['san diego','sd'], desc: '7,954 STRO licenses · 4-tier system' },
  { city: 'Charleston, SC',      zips: ['294'], aliases: ['charleston'], desc: 'Strict zoning overlay · ~700 permits' },
  { city: 'Savannah, GA',        zips: ['314'], aliases: ['savannah'], desc: 'STVR overlay · 20% ward cap · 8% hotel/motel tax' },
  { city: 'San Francisco, CA',   zips: ['941'], aliases: ['san francisco','sf','san fran'], desc: '$925 app fee · 90-night cap · Legistar monitoring' },
  { city: 'Miami Beach, FL',     zips: ['331'], aliases: ['miami','miami beach','south beach'], desc: '$20K+ fines · Strict zoning · 4 licenses required' },
  { city: 'Gatlinburg, TN',      zips: ['377'], aliases: ['gatlinburg','smoky mountains','smokies'], desc: 'Tourist Residency Permit · Smoky Mountains' },
  { city: 'Asheville, NC',       zips: ['287','288'], aliases: ['asheville'], desc: 'Whole-home STRs banned residential · Homestays only' },
  { city: 'Key West, FL',        zips: ['330','340'], aliases: ['key west','florida keys','keys'], desc: 'Finite transient licenses · 5% TDT · Monroe County' },
  { city: 'Sedona, AZ',          zips: ['863'], aliases: ['sedona'], desc: 'Annual permit · 1,200+ STRs · 24/7 hotline' },
  { city: 'Park City, UT',       zips: ['840'], aliases: ['park city'], desc: 'Nightly Rental License · Resort zones only' },
  { city: 'Breckenridge, CO',    zips: ['804'], aliases: ['breckenridge','breck','summit county'], desc: '4 STR zones with caps · Waitlists active' },
  { city: 'Big Bear, CA',        zips: ['923'], aliases: ['big bear','big bear lake'], desc: 'SB County permit · $1,144 app fee · Noise monitoring' },
  { city: 'Honolulu, HI',        zips: ['968'], aliases: ['honolulu','oahu','waikiki','hawaii'], desc: '90-day minimum residential · $500/day fines' },
  { city: 'Outer Banks, NC',     zips: ['279','272'], aliases: ['outer banks','obx','nags head','kill devil hills'], desc: 'Multi-jurisdiction · Largest US VR market' },
  { city: 'NYC, NY',             zips: ['100','101','102','103','104','110','111','112','113','114','116'], aliases: ['new york','new york city','nyc','manhattan','brooklyn','queens'], desc: 'OSE registration · Local Law 18 · Strict enforcement' },
  { city: 'Los Angeles, CA',     zips: ['900','901','902','903','904','905','906','907','908','910','911','912','913','914','915','916'], aliases: ['los angeles','la','hollywood','venice'], desc: 'Home Sharing Ordinance · $850 registration · HSO zones' },
  { city: 'Portland, OR',        zips: ['970','971','972'], aliases: ['portland','pdx'], desc: '11.5% TLT · $4/night fee · Quarterly filing' },
  { city: 'Orlando, FL',         zips: ['328','327','347','348'], aliases: ['orlando','disney','kissimmee'], desc: 'Home Sharing Registration · Orange County TDT' },
  { city: 'Las Vegas, NV',       zips: ['889','890','891'], aliases: ['las vegas','vegas'], desc: 'Clark County STR licensing · Business license required' },
  { city: 'Boston, MA',          zips: ['021','022'], aliases: ['boston'], desc: 'ISD registration · Legistar council monitoring' },
  { city: 'Maui, HI',            zips: ['967'], aliases: ['maui','lahaina','kihei','wailea'], desc: 'STRH permits · B&B permits · Planning commission' },
  { city: 'Lake Tahoe, CA',      zips: ['961','960','894','895'], aliases: ['lake tahoe','tahoe','south lake tahoe'], desc: 'El Dorado VHR · Placer County · Multi-jurisdiction' },
  { city: 'Tybee Island, GA',    zips: ['313'], aliases: ['tybee','tybee island'], desc: 'STVR certificate · Chatham County · GA hotel/motel fee' },
  { city: 'Destin, FL',          zips: ['325'], aliases: ['destin','30a','miramar beach','santa rosa beach'], desc: '6% TDT · Okaloosa County · FL DBPR license' },
  { city: 'Indianapolis, IN',   zips: ['462','460','461','463','464','465','466'], aliases: ['indianapolis','indy','marion county'], desc: '$150 permit · DBNS licensing · Marion County 10% CIT' },
]

export const MARKET_CITIES: string[] = MARKETS.map(m => m.city)

export function isKnownMarket(city: string): boolean {
  return MARKET_CITIES.includes(city)
}
