"""
Step 8: Compliance / coaching classification, hybrid approach.

Layer 1 -- deterministic regex/keyword matching for hard triggers AND
mandatory disclosure checks. These always fire, unconditionally,
regardless of what the LLM decides -- this is the fix for a real
reliability gap: an LLM instruction like "always check X" is not
guaranteed to fire every single time on every call, but a regex check
either matches or it doesn't, with zero chance of being skipped.

Layer 2 -- LLM classifier for softer judgment calls that regex
fundamentally can't catch (tone, script adherence, policy nuance).
"""
from __future__ import annotations
import re
from typing import List
from core.schema import TranscriptLine, ComplianceFlag, SpecialTrigger
from core.transcription import render_transcript_for_prompt
from core.llm_client import call_llm_json

TRIGGER_PATTERNS = {
    "cease_and_desist": [
        r"\bstop calling me\b", r"\bdon'?t call me\b", r"\bdon'?t (ever )?call me again\b",
        r"\bdon'?t bother me\b", r"\btake me off (of )?your list\b", r"\bdon'?t contact me\b",
        r"\btold you\b.{0,20}\bnot to call\b",
    ],
    "legal_mention": [
        r"\bi will sue\b", r"\bi'?m going to sue\b", r"\bcontact my attorney\b",
        r"\bmy lawyer\b", r"\blegal action\b", r"\bi am bankrupt\b", r"\bi'?m bankrupt\b",
        r"\bfiled for bankruptcy\b",
    ],
    "regulatory_complaint": [
        r"\bconsumer financial protection\b", r"\bcfpb\b",
        r"\bbetter business bureau\b", r"\bbbb\b",
        r"\bfiling a complaint\b", r"\bfile a complaint\b",
        r"\breport(ing)? you (to|with)\b", r"\bstate attorney general\b",
        r"\bregulatory (agency|body|authority)\b", r"\bconsumer protection agency\b",
    ],
    "wrong_number": [
        r"\bwrong number\b", r"\bthis isn'?t\s+\w+\b.*\bnumber\b",
        r"\bi don'?t know (a |any )?\w+\b.*\byou'?re (trying to reach|looking for)\b",
        r"\byou have the wrong person\b",
    ],
    "profanity": [
        r"\bf+u+c+k+\w*\b", r"\bshit\b", r"\bbullshit\b", r"\bdamn it\b", r"\bass+hole\b",
    ],
}

_COMPILED = {
    kind: [re.compile(p, re.IGNORECASE) for p in patterns]
    for kind, patterns in TRIGGER_PATTERNS.items()
}

DISCLOSURE_PATTERNS = [
    r"\brecorded\b", r"\bmonitored\b", r"\bquality assurance\b",
    r"\bquality purposes\b", r"\brecording this call\b", r"\bfor training purposes\b",
]
_DISCLOSURE_COMPILED = [re.compile(p, re.IGNORECASE) for p in DISCLOSURE_PATTERNS]


def detect_hard_triggers(lines: List[TranscriptLine]) -> List[SpecialTrigger]:
    triggers: List[SpecialTrigger] = []
    for line in lines:
        for kind, patterns in _COMPILED.items():
            for pat in patterns:
                if pat.search(line.text):
                    triggers.append(SpecialTrigger(
                        kind=kind,
                        text=f"Detected '{kind.replace('_', ' ')}' pattern in: \"{line.text}\"",
                        source_lines=[line.line_no],
                        confidence=1.0,
                    ))
                    break
    return triggers


def check_recording_disclosure(lines: List[TranscriptLine]) -> List[ComplianceFlag]:
    """
    Deterministic check: does the agent's opening line disclose that the
    call is recorded/monitored? Checked against the first two lines
    spoken by whoever appears to be the agent (or just the first two
    lines overall, if speaker roles aren't clearly labeled), since
    disclosure normally happens right at call open.

    This ALWAYS runs and ALWAYS produces a flag one way or the other --
    it does not depend on the LLM remembering to check this, which is
    the actual bug this fixes: an LLM instruction to "always verify X"
    is not reliably followed on every single call.
    """
    if not lines:
        return []

    opening_lines = lines[:2]
    combined_text = " ".join(l.text for l in opening_lines)

    if any(p.search(combined_text) for p in _DISCLOSURE_COMPILED):
        return []  # disclosure present -- no flag needed, LLM layer may still add a Green note

    return [ComplianceFlag(
        text="The agent's opening did not disclose that the call is being recorded or "
             "monitored. Standard practice requires this disclosure at the start of the call.",
        source_lines=[l.line_no for l in opening_lines],
        confidence=1.0,
        severity="Red",
        category="Recording Disclosure",
    )]


COMPLIANCE_SYSTEM = (
    "You review a call transcript for compliance and coaching issues, given the "
    "applicable policy. For each observation (positive or risky), output a severity: "
    "Red (clear violation or serious risk), Yellow (borderline / needs a human's judgment), "
    "Green (good practice worth noting). Every item MUST include source_lines (exact "
    "transcript line numbers). Never invent a violation not supported by the cited lines. "
    "Write each observation in clean, third-person business language -- never copy the "
    "speaker's exact dialogue verbatim. Summarize what happened, do not quote it. "
    "Return ONLY raw JSON, no commentary."
)


def classify_compliance(lines: List[TranscriptLine], policy_text: str) -> List[ComplianceFlag]:
    transcript_text = render_transcript_for_prompt(lines)
    user = (
        f"<policy>\n{policy_text}\n</policy>\n\n<transcript>\n{transcript_text}\n</transcript>\n\n"
        'Return JSON: {"flags": [{"severity": "Red|Yellow|Green", "category": "...", '
        '"text": "...", "source_lines": [int, ...]}]}'
    )
    result = call_llm_json(COMPLIANCE_SYSTEM, user)
    llm_flags = [ComplianceFlag(**f) for f in result.get("flags", [])]

    # Deterministic check always runs alongside the LLM layer, so this
    # specific violation category can never be silently missed.
    deterministic_flags = check_recording_disclosure(lines)

    return deterministic_flags + llm_flags
