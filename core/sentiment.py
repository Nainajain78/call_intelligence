"""
Step 10: Sentiment / profanity / anger (bonus feature).

Kept separate from compliance Red/Yellow/Green -- "customer is angry" and
"agent violated policy" are different axes and shouldn't be conflated into
one score. Profanity detection is cross-checked against the deterministic
layer in compliance.py so it doesn't rely purely on the LLM's say-so.
"""
from __future__ import annotations
from typing import List
from core.schema import TranscriptLine, SentimentResult, SpecialTrigger
from core.transcription import render_transcript_for_prompt
from core.llm_client import call_llm_json

SENTIMENT_SYSTEM = (
    "You analyze the emotional tone of a call transcript. Judge sentiment per speaker "
    "and overall. Flag anger only if there is clear textual evidence (raised tone implied "
    "by word choice, explicit frustration, repeated complaints), not just a negative topic. "
    "Return ONLY raw JSON, no commentary."
)


def analyze_sentiment(
    lines: List[TranscriptLine], profanity_triggers: List[SpecialTrigger]
) -> SentimentResult:
    transcript_text = render_transcript_for_prompt(lines)
    user = (
        f"<transcript>\n{transcript_text}\n</transcript>\n\n"
        'Return JSON: {"overall": "positive|neutral|negative|mixed", '
        '"customer_sentiment": "...", "agent_sentiment": "...", '
        '"anger_detected": true|false, "notes": "<one short sentence>"}'
    )
    result = call_llm_json(SENTIMENT_SYSTEM, user)
    return SentimentResult(
        overall=result["overall"],
        customer_sentiment=result.get("customer_sentiment"),
        agent_sentiment=result.get("agent_sentiment"),
        anger_detected=bool(result.get("anger_detected")),
        # profanity comes from the deterministic layer, not the LLM's opinion
        profanity_detected=len(profanity_triggers) > 0,
        notes=result.get("notes"),
    )
