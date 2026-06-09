# groq_client.py — Groq Llama structured reasoning layer
#
# Architecture rule:
#   Python code handles: normalization, recurrence counts, priority scores, aggregation.
#   Groq Llama handles: nuanced classification explanation, evidence phrasing, action wording.
#   NEVER ask the LLM to calculate ratings or count occurrences.

from __future__ import annotations

import json
import time
from typing import Optional

from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL, GROQ_TIMEOUT

# ---------------------------------------------------------------------------
# Client singleton
# ---------------------------------------------------------------------------

_client: Optional[Groq] = None


def get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


# ---------------------------------------------------------------------------
# Helper: safe JSON parse from LLM response
# ---------------------------------------------------------------------------

def _parse_json(text: str) -> dict:
    """Strip markdown fences and parse JSON from LLM response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find the first { ... } block
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        return {}


# ---------------------------------------------------------------------------
# 1. Review-level structured classification
# ---------------------------------------------------------------------------

REVIEW_CLASSIFY_SYSTEM = """You are an operations analyst for Spacez, a villa hospitality company.
Your job is to classify guest reviews and assign operational accountability.

CRITICAL RULES — follow strictly:
1. Do NOT blame the caretaker for: listing mismatch, occupancy policy, road/access, infrastructure failures (pool pump, heating, WiFi, geyser), or external location issues.
2. Caretaker is only accountable for: check-in punctuality, responsiveness, and on-ground service quality.
3. Return ONLY valid JSON — no markdown, no explanation outside the JSON.
4. Keep evidence_snippet under 30 words, taken directly from the review text.
5. Keep action_recommendation under 25 words, specific and operational.
"""

REVIEW_CLASSIFY_USER = """Guest review to classify:

Property: {property_name}
Platform: {platform}
Caretaker: {caretaker_name}
Normalized rating (out of 5): {normalized_rating}
Rule-based tags already detected: {issue_tags}

Review text:
\"\"\"{review_text}\"\"\"

Return JSON with exactly these keys:
{{
  "primary_issue": "<slug from tags or 'general_feedback'>",
  "secondary_issues": ["<slug>", ...],
  "owner_bucket": "<Ops/Maintenance | Housekeeping vendor | Caretaker/Ops staffing | Listing/Content | Policy/Reservations | External/Location | Positive>",
  "caretaker_controllable": <true | false>,
  "severity": "<low | medium | high>",
  "evidence_snippet": "<direct quote or paraphrase, max 30 words>",
  "action_recommendation": "<specific operational next step, max 25 words>"
}}"""


def classify_review(
    review_text: str,
    property_name: str,
    platform: str,
    caretaker_name: str,
    normalized_rating: float,
    issue_tags: list[str],
    retries: int = 2,
) -> dict:
    """Call Groq Llama to produce structured classification for one review.

    Returns a dict with classification keys, or empty dict on failure.
    The caller must fall back to rule-based values if this returns {}.
    """
    prompt = REVIEW_CLASSIFY_USER.format(
        property_name=property_name,
        platform=platform,
        caretaker_name=caretaker_name,
        normalized_rating=round(normalized_rating, 2),
        issue_tags=", ".join(issue_tags),
        review_text=str(review_text)[:1200],  # cap to avoid token waste
    )

    for attempt in range(retries + 1):
        try:
            client = get_client()
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": REVIEW_CLASSIFY_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # low temperature = consistent outputs
                max_tokens=400,
                timeout=GROQ_TIMEOUT,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            return _parse_json(raw)
        except Exception as exc:
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
            else:
                print(f"[groq_client] classify_review failed after {retries+1} attempts: {exc}")
                return {}
    return {}


# ---------------------------------------------------------------------------
# 2. Aggregate issue cluster summary
# ---------------------------------------------------------------------------

CLUSTER_SUMMARY_SYSTEM = """You are summarizing recurring guest review issues for the operations team of Spacez (villa hospitality).
Be concise, factual, and operational. Return ONLY valid JSON."""

CLUSTER_SUMMARY_USER = """Recurring issue cluster to summarize:

Property: {property_name}
Issue type: {issue_type}
Owner: {owner_bucket}
Recurrence count: {recurrence_count}
Average normalized rating (out of 5): {avg_rating}
Caretaker involved: {caretaker_name}

Review evidence snippets:
{snippets}

Return JSON with exactly these keys:
{{
  "problem_summary": "<1 sentence, max 20 words>",
  "why_it_matters": "<1-2 sentences, guest experience and business impact>",
  "who_should_act": "<team or role name>",
  "recommended_next_step": "<specific and actionable, max 30 words>",
  "confidence_note": "<note on recurrence count and evidence strength, max 20 words>"
}}"""


def summarize_issue_cluster(
    property_name: str,
    issue_type: str,
    owner_bucket: str,
    recurrence_count: int,
    avg_rating: float,
    caretaker_name: str,
    snippets: list[str],
    retries: int = 2,
) -> dict:
    """Call Groq Llama for a structured summary of a recurring issue cluster."""
    snippet_text = "\n".join(
        f"- \"{s}\"" for s in snippets[:5]  # cap at 5 snippets
    )

    prompt = CLUSTER_SUMMARY_USER.format(
        property_name=property_name,
        issue_type=issue_type.replace("_", " "),
        owner_bucket=owner_bucket,
        recurrence_count=recurrence_count,
        avg_rating=round(avg_rating, 2),
        caretaker_name=caretaker_name or "N/A",
        snippets=snippet_text,
    )

    for attempt in range(retries + 1):
        try:
            client = get_client()
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": CLUSTER_SUMMARY_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.15,
                max_tokens=350,
                timeout=GROQ_TIMEOUT,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            return _parse_json(raw)
        except Exception as exc:
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
            else:
                print(f"[groq_client] summarize_issue_cluster failed: {exc}")
                return {}
    return {}


# ---------------------------------------------------------------------------
# 3. Cross-property caretaker pattern explanation
# ---------------------------------------------------------------------------

CROSS_PROPERTY_SYSTEM = """You are an operations analyst. Explain a cross-property caretaker pattern clearly and fairly.
Return ONLY valid JSON."""

CROSS_PROPERTY_USER = """A caretaker has the same recurring issue across multiple properties:

Caretaker: {caretaker_name}
Issue: {issue_type}
Properties affected: {properties}
Total occurrences: {count}
Average rating: {avg_rating}

Evidence:
{snippets}

Return JSON:
{{
  "pattern_explanation": "<1-2 sentences explaining the cross-property pattern>",
  "recommended_action": "<specific staffing or operational fix, max 30 words>",
  "is_caretaker_fault": <true | false>,
  "escalation_note": "<who should receive this report>"
}}"""


def explain_cross_property_pattern(
    caretaker_name: str,
    issue_type: str,
    properties: list[str],
    count: int,
    avg_rating: float,
    snippets: list[str],
    retries: int = 1,
) -> dict:
    snippet_text = "\n".join(f"- \"{s}\"" for s in snippets[:4])
    prompt = CROSS_PROPERTY_USER.format(
        caretaker_name=caretaker_name,
        issue_type=issue_type.replace("_", " "),
        properties=", ".join(properties),
        count=count,
        avg_rating=round(avg_rating, 2),
        snippets=snippet_text,
    )

    for attempt in range(retries + 1):
        try:
            client = get_client()
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": CROSS_PROPERTY_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=300,
                timeout=GROQ_TIMEOUT,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            return _parse_json(raw)
        except Exception as exc:
            if attempt < retries:
                time.sleep(1.5)
            else:
                print(f"[groq_client] explain_cross_property failed: {exc}")
                return {}
    return {}


# ---------------------------------------------------------------------------
# 4. Batch classify reviews (with rate-limit friendly pacing)
# ---------------------------------------------------------------------------

def batch_classify_reviews(
    rows: list[dict],
    delay_between: float = 0.3,
    progress_callback=None,
) -> list[dict]:
    """Run classify_review on a list of review dicts.

    Each dict must have: review_text, propertyname, platform, caretakername,
    normalized_rating, issue_tags.

    Returns a list of result dicts (same length as rows; empty dict on failure).
    """
    results = []
    for i, row in enumerate(rows):
        result = classify_review(
            review_text=row.get("reviewtext", ""),
            property_name=row.get("propertyname", ""),
            platform=row.get("platform", ""),
            caretaker_name=row.get("caretakername", ""),
            normalized_rating=float(row.get("normalized_rating", 3.0)),
            issue_tags=row.get("issue_tags", []),
        )
        results.append(result)
        if progress_callback:
            progress_callback(i + 1, len(rows))
        if i < len(rows) - 1:
            time.sleep(delay_between)
    return results
