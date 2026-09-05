"""
Step 5: Extraction.

Deliberately split into narrow, single-purpose passes (decisions,
action items, blockers, summary/tag) rather than one giant "extract
everything" prompt. Narrow prompts hallucinate less. Every prompt
carries the hard rule: no source_lines, no item.
"""
from __future__ import annotations
from typing import List
from core.schema import TranscriptLine, Decision, ActionItem, Blocker
from core.transcription import render_transcript_for_prompt
from core.llm_client import call_llm_json

GROUNDING_RULE = (
    "Hard rule: every item you output MUST include source_lines, a list of the exact "
    "transcript line numbers (integers) that support it. If you cannot point to specific "
    "line(s) that support a claim, do NOT include that item at all. Never invent an item, "
    "an owner, or a date that is not directly supported by the cited lines. "
    "\n\n"
    "IMPORTANT ON CITATIONS: when a commitment spans a negotiation between two speakers "
    "-- e.g. one party proposes something, and the other party confirms or restates it -- "
    "cite ALL of the lines involved in that exchange (e.g. [7, 8]), not just the final "
    "confirming line. A commitment made by Speaker A and then confirmed/restated back by "
    "Speaker B is grounded across BOTH lines together, not just the restatement alone. "
    "\n\n"
    "IMPORTANT ON WRITING STYLE -- write a clean, third-person, professional summary, "
    "NEVER copy the speaker's dialogue verbatim or near-verbatim. Do not reuse phrases "
    "like 'let me note that', 'I'll', 'could I', or quote marks -- rewrite the substance "
    "in plain business language, as a QA analyst would write it in a report. "
    "\n"
    "  BAD (dialogue copied): \"Let me note that -- $700 today and $700 on the 15th of "
    "next month\"\n"
    "  GOOD (clean summary): \"Consumer agreed to pay $700 immediately and $700 by "
    "August 15\"\n"
    "\n"
    "  BAD (dialogue copied): \"I am escalating the duplicate charge inquiry to our "
    "billing disputes team\"\n"
    "  GOOD (clean summary): \"Escalated the duplicate charge inquiry to the billing "
    "disputes team\"\n"
    "\n"
    "Every item's text field should read as a short, clear, third-person statement of "
    "fact -- never as a quoted line of speech, and never starting with 'I' as if the "
    "speaker were talking. "
    "\n\n"
    "Return ONLY raw JSON -- no markdown fences, no preamble, no commentary."
)


def _prompt_header(transcript_text: str, context_block: str) -> str:
    return (
        f"<context>\n{context_block}\n</context>\n\n"
        f"<transcript>\n{transcript_text}\n</transcript>\n"
    )


def extract_summary_and_tag(lines: List[TranscriptLine], call_type: str) -> tuple[str, str]:
    transcript_text = render_transcript_for_prompt(lines)
    system = (
        "You summarize call transcripts factually and concisely, in plain language, "
        "based only on what is present in the transcript. Write in clean third-person "
        "prose, never quoting dialogue verbatim. Return ONLY raw JSON."
    )
    user = (
        f"<transcript>\n{transcript_text}\n</transcript>\n\n"
        f"Call type: {call_type}\n\n"
        'Return JSON: {"tag": "<3-6 word tag>", "summary": "<2-4 sentence summary>"}'
    )
    result = call_llm_json(system, user)
    return result["tag"], result["summary"]


def extract_decisions(lines: List[TranscriptLine], context_block: str) -> List[Decision]:
    transcript_text = render_transcript_for_prompt(lines)
    system = (
        "You extract decisions that were explicitly made during a call. "
        f"{GROUNDING_RULE} "
        "A decision is something that was explicitly agreed, settled, or committed to "
        "-- e.g. 'Agreed to escalate the issue to billing disputes', 'Settled on a "
        "$700/$700 payment split'. It describes WHAT was decided, not the specific "
        "forward-looking task that follows from it -- that belongs in action items "
        "instead. Do not duplicate the action item's wording; state the decision "
        "itself, more briefly. "
        "If BOTH parties are agreeing to something (e.g. a payment plan), you may "
        "produce a single decision describing the mutual agreement, citing every line "
        "involved in reaching it."
    )
    user = (
        _prompt_header(transcript_text, context_block)
        + '\nReturn JSON: {"decisions": [{"text": "...", "source_lines": [int, ...]}]}\n'
    )
    result = call_llm_json(system, user)
    return [Decision(**d) for d in result.get("decisions", [])]


def extract_action_items(lines: List[TranscriptLine], context_block: str) -> List[ActionItem]:
    transcript_text = render_transcript_for_prompt(lines)
    system = (
        "You extract action items (concrete forward-looking commitments to future action) from "
        f"a call transcript. {GROUNDING_RULE} "
        "\n\n"
        "IMPORTANT -- capture commitments and deadlines from BOTH parties, not just the agent. "
        "If a customer proposes a commitment (e.g. 'could I do $700 now and $700 next month?') "
        "and the other party then confirms or restates it, that IS a real action item for the "
        "customer -- create it, citing both the proposing line and the confirming line together. "
        "Do not skip a party's commitment just because they didn't literally say 'I will' -- a "
        "proposal that gets confirmed back is an agreed commitment. Adding more precision when "
        "confirming (e.g. 'next month' becoming 'the 15th of next month') does not make it "
        "unconfirmed -- that is normal clarification, not a contradiction. "
        "\n\n"
        "If a customer states a deadline or demand (e.g. 'I want my refund by Monday'), that is "
        "still an action item -- capture it with owner set to whichever party is responsible for "
        "acting on it (often the agent/company), and date_basis set to the customer's stated phrase. "
        "\n\n"
        "Do not restate a decision verbatim as an action item -- an action item is the distinct, "
        "concrete NEXT STEP that follows from a decision, not a copy of the decision's wording. "
        "\n\n"
        "For owner: prefer a real name over a generic role label. If a speaker introduces "
        "themselves by name anywhere in the transcript (e.g. 'this is Sarah from...', 'this is "
        "Marcus calling...'), use that name (e.g. 'Sarah (Agent)') instead of just 'Agent'. If no "
        "name is ever given for that speaker, fall back to the role label exactly as it appears "
        "in the transcript ('Agent', 'Customer', 'Consumer', etc.) -- never invent a name that "
        "was not stated. "
        "\n\n"
        "For date_basis, capture the exact phrase used for timing (e.g. 'by Friday', 'by Monday', "
        "'next month') verbatim from the transcript; do not resolve it to a calendar date yourself, "
        "a downstream step does that."
    )
    user = (
        _prompt_header(transcript_text, context_block)
        + '\nReturn JSON: {"action_items": [{"text": "...", "owner": "... or null", '
        '"date_basis": "... or null", "source_lines": [int, ...]}]}\n'
    )
    result = call_llm_json(system, user)
    return [ActionItem(**a) for a in result.get("action_items", [])]


def extract_blockers(lines: List[TranscriptLine], context_block: str) -> List[Blocker]:
    transcript_text = render_transcript_for_prompt(lines)
    system = (
        "You extract blockers -- things explicitly stopping progress or leaving an issue "
        f"unresolved. {GROUNDING_RULE} "
        "\n\n"
        "A blocker is often the CORE unresolved issue itself (e.g. 'The disputed charge "
        "remains unresolved pending review by the billing disputes team'), not just a "
        "side-effect, threat, or warning mentioned near it. Before listing a secondary or "
        "tangential blocker, check whether the transcript's main unresolved problem is "
        "also captured as its own blocker -- if the call ends without the central issue "
        "being fixed, that itself is usually a blocker."
    )
    user = (
        _prompt_header(transcript_text, context_block)
        + '\nReturn JSON: {"blockers": [{"text": "...", "source_lines": [int, ...]}]}\n'
    )
    result = call_llm_json(system, user)
    return [Blocker(**b) for b in result.get("blockers", [])]
