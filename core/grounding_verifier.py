"""
Step 6: Grounding verifier -- BATCHED. Verifies all items for a category
in a single call instead of one call per item, to keep total request
count low.
"""
from __future__ import annotations
from typing import List, Tuple, Dict
from core.schema import TranscriptLine, Grounded
from core.llm_client import call_llm_json

VERIFY_SYSTEM = (
    "You are a strict fact-checker. You are given a list of claims, each with the exact "
    "transcript line(s) it claims to be based on. For EACH claim, decide ONLY whether "
    "those specific lines actually support that specific claim -- do not use outside "
    "knowledge, do not be lenient. "
    "\n\n"
    "ONE SPECIFIC EXCEPTION -- proposal + acknowledgment counts as a real commitment: "
    "if one speaker proposes terms in general form (e.g. amounts, a rough timeframe like "
    "'next month'), and the other speaker repeats those SAME core terms back while "
    "logging or noting them, ADDING more precision (e.g. turning 'next month' into "
    "'the 15th of next month') is NOT a contradiction or a change of terms -- it is "
    "normal clarification during confirmation. Adding a specific date/detail that is "
    "consistent with (not contradicting) the original proposal still counts as "
    "confirming the SAME commitment. Only treat it as unconfirmed if the second "
    "speaker's version actually conflicts with the first (different amount, different "
    "month, different condition) -- or if the second speaker merely says something "
    "vague like 'okay' or 'noted' without repeating any of the substance. "
    "\n\n"
    "Example that SHOULD pass: Speaker A says 'could I do $700 now and $700 next month?' "
    "and Speaker B says 'let me note that -- $700 today and $700 on the 15th of next "
    "month.' This is a confirmed commitment by Speaker A, restated with normal added "
    "precision by Speaker B -- treat this as supported. "
    "\n\n"
    'Return ONLY raw JSON: {"results": [{"index": 0, "supported": true|false, '
    '"reason": "<short sentence>"}, ...]} -- one entry per claim, in the same order '
    "given, using the 0-based index provided."
)


def _lines_by_no(lines: List[TranscriptLine]) -> Dict[int, TranscriptLine]:
    return {l.line_no: l for l in lines}


def check_lines_exist(item: Grounded, index: Dict[int, TranscriptLine]) -> bool:
    if not item.source_lines:
        return False
    return all(n in index for n in item.source_lines)


def verify_items(
    items: List[Grounded], lines: List[TranscriptLine]
) -> Tuple[List[Grounded], List[Grounded]]:
    index = _lines_by_no(lines)
    verified, failed = [], []

    candidates = []
    for item in items:
        if not check_lines_exist(item, index):
            item.confidence = 0.0
            failed.append(item)
        else:
            candidates.append(item)

    if not candidates:
        return verified, failed

    claim_blocks = []
    for i, item in enumerate(candidates):
        cited_text = "\n".join(f"{n}: {index[n].speaker}: {index[n].text}" for n in item.source_lines)
        claim_blocks.append(f"[{i}] Claim: \"{item.text}\"\nCited lines:\n{cited_text}")
    user = "\n\n".join(claim_blocks)

    result = call_llm_json(VERIFY_SYSTEM, user, max_tokens=2000)
    results_by_index = {r["index"]: r for r in result.get("results", [])}

    for i, item in enumerate(candidates):
        r = results_by_index.get(i)
        if r and r.get("supported"):
            item.confidence = 1.0
            verified.append(item)
        else:
            item.confidence = 0.0
            reason = r.get("reason", "no verification result returned") if r else "no verification result returned"
            item.text = f"{item.text}  [FAILED VERIFICATION: {reason}]"
            failed.append(item)

    return verified, failed
