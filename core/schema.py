"""
Step 1: Output schema.
Every stage in the pipeline fills part of this object. Nothing is allowed
into the final report unless it carries source_lines pointing back to the
transcript. This is the contract the rest of the system is built around.
"""
from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class TranscriptLine(BaseModel):
    line_no: int
    speaker: str
    text: str
    timestamp: Optional[str] = None  # e.g. "00:03:12"


class Grounded(BaseModel):
    """Mixin-style base: anything asserted about the call must cite lines."""
    text: str
    source_lines: List[int] = Field(default_factory=list)
    confidence: float = 1.0  # 0-1, set by the grounding verifier


class Decision(Grounded):
    pass


class ActionItem(Grounded):
    owner: Optional[str] = None
    due_date: Optional[str] = None          # ISO date, resolved
    date_basis: Optional[str] = None        # original phrase, e.g. "Friday"
    status: Literal["open", "blocked", "done"] = "open"


class Blocker(Grounded):
    pass


class ComplianceFlag(Grounded):
    severity: Literal["Red", "Yellow", "Green"]
    category: str  # e.g. "consent", "script_adherence", "cease_and_desist"


class SpecialTrigger(Grounded):
    kind: Literal[
        "cease_and_desist", "legal_mention", "regulatory_complaint", "wrong_number",
        "profanity", "sensitive_info"
    ]


class SentimentResult(BaseModel):
    overall: Literal["positive", "neutral", "negative", "mixed"]
    customer_sentiment: Optional[str] = None
    agent_sentiment: Optional[str] = None
    anger_detected: bool = False
    profanity_detected: bool = False
    notes: Optional[str] = None


class HumanReviewItem(BaseModel):
    reason: str
    related_item: Optional[str] = None     # free text pointer e.g. "action_item[0]"
    source_lines: List[int] = Field(default_factory=list)
    severity: Literal["low", "medium", "high"] = "medium"
    auto_flagged: bool = False             # True if a deterministic rule triggered this


class CallReport(BaseModel):
    call_id: str
    call_date: str                          # ISO date, needed for relative-date resolution
    call_type: str                          # sales / support / collections / standup / other
    tag: str
    summary: str

    decisions: List[Decision] = Field(default_factory=list)
    action_items: List[ActionItem] = Field(default_factory=list)
    blockers: List[Blocker] = Field(default_factory=list)
    compliance_flags: List[ComplianceFlag] = Field(default_factory=list)
    special_triggers: List[SpecialTrigger] = Field(default_factory=list)

    sentiment: Optional[SentimentResult] = None
    human_review: List[HumanReviewItem] = Field(default_factory=list)

    class Config:
        extra = "forbid"
