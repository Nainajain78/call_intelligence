"""
Step 9: Human-review routing.

A rules engine, not a prompt, decides what escalates. The deterministic
triggers (consent, cease-and-desist, legal, sensitive info) ALWAYS route
to review -- this must never depend on the model choosing to flag them.
On top of the hard rules, one more LLM pass is allowed to add open-ended
flags for anything a sensible reviewer would want to check, since the
list of possible concerns isn't fixed.
"""
from __future__ import annotations
from typing import List
from core.schema import (
    TranscriptLine, ActionItem, Blocker, ComplianceFlag, SpecialTrigger,
    Grounded, HumanReviewItem, SentimentResult,
)
from core.transcription import render_transcript_for_prompt
from core.llm_client import call_llm_json

VAGUE_DATE_MARKERS = {"soon", "later", "eventually", "at some point", None}

OPEN_ENDED_SYSTEM = (
    "You are a careful reviewer of a call transcript, alongside a set of items that were "
    "already extracted automatically. Flag anything ELSE a sensible reviewer would want a "
    "human to check -- things not already covered by the given items -- such as ambiguity, "
    "unclear consent, judgment calls beyond what software should decide, or anything that "
    "seems off. Do not repeat items already listed. Every flag MUST include source_lines. "
    "If nothing else needs review, return an empty list. Return ONLY raw JSON."
)


def build_human_review(
    lines: List[TranscriptLine],
    action_items: List[ActionItem],
    blockers: List[Blocker],
    compliance_flags: List[ComplianceFlag],
    special_triggers: List[SpecialTrigger],
    failed_items: List[Grounded],
    sentiment: SentimentResult,
    already_extracted_summary: str,
) -> List[HumanReviewItem]:
    review: List[HumanReviewItem] = []

    # --- Deterministic rules (always fire, independent of the model) -------
    for ai in action_items:
        if not ai.owner:
            review.append(HumanReviewItem(
                reason="Action item has no clear owner.", related_item=ai.text,
                source_lines=ai.source_lines, severity="high", auto_flagged=True,
            ))
        if ai.due_date is None and ai.date_basis:
            review.append(HumanReviewItem(
                reason=f"Due date could not be confidently resolved from phrase "
                       f"'{ai.date_basis}'.",
                related_item=ai.text, source_lines=ai.source_lines,
                severity="medium", auto_flagged=True,
            ))

    for trig in special_triggers:
        severity = "high" if trig.kind in (
            "cease_and_desist", "legal_mention", "regulatory_complaint", "sensitive_info"
        ) else "medium"
        review.append(HumanReviewItem(
            reason=f"{trig.kind.replace('_', ' ').title()} detected -- requires human handling.",
            related_item=trig.text, source_lines=trig.source_lines,
            severity=severity, auto_flagged=True,
        ))

    for flag in compliance_flags:
        if flag.severity in ("Red", "Yellow"):
            review.append(HumanReviewItem(
                reason=f"Compliance flag ({flag.severity}): {flag.category}.",
                related_item=flag.text, source_lines=flag.source_lines,
                severity="high" if flag.severity == "Red" else "medium",
                auto_flagged=True,
            ))

    for item in failed_items:
        review.append(HumanReviewItem(
            reason="Item failed automated grounding verification -- do not trust as-is.",
            related_item=item.text, source_lines=item.source_lines,
            severity="high", auto_flagged=True,
        ))

    if sentiment.anger_detected:
        review.append(HumanReviewItem(
            reason="Customer anger detected during call.",
            severity="low", auto_flagged=True,
        ))

    # --- Open-ended LLM pass for anything not covered above -----------------
    transcript_text = render_transcript_for_prompt(lines)
    user = (
        f"<transcript>\n{transcript_text}\n</transcript>\n\n"
        f"<already_flagged_summary>\n{already_extracted_summary}\n</already_flagged_summary>\n\n"
        'Return JSON: {"additional_flags": [{"reason": "...", "source_lines": [int, ...], '
        '"severity": "low|medium|high"}]}'
    )
    result = call_llm_json(OPEN_ENDED_SYSTEM, user)
    for f in result.get("additional_flags", []):
        review.append(HumanReviewItem(
            reason=f["reason"], source_lines=f.get("source_lines", []),
            severity=f.get("severity", "medium"), auto_flagged=False,
        ))

    return review
