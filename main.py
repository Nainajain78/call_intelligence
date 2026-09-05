"""
End-to-end demo, using the debt-collection example from the spec.

Requires ANTHROPIC_API_KEY to be set in the environment:
    export ANTHROPIC_API_KEY=sk-ant-...
    pip install -r requirements.txt
    python main.py
"""
import json
from core.transcription import parse_text_transcript
from core.orchestrator import run_pipeline
from core.search import TranscriptSearchIndex

EXAMPLE_TRANSCRIPT = """
1: Agent: Hi, this is Marcus from Alpine Recovery calling about your account. Is this James?
2: Consumer: Yeah, this is James.
3: Agent: This call is being recorded for quality purposes. Your account balance is $1,400, past due since May.
4: Consumer: I know, things have been tight. I lost my job in April.
5: Agent: I understand. We can work out a payment plan. What can you manage?
6: Agent: The standard plan would be $1,400 in one payment, or two payments of $700 each.
7: Consumer: That's still too much right now. Could I do $700 now and $700 next month?
8: Agent: Let me note that -- $700 today and $700 on the 15th of next month. I'll need a supervisor to approve the settlement split, I'll follow up by Friday.
9: Consumer: Okay, that works. Just don't call me at work anymore, please.
10: Agent: Understood, I'll note to only call this number after 6pm.
"""

def main():
    lines = parse_text_transcript(EXAMPLE_TRANSCRIPT)

    report = run_pipeline(
        call_id="call_2026_07_01_0007",
        call_date="2026-07-01",
        call_type="collections",
        lines=lines,
        customer_id="cust_00123",
    )

    print(json.dumps(report.model_dump(), indent=2))

    # Bonus: index + search demo
    index = TranscriptSearchIndex()
    index.add_call(report.call_id, report.call_date, lines)
    print("\n--- search: 'supervisor approval' ---")
    for hit in index.search("supervisor approval", top_k=3):
        print(hit)


if __name__ == "__main__":
    main()
