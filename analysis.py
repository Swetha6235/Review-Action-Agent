# analysis.py — Spacez Review Action Agent core analysis engine
# All classification is deterministic rule-based first; LLM is optional.

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pandas as pd

from config import (
    ACTION_MAP,
    CARETAKER_CONTROLLABLE,
    CROSS_PROPERTY_CARETAKERS,
    HIGH_IMPACT_ISSUES,
    ISSUE_MAP,
    LOW_AGENCY_OWNERS,
    OWNER_MAP,
    PRIORITY_LOW_RATING_THRESHOLD,
    PRIORITY_RECURRENCE_THRESHOLD,
)


# ---------------------------------------------------------------------------
# 1. Load reviews
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = {"platform", "propertyname", "caretakername", "ratingraw", "ratingscale", "reviewtext"}

COLUMN_ALIASES = {
    # Flexible column name normalisation
    "property": "propertyname",
    "property_name": "propertyname",
    "caretaker": "caretakername",
    "caretaker_name": "caretakername",
    "rating_raw": "ratingraw",
    "rating": "ratingraw",
    "raw_rating": "ratingraw",
    "rating_scale": "ratingscale",
    "scale": "ratingscale",
    "review": "reviewtext",
    "review_text": "reviewtext",
    "text": "reviewtext",
    "comment": "reviewtext",
    "date": "reviewdate",
    "review_date": "reviewdate",
}


def load_reviews(file) -> pd.DataFrame:
    """Load reviews from an xlsx file or file-like object.

    Normalises column names and validates required columns.
    """
    df = pd.read_excel(file, sheet_name=0)

    # Normalise column names: lower-case, strip whitespace, apply aliases
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df.rename(columns=COLUMN_ALIASES, inplace=True)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Dataset is missing required columns: {missing}. "
            f"Found: {list(df.columns)}"
        )

    # Optional date column
    if "reviewdate" in df.columns:
        df["reviewdate"] = pd.to_datetime(df["reviewdate"], errors="coerce")

    # Drop fully empty rows
    df.dropna(subset=["reviewtext", "ratingraw"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df


# ---------------------------------------------------------------------------
# 2. Normalize rating
# ---------------------------------------------------------------------------

def normalize_rating(df: pd.DataFrame) -> pd.DataFrame:
    """Add normalized_rating column (all ratings converted to 0–5 scale)."""
    df = df.copy()
    df["ratingraw"] = pd.to_numeric(df["ratingraw"], errors="coerce")
    df["ratingscale"] = pd.to_numeric(df["ratingscale"], errors="coerce").fillna(5)
    df["normalized_rating"] = (df["ratingraw"] / df["ratingscale"] * 5).round(2)
    df["normalized_rating"] = df["normalized_rating"].clip(0, 5)
    return df


# ---------------------------------------------------------------------------
# 3. Issue extraction
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    return str(text).lower().strip()


def extract_issue_tags(text: str) -> list[str]:
    """Return all matching issue slugs for a review text."""
    clean = _clean_text(text)
    matched = []
    for issue_slug, phrases in ISSUE_MAP.items():
        for phrase in phrases:
            if phrase.lower() in clean:
                matched.append(issue_slug)
                break  # one phrase per issue is enough
    return matched if matched else ["no_issue_detected"]


def assign_primary_issue(tags: list[str]) -> str:
    """Choose the single most actionable issue from a list of tags.

    Priority order: high-impact operational issues first, then others,
    positive last.
    """
    if not tags or tags == ["no_issue_detected"]:
        return "no_issue_detected"

    # Prefer high-impact operational issues
    for issue in tags:
        if issue in HIGH_IMPACT_ISSUES:
            return issue

    # Then any non-positive issue
    for issue in tags:
        if issue != "positive_host_service":
            return issue

    return tags[0]


# ---------------------------------------------------------------------------
# 4. Owner and controllability
# ---------------------------------------------------------------------------

def assign_owner(issue: str) -> str:
    return OWNER_MAP.get(issue, "Ops/General")


def is_caretaker_controllable(issue: str) -> bool:
    return CARETAKER_CONTROLLABLE.get(issue, False)


# ---------------------------------------------------------------------------
# 5. Sentiment label (simple rule-based)
# ---------------------------------------------------------------------------

def sentiment_label(normalized_rating: float, tags: list[str]) -> str:
    if "positive_host_service" in tags and normalized_rating >= 4.0:
        return "Positive"
    if normalized_rating >= 4.0:
        return "Positive"
    if normalized_rating >= 3.0:
        return "Mixed"
    return "Negative"


# ---------------------------------------------------------------------------
# 6. Evidence snippet
# ---------------------------------------------------------------------------

def extract_evidence_snippet(text: str, issue: str, max_chars: int = 200) -> str:
    """Extract the most relevant sentence from a review for a given issue."""
    if issue == "no_issue_detected":
        return str(text)[:max_chars]

    sentences = re.split(r"[.!?]", str(text))
    phrases = ISSUE_MAP.get(issue, [])
    best = ""
    for sentence in sentences:
        sl = sentence.lower()
        for phrase in phrases:
            if phrase.lower() in sl:
                best = sentence.strip()
                break
        if best:
            break

    if not best:
        best = sentences[0].strip() if sentences else str(text)[:max_chars]

    return (best[:max_chars] + "…") if len(best) > max_chars else best


# ---------------------------------------------------------------------------
# 7. Compute all review-level derived fields
# ---------------------------------------------------------------------------

def compute_review_level_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Enrich each review row with all derived columns."""
    df = normalize_rating(df)

    rows = []
    for _, row in df.iterrows():
        text = str(row["reviewtext"])
        tags = extract_issue_tags(text)
        primary = assign_primary_issue(tags)
        owner = assign_owner(primary)
        controllable = is_caretaker_controllable(primary)
        rating = float(row["normalized_rating"]) if pd.notna(row["normalized_rating"]) else 3.0
        label = sentiment_label(rating, tags)
        snippet = extract_evidence_snippet(text, primary)

        rows.append(
            {
                **row.to_dict(),
                "issue_tags": tags,
                "primary_issue": primary,
                "owner_bucket": owner,
                "caretaker_controllable": controllable,
                "sentiment_label": label,
                "evidence_snippet": snippet,
            }
        )

    enriched = pd.DataFrame(rows)
    return enriched


# ---------------------------------------------------------------------------
# 8. Aggregate issue clusters
# ---------------------------------------------------------------------------

def aggregate_issue_clusters(df: pd.DataFrame) -> pd.DataFrame:
    """Group reviews by (property, primary_issue) and compute cluster stats."""
    actionable = df[df["primary_issue"] != "no_issue_detected"].copy()

    grouped = (
        actionable.groupby(["propertyname", "primary_issue"])
        .agg(
            recurrence_count=("primary_issue", "count"),
            avg_normalized_rating=("normalized_rating", "mean"),
            caretaker_controllable=("caretaker_controllable", "first"),
            owner_bucket=("owner_bucket", "first"),
            caretakername=("caretakername", "first"),
            snippets=("evidence_snippet", list),
            review_dates=("reviewdate", list) if "reviewdate" in df.columns else ("propertyname", "count"),
        )
        .reset_index()
    )

    grouped["avg_normalized_rating"] = grouped["avg_normalized_rating"].round(2)
    grouped["recurring_flag"] = grouped["recurrence_count"] >= PRIORITY_RECURRENCE_THRESHOLD

    # Detect resolved signal: if latest normalized rating improves above 3.5 but
    # earlier reviews were negative, flag as "possibly improving"
    def resolved_signal(prop: str, issue: str) -> bool:
        subset = df[(df["propertyname"] == prop) & (df["primary_issue"] == issue)]
        if "reviewdate" in subset.columns and subset["reviewdate"].notna().any():
            subset = subset.sort_values("reviewdate")
            if len(subset) >= 2:
                last_rating = subset.iloc[-1]["normalized_rating"]
                first_rating = subset.iloc[0]["normalized_rating"]
                return bool(last_rating >= 3.5 and first_rating < 3.5)
        return False

    grouped["resolved_signal"] = grouped.apply(
        lambda r: resolved_signal(r["propertyname"], r["primary_issue"]), axis=1
    )

    # Recommended action
    grouped["recommended_action"] = grouped["primary_issue"].apply(
        lambda i: ACTION_MAP.get(i, "Investigate and escalate to relevant team.")
    )

    # Best evidence snippet (first non-empty)
    grouped["best_snippet"] = grouped["snippets"].apply(
        lambda s: next((x for x in s if x), "No snippet available")
    )

    return grouped


# ---------------------------------------------------------------------------
# 9. Priority scoring
# ---------------------------------------------------------------------------

def score_priority(agg_df: pd.DataFrame) -> pd.DataFrame:
    """Compute priority score and label for each issue cluster."""
    agg_df = agg_df.copy()
    scores = []

    for _, row in agg_df.iterrows():
        score = 0

        if row["recurrence_count"] >= PRIORITY_RECURRENCE_THRESHOLD:
            score += 3
        if row["avg_normalized_rating"] < PRIORITY_LOW_RATING_THRESHOLD:
            score += 2
        if row["primary_issue"] in HIGH_IMPACT_ISSUES:
            score += 2
        if row.get("caretaker_controllable", False):
            score += 1
        if row.get("resolved_signal", False):
            score -= 1
        if row.get("owner_bucket", "") in LOW_AGENCY_OWNERS:
            score -= 1

        scores.append(score)

    agg_df["priority_score"] = scores
    agg_df["priority"] = agg_df["priority_score"].apply(
        lambda s: "🔴 High" if s >= 6 else ("🟡 Medium" if s >= 4 else "🟢 Low")
    )
    agg_df = agg_df.sort_values("priority_score", ascending=False).reset_index(drop=True)
    return agg_df


# ---------------------------------------------------------------------------
# 10. Cross-property caretaker patterns
# ---------------------------------------------------------------------------

def detect_cross_property_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """Find caretakers with the same recurring issue across multiple properties."""
    actionable = df[df["primary_issue"] != "no_issue_detected"]

    patterns = (
        actionable.groupby(["caretakername", "primary_issue"])
        .agg(
            properties=("propertyname", lambda x: sorted(set(x))),
            count=("primary_issue", "count"),
            avg_rating=("normalized_rating", "mean"),
            snippets=("evidence_snippet", list),
        )
        .reset_index()
    )

    # Only keep patterns that span ≥ 2 properties
    patterns = patterns[patterns["properties"].apply(len) >= 2].copy()
    patterns["avg_rating"] = patterns["avg_rating"].round(2)
    patterns["property_list"] = patterns["properties"].apply(lambda x: ", ".join(x))
    return patterns


# ---------------------------------------------------------------------------
# 11. "Do not blame caretaker" panel data
# ---------------------------------------------------------------------------

MISATTRIBUTION_EXAMPLES = [
    {
        "property": "Hilltop Haven",
        "issue_type": "listing_mismatch",
        "display_issue": "Misleading listing photos",
        "caretaker": "Mahesh",
        "why_not_caretaker": (
            "The listing photos do not reflect the current state of the property. "
            "This is a Content team failure — photos are set centrally, not by the caretaker. "
            "Mahesh cannot update listing photos."
        ),
        "real_owner": "Listing/Content team",
    },
    {
        "property": "Coorg Canopy",
        "issue_type": "road_access",
        "display_issue": "Poor road condition to property",
        "caretaker": "Lokesh Gowda",
        "why_not_caretaker": (
            "The road leading up to the property is municipal/private infrastructure. "
            "No caretaker can repair a public access road. "
            "The fix is a listing disclaimer and vehicle guidance note."
        ),
        "real_owner": "Listing/Content + Ops expectation-setting",
    },
    {
        "property": "Hilltop Haven",
        "issue_type": "occupancy_policy",
        "display_issue": "Occupancy policy confusion",
        "caretaker": "Mahesh",
        "why_not_caretaker": (
            "Guest was surprised by occupancy limits not clearly shown at booking. "
            "Policy is set by the Reservations team. Caretaker correctly enforced policy — "
            "the failure is in pre-arrival communication."
        ),
        "real_owner": "Policy/Reservations team",
    },
    {
        "property": "Backwater Bungalow",
        "issue_type": "listing_mismatch",
        "display_issue": "Restaurant/amenity distance mismatch",
        "caretaker": None,
        "why_not_caretaker": (
            "Guest complained the nearest restaurant was much farther than implied in listing. "
            "This is a listing accuracy issue — the Content team must add accurate distances. "
            "No caretaker action can fix geography."
        ),
        "real_owner": "Listing/Content team",
    },
]


def get_misattribution_examples(df: pd.DataFrame) -> list[dict]:
    """Augment static examples with any data-driven matches from the uploaded dataset."""
    examples = list(MISATTRIBUTION_EXAMPLES)

    # Add data-driven examples: non-caretaker-controllable issues with low ratings
    extra = df[
        (df["caretaker_controllable"] == False)
        & (df["primary_issue"] != "no_issue_detected")
        & (df["primary_issue"] != "positive_host_service")
        & (df["normalized_rating"] < 3.0)
    ].copy()

    seen = {(e["property"], e["issue_type"]) for e in examples}
    for _, row in extra.iterrows():
        key = (str(row["propertyname"]), str(row["primary_issue"]))
        if key not in seen:
            seen.add(key)
            examples.append(
                {
                    "property": str(row["propertyname"]),
                    "issue_type": str(row["primary_issue"]),
                    "display_issue": str(row["primary_issue"]).replace("_", " ").title(),
                    "caretaker": str(row.get("caretakername", "N/A")),
                    "why_not_caretaker": (
                        "This '"
                        + str(row["primary_issue"]).replace("_", " ")
                        + "' issue is owned by "
                        + str(row["owner_bucket"])
                        + ", not the caretaker. Evidence: \""
                        + str(row["evidence_snippet"])
                        + "\""
                    ),
                    "real_owner": str(row["owner_bucket"]),
                }
            )

    return examples


# ---------------------------------------------------------------------------
# 12. LLM enrichment (Groq layer — optional, runs AFTER rule-based pipeline)
# ---------------------------------------------------------------------------

def llm_enrich_clusters(
    priority_queue: pd.DataFrame,
    df: pd.DataFrame,
    progress_callback=None,
) -> pd.DataFrame:
    """Enrich each issue cluster in priority_queue with a Groq-generated summary.

    Adds columns: llm_problem_summary, llm_why_it_matters,
                  llm_recommended_next_step, llm_confidence_note.

    NOTE: recurrence_count, avg_normalized_rating, priority_score are NEVER
    passed to the LLM for computation — they are computed in Python above.
    The LLM only produces human-readable narratives.
    """
    from groq_client import summarize_issue_cluster, explain_cross_property_pattern

    enriched = priority_queue.copy()
    llm_cols = {
        "llm_problem_summary": "",
        "llm_why_it_matters": "",
        "llm_recommended_next_step": "",
        "llm_confidence_note": "",
    }
    for col, default in llm_cols.items():
        enriched[col] = default

    total = len(enriched)
    for idx, row in enriched.iterrows():
        result = summarize_issue_cluster(
            property_name=str(row["propertyname"]),
            issue_type=str(row["primary_issue"]),
            owner_bucket=str(row["owner_bucket"]),
            recurrence_count=int(row["recurrence_count"]),
            avg_rating=float(row["avg_normalized_rating"]),
            caretaker_name=str(row.get("caretakername", "N/A")),
            snippets=list(row.get("snippets", [])),
        )
        if result:
            enriched.at[idx, "llm_problem_summary"] = result.get("problem_summary", "")
            enriched.at[idx, "llm_why_it_matters"] = result.get("why_it_matters", "")
            enriched.at[idx, "llm_recommended_next_step"] = result.get("recommended_next_step", "")
            enriched.at[idx, "llm_confidence_note"] = result.get("confidence_note", "")

        if progress_callback:
            progress_callback(list(enriched.index).index(idx) + 1, total)

    return enriched


def llm_enrich_cross_property(
    cross_property: pd.DataFrame,
) -> pd.DataFrame:
    """Add Groq-generated explanations to cross-property patterns."""
    from groq_client import explain_cross_property_pattern

    enriched = cross_property.copy()
    enriched["llm_pattern_explanation"] = ""
    enriched["llm_recommended_action"] = ""
    enriched["llm_escalation_note"] = ""

    for idx, row in enriched.iterrows():
        result = explain_cross_property_pattern(
            caretaker_name=str(row["caretakername"]),
            issue_type=str(row["primary_issue"]),
            properties=list(row["properties"]),
            count=int(row["count"]),
            avg_rating=float(row["avg_rating"]),
            snippets=list(row.get("snippets", [])),
        )
        if result:
            enriched.at[idx, "llm_pattern_explanation"] = result.get("pattern_explanation", "")
            enriched.at[idx, "llm_recommended_action"] = result.get("recommended_action", "")
            enriched.at[idx, "llm_escalation_note"] = result.get("escalation_note", "")

    return enriched


# ---------------------------------------------------------------------------
# 13. Full pipeline
# ---------------------------------------------------------------------------

def run_full_pipeline(file, use_llm: bool = False, progress_callback=None) -> dict:
    """Run the complete analysis pipeline and return all result frames.

    Args:
        file: Path string or file-like object for the Excel dataset.
        use_llm: If True, run optional Groq Llama enrichment pass after
                 rule-based classification. Adds narrative summaries to clusters.
        progress_callback: Optional callable(done, total) for progress reporting.
    """
    df_raw = load_reviews(file)
    df = compute_review_level_fields(df_raw)
    agg = aggregate_issue_clusters(df)
    priority_queue = score_priority(agg)
    cross_property = detect_cross_property_patterns(df)
    misattributions = get_misattribution_examples(df)

    # Optional LLM enrichment — always AFTER Python analytics
    llm_available = False
    if use_llm:
        try:
            priority_queue = llm_enrich_clusters(priority_queue, df, progress_callback)
            if not cross_property.empty:
                cross_property = llm_enrich_cross_property(cross_property)
            llm_available = True
        except Exception as exc:
            print(f"[analysis] LLM enrichment failed, using rule-based only: {exc}")

    # Summary stats — always computed in Python, never by LLM
    total_reviews = len(df)
    properties_with_issues = priority_queue[priority_queue["recurring_flag"]]["propertyname"].nunique()
    high_priority_count = (priority_queue["priority"] == "🔴 High").sum()
    misattributed_count = df[
        (df["caretaker_controllable"] == False)
        & (df["primary_issue"] != "no_issue_detected")
        & (df["primary_issue"] != "positive_host_service")
    ].shape[0]

    return {
        "df": df,
        "priority_queue": priority_queue,
        "cross_property": cross_property,
        "misattributions": misattributions,
        "llm_available": llm_available,
        "summary": {
            "total_reviews": total_reviews,
            "properties_with_issues": int(properties_with_issues),
            "high_priority_count": int(high_priority_count),
            "misattributed_count": int(misattributed_count),
        },
    }
