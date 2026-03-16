# STRWatch — Jurisdiction Coverage Audit & Expansion Plan

**Last updated:** March 16, 2026
**Status:** Phase A complete, Phase B in progress

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

| Metric | Current | After Phase A | After Full Expansion |
|--------|---------|---------------|---------------------|
| Total page watchers | ~85 URLs | ~97 URLs | ~115 URLs |
| Markets with county coverage | 10/30 | 10/30 | 28/30 |
| Markets with state coverage | 2/30 | 12/30 | 25/30 |
| Markets with legislation monitoring | 2/30 | 2/30 | 6/30 |
| Shared state scrapers | 0 | 1 (5 states) | 1 (5 states) |

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

## Phase B — Critical County Pages (TODO)

**Priority:** Fill the biggest single-market gaps

| # | Page | Market | Priority |
|---|------|--------|----------|
| 1 | Davidson County Clerk — business tax/permits | Nashville | 🔴 HIGH |
| 2 | Travis County tax office — Hotel Occupancy Tax | Austin | 🔴 HIGH |
| 3 | El Dorado County — VHR program | Lake Tahoe | 🔴 HIGH |
| 4 | Multnomah County — transient lodging tax | Portland | 🔴 HIGH |
| 5 | Monroe County — tax collector / BTR | Key West | 🟡 MEDIUM |
| 6 | San Bernardino County — STR program (str.sbcounty.gov) | Big Bear | 🟡 MEDIUM |
| 7 | Okaloosa County — tax collector | Destin | 🟡 MEDIUM |
| 8 | Chatham County — hotel/motel tax | Savannah + Tybee | 🟡 MEDIUM |

---

## Phase C — Legistar Expansion (TODO)

**Impact:** Adds legislation keyword monitoring to major cities

We already have Nashville and New Orleans on Legistar. These cities also use it:

| City | Legistar Base URL | Priority |
|------|------------------|----------|
| Denver | webapi.legistar.com/v1/denver | 🔴 HIGH |
| NYC | webapi.legistar.com/v1/newyorkcity | 🔴 HIGH |
| Los Angeles | webapi.legistar.com/v1/lacity | 🔴 HIGH |
| San Francisco | webapi.legistar.com/v1/sfgov | 🟡 MEDIUM |
| San Diego | webapi.legistar.com/v1/sandiego | 🟡 MEDIUM |
| Boston | webapi.legistar.com/v1/boston | 🟡 MEDIUM |

Each follows the same pattern as `nashville_legistar.py` — change the base URL and keyword list.

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
- **County:** ❌ Missing Davidson County Clerk tax page
- **State:** ✅ TN DOR (Phase A)
- **Legislation:** ✅ Legistar API

### 2. Austin, TX
- **City:** ✅ Page watchers + council agenda PDF parser
- **County:** ❌ Missing Travis County HOT page
- **State:** ❌ Missing TX Comptroller HOT page
- **Legislation:** ✅ Council agenda keyword scanning

### 3. Denver, CO
- **City:** ✅ SODA API + page watchers
- **County:** ⚠️ Denver is city-county combined, missing lodging tax page
- **State:** ✅ Colorado SODA covers state dataset
- **Legislation:** ❌ No council monitoring (Legistar available — Phase C)

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
- **County:** ❌ Missing Chatham County tax page
- **State:** ✅ GA DOR (Phase A)
- **Legislation:** ❌ No council monitoring

### 10. San Francisco, CA
- **City:** ✅ 4 page watchers
- **County:** ✅ SF is city-county combined
- **State:** N/A (CA TOT is local)
- **Legislation:** ❌ No Board of Supervisors monitoring (Legistar — Phase C)

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
- **Legislation:** ❌ No City Council monitoring (Legistar — Phase C)

### 14. Los Angeles, CA
- **City:** ✅ 3 page watchers
- **County:** ❌ Missing LA County TOT page
- **State:** N/A (CA TOT is local)
- **Legislation:** ❌ No council monitoring (Legistar — Phase C)

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
- **Legislation:** ❌ No council monitoring (Legistar — Phase C)

### 18. Portland, OR
- **City:** ✅ 3 page watchers (ASTR permits)
- **County:** ❌ Missing Multnomah County transient lodging tax page
- **State:** ❌ Missing OR DOR page
- **Legislation:** ❌ Portland uses own system (not Legistar)

### 19. Destin/30A, FL
- **City:** ✅ Code Compliance + STR FAQ
- **County:** ⚠️ Walton County TDC only — missing Okaloosa County (Destin proper)
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
- **County:** ❌ Missing Monroe County tax collector page
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
- **County:** ❌ Missing San Bernardino County STR page (str.sbcounty.gov)
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
- **County (El Dorado):** ❌ Missing El Dorado County VHR page
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
