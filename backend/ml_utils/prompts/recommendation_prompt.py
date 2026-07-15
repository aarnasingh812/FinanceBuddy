
import json
from datetime import datetime

# ---------------------------------------------------------------------------
# System instruction — kept minimal; schema enforces structure
# ---------------------------------------------------------------------------

SYSTEM_INSTRUCTION = """\
You are FinanceBuddy AI Coach — a friendly personal finance advisor.

Rules:
- Ground EVERY claim in the provided data. NEVER invent figures.
- Use ₹ for money. Speak in 2nd person ("you"/"your").
- Be encouraging but honest. Prioritise high-impact advice.
- Short paragraphs (2-3 sentences). Bullet lists for actions.
- Output ONLY the JSON object — no markdown fences, no commentary.\
"""


# ---------------------------------------------------------------------------
# Response schema — descriptions stripped to essentials
# ---------------------------------------------------------------------------

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_summary": {
            "type": "string",
            "description": "2-3 sentence financial health snapshot.",
        },
        "savings_narrative": {
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "personalized_tips": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rec_index": {"type": "integer"},
                            "personalized_detail": {"type": "string"},
                            "motivation": {"type": "string"},
                        },
                        "required": ["rec_index", "personalized_detail", "motivation"],
                    },
                },
                "coaching_note": {"type": "string"},
            },
            "required": ["headline", "personalized_tips", "coaching_note"],
        },
        "spend_narrative": {
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "category_insights": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "narrative": {"type": "string"},
                        },
                        "required": ["category", "narrative"],
                    },
                },
                "trend_alert": {"type": "string"},
            },
            "required": ["headline", "category_insights", "trend_alert"],
        },
        "goal_narratives": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "goal_id": {"type": "integer"},
                    "personalized_insight": {"type": "string"},
                    "action_plan": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "encouragement": {"type": "string"},
                },
                "required": ["goal_id", "personalized_insight", "action_plan", "encouragement"],
            },
        },
    },
    "required": [
        "overall_summary",
        "savings_narrative",
        "spend_narrative",
        "goal_narratives",
    ],
}


# ---------------------------------------------------------------------------
# Prompt builder — compact, data-dense, no fluff
# ---------------------------------------------------------------------------

def _fmt(amount) -> str:
    """Format a number as ₹X,XXX — no decimals if whole."""
    val = float(amount)
    return f"₹{val:,.0f}" if val == int(val) else f"₹{val:,.2f}"


def build_prompt(context: dict) -> str:
   
    lines = []

    # -- User profile (single line)
    p = context.get("user_profile", {})
    lines.append(
        f"USER: {p.get('username','User')} | "
        f"acct_age={p.get('account_age_months','?')}mo | "
        f"date={p.get('analysis_date', datetime.now().strftime('%Y-%m-%d'))}"
    )

    # -- Financial snapshot (single line)
    s = context.get("financial_snapshot", {})
    if s:
        lines.append(
            f"SNAPSHOT: income={_fmt(s.get('avg_monthly_income',0))}/mo "
            f"expense={_fmt(s.get('avg_monthly_expense',0))}/mo "
            f"this_month={_fmt(s.get('current_month_expense',0))} "
            f"months={s.get('total_months',0)}"
        )

    # -- Savings recommendations (compact table)
    recs = context.get("savings_recommendations", [])
    if recs:
        total = context.get("total_potential_savings", 0)
        lines.append(f"\nSAVINGS RECS (total potential: {_fmt(total)}/mo):")
        for i, r in enumerate(recs):
            lines.append(
                f"  [{i}] {r.get('title','')} | "
                f"save={_fmt(r.get('estimated_monthly_savings',0))}/mo | "
                f"pri={r.get('priority','med')} | "
                f"type={r.get('type','')}"
            )

    # -- Spend optimization (compact)
    spend = context.get("spend_optimization")
    if spend:
        top = spend.get("top_categories") or []
        if top:
            lines.append("\nTOP SPEND:")
            for c in top:
                lines.append(
                    f"  {c['category']}: avg={_fmt(c['avg_monthly_spend'])}/mo "
                    f"now={_fmt(c['current_month_spend'])} "
                    f"MoM={c['month_over_month_change_percent']:+.0f}% "
                    f"trend={c['trend']}"
                )
        rising = spend.get("rising_spend_categories") or []
        if rising:
            lines.append("RISING:")
            for c in rising:
                lines.append(
                    f"  {c['category']}: avg={_fmt(c['avg_monthly'])} "
                    f"now={_fmt(c['current_month'])}"
                )

    # -- Goal forecasts (compact)
    goals = context.get("goal_forecasts")
    if goals:
        ss = goals.get("savings_summary", {})
        ap = goals.get("allocation_plan", {})
        lines.append(
            f"\nGOALS: avg_savings={_fmt(ss.get('avg_monthly_savings',0))}/mo "
            f"trend={ss.get('savings_trend','stable')} "
            f"achievable={ap.get('achievable_goals',0)}/{ap.get('total_goals',0)}"
        )
        for f in (goals.get("forecasts") or []):
            parts = [
                f"  id={f.get('goal_id','')}",
                f"name=\"{f.get('goal_name','')}\"",
                f"target={_fmt(f.get('target_amount',0))}",
                f"remaining={_fmt(f.get('remaining_amount',0))}",
                f"progress={f.get('progress_percent',0):.0f}%",
                f"status={f.get('status','')}",
                f"months_left={f.get('months_remaining',0)}",
            ]
            alloc = f.get("allocated_monthly_savings", 0)
            req = f.get("required_monthly_savings", 0)
            if alloc:
                parts.append(f"alloc={_fmt(alloc)}/mo")
            if req:
                parts.append(f"req={_fmt(req)}/mo")
            pred = f.get("predicted_achievement_date")
            if pred:
                parts.append(f"eta={pred}")
            lines.append(" | ".join(parts))

            # Projections on one line
            projs = f.get("projections") or []
            if projs:
                proj_parts = []
                for pr in projs:
                    m = pr.get("months_to_goal")
                    proj_parts.append(
                        f"{pr['scenario']}:{_fmt(pr['monthly_savings_rate'])}/mo→{m or '∞'}mo"
                    )
                lines.append(f"    projections: {' | '.join(proj_parts)}")

    # -- Anomalies (top 3 per period max)
    anomalies = context.get("anomaly_summary")
    if anomalies:
        lines.append("\nANOMALIES:")
        for period, items in anomalies.items():
            if items:
                for a in items[:3]:
                    lines.append(
                        f"  [{period}] {a.get('title','')}: "
                        f"{_fmt(a.get('amount',0))} in {a.get('category','')} "
                        f"score={a.get('anomaly_score',0):.1f}"
                    )

    # -- Recurring (top 5 max)
    # recurring = context.get("recurring_summary")
    # if recurring:
    #     lines.append("\nRECURRING:")
    #     for item in recurring[:5]:
    #         lines.append(
    #             f"  {item.get('title','')}: {_fmt(item.get('amount',0))} "
    #             f"every ~{item.get('mean_gap_days',30):.0f}d "
    #             f"({item.get('recurring_type','?')})"
    #         )

    # -- Task instruction (single line)
    lines.append(
        "\nTASK: Write personalised coaching narrative as JSON. "
        "Use ONLY the data above — no invented figures."
    )

    return "\n".join(lines)
