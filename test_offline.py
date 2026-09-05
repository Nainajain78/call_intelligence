"""
Offline tests -- NO API key required. These check every deterministic
piece of the pipeline: parsing, date resolution, hard-trigger regexes,
and search. Run this FIRST, before spending any API calls, since if
something's broken here it'll break everything downstream too.

Run:
    python test_offline.py
"""
import sys
from datetime import date
from core.transcription import parse_text_transcript
from core.date_resolver import resolve_date_phrase
from core.compliance import detect_hard_triggers
from core.search import TranscriptSearchIndex
from data.fake_transcripts import ALL_FAKE_CALLS, COLLECTIONS_CALL, COLLECTIONS_ESCALATION_CALL, SUPPORT_CALL

passed = 0
failed = 0


def check(label: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}  {detail}")


print("=== 1. Transcript parsing ===")
for call in ALL_FAKE_CALLS:
    lines = parse_text_transcript(call["transcript"])
    check(f"{call['call_id']}: parses to >0 lines", len(lines) > 0)
    line_nos = [l.line_no for l in lines]
    check(f"{call['call_id']}: line numbers are unique", len(line_nos) == len(set(line_nos)))
    check(f"{call['call_id']}: line numbers ascending", line_nos == sorted(line_nos))

print("\n=== 2. Date resolution (against known-correct answers) ===")
d = date(2026, 7, 1)
cases = [
    ("the 15th of next month", date(2026, 8, 15)),
    ("by Friday", date(2026, 7, 3)),
    ("next month", date(2026, 8, 1)),
    ("tomorrow", date(2026, 7, 2)),
    ("in 2 weeks", date(2026, 7, 15)),
    ("today", date(2026, 7, 1)),
]
for phrase, expected in cases:
    got = resolve_date_phrase(phrase, d)
    check(f"'{phrase}' -> {expected}", got == expected, f"got {got}")

print("\n=== 3. Hard compliance triggers ===")
lines = parse_text_transcript(COLLECTIONS_CALL["transcript"])
triggers = {t.kind for t in detect_hard_triggers(lines)}
check("collections call: cease_and_desist detected", "cease_and_desist" in triggers)

lines2 = parse_text_transcript(COLLECTIONS_ESCALATION_CALL["transcript"])
triggers2 = {t.kind for t in detect_hard_triggers(lines2)}
check("escalation call: cease_and_desist detected", "cease_and_desist" in triggers2)
check("escalation call: legal_mention detected", "legal_mention" in triggers2)
check("escalation call: profanity detected", "profanity" in triggers2)

lines3 = parse_text_transcript(SUPPORT_CALL["transcript"])
triggers3 = {t.kind for t in detect_hard_triggers(lines3)}
check("support call: wrong_number detected", "wrong_number" in triggers3)

from data.fake_transcripts import STANDUP_CALL
lines4 = parse_text_transcript(STANDUP_CALL["transcript"])
triggers4 = {t.kind for t in detect_hard_triggers(lines4)}
check("standup call: no false-positive triggers", len(triggers4) == 0, f"got {triggers4}")

print("\n=== 4. Search index ===")
idx = TranscriptSearchIndex()
for call in ALL_FAKE_CALLS:
    idx.add_call(call["call_id"], call["call_date"], parse_text_transcript(call["transcript"]))
results = idx.search("supervisor approval")
check("search returns results for 'supervisor approval'", len(results) > 0)
check(
    "relevant call appears in top results",
    any(r["call_id"] == "call_collections_001" for r in results[:3]),
    f"got {[r['call_id'] for r in results[:3]]}",
)

results_sue = idx.search("sue attorney")
check("search finds legal mention call", any(r["call_id"] == "call_collections_002" for r in results_sue))

print(f"\n{'='*40}\n{passed} passed, {failed} failed\n{'='*40}")
sys.exit(1 if failed else 0)
