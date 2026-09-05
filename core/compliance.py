"""
Step 8: Compliance / coaching classification, hybrid approach.

Layer 1 -- deterministic regex/keyword matching for hard triggers
(cease-and-desist, legal mentions, regulatory complaint threats, wrong
number, profanity). These are too high-stakes to leave purely to LLM
judgment; they run first and ALWAYS produce a hit regardless of what
the model later decides.

Layer 2 -- LLM classifier for softer judgment calls (tone, script
adherence, Red/Yellow/Green), still required to cite lines.
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


COMPLIANCE_SYSTEM = (
    "You review a call transcript for compliance and coaching issues, given the "
    "applicable policy. For each observation (positive or risky), output a severity: "
    "Red (clear violation or serious risk), Yellow (borderline / needs a human's judgment), "
    "Green (good practice worth noting). Every item MUST include source_lines (exact "
    "transcript line numbers). Never invent a violation not supported by the cited lines. "
    "Write each observation in clean, third-person business language -- never copy the speaker's exact dialogue verbatim. Summarize what happened, do not quote it. "
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
    return [ComplianceFlag(**f) for f in result.get("flags", [])]

