"""
Full pipeline test -- REQUIRES ANTHROPIC_API_KEY. Runs every fake call
through the actual LLM-backed pipeline and scores the result against the
golden cases using core/eval_harness.py.

Run:
    $env:ANTHROPIC_API_KEY="sk-ant-..."
    python test_full_pipeline.py
"""
import json
import sys
from core.transcription import parse_text_transcript
from core.orchestrator import run_pipeline
from core.eval_harness import run_eval_suite
from data.golden_cases import GOLDEN_CASES

results = []

for golden in GOLDEN_CASES:
    print(f"\nRunning pipeline on {golden.call_id} ...")
    lines = parse_text_transcript(golden.transcript_text)

    report = run_pipeline(
        call_id=golden.call_id,
        call_date=golden.call_date,
        call_type=golden.call_type,
        lines=lines,
    )

    n_total = len(report.decisions) + len(report.action_items) + len(report.blockers)
    n_failed = sum(1 for r in report.human_review if "grounding verification" in r.reason)

    results.append((golden, report, n_failed, max(n_total, 1)))

    with open(f"report_{golden.call_id}.json", "w") as f:
        json.dump(report.model_dump(), f, indent=2)
    print(f"  -> saved full report to report_{golden.call_id}.json")

    print(f"  tag: {report.tag}")
    print(f"  decisions: {len(report.decisions)}  action_items: {len(report.action_items)}  "
          f"blockers: {len(report.blockers)}")
    print(f"  triggers: {[t.kind for t in report.special_triggers]}")
    print(f"  human_review items: {len(report.human_review)}")

print("\n" + "=" * 60)
print("EVAL SUMMARY")
print("=" * 60)
eval_result = run_eval_suite(results)
print(json.dumps(eval_result["summary"], indent=2))

print("\nPer-case breakdown:")
for case_result in eval_result["per_case"]:
    print(json.dumps(case_result, indent=2))

summary = eval_result["summary"]
critical_failure = (
    summary["any_trigger_false_negatives"]
    or summary["avg_hallucination_rate"] > 0.1
)
if critical_failure:
    print("\nCRITICAL: hard-trigger false negatives or high hallucination rate detected.")
    sys.exit(1)

print("\nAll checks within acceptable range.")
sys.exit(0)
