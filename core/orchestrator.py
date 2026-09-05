"""
Step 12: Orchestration.

A fixed pipeline with LLM steps inside it, not a free-roaming agent --
the value here is auditability. Every stage's output is inspectable and
the order never changes, which makes this testable and debuggable in a
way an agent choosing its own steps would not be.
"""
from __future__ import annotations
from datetime import date as date_cls
from typing import List, Optional
from core.schema import CallReport, TranscriptLine, ActionItem
from core.context_retrieval import retrieve_context, render_context_block
from core.extraction import extract_summary_and_tag, extract_decisions, extract_action_items, extract_blockers
from core.grounding_verifier import verify_items
from core.date_resolver import resolve_date_phrase
from core.compliance import detect_hard_triggers, classify_compliance
from core.sentiment import analyze_sentiment
from core.human_review import build_human_review


def run_pipeline(
    call_id: str,
    call_date: str,
    call_type: str,
    lines: List[TranscriptLine],
    customer_id: Optional[str] = None,
) -> CallReport:
    call_date_obj = date_cls.fromisoformat(call_date)

    # 3. Route by call type -> pull the right policy/context
    ctx = retrieve_context(call_type, customer_id)
    context_block = render_context_block(ctx)

    # 5. Extraction (separate, focused passes)
    tag, summary = extract_summary_and_tag(lines, call_type)
    decisions_raw = extract_decisions(lines, context_block)
    action_items_raw = extract_action_items(lines, context_block)
    blockers_raw = extract_blockers(lines, context_block)

    # 6. Grounding verification -- split into verified vs failed for every list
    decisions, failed_decisions = verify_items(decisions_raw, lines)
    action_items, failed_actions = verify_items(action_items_raw, lines)
    blockers, failed_blockers = verify_items(blockers_raw, lines)
    all_failed = failed_decisions + failed_actions + failed_blockers

    # 7. Resolve dates deterministically (never let the LLM do the arithmetic)
    resolved_action_items: List[ActionItem] = []
    for ai in action_items:
        resolved = resolve_date_phrase(ai.date_basis, call_date_obj)
        ai.due_date = resolved.isoformat() if resolved else None
        resolved_action_items.append(ai)

    # 8. Compliance -- deterministic hard triggers + LLM soft-judgment layer
    special_triggers = detect_hard_triggers(lines)
    compliance_flags = classify_compliance(lines, ctx.policy_text)

    # 10. Sentiment / profanity / anger
    profanity_hits = [t for t in special_triggers if t.kind == "profanity"]
    sentiment = analyze_sentiment(lines, profanity_hits)

    # 9. Human review routing (rules engine + open-ended LLM pass)
    already_extracted_summary = (
        f"{len(decisions)} decisions, {len(resolved_action_items)} action items, "
        f"{len(blockers)} blockers, {len(compliance_flags)} compliance flags already captured."
    )
    human_review = build_human_review(
        lines=lines,
        action_items=resolved_action_items,
        blockers=blockers,
        compliance_flags=compliance_flags,
        special_triggers=special_triggers,
        failed_items=all_failed,
        sentiment=sentiment,
        already_extracted_summary=already_extracted_summary,
    )

    return CallReport(
        call_id=call_id,
        call_date=call_date,
        call_type=call_type,
        tag=tag,
        summary=summary,
        decisions=decisions,
        action_items=resolved_action_items,
        blockers=blockers,
        compliance_flags=compliance_flags,
        special_triggers=special_triggers,
        sentiment=sentiment,
        human_review=human_review,
    )
