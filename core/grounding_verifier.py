"""
Step 6: Grounding verifier -- BATCHED, with a small context window.

Verifies all items for a category in a single call. In addition to the
exact cited source_lines, the verifier is also shown up to 2 lines of
context immediately BEFORE the first cited line -- this lets it
correctly resolve references like "the remaining balance" or "that
amount" back to where the actual figure was stated, even when the
extraction step's citation only covers the confirming/follow-up lines.
The context is clearly separated from the citation and does not, by
itself, count as grounding -- the claim must still be substantively
supported by the cited lines, using the context only to interpret them
correctly.
"""
from __future__ import annotations
from typing import List, Tuple, Dict
from core.schema import TranscriptLine, Grounded
from core.llm_client import call_llm_json

CONTEXT_LINES_BEFORE = 2

VERIFY_SYSTEM = (
    "You are a strict fact-checker. You are given a list of claims, each with the exact "
    "transcript line(s) it claims to be based on ('Cited lines'), plus a small amount of "
    "'Context' -- the 1-2 lines immediately before the citation, shown ONLY to help you "
    "correctly interpret references in the cited lines (like 'that amount', 'the balance', "
    "'this plan') back to whatever they refer to. "
    "\n\n"
    "IMPORTANT: the context is not itself a valid citation. A claim is supported if the "
    "cited lines, correctly interpreted USING the context to resolve any references, "
    "actually state or clearly imply the claim. Do not require the specific number or "
    "detail to be re-stated verbatim in the cited lines themselves if the cited lines "
    "clearly refer back to something the context already established -- e.g. if the "
    "context states 'the remaining balance of $8,500' and the cited line says 'that "
    "balance is pending review', the claim 'the $8,500 balance is pending review' IS "
    "supported, because the cited line's reference resolves unambiguously to the context. "
    "\n\n"
    "Do not use the context to justify a claim the cited lines don't actually address at "
    "all -- the context is for resolving references, not for supplying facts the cited "
    "lines never mention or allude to. "
    "\n\n"
    "ONE SPECIFIC EXCEPTION -- proposal + acknowledgment counts as a real commitment: "
    "if one speaker proposes terms in general form and the other speaker repeats those "
    "SAME core terms back while logging or noting them, ADDING more precision (e.g. "
    "'next month' becoming 'the 15th of next month') is NOT a contradiction -- it is "
    "normal clarification during confirmation. Only treat it as unconfirmed if the "
    "second speaker's version actually conflicts with the first, or is vague ('okay', "
    "'noted') without repeating any of the substance. "
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


def _build_context_block(item: Grounded, index: Dict[int, TranscriptLine]) -> str:
    """Returns up to CONTEXT_LINES_BEFORE lines immediately preceding the
    earliest cited line, for reference resolution only."""
    if not item.source_lines:
        return ""
    earliest = min(item.source_lines)
    context_line_nos = [
        n for n in range(earliest - CONTEXT_LINES_BEFORE, earliest)
        if n in index and n not in item.source_lines
    ]
    if not context_line_nos:
        return ""
    return "\n".join(f"{n}: {index[n].speaker}: {index[n].text}" for n in context_line_nos)


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
        context_text = _build_context_block(item, index)
        block = f"[{i}] Claim: \"{item.text}\"\nCited lines:\n{cited_text}"
        if context_text:
            block += f"\nContext (not a citation, for reference resolution only):\n{context_text}"
        claim_blocks.append(block)
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
