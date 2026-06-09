# 🏡 Spacez Review Action Agent

> Operational intelligence from guest reviews — convert raw multi-platform review data into prioritized action queues.

---

## Overview

The **Spacez Review Action Agent** is a Python + Streamlit prototype built for the **Operations team**. It ingests an Excel sheet of guest reviews from Airbnb, Booking.com, and Google, normalizes ratings across platforms, classifies issues using a deterministic rule engine, and outputs a prioritized action queue with owner assignments and evidence snippets.

**Stakeholder:** Operations manager, maintenance lead, housekeeping coordinator, listing owner.

---

## Why Operations?

Operations has the clearest action loop in this dataset:

| Recurring Problem | Property | Owner |
|---|---|---|
| Pool cleanliness | Serenity Villa | Ops/Maintenance |
| Arrival cleanliness failures | Vineyard Villa | Housekeeping vendor |
| Heating issue in winter | Cliffside Retreat | Ops/Maintenance |
| Cross-property check-in delays | Misty Estate + Coorg Canopy (Lokesh Gowda) | Caretaker/Ops staffing |
| Misleading photos + occupancy confusion | Hilltop Haven | Listing/Content + Policy |

---

## MVP Features

| # | Feature | Description |
|---|---|---|
| 1 | **Excel ingestion** | Upload `.xlsx` or preload from `data/` folder |
| 2 | **Rating normalization** | `normalized_rating = ratingraw / ratingscale × 5` — never compares raw Booking 10-pt to Airbnb 5-pt |
| 3 | **Issue extraction** | Keyword-based taxonomy: pool, cleanliness, heating, WiFi, check-in delay, listing mismatch, occupancy policy, road/access, dampness/mosquitoes |
| 4 | **Attribution** | Each issue assigned to: Caretaker, Ops/Maintenance, Housekeeping vendor, Listing/Content, Policy/Reservations, External/Location |
| 5 | **Ops dashboard** | 4-section Streamlit UI: summary cards → priority queue → drill-down → attribution check |

---

## Screens

```
┌─────────────────────────────────────────────────────┐
│  1. Summary Cards                                   │
│     Total reviews · Properties with issues ·        │
│     High-priority count · Misattributed reviews     │
├─────────────────────────────────────────────────────┤
│  2. Priority Queue                                  │
│     Filterable by property / owner / priority       │
│     Issue cards with recurrence, rating, action     │
├─────────────────────────────────────────────────────┤
│  3. Drill-Down                                      │
│     Select property + issue → timeline of reviews   │
│     Evidence snippets · Rating trend chart          │
├─────────────────────────────────────────────────────┤
│  4. Attribution Check                               │
│     "Do Not Blame Caretaker" panel                  │
│     Hilltop Haven photos · Coorg road · Policy      │
└─────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
spacez-ops-agent/
├── app.py              # Streamlit UI (4 sections)
├── analysis.py         # Full analysis pipeline (rule-based)
├── prompts.py          # LLM prompt templates (optional)
├── config.py           # Issue taxonomy, owner map, controllability flags
├── requirements.txt    # Python dependencies
├── README.md
└── data/
    └── spacez_reviews_dataset.xlsx   ← place your Excel file here
```

---

## Setup & Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Place your Excel file
#    Copy spacez_reviews_dataset.xlsx into the data/ folder

# 3. Launch the app
streamlit run app.py
```

The app will auto-detect `data/spacez_reviews_dataset.xlsx` on startup.  
You can also upload any `.xlsx` file directly via the UI.

---

## Expected Dataset Columns

| Column | Description |
|---|---|
| `platform` | Airbnb / Booking.com / Google |
| `propertyname` | Villa name |
| `caretakername` | Caretaker assigned to property |
| `ratingraw` | Raw rating from platform |
| `ratingscale` | Max rating on that platform (5 or 10) |
| `reviewtext` | Full review text |
| `reviewdate` | *(optional)* Date of review for timeline charts |

---

## Rule Logic

### Rating Normalization
```
normalized_rating = (ratingraw / ratingscale) × 5
```
Required because the dataset mixes Airbnb 5-pt, Booking.com 10-pt, and Google 5-pt scales.

### Priority Scoring
```python
score = 0
if recurrence_count >= 2:   score += 3   # recurring pattern
if avg_rating < 3.0:        score += 2   # low satisfaction
if issue in HIGH_IMPACT:    score += 2   # cleanliness/heating/pool/check-in
if caretaker_controllable:  score += 1
if resolved_signal:         score -= 1   # later reviews show improvement
if owner in LOW_AGENCY:     score -= 1   # listing/policy/external

# >= 6 → 🔴 High   |   4–5 → 🟡 Medium   |   < 4 → 🟢 Low
```

### Caretaker Controllability
Only `checkin_delay` and `positive_host_service` are flagged as caretaker-controllable.  
Pool maintenance, cleanliness, heating, WiFi, listing accuracy, policy, and road access are **not** caretaker-controllable by design.

---

## Attribution Pushback

> **Sending caretakers reports for every review they hosted is operationally misleading.**

Many guest complaints concern:
- **Listing accuracy** (misleading photos, bedroom count) → Content team
- **Access roads** (terrible road to Coorg Canopy) → Location/listing disclaimer
- **Occupancy policy** (extra guests turned away) → Reservations team
- **Infrastructure** (pool pump, geyser, heating) → Ops/Maintenance

A fair caretaker product surfaces only items within caretaker control: responsiveness, check-in punctuality, and on-ground service quality.

---

## Output Example

```
Issue: Vineyard Villa — Cleanliness on Arrival
Why flagged: 4 reviews mention unclean arrival conditions — dirty dishes,
             unchanged bedsheets, repeated across months.
Owner:       Housekeeping vendor / Ops
Caretaker controllable: No
Priority:    🔴 High
Action:      Audit housekeeping SLA. Introduce pre-check photo proof before
             every check-in. Monitor next 3 stays.
```

```
Issue: Cross-property check-in delays (Lokesh Gowda)
Why flagged: Late arrival / reception issues across both Misty Estate and
             Coorg Canopy — cross-property caretaker pattern.
Owner:       Caretaker/Ops staffing
Priority:    🔴 High
Action:      Review arrival SLA. Add 30-min buffer policy. Audit travel
             schedule for dual-property caretaker coverage.
```

---

## Tech Stack

- **Python 3.9+**
- **Streamlit** — single-page ops dashboard
- **Pandas** — data manipulation and aggregation
- **Plotly** — interactive charts (issue frequency, property ratings, trend lines)
- **openpyxl** — Excel ingestion
- Classification: **deterministic rule-based** (no LLM dependency for MVP)

---

*Built for the Spacez Operations take-home assignment.*
