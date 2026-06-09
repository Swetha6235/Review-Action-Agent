# config.py — Spacez Review Action Agent configuration
import os
from dotenv import load_dotenv

load_dotenv()  # loads .env file from project root

# ---------------------------------------------------------------------------
# Groq LLM settings
# ---------------------------------------------------------------------------
try:
    import streamlit as st
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
except Exception:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

GROQ_MODEL = "llama-3.3-70b-versatile"   # fallback: llama-3.1-8b-instant
GROQ_TIMEOUT = 30  # seconds per API call

APP_TITLE = "Spacez Review Action Agent"
APP_SUBTITLE = "Operational Intelligence from Guest Reviews"

# ---------------------------------------------------------------------------
# Issue keyword taxonomy
# Each key is the canonical issue slug; values are trigger phrases.
# Ordered so more specific phrases are checked first.
# ---------------------------------------------------------------------------
ISSUE_MAP = {
    "pool_maintenance": [
        "pool looked green", "murky water", "pool was dirty", "pool was not clean",
        "pool maintenance", "algae", "green pool", "pool needs", "pool wasn't",
        "pool wasn't clean", "pool wasn't maintained", "pool cleanliness"
    ],
    "cleanliness": [
        "not cleaned", "dirty dishes", "hair in the beds", "bedsheets were not changed",
        "unclean property", "cleanliness", "was dirty", "not clean",
        "hadn't been cleaned", "unwashed", "stains on", "dust", "crumbs",
        "arrival conditions", "unclean on arrival", "dishes left", "previous guests"
    ],
    "heating": [
        "heating didn't work", "heater broken", "very cold", "extra blankets",
        "heating could be better", "no heating", "freezing inside", "heating was poor",
        "cold inside", "no heater", "blankets weren't enough", "cold night",
        "heating issue", "no warmth"
    ],
    "wifi": [
        "wifi did not work", "wifi was patchy", "no wifi", "internet was slow",
        "couldn't connect", "wifi issues", "poor connectivity", "no internet",
        "wifi kept dropping", "streaming was impossible"
    ],
    "checkin_delay": [
        "check-in was a mess", "arrived 90 minutes late", "nobody was there",
        "delayed by over an hour", "late check-in", "no one at property",
        "caretaker wasn't there", "waited for", "took a long time to arrive",
        "not available on arrival", "arrival was delayed", "check-in delay",
        "caretaker was late", "host was late", "reception was late",
        "no one received", "wasn't there to receive"
    ],
    "listing_mismatch": [
        "felt misled", "under-construction building", "listing said 4 bedrooms",
        "oversold", "misleading photos", "not as described", "photos were misleading",
        "didn't match the listing", "different from photos", "looked nothing like",
        "not what we expected", "false advertising", "inaccurate listing",
        "photos were old"
    ],
    "occupancy_policy": [
        "turned away our extra guests", "occupancy policy", "wasn't clear at booking",
        "extra guests not allowed", "guest limit", "maximum occupancy",
        "refused entry", "couldn't bring friends", "head count policy",
        "additional guests"
    ],
    "road_access": [
        "road leading up is in terrible condition", "scraped the bottom",
        "bad road", "terrible road", "road is bad", "access road",
        "road condition", "narrow road", "steep road", "bumpy road",
        "road is rough", "vehicle got stuck"
    ],
    "dampness_mosquitoes": [
        "mosquitoes", "smelled a bit damp", "damp smell", "mold", "mildew",
        "musty smell", "lots of mosquitoes", "insects", "bugs inside",
        "dampness", "humid and damp"
    ],
    "hot_water": [
        "hot water didn't work", "geyser was faulty", "no hot water",
        "cold water only", "hot water issue", "geyser not working",
        "shower was cold", "water wasn't hot"
    ],
    "noise": [
        "very noisy", "noise from", "couldn't sleep", "loud music", "barking dogs",
        "street noise", "noisy neighbors", "construction noise"
    ],
    "positive_host_service": [
        "helpful", "went above and beyond", "arranged", "great host", "fantastic",
        "attentive", "wonderful host", "very responsive", "excellent service",
        "made us feel welcome", "outstanding", "highly recommend", "loved it",
        "perfect stay", "amazing", "superb", "great experience"
    ],
}

# ---------------------------------------------------------------------------
# Owner mapping: who is responsible for fixing this issue
# ---------------------------------------------------------------------------
OWNER_MAP = {
    "pool_maintenance": "Ops/Maintenance",
    "cleanliness": "Housekeeping vendor",
    "heating": "Ops/Maintenance",
    "wifi": "Ops/Maintenance",
    "checkin_delay": "Caretaker/Ops staffing",
    "listing_mismatch": "Listing/Content",
    "occupancy_policy": "Policy/Reservations",
    "road_access": "Listing/Content",
    "dampness_mosquitoes": "Ops/Expectation-setting",
    "hot_water": "Ops/Maintenance",
    "noise": "Ops/Expectation-setting",
    "positive_host_service": "Positive",
}

# ---------------------------------------------------------------------------
# Caretaker controllability:
# True = caretaker is directly responsible
# False = structural / vendor / policy / location issue → do NOT blame caretaker
# ---------------------------------------------------------------------------
CARETAKER_CONTROLLABLE = {
    "pool_maintenance": False,  # Ops/vendor contract issue
    "cleanliness": False,       # Housekeeping vendor failure
    "heating": False,           # Infrastructure / equipment
    "wifi": False,              # ISP / equipment
    "checkin_delay": True,      # Caretaker scheduling / punctuality
    "listing_mismatch": False,  # Content team responsibility
    "occupancy_policy": False,  # Policy set by reservations team
    "road_access": False,       # External / location
    "dampness_mosquitoes": False,  # Structural / seasonal
    "hot_water": False,         # Equipment / maintenance
    "noise": False,             # External / location
    "positive_host_service": True,  # Caretaker excellence
}

# ---------------------------------------------------------------------------
# Recommended actions per issue type
# ---------------------------------------------------------------------------
ACTION_MAP = {
    "pool_maintenance": (
        "Audit pool maintenance SLA and frequency. Introduce pre-guest photo proof "
        "of clean pool. Add pool water quality to caretaker handover checklist."
    ),
    "cleanliness": (
        "Audit housekeeping SLA. Introduce pre-check photo proof before every check-in. "
        "Monitor next 3 consecutive stays for same property. Escalate to vendor head."
    ),
    "heating": (
        "Schedule urgent equipment inspection for heating units. "
        "Provide interim extra-blanket protocol for winter stays. "
        "Flag for capital maintenance budget."
    ),
    "wifi": (
        "Inspect router placement and ISP contract. Test speed before peak season. "
        "Add backup 4G router. Update listing to reflect actual connectivity."
    ),
    "checkin_delay": (
        "Review arrival SLA and overlap staffing. Audit travel time for properties "
        "covered by same caretaker. Introduce 30-min buffer policy for check-in windows."
    ),
    "listing_mismatch": (
        "Re-photograph property with current state. Update listing description. "
        "Add accurate distance-to-amenities info. Conduct quarterly listing accuracy audit."
    ),
    "occupancy_policy": (
        "Add clear occupancy limits to booking confirmation email. "
        "Ensure guest-facing policy is visible on all platforms. "
        "Train caretakers on polite communication of policy."
    ),
    "road_access": (
        "Add road access warning to listing. Recommend vehicle type in booking notes. "
        "Explore partnership with local transport. Update photos to show road condition."
    ),
    "dampness_mosquitoes": (
        "Set expectation in listing copy for seasonal dampness. "
        "Provide mosquito repellent in welcome kit. Inspect property for waterproofing gaps."
    ),
    "hot_water": (
        "Service or replace faulty geyser. Add hot-water test to pre-check checklist. "
        "Keep plumber contact on-call for same-day fixes."
    ),
    "noise": (
        "Add noise disclaimer to listing for affected seasons. "
        "Provide earplugs in welcome kit. Investigate if noise is seasonal or permanent."
    ),
    "positive_host_service": "No action required — reinforce behavior in caretaker recognition program.",
}

# ---------------------------------------------------------------------------
# Priority scoring weights
# ---------------------------------------------------------------------------
PRIORITY_RECURRENCE_THRESHOLD = 2   # ≥ this many reviews = recurring
PRIORITY_LOW_RATING_THRESHOLD = 3.0 # avg normalized rating below this adds score

HIGH_IMPACT_ISSUES = {"cleanliness", "heating", "checkin_delay", "pool_maintenance", "hot_water"}

# Owner buckets that reduce priority (structural / external)
LOW_AGENCY_OWNERS = {"Listing/Content", "Policy/Reservations", "External/Location"}

# ---------------------------------------------------------------------------
# Seeded property names (for display hints)
# ---------------------------------------------------------------------------
KNOWN_PROPERTIES = [
    "Serenity Villa",
    "Vineyard Villa",
    "Cliffside Retreat",
    "Misty Estate",
    "Coorg Canopy",
    "Hilltop Haven",
    "Backwater Bungalow",
]

KNOWN_CARETAKERS = [
    "Lokesh Gowda",
    "Mahesh",
]

# Caretaker cross-property patterns to highlight
CROSS_PROPERTY_CARETAKERS = ["Lokesh Gowda"]
