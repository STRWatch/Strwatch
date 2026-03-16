# STRWatch — Jurisdiction Coverage Audit & Expansion Plan

**Last updated:** March 16, 2026
**Status:** Phase A ✅ · Phase B ✅ · Phase C ✅ · Phase D next

---

## Overview

Each STR market has up to 4 regulatory layers. A host can be fined for missing compliance at ANY layer:

1. **City** — municipal STR ordinance, permits, code enforcement
2. **County** — county tax (TDT/TOT/lodging tax), county-level permits
3. **State** — state licensing (FL DBPR, HI DOTAX, etc.), state tax registration
4. **Legislation** — council agendas, proposed ordinances, upcoming votes

**Rating key:** ✅ Covered | ⚠️ Partial | ❌ Missing

---

## Current Coverage Summary

| Metric | Current (Post Phase C) | After Full Expansion |
|--------|----------------------|---------------------|
| Total page watchers | ~117 URLs | ~130+ URLs |
| Markets with county coverage | 18/30 | 28/30 |
| Markets with state coverage | 12/30 | 25/30 |
| Markets with legislation monitoring | 5/30 | 6/30 |
| Shared state scrapers | 1 (5 states) | 1 (5 states) |
| Shared county scrapers | 1 (8 counties) | 1 (8 counties) |
| Shared Legistar scrapers | 1 (3 cities) + 2 individual | 1 (3 cities) + 2 individual |

---

## Phase A — State-Level Pages ✅ COMPLETE

**File:** `scrapers/state_pages_web.py`
**Impact:** 12 URLs across 5 states, covering 12+ markets

| State | Pages | Markets Covered | Status |
|-------|-------|----------------|--------|
| FL DBPR | 3 (VR guide, H&R division, license checklist) | Miami Beach, Orlando, Key West, Destin/30A | ✅ |
| HI DOTAX | 2 (rental property guide, TAT forms) | Honolulu, Maui | ✅ |
| TN DOR | 2 (local occupancy tax, registration) | Nashville, Gatlinburg | ✅ |
| AZ DOR | 3 (STR lodging TPT, OLM, reporting guide) | Scottsdale, Sedona | ✅ |
| GA DOR | 2 (hotel-motel fee, registration guide) | Savannah, Tybee Island | ✅ |

**Note:** California has no single state TOT page — TOT is city/county administered. County pages added in Phase B.

---

## Phase B — Critical County Pages ✅ COMPLETE

**File:** `scrapers/county_pages_web.py`
**Impact:** 20 URLs across 8 counties, covering 8+ markets
**Deployed:** March 16, 2026 — 18/20 baselined on first run (El Dorado 403, Savannah timeout — Apify fallback on next cron)

| # | County | Market | Pages | URLs | Status |
|---|--------|--------|-------|------|--------|
| 1 | Davidson County, TN | Nashville | 3 | County Clerk STR license, Codes STR hub, permit app | ✅ Baselined |
| 2 | Travis County / Austin, TX | Austin | 2 | Hotel & Rental Tax overview, HOT rates & filing | ✅ Baselined |
| 3 | El Dorado County, CA | Lake Tahoe | 3 | VHR Division main, apps/forms, ordinance info | ⚠️ 403 (Apify fallback) |
| 4 | Multnomah County, OR | Portland | 2 | County TLT, Portland Revenue TLT filing | ✅ Baselined |
| 5 | Monroe County, FL | Key West | 1 | Tax Collector tourist development tax | ✅ Baselined |
| 6 | San Bernardino County, CA | Big Bear | 3 | STR program home, getting started, permitted map | ✅ Baselined |
| 7 | Okaloosa County, FL | Destin | 2 | Clerk tourist dev tax, FAQ | ✅ Baselined |
| 8 | Chatham County, GA | Savannah + Tybee | 2 | Savannah local/state taxes, STR vacation rentals | ⚠️ Timeout (retry) |

---

## Phase C — Legistar Expansion (TODO)

## Phase C — Legistar Expansion ✅ COMPLETE

**File:** `scrapers/legistar_multi.py`
**Impact:** Adds legislation keyword monitoring to 3 new cities (total 5/30 with legislation monitoring)

Existing Legistar scrapers: Nashville (`nashville_legistar.py`) + New Orleans (`nola_legistar.py`)

| City | Legistar Slug | API Status | Status |
|------|--------------|------------|--------|
| Denver | `denver` | ✅ 200 OK | ✅ Built |
| San Francisco | `sfgov` | ✅ 200 OK | ✅ Built |
| Boston | `boston` | ✅ 200 OK | ✅ Built |
| NYC | N/A | ❌ Requires API token (apply at council.nyc.gov) | Deferred |
| Los Angeles | N/A | ❌ Uses own CFMS system, not Legistar | Dropped |
| San Diego | N/A | ❌ City doesn't use Legistar (county does) | Dropped |

Single generalized scraper replaces the copy-paste pattern — loops through all cities with shared keyword matching.

---

## Phase D — Secondary County/State Pages (TODO)

| # | Page | Market(s) | Priority |
|---|------|-----------|----------|
| 1 | TX Comptroller — Hotel Occupancy Tax | Austin | 🟡 MEDIUM |
| 2 | NV Dept of Taxation — transient lodging | Las Vegas | 🟢 LOW |
| 3 | MA DOR — room occupancy excise | Boston | 🟢 LOW |
| 4 | OR DOR — transient lodging tax | Portland | 🟢 LOW |
| 5 | SC DOR — accommodations tax | Charleston | 🟢 LOW |
| 6 | NC DOR — occupancy tax | Outer Banks | 🟢 LOW |
| 7 | NY State — Multiple Dwelling Law | NYC | 🟢 LOW |
| 8 | UT Tax Commission — transient room tax | Park City | 🟢 LOW |
| 9 | LA Revenue Dept — STR tax | New Orleans | 🟢 LOW |
| 10 | Riverside County — TOT | Palm Springs | 🟡 MEDIUM |
| 11 | Maricopa County — transient lodging | Scottsdale | 🟡 MEDIUM |
| 12 | Yavapai County — tax | Sedona | 🟢 LOW |
| 13 | Washoe County — STR (NV side) | Lake Tahoe | 🟢 LOW |
| 14 | LA County — TOT (unincorporated) | Los Angeles | 🟡 MEDIUM |
| 15 | SD County — TOT | San Diego | 🟢 LOW |
| 16 | Summit County, UT — STR | Park City | 🟢 LOW |

---

## Per-Market Detail

### 1. Nashville, TN
- **City:** ✅ Legistar API + page watchers
- **County:** ✅ Davidson County Clerk STR license + Codes hub + permit app (Phase B)
- **State:** ✅ TN DOR (Phase A)
- **Legislation:** ✅ Legistar API

### 2. Austin, TX
- **City:** ✅ Page watchers + council agenda PDF parser
- **County:** ✅ Austin HOT overview + rates/filing (Phase B)
- **State:** ❌ Missing TX Comptroller HOT page
- **Legislation:** ✅ Council agenda keyword scanning

### 3. Denver, CO
- **City:** ✅ SODA API + page watchers
- **County:** ⚠️ Denver is city-county combined, missing lodging tax page
- **State:** ✅ Colorado SODA covers state dataset
- **Legislation:** ✅ Legistar API via legistar_multi.py (Phase C)

### 4. Miami Beach, FL
- **City:** ✅ 3 page watchers + Miami-Dade County page
- **County:** ✅ Miami-Dade STR regulations page
- **State:** ✅ FL DBPR (Phase A)
- **Legislation:** ❌ No commission monitoring

### 5. Scottsdale, AZ
- **City:** ✅ ArcGIS API
- **County:** ❌ Missing Maricopa County tax page
- **State:** ✅ AZ DOR TPT (Phase A)
- **Legislation:** ❌ No council monitoring

### 6. Palm Springs, CA
- **City:** ⚠️ Page watchers (verify URLs)
- **County:** ❌ Missing Riverside County TOT page
- **State:** N/A (CA TOT is local, not state)
- **Legislation:** ❌ No council monitoring

### 7. New Orleans, LA
- **City:** ✅ SODA API + Legistar + page watchers
- **County:** ⚠️ Orleans Parish is city-parish combined
- **State:** ❌ Missing LA Revenue Dept page
- **Legislation:** ✅ Legistar API

### 8. Charleston, SC
- **City:** ✅ 3 page watchers
- **County:** ❌ Missing Charleston County accommodations tax page
- **State:** ❌ Missing SC DOR page
- **Legislation:** ❌ No council monitoring

### 9. Savannah, GA
- **City:** ✅ 4 page watchers
- **County:** ✅ Chatham County — Savannah taxes + STR page (Phase B)
- **State:** ✅ GA DOR (Phase A)
- **Legislation:** ❌ No council monitoring

### 10. San Francisco, CA
- **City:** ✅ 4 page watchers
- **County:** ✅ SF is city-county combined
- **State:** N/A (CA TOT is local)
- **Legislation:** ✅ Legistar API via legistar_multi.py (Phase C)

### 11. San Diego, CA
- **City:** ✅ 3 page watchers
- **County:** ❌ Missing SD County TOT page
- **State:** N/A (CA TOT is local)
- **Legislation:** ⚠️ Council dockets page watched, not keyword scanning

### 12. Miami Beach, FL — see #4

### 13. NYC
- **City:** ✅ 4 page watchers (OSE)
- **County:** ✅ NYC is city-county combined
- **State:** ❌ Missing NY State MDL page
- **Legislation:** ❌ Legistar requires API token (apply at council.nyc.gov/legislation/api/)

### 14. Los Angeles, CA
- **City:** ✅ 3 page watchers
- **County:** ❌ Missing LA County TOT page
- **State:** N/A (CA TOT is local)
- **Legislation:** ❌ LA uses own CFMS system, not Legistar

### 15. Orlando, FL
- **City:** ✅ Home Sharing Registration page
- **County:** ✅ Orange County Comptroller TDT
- **State:** ✅ FL DBPR (Phase A)
- **Legislation:** ❌ No council monitoring

### 16. Las Vegas, NV
- **City:** ✅ City of LV STR page
- **County:** ✅ Clark County STR licensing + FAQ
- **State:** ❌ Missing NV Dept of Taxation page
- **Legislation:** ❌ No council monitoring

### 17. Boston, MA
- **City:** ✅ 3 page watchers (ISD)
- **County:** ✅ Suffolk County co-extensive with Boston
- **State:** ❌ Missing MA DOR room occupancy excise page
- **Legislation:** ✅ Legistar API via legistar_multi.py (Phase C)

### 18. Portland, OR
- **City:** ✅ 3 page watchers (ASTR permits)
- **County:** ✅ Multnomah County TLT + Portland Revenue TLT (Phase B)
- **State:** ❌ Missing OR DOR page
- **Legislation:** ❌ Portland uses own system (not Legistar)

### 19. Destin/30A, FL
- **City:** ✅ Code Compliance + STR FAQ
- **County:** ✅ Okaloosa County Clerk TDT + FAQ (Phase B)
- **State:** ✅ FL DBPR (Phase A)
- **Legislation:** ❌ No council monitoring

### 20. Maui, HI
- **City:** ✅ 3 page watchers (STRH, planning, B&B)
- **County:** ✅ Maui is county-level
- **State:** ✅ HI DOTAX (Phase A)
- **Legislation:** ❌ No council monitoring

### 21. Honolulu, HI
- **City:** ✅ 2 page watchers
- **County:** ✅ Honolulu is city-county combined
- **State:** ✅ HI DOTAX (Phase A)
- **Legislation:** ❌ No council monitoring

### 22. Gatlinburg, TN
- **City:** ✅ 2 page watchers
- **County:** ✅ Sevier County STRU inspection page
- **State:** ✅ TN DOR (Phase A)
- **Legislation:** ❌ No council monitoring

### 23. Asheville, NC
- **City:** ✅ 3 page watchers (via Apify)
- **County:** ❌ Missing Buncombe County tax page
- **State:** ❌ Missing NC DOR page
- **Legislation:** ❌ No council monitoring

### 24. Key West, FL
- **City:** ✅ 3 page watchers
- **County:** ✅ Monroe County Tax Collector TDT (Phase B)
- **State:** ✅ FL DBPR (Phase A)
- **Legislation:** ❌ No council monitoring

### 25. Sedona, AZ
- **City:** ✅ 3 page watchers
- **County:** ❌ Missing Yavapai County tax page
- **State:** ✅ AZ DOR TPT (Phase A)
- **Legislation:** ❌ No council monitoring

### 26. Park City, UT
- **City:** ✅ 2 page watchers
- **County:** ❌ Missing Summit County UT page
- **State:** ❌ Missing UT Tax Commission page
- **Legislation:** ❌ No council monitoring

### 27. Breckenridge, CO
- **City:** ✅ Town STR licensing page
- **County:** ✅ Summit County CO STR regs + license app (2 pages)
- **State:** ✅ Colorado SODA covers state data
- **Legislation:** ❌ No council monitoring

**Status: BEST-COVERED MARKET ✅**

### 28. Big Bear, CA
- **City:** ✅ 3 page watchers
- **County:** ✅ San Bernardino County STR program + getting started + map (Phase B)
- **State:** N/A (CA TOT is local)
- **Legislation:** ❌ No council monitoring

### 29. Outer Banks, NC
- **City:** ✅ Nags Head + Kill Devil Hills pages
- **County:** ✅ Dare County occupancy tax page
- **State:** ❌ Missing NC DOR page
- **Legislation:** ❌ No council monitoring

### 30. Lake Tahoe, CA/NV
- **City (SLT):** ✅ STR page + Measure T FAQ
- **County (Placer):** ✅ Placer County STR page
- **County (El Dorado):** ✅ VHR Division + apps/forms + ordinance (Phase B)
- **County (Washoe, NV):** ❌ Missing Washoe County STR page
- **State:** N/A (CA TOT is local) / ❌ Missing NV Dept of Tax
- **Legislation:** ❌ No council monitoring

---

## Shared State Pages Reference

These are high-efficiency additions — one scraper covers multiple markets:

| State Page | Markets Covered | Status |
|-----------|----------------|--------|
| FL DBPR vacation rental licensing | Miami Beach, Orlando, Key West, Destin/30A | ✅ Phase A |
| HI DOTAX (GET + TAT) | Honolulu, Maui | ✅ Phase A |
| TN DOR transient tax | Nashville, Gatlinburg | ✅ Phase A |
| AZ DOR TPT | Scottsdale, Sedona | ✅ Phase A |
| GA DOR hotel/motel excise | Savannah, Tybee Island | ✅ Phase A |
| TX Comptroller HOT | Austin | ❌ Phase D |
| NV Dept of Taxation | Las Vegas | ❌ Phase D |
| MA DOR room occupancy | Boston | ❌ Phase D |
| OR DOR transient lodging | Portland | ❌ Phase D |
| SC DOR accommodations | Charleston | ❌ Phase D |
| NC DOR occupancy | Outer Banks, Asheville | ❌ Phase D |
| NY State MDL | NYC | ❌ Phase D |
| UT Tax Commission | Park City | ❌ Phase D |
| LA Revenue Dept | New Orleans | ❌ Phase D |
