# prompts.py — LLM prompt templates (optional enhancement layer)
# Core classification is done deterministically in analysis.py.
# These prompts are used ONLY for human-readable narrative generation.

REVIEW_CLASSIFICATION_PROMPT = """You are an operations analyst for a villa hospitality company called Spacez.
Given a guest review and preliminary rule-based issue tags, return a JSON object with exactly these keys:
- primary_issue: string (one of the detected tags, or "general_feedback")
- secondary_issues: list of strings
- likely_owner_bucket: string
- caretaker_controllable: boolean
- severity: string ("low" | "medium" | "high")
- concise_evidence_snippet: string (max 25 words, direct quote or paraphrase from review)
- action_recommendation: string (max 30 words, operational next step)

RULES — FOLLOW STRICTLY:
1. Do NOT blame caretaker for listing mismatch, occupancy policy, road/access, or external location issues.
2. Do NOT mark severity=high for positive feedback.
3. Normalize platform differences mentally; do not recompute ratings.
4. Focus on operational actionability — what can ops do about this?
5. Return ONLY valid JSON, no markdown fences.

Review: {review_text}
Platform: {platform}
Property: {property_name}
Caretaker: {caretaker_name}
Preliminary tags: {issue_tags}
Normalized rating (out of 5): {normalized_rating}
"""

AGGREGATE_SUMMARY_PROMPT = """You are summarizing recurring guest review issues for the operations team of Spacez (villa hospitality).
Given multiple review snippets for the same issue cluster, produce a JSON with:
- problem_summary: string (1 sentence, ≤ 20 words)
- why_it_matters: string (1–2 sentences, business impact)
- who_should_act: string
- recommended_next_step: string (≤ 30 words, specific and actionable)
- confidence_note: string (note recurrence count and date spread)

Review snippets:
{snippets}

Issue type: {issue_type}
Property: {property_name}
Recurrence count: {recurrence_count}
Average normalized rating: {avg_rating}

Return ONLY valid JSON, no markdown fences.
"""

CARETAKER_REPORT_PUSHBACK_PROMPT = """You are advising the Spacez operations team on caretaker accountability.
A review mentions: "{review_text}"
The issue has been classified as: {issue_type}
Owner: {owner_bucket}
Caretaker controllable: {caretaker_controllable}

In 2 sentences, explain why this issue should or should not be escalated to the caretaker.
Be specific about who actually owns the fix.
"""
