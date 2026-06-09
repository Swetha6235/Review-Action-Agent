# app.py — Spacez Review Action Agent  •  Streamlit UI
# Run:  streamlit run app.py

from __future__ import annotations

import html as html_lib
import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go

from analysis import run_full_pipeline
from config import APP_SUBTITLE, APP_TITLE, CROSS_PROPERTY_CARETAKERS, GROQ_MODEL

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Custom CSS — premium dark UI
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ─── Base ─────────────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0d1117;
    color: #e6edf3;
}

.main .block-container {
    padding: 2rem 2.5rem 4rem;
    max-width: 1400px;
}

/* ─── Header ────────────────────────────────────────────────────────────── */
.sz-header {
    background: linear-gradient(135deg, #1a2332 0%, #0d1117 60%, #111827 100%);
    border: 1px solid #21262d;
    border-radius: 16px;
    padding: 2rem 2.5rem 1.8rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.sz-header::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(88,166,255,0.12) 0%, transparent 70%);
    border-radius: 50%;
}
.sz-header h1 {
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #58a6ff, #79c0ff, #a5d8ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 0.3rem;
}
.sz-header p {
    color: #8b949e;
    font-size: 0.95rem;
    margin: 0;
    font-weight: 400;
}
.sz-badge {
    display: inline-block;
    background: rgba(88,166,255,0.15);
    border: 1px solid rgba(88,166,255,0.3);
    color: #58a6ff;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    margin-bottom: 0.8rem;
    text-transform: uppercase;
}

/* ─── Section titles ─────────────────────────────────────────────────────── */
.sz-section {
    font-size: 1.05rem;
    font-weight: 700;
    color: #e6edf3;
    margin: 2rem 0 1rem;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.sz-section::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, #21262d, transparent);
    margin-left: 0.5rem;
}

/* ─── Summary cards ──────────────────────────────────────────────────────── */
.sz-card {
    background: linear-gradient(145deg, #161b22, #0d1117);
    border: 1px solid #21262d;
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    text-align: center;
    transition: border-color 0.2s, transform 0.2s;
    position: relative;
    overflow: hidden;
}
.sz-card:hover {
    border-color: #58a6ff44;
    transform: translateY(-2px);
}
.sz-card .card-icon {
    font-size: 1.8rem;
    margin-bottom: 0.4rem;
    display: block;
}
.sz-card .card-value {
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #58a6ff, #79c0ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.1;
}
.sz-card .card-value.red {
    background: linear-gradient(135deg, #ff7b72, #ffa198);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.sz-card .card-value.yellow {
    background: linear-gradient(135deg, #f0883e, #ffa657);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.sz-card .card-value.purple {
    background: linear-gradient(135deg, #bc8cff, #d2a8ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.sz-card .card-label {
    font-size: 0.8rem;
    color: #8b949e;
    font-weight: 500;
    margin-top: 0.3rem;
    letter-spacing: 0.02em;
}

/* ─── Priority table ─────────────────────────────────────────────────────── */
.sz-issue-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-left: 4px solid #58a6ff;
    border-radius: 10px;
    padding: 1.1rem 1.4rem;
    margin-bottom: 0.8rem;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.sz-issue-card:hover {
    border-left-color: #79c0ff;
    box-shadow: 0 4px 20px rgba(88,166,255,0.08);
}
.sz-issue-card.high {
    border-left-color: #ff7b72;
}
.sz-issue-card.medium {
    border-left-color: #f0883e;
}
.sz-issue-card.low {
    border-left-color: #3fb950;
}
.issue-title {
    font-size: 1rem;
    font-weight: 700;
    color: #e6edf3;
    margin-bottom: 0.4rem;
}
.issue-meta {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    font-size: 0.78rem;
    color: #8b949e;
    margin-bottom: 0.5rem;
}
.issue-meta span {
    display: flex;
    align-items: center;
    gap: 0.25rem;
}
.issue-action {
    font-size: 0.82rem;
    color: #58a6ff;
    background: rgba(88,166,255,0.08);
    border-radius: 6px;
    padding: 0.4rem 0.7rem;
    margin-top: 0.5rem;
    line-height: 1.5;
}
.snippet-box {
    font-size: 0.8rem;
    color: #8b949e;
    font-style: italic;
    border-left: 2px solid #30363d;
    padding-left: 0.7rem;
    margin-top: 0.5rem;
    line-height: 1.5;
}

/* ─── Attribution panel ──────────────────────────────────────────────────── */
.sz-misattrib-card {
    background: linear-gradient(145deg, #1c1212, #161b22);
    border: 1px solid #3d1f1f;
    border-left: 4px solid #ff7b72;
    border-radius: 10px;
    padding: 1.1rem 1.4rem;
    margin-bottom: 0.8rem;
}
.misattrib-header {
    font-weight: 700;
    color: #ffa198;
    font-size: 0.95rem;
    margin-bottom: 0.35rem;
}
.misattrib-reason {
    font-size: 0.82rem;
    color: #8b949e;
    line-height: 1.6;
    margin-bottom: 0.4rem;
}
.misattrib-owner {
    font-size: 0.78rem;
    font-weight: 600;
    color: #3fb950;
    background: rgba(63,185,80,0.1);
    border-radius: 5px;
    padding: 0.25rem 0.6rem;
    display: inline-block;
}

/* ─── Cross-property alert ───────────────────────────────────────────────── */
.sz-cross-card {
    background: linear-gradient(145deg, #1a1500, #161b22);
    border: 1px solid #3d3000;
    border-left: 4px solid #f0883e;
    border-radius: 10px;
    padding: 1.1rem 1.4rem;
    margin-bottom: 0.8rem;
}
.cross-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #ffa657;
    margin-bottom: 0.35rem;
}

/* ─── Drilldown timeline ─────────────────────────────────────────────────── */
.timeline-item {
    border-left: 2px solid #21262d;
    padding: 0.6rem 0 0.6rem 1.2rem;
    position: relative;
    margin-bottom: 0.5rem;
}
.timeline-item::before {
    content: '';
    position: absolute;
    left: -5px; top: 50%;
    transform: translateY(-50%);
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #58a6ff;
    border: 2px solid #0d1117;
}

/* ─── Upload zone ─────────────────────────────────────────────────────────── */
.stFileUploader > div {
    background: #161b22;
    border: 1px dashed #30363d;
    border-radius: 12px;
}

/* ─── Streamlit overrides ────────────────────────────────────────────────── */
.stSelectbox > div > div, .stMultiSelect > div > div {
    background: #161b22 !important;
    border-color: #30363d !important;
    border-radius: 8px !important;
    color: #e6edf3 !important;
}
div[data-testid="stExpander"] {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
}
div[data-testid="stMetric"] {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 1rem;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #0d1117;
    border-bottom: 1px solid #21262d;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px 8px 0 0;
    color: #8b949e;
    font-weight: 500;
    padding: 0.6rem 1.2rem;
}
.stTabs [aria-selected="true"] {
    background: #161b22 !important;
    color: #58a6ff !important;
    border-bottom: 2px solid #58a6ff;
}
hr { border-color: #21262d; }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def priority_css_class(priority: str) -> str:
    if "High" in priority:
        return "high"
    if "Medium" in priority:
        return "medium"
    return "low"


def fmt_issue(slug: str) -> str:
    return slug.replace("_", " ").title()


def rating_stars(rating: float) -> str:
    full = int(rating)
    half = 1 if (rating - full) >= 0.4 else 0
    empty = 5 - full - half
    return "★" * full + ("½" if half else "") + "☆" * empty


def render_summary_cards(summary: dict):
    cols = st.columns(4)
    cards = [
        ("📋", summary["total_reviews"], "Total Reviews Analyzed", "blue"),
        ("🏘️", summary["properties_with_issues"], "Properties with Recurring Issues", "yellow"),
        ("🔴", summary["high_priority_count"], "High-Priority Issues", "red"),
        ("⚠️", summary["misattributed_count"], "Potential Caretaker Misattributions", "purple"),
    ]
    for col, (icon, value, label, color) in zip(cols, cards):
        col.markdown(
            f"""<div class="sz-card">
                <span class="card-icon">{icon}</span>
                <div class="card-value {color}">{value}</div>
                <div class="card-label">{label}</div>
            </div>""",
            unsafe_allow_html=True,
        )


def render_issue_card(row: dict, show_action: bool = True, llm_mode: bool = False):
    css = priority_css_class(row["priority"])

    # Escape ALL user-provided text before embedding in HTML
    snippet_raw  = html_lib.escape(str(row.get("best_snippet", "")))
    property_esc = html_lib.escape(str(row.get("propertyname", "")))
    owner_esc    = html_lib.escape(str(row.get("owner_bucket", "")))
    priority_esc = html_lib.escape(str(row.get("priority", "")))
    issue_esc    = html_lib.escape(fmt_issue(row["primary_issue"]))

    snippet_html = f'<div class="snippet-box">"{snippet_raw}"</div>' if snippet_raw else ""

    raw_action  = (
        row.get("llm_recommended_next_step") or row.get("recommended_action", "")
        if llm_mode else row.get("recommended_action", "")
    )
    action_esc  = html_lib.escape(str(raw_action or ""))
    action_html = (
        f'<div class="issue-action">&#128204; {action_esc}</div>'
        if show_action and action_esc else ""
    )

    ctrl = row.get("caretaker_controllable", False)
    controlled_badge = (
        "&#10003; Caretaker-linked" if ctrl else "&#128683; Not caretaker-controlled"
    )

    n_reviews = row["recurrence_count"]
    recurrence_badge = (
        f'<span>&#128257; {n_reviews} review{"s &mdash; recurring" if n_reviews > 1 else " (not recurring)"}</span>'
    )

    llm_html = ""
    if llm_mode:
        s = html_lib.escape(str(row.get("llm_problem_summary", "")))
        m = html_lib.escape(str(row.get("llm_why_it_matters", "")))
        c = html_lib.escape(str(row.get("llm_confidence_note", "")))
        if s or m:
            llm_html = (
                '<div style="margin-top:0.6rem;padding:0.7rem 0.9rem;'
                'background:rgba(88,166,255,0.06);border-radius:8px;border-left:3px solid #58a6ff;">'
                '<div style="font-size:0.78rem;color:#58a6ff;font-weight:600;margin-bottom:0.3rem;">&#129302; AI Analysis</div>'
                + (f'<div style="font-size:0.82rem;color:#e6edf3;margin-bottom:0.2rem;">{s}</div>' if s else "")
                + (f'<div style="font-size:0.78rem;color:#8b949e;">{m}</div>' if m else "")
                + (f'<div style="font-size:0.74rem;color:#6e7681;margin-top:0.3rem;">&#128269; {c}</div>' if c else "")
                + "</div>"
            )

    avg_rating_str = f"{row['avg_normalized_rating']:.1f}/5"
    html_out = (
        '<div class="sz-issue-card ' + css + '">'
        + '<div class="issue-title">' + property_esc + ' &mdash; ' + issue_esc + '</div>'
        + '<div class="issue-meta">'
        + '<span>&#128100; ' + owner_esc + '</span>'
        + recurrence_badge
        + '<span>&#11088; ' + avg_rating_str + '</span>'
        + '<span>' + priority_esc + '</span>'
        + '<span>' + controlled_badge + '</span>'
        + '</div>'
        + snippet_html
        + llm_html
        + action_html
        + '</div>'
    )
    st.markdown(html_out, unsafe_allow_html=True)


def render_cross_property_card(row: dict, llm_mode: bool = False):
    props      = html_lib.escape(str(row.get("property_list", "")))
    caretaker  = html_lib.escape(str(row.get("caretakername", "")))
    issue_esc  = html_lib.escape(fmt_issue(row["primary_issue"]))
    snippets   = row.get("snippets", [])
    first_snip = html_lib.escape(str(snippets[0]) if snippets else "")

    llm_html = ""
    if llm_mode:
        explanation = html_lib.escape(str(row.get("llm_pattern_explanation", "")))
        action      = html_lib.escape(str(row.get("llm_recommended_action", "")))
        escalation  = html_lib.escape(str(row.get("llm_escalation_note", "")))
        if explanation:
            llm_html = (
                '<div style="margin-top:0.5rem;padding:0.6rem 0.8rem;'
                'background:rgba(240,136,62,0.08);border-radius:8px;border-left:3px solid #f0883e;">'
                '<div style="font-size:0.78rem;color:#ffa657;font-weight:600;margin-bottom:0.25rem;">&#129302; AI Pattern Analysis</div>'
                + (f'<div style="font-size:0.82rem;color:#e6edf3;">{explanation}</div>' if explanation else "")
                + (f'<div style="font-size:0.78rem;color:#58a6ff;margin-top:0.3rem;">&#128204; {action}</div>' if action else "")
                + (f'<div style="font-size:0.74rem;color:#6e7681;margin-top:0.2rem;">Escalate to: {escalation}</div>' if escalation else "")
                + "</div>"
            )

    html_out = (
        f'<div class="sz-cross-card">'
        f'<div class="cross-title">&#9889; Cross-Property Pattern: {caretaker} &mdash; {issue_esc}</div>'
        f'<div class="issue-meta" style="color:#8b949e;font-size:0.82rem;display:flex;gap:1rem;flex-wrap:wrap;margin:0.3rem 0;">'
        f'<span>&#127960; Properties: {props}</span>'
        f'<span>&#128257; {row["count"]} occurrences</span>'
        f'<span>&#11088; Avg {row["avg_rating"]:.1f}/5</span>'
        f'</div>'
        f'<div class="snippet-box">"{first_snip}"</div>'
        + llm_html
        + '</div>'
    )
    st.markdown(html_out, unsafe_allow_html=True)


def render_misattribution_card(ex: dict):
    caretaker_str = html_lib.escape(str(ex.get("caretaker") or "N/A"))
    property_esc  = html_lib.escape(str(ex.get("property", "")))
    issue_esc     = html_lib.escape(str(ex.get("display_issue", "")))
    why_esc       = html_lib.escape(str(ex.get("why_not_caretaker", "")))
    owner_esc     = html_lib.escape(str(ex.get("real_owner", "")))
    html_out = (
        f'<div class="sz-misattrib-card">'
        f'<div class="misattrib-header">&#128683; {property_esc} &mdash; {issue_esc}</div>'
        f'<div class="misattrib-reason">{why_esc}</div>'
        f'<span class="misattrib-owner">&#10003; Real owner: {owner_esc}</span>'
        f'&nbsp;&nbsp;'
        f'<span style="font-size:0.78rem;color:#6e7681;">Caretaker on record: {caretaker_str}</span>'
        f'</div>'
    )
    st.markdown(html_out, unsafe_allow_html=True)



# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main():
    # ── Sidebar: AI settings ─────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            """<div style="padding:1rem 0 0.5rem;">
            <div style="font-size:1.1rem;font-weight:700;color:#e6edf3;">⚙️ Settings</div>
            </div>""",
            unsafe_allow_html=True,
        )
        use_llm = st.toggle(
            "🤖 Enable AI Summaries (Groq Llama)",
            value=False,
            help=(
                f"Uses {GROQ_MODEL} to generate narrative summaries "
                "for each issue cluster. Core analytics always run in Python."
            ),
        )
        if use_llm:
            st.success(f"AI mode ON — {GROQ_MODEL}")
            st.caption(
                "Counts, ratings, and priority scores are always computed "
                "in Python. The LLM only writes the explanations."
            )
        else:
            st.info("Rule-based mode (fast, deterministic)")

        st.divider()
        st.markdown(
            """<div style="font-size:0.78rem;color:#6e7681;line-height:1.7;">
            <b style="color:#8b949e;">Architecture</b><br>
            ✅ Rating normalization — Python<br>
            ✅ Issue tagging — Rule-based<br>
            ✅ Recurrence detection — Python<br>
            ✅ Priority scoring — Python<br>
            🤖 Narrative summaries — Groq Llama<br>
            🤖 Cluster explanations — Groq Llama
            </div>""",
            unsafe_allow_html=True,
        )

    # ── Header ──────────────────────────────────────────────────────────────
    st.markdown(
        f'<div class="sz-header">'
        f'<span class="sz-badge">Operations Intelligence</span>'
        f'<h1>&#127969; {APP_TITLE}</h1>'
        f'<p>{APP_SUBTITLE} &mdash; Convert raw multi-platform reviews into prioritized operational actions.</p>'
        f'<p style="font-size:0.78rem;color:#6e7681;margin-top:0.5rem;border-top:1px solid #21262d;'
        f'padding-top:0.5rem;">'
        f'&#128202; Ratings normalized to a 5-point scale across Airbnb, Booking.com, and Google &mdash; '
        f'raw scores are never compared directly across platforms.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Data ingestion ───────────────────────────────────────────────────────
    local_data = Path(__file__).parent / "data" / "spacez_reviews_dataset.xlsx"

    with st.container():
        st.markdown('<div class="sz-section">📂 Data Source</div>', unsafe_allow_html=True)
        col_up, col_info = st.columns([2, 1])

        with col_up:
            uploaded_file = st.file_uploader(
                "Upload your reviews Excel file (.xlsx)",
                type=["xlsx"],
                help="Must contain columns: platform, propertyname, caretakername, ratingraw, ratingscale, reviewtext",
            )

        with col_info:
            st.markdown(
                """<div style="background:#161b22;border:1px solid #21262d;border-radius:10px;padding:1rem;font-size:0.82rem;color:#8b949e;line-height:1.7;">
                <b style="color:#58a6ff;">Expected columns:</b><br>
                platform · propertyname · caretakername<br>
                ratingraw · ratingscale · reviewtext<br>
                reviewdate <span style="color:#3fb950;">(optional)</span>
                </div>""",
                unsafe_allow_html=True,
            )

    # Determine which file to use
    source_file = None
    source_label = ""
    if uploaded_file is not None:
        source_file = uploaded_file
        source_label = f"Uploaded: **{uploaded_file.name}**"
    elif local_data.exists():
        source_file = str(local_data)
        source_label = f"Using local dataset: `{local_data.name}`"

    if source_file is None:
        st.info(
            "👆 Upload a reviews spreadsheet to begin analysis. "
            "If you place **spacez_reviews_dataset.xlsx** in the `data/` folder it will load automatically.",
            icon="📊",
        )
        st.stop()

    # ── Run pipeline (cached) ────────────────────────────────────────────────
    @st.cache_data(show_spinner="Analysing reviews…")
    def cached_pipeline(file_bytes: bytes | str, _use_llm: bool = False):
        """Cache key includes use_llm so switching AI mode re-runs analysis."""
        if isinstance(file_bytes, bytes):
            return run_full_pipeline(io.BytesIO(file_bytes), use_llm=_use_llm)
        return run_full_pipeline(file_bytes, use_llm=_use_llm)

    try:
        with st.spinner("🤖 Running AI analysis with Groq Llama…" if use_llm else "Analysing reviews…"):
            if isinstance(source_file, str):
                results = cached_pipeline(source_file, _use_llm=use_llm)
            else:
                results = cached_pipeline(source_file.read(), _use_llm=use_llm)
    except Exception as exc:
        st.error(f"❌ Failed to process file: {exc}")
        st.stop()

    llm_active = results.get("llm_available", False) and use_llm

    df = results["df"]
    priority_queue = results["priority_queue"]
    cross_property = results["cross_property"]

    if llm_active:
        st.success(f"🤖 AI summaries generated using **{GROQ_MODEL}**", icon="✨")
    misattributions = results["misattributions"]
    summary = results["summary"]

    st.caption(source_label)

    # ── Derived views ─────────────────────────────────────────────────────────
    # Exclude positive_host_service from ops queue entirely
    ops_queue = priority_queue[
        priority_queue["primary_issue"] != "positive_host_service"
    ].copy()
    # Recognition-worthy rows (positive service)
    recognition_rows = priority_queue[
        priority_queue["primary_issue"] == "positive_host_service"
    ].copy()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 1 — Summary Cards
    # ════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="sz-section">📊 Overview</div>', unsafe_allow_html=True)
    render_summary_cards(summary)

    # ── TOP 3 ACTIONS THIS WEEK ───────────────────────────────────────────────
    top3 = ops_queue[ops_queue["primary_issue"] != "positive_host_service"].head(3)
    if not top3.empty:
        st.markdown(
            '<div class="sz-section">🎯 Top 3 Actions This Week</div>',
            unsafe_allow_html=True,
        )
        t_cols = st.columns(len(top3))
        rank_colors = ["#ff7b72", "#f0883e", "#58a6ff"]
        rank_labels = ["#1 Fix Now", "#2 Schedule", "#3 Plan"]
        for i, (col, (_, row)) in enumerate(zip(t_cols, top3.iterrows())):
            prop    = html_lib.escape(str(row["propertyname"]))
            issue   = html_lib.escape(fmt_issue(row["primary_issue"]))
            owner   = html_lib.escape(str(row["owner_bucket"]))
            raw_act = str(row.get("llm_recommended_next_step") or row.get("recommended_action", ""))
            action  = html_lib.escape(raw_act)
            color   = rank_colors[i]
            label   = rank_labels[i]
            col.markdown(
                f'<div style="background:linear-gradient(145deg,#161b22,#0d1117);'
                f'border:1px solid #21262d;border-top:3px solid {color};'
                f'border-radius:12px;padding:1.2rem 1.4rem;height:100%;">'
                f'<div style="font-size:0.7rem;font-weight:700;color:{color};'
                f'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.5rem;">{label}</div>'
                f'<div style="font-size:0.95rem;font-weight:700;color:#e6edf3;margin-bottom:0.3rem;">'
                f'{prop}</div>'
                f'<div style="font-size:0.82rem;color:#79c0ff;margin-bottom:0.6rem;">{issue}</div>'
                f'<div style="font-size:0.78rem;color:#8b949e;margin-bottom:0.5rem;">'
                f'<b style="color:#6e7681;">Owner:</b> {owner}</div>'
                f'<div style="font-size:0.78rem;color:#58a6ff;background:rgba(88,166,255,0.08);'
                f'border-radius:6px;padding:0.4rem 0.6rem;line-height:1.5;">'
                f'&#128204; {action}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Quick chart row
    st.markdown("<br>", unsafe_allow_html=True)
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        issue_counts = (
            df[
                (df["primary_issue"] != "no_issue_detected")
                & (df["primary_issue"] != "positive_host_service")
            ]
            .groupby("primary_issue")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=True)
        )
        if not issue_counts.empty:
            fig = px.bar(
                issue_counts,
                x="count",
                y="primary_issue",
                orientation="h",
                color="count",
                color_continuous_scale=["#1f6feb", "#58a6ff", "#79c0ff"],
                labels={"count": "Occurrences", "primary_issue": ""},
                title="Operational Issue Frequency",
            )
            fig.update_layout(
                plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                font_color="#8b949e", title_font_color="#e6edf3",
                coloraxis_showscale=False, margin=dict(l=0, r=0, t=40, b=0),
                yaxis=dict(tickfont=dict(size=11)),
            )
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(fig, width="stretch")

    with chart_col2:
        prop_ratings = (
            df.groupby("propertyname")["normalized_rating"]
            .mean().reset_index().sort_values("normalized_rating")
        )
        if not prop_ratings.empty:
            fig2 = px.bar(
                prop_ratings, x="normalized_rating", y="propertyname",
                orientation="h",
                labels={"normalized_rating": "Avg Normalized Rating (0–5)", "propertyname": ""},
                title="Average Normalized Rating by Property",
                color="normalized_rating",
                color_continuous_scale=["#ff7b72", "#f0883e", "#3fb950"],
                range_color=[0, 5],
            )
            fig2.add_vline(x=3.0, line_dash="dash", line_color="#8b949e", opacity=0.5)
            fig2.update_layout(
                plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                font_color="#8b949e", title_font_color="#e6edf3",
                coloraxis_showscale=False, margin=dict(l=0, r=0, t=40, b=0),
            )
            st.plotly_chart(fig2, width="stretch")

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 2 — Priority Queue
    # ════════════════════════════════════════════════════════════════════════
    st.markdown(
        '<div class="sz-section">🚨 Recurring Issues Requiring Ops Action</div>',
        unsafe_allow_html=True,
    )

    # Filters
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        all_props = sorted(ops_queue["propertyname"].unique())
        sel_props = st.multiselect("Filter by Property", all_props, placeholder="All properties")
    with fc2:
        all_owners = sorted(ops_queue["owner_bucket"].unique())
        sel_owners = st.multiselect("Filter by Owner", all_owners, placeholder="All owners")
    with fc3:
        all_priorities = ["🔴 High", "🟡 Medium", "🟢 Low"]
        sel_pris = st.multiselect("Filter by Priority", all_priorities, placeholder="All priorities")
    with fc4:
        show_recurring_only = st.checkbox("Recurring only (≥2 reviews)", value=False)

    fdf = ops_queue.copy()
    if sel_props:
        fdf = fdf[fdf["propertyname"].isin(sel_props)]
    if sel_owners:
        fdf = fdf[fdf["owner_bucket"].isin(sel_owners)]
    if sel_pris:
        fdf = fdf[fdf["priority"].isin(sel_pris)]
    if show_recurring_only:
        fdf = fdf[fdf["recurring_flag"]]

    if fdf.empty:
        st.info("No issues match the current filters.")
    else:
        for _, row in fdf.iterrows():
            render_issue_card(row.to_dict(), llm_mode=llm_active)

    # Recognition panel (positive service — separated from ops queue)
    if not recognition_rows.empty:
        with st.expander("🌟 Caretaker Recognition (positive service — not an ops issue)", expanded=False):
            st.caption("These reviews reflect excellent caretaker performance. Surface to HR/recognition program, not ops escalation.")
            for _, row in recognition_rows.iterrows():
                prop  = html_lib.escape(str(row["propertyname"]))
                care  = html_lib.escape(str(row.get("caretakername", "")))
                snip  = html_lib.escape(str(row.get("best_snippet", "")))
                st.markdown(
                    f'<div style="background:#0d1f0d;border:1px solid #1c3a1c;border-left:3px solid #3fb950;'
                    f'border-radius:8px;padding:0.8rem 1rem;margin-bottom:0.5rem;">'
                    f'<b style="color:#3fb950;">{prop}</b> &nbsp;·&nbsp; '
                    f'<span style="color:#8b949e;font-size:0.82rem;">Caretaker: {care}</span><br>'
                    f'<span style="color:#6e7681;font-size:0.8rem;font-style:italic;">"{snip}"</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # Cross-property pattern highlight
    if not cross_property.empty:
        st.markdown(
            '<div class="sz-section">⚡ Cross-Property Caretaker Pattern Detected</div>',
            unsafe_allow_html=True,
        )
        for _, row in cross_property.iterrows():
            render_cross_property_card(row.to_dict(), llm_mode=llm_active)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 3 — Drill-Down
    # ════════════════════════════════════════════════════════════════════════
    st.markdown(
        '<div class="sz-section">🔍 Drill-Down: Property &amp; Issue Detail</div>',
        unsafe_allow_html=True,
    )

    dd_col1, dd_col2 = st.columns(2)
    with dd_col1:
        sel_property = st.selectbox(
            "Select Property",
            ["(all)"] + sorted(df["propertyname"].unique()),
            key="dd_property",
        )
    with dd_col2:
        issues_for_prop = df[
            (df["propertyname"] == sel_property) if sel_property != "(all)" else df["primary_issue"].notna()
        ]["primary_issue"].unique()
        issue_options = sorted([
            i for i in issues_for_prop
            if i not in ("no_issue_detected", "positive_host_service")
        ])
        sel_issue = st.selectbox(
            "Select Issue",
            ["(all)"] + issue_options,
            key="dd_issue",
        )

    drilldown_df = df.copy()
    if sel_property != "(all)":
        drilldown_df = drilldown_df[drilldown_df["propertyname"] == sel_property]
    if sel_issue != "(all)":
        drilldown_df = drilldown_df[drilldown_df["primary_issue"] == sel_issue]

    drilldown_df = drilldown_df[
        ~drilldown_df["primary_issue"].isin(["no_issue_detected", "positive_host_service"])
    ]

    # Infrastructure issues that should never be caretaker-blamed — shown as inline note
    INFRASTRUCTURE_NOTES = {
        "wifi": (
            "&#128274; Infrastructure issue — WiFi is ISP/router equipment, "
            "not caretaker responsibility. Escalate to Ops/Maintenance, not the caretaker."
        ),
        "heating": (
            "&#128274; Infrastructure issue — Heating equipment requires maintenance contractor. "
            "Caretaker cannot repair boilers or HVAC units."
        ),
        "hot_water": (
            "&#128274; Infrastructure issue — Geyser/boiler is fixed equipment. "
            "Escalate to plumber on-call, not caretaker."
        ),
        "pool_maintenance": (
            "&#128274; Infrastructure issue — Pool chemical balance and pump maintenance "
            "require specialist vendor, not caretaker."
        ),
        "dampness_mosquitoes": (
            "&#127807; Environmental / structural condition — Dampness near water bodies "
            "is seasonal and location-specific, not a housekeeping failure. "
            "Action: set expectation in listing copy; provide mosquito repellent in welcome kit."
        ),
    }

    if drilldown_df.empty:
        st.info("No matching reviews for this selection.")
    else:
        issue_group = drilldown_df.groupby("primary_issue").agg(
            count=("primary_issue", "count"),
            avg_rating=("normalized_rating", "mean"),
        )

        for issue_slug, grp in issue_group.iterrows():
            with st.expander(
                f"📌 {fmt_issue(issue_slug)} — {int(grp['count'])} review(s), "
                f"Normalized Rating (0–5): {grp['avg_rating']:.2f}",
                expanded=True,
            ):
                issue_reviews = drilldown_df[drilldown_df["primary_issue"] == issue_slug]
                recurrence    = int(grp["count"])
                owner         = html_lib.escape(str(issue_reviews.iloc[0]["owner_bucket"]))
                controllable  = issue_reviews.iloc[0]["caretaker_controllable"]
                ctrl_text = (
                    "Controllable by caretaker: ✅ Yes"
                    if controllable
                    else "Controllable by caretaker: 🚫 No — escalate to the correct owner"
                )

                # Infrastructure note if applicable
                infra_note = INFRASTRUCTURE_NOTES.get(issue_slug, "")
                infra_html = (
                    f'<div style="background:rgba(255,123,114,0.08);border:1px solid #3d1f1f;'
                    f'border-radius:8px;padding:0.6rem 0.9rem;margin-bottom:0.8rem;'
                    f'font-size:0.82rem;color:#ffa198;">{infra_note}</div>'
                    if infra_note else ""
                )

                # Why priority now — evidence-based phrasing
                n_props = issue_reviews["propertyname"].nunique()
                prop_part = (
                    f"across {n_props} properties" if n_props > 1 else ""
                )
                reasons = []
                if recurrence >= 1:
                    r_str = f"{recurrence} review{'s' if recurrence > 1 else ''}"
                    reasons.append(
                        f"appears in {r_str} {prop_part}".strip()
                        + f" with avg normalized rating {grp['avg_rating']:.2f}/5"
                    )
                if not controllable:
                    reasons.append("not within caretaker control — re-route to correct owner")
                why_now = ("Evidence: " + " \u00b7 ".join(reasons) + ".") if reasons else ""

                st.markdown(
                    f'<div style="background:#161b22;border:1px solid #21262d;'
                    f'border-radius:10px;padding:1rem;margin-bottom:1rem;">'
                    f'{infra_html}'
                    f'<div style="margin-bottom:0.4rem;">'
                    f'<b style="color:#58a6ff;">Owner:</b> {owner}&nbsp;&nbsp;'
                    f'<span style="color:{"#3fb950" if controllable else "#ff7b72"};">{ctrl_text}</span>'
                    f'</div>'
                    + (f'<div style="font-size:0.8rem;color:#f0883e;margin-top:0.3rem;">⚠️ {why_now}</div>' if why_now else "")
                    + '</div>',
                    unsafe_allow_html=True,
                )

                # Timeline
                has_dates = "reviewdate" in issue_reviews.columns and issue_reviews["reviewdate"].notna().any()
                sorted_reviews = issue_reviews.sort_values("reviewdate") if has_dates else issue_reviews

                st.markdown("**Review Timeline**")
                for _, rev in sorted_reviews.iterrows():
                    date_str  = (
                        rev["reviewdate"].strftime("%b %Y")
                        if has_dates and pd.notna(rev.get("reviewdate"))
                        else "Date unknown"
                    )
                    plat      = html_lib.escape(str(rev.get("platform", "")).capitalize())
                    rating_str = f"Normalized Rating (0–5): {rev['normalized_rating']:.1f}"
                    caretaker  = html_lib.escape(str(rev.get("caretakername", "N/A")))
                    snippet    = html_lib.escape(str(rev.get("evidence_snippet", rev.get("reviewtext", ""))))

                    st.markdown(
                        f'<div class="timeline-item">'
                        f'<div style="font-size:0.78rem;color:#58a6ff;margin-bottom:0.25rem;">'
                        f'{date_str} &nbsp;·&nbsp; {plat} &nbsp;·&nbsp; {rating_str}'
                        f' &nbsp;·&nbsp; Caretaker: {caretaker}</div>'
                        f'<div class="snippet-box">"{snippet}"</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                if has_dates and len(sorted_reviews) >= 2:
                    fig3 = px.line(
                        sorted_reviews, x="reviewdate", y="normalized_rating",
                        markers=True,
                        labels={"reviewdate": "Date", "normalized_rating": "Normalized Rating (0–5)"},
                        title=f"Rating Trend — {fmt_issue(issue_slug)}",
                        color_discrete_sequence=["#58a6ff"],
                    )
                    fig3.add_hline(y=3.0, line_dash="dash", line_color="#8b949e", opacity=0.5)
                    fig3.update_layout(
                        plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                        font_color="#8b949e", title_font_color="#e6edf3",
                        yaxis=dict(range=[0, 5.5]),
                        margin=dict(l=0, r=0, t=40, b=0),
                    )
                    st.plotly_chart(fig3, width="stretch")

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 4 — Attribution Check ("Do not blame caretaker")
    # ════════════════════════════════════════════════════════════════════════
    st.markdown(
        '<div class="sz-section">🚫 Attribution Check — "Do Not Blame Caretaker"</div>',
        unsafe_allow_html=True,
    )

    misattrib_count = summary["misattributed_count"]
    st.markdown(
        f'<div style="background:linear-gradient(145deg,#1a1214,#161b22);border:1px solid #3d1f1f;'
        f'border-radius:12px;padding:1.2rem 1.5rem;margin-bottom:1.5rem;color:#8b949e;'
        f'font-size:0.88rem;line-height:1.7;">'
        f'<b style="color:#ffa198;">⚠️ Caretaker Reporting Risk:</b> '
        f'<b style="color:#e6edf3;">{misattrib_count} reviews</b> in this dataset involve issues '
        f'that are <i>not</i> within caretaker control — yet they would appear in a caretaker '
        f'performance report if naively filtered by "caretaker hosted this stay." '
        f'<br><br>Issues excluded from caretaker accountability: '
        f'<b>listing mismatch, occupancy policy, road/access, infrastructure failures '
        f'(pool pump, heating, WiFi, geyser), and external location factors.</b> '
        f'Only <b>check-in punctuality</b> and <b>on-ground service quality</b> '
        f'are treated as caretaker-controllable in this system.'
        f'<br><span style="font-size:0.75rem;color:#6e7681;">Logic: a review is counted here '
        f'when caretaker_controllable=False AND primary_issue is a classified operational issue '
        f'(not positive feedback or unclassified).</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    for ex in misattributions:
        render_misattribution_card(ex)

    # ── Enriched data table ───────────────────────────────────────────────────
    with st.expander("🗂️ Processed Review Data"):
        CURATED_COLS = {
            "propertyname": "Property",
            "platform": "Platform",
            "caretakername": "Caretaker",
            "ratingraw": "Raw Rating",
            "normalized_rating": "Normalized Rating (0–5)",
            "primary_issue": "Primary Issue",
            "owner_bucket": "Owner",
            "caretaker_controllable": "Controllable by Caretaker?",
            "sentiment_label": "Sentiment",
            "evidence_snippet": "Evidence Snippet",
        }
        avail_curated = {k: v for k, v in CURATED_COLS.items() if k in df.columns}
        show_full = st.checkbox("Show full processed data (all columns)", value=False)

        if show_full:
            display_df = df.rename(columns=avail_curated)
        else:
            display_df = df[list(avail_curated.keys())].rename(columns=avail_curated)

        st.dataframe(
            display_df.style.background_gradient(
                subset=["Normalized Rating (0–5)"], cmap="RdYlGn", vmin=0, vmax=5
            ),
            width="stretch",
            height=380,
        )
        csv_bytes = display_df.to_csv(index=False).encode()
        st.download_button(
            "⬇️ Download as CSV",
            data=csv_bytes,
            file_name="spacez_enriched_reviews.csv",
            mime="text/csv",
        )

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="text-align:center;color:#6e7681;font-size:0.78rem;margin-top:3rem;'
        'padding-top:1.5rem;border-top:1px solid #21262d;">'
        'Spacez Review Action Agent &nbsp;·&nbsp; Built for Operations &nbsp;·&nbsp;'
        'Deterministic rule-based classification + optional Groq Llama narrative layer'
        '</div>',
        unsafe_allow_html=True,
    )




if __name__ == "__main__":
    main()

