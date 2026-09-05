"""
Golden cases: hand-written "correct answers" for each fake transcript,
used with core/eval_harness.py to score the pipeline's actual output
against what a human would expect.

Expected text doesn't need to match word-for-word -- eval_harness.py uses
fuzzy matching -- but it should capture the same underlying fact.
"""
from core.eval_harness import GoldenCase
from data.fake_transcripts import (
    COLLECTIONS_CALL, COLLECTIONS_ESCALATION_CALL, SUPPORT_CALL,
    SALES_CALL, STANDUP_CALL, AMBIGUOUS_CALL,
)

GOLDEN_CASES = [
    GoldenCase(
        call_id=COLLECTIONS_CALL["call_id"],
        call_date=COLLECTIONS_CALL["call_date"],
        call_type=COLLECTIONS_CALL["call_type"],
        transcript_text=COLLECTIONS_CALL["transcript"],
        expected_decisions=[
            "Consumer agreed to pay $700 now and $700 on the 15th of next month",
        ],
        expected_action_items=[
            "Consumer to pay second $700 installment on 2026-08-15",
            "Agent to follow up on supervisor approval for settlement split by 2026-07-03",
        ],
        expected_triggers=["cease_and_desist"],
    ),
    GoldenCase(
        call_id=COLLECTIONS_ESCALATION_CALL["call_id"],
        call_date=COLLECTIONS_ESCALATION_CALL["call_date"],
        call_type=COLLECTIONS_ESCALATION_CALL["call_type"],
        transcript_text=COLLECTIONS_ESCALATION_CALL["transcript"],
        expected_decisions=[
            "Agent agreed to pause the account pending bankruptcy verification",
        ],
        expected_action_items=[
            "Agent to escalate account to a supervisor today",
        ],
        expected_triggers=["cease_and_desist", "legal_mention", "profanity"],
    ),
    GoldenCase(
        call_id=SUPPORT_CALL["call_id"],
        call_date=SUPPORT_CALL["call_date"],
        call_type=SUPPORT_CALL["call_type"],
        transcript_text=SUPPORT_CALL["transcript"],
        expected_decisions=[],
        expected_action_items=[
            "Agent to escalate logout issue to engineering",
            "Agent to check with manager about account credit",
        ],
        expected_triggers=["wrong_number"],
    ),
    GoldenCase(
        call_id=SALES_CALL["call_id"],
        call_date=SALES_CALL["call_date"],
        call_type=SALES_CALL["call_type"],
        transcript_text=SALES_CALL["transcript"],
        expected_decisions=[
            "Agent offered prospect a 30% discount to sign this week",
        ],
        expected_action_items=[
            "Agent to send contract by tomorrow morning",
        ],
        expected_triggers=[],
    ),
    GoldenCase(
        call_id=STANDUP_CALL["call_id"],
        call_date=STANDUP_CALL["call_date"],
        call_type=STANDUP_CALL["call_type"],
        transcript_text=STANDUP_CALL["transcript"],
        expected_decisions=[
            "Team decided to go with option B for the onboarding flow",
        ],
        expected_action_items=[
            "Priya to review Alex's PR today",
            "Sam to ping DevOps about staging deploy API key today",
            "Alex to start on onboarding flow option B tomorrow",
        ],
        expected_triggers=[],
    ),
    GoldenCase(
        call_id=AMBIGUOUS_CALL["call_id"],
        call_date=AMBIGUOUS_CALL["call_date"],
        call_type=AMBIGUOUS_CALL["call_type"],
        transcript_text=AMBIGUOUS_CALL["transcript"],
        expected_decisions=[],
        expected_action_items=[],
        expected_triggers=[],
    ),
]
