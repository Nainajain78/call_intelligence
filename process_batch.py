"""
Batch-processes a JSON array of {call_id, date, transcript[]} objects
through the REAL pipeline, writing outputs where the dashboard expects
them: report_<call_id>.json in the project root, and <call_id>.txt in
uploaded_calls/ (so "View source" excerpts work).

Run:
    $env:GROQ_API_KEY="your-key"
    python process_batch.py new_calls_batch.json
"""
import json
import sys
from pathlib import Path

from core.transcription import parse_text_transcript
from core.orchestrator import run_pipeline

ROOT = Path(__file__).parent
UPLOAD_DIR = ROOT / "uploaded_calls"
UPLOAD_DIR.mkdir(exist_ok=True)


def infer_call_type(transcript_text: str) -> str:
    t = transcript_text.lower()
    if any(k in t for k in ["loan", "overdue", "balance", "payment plan", "settlement", "mortgage", "underwriting"]):
        return "collections"
    return "support"


def main(batch_path: str):
    calls = json.loads(Path(batch_path).read_text(encoding="utf-8-sig"))
    print(f"Loaded {len(calls)} calls from {batch_path}\n")

    for entry in calls:
        call_id = entry["call_id"]
        call_date = entry["date"]
        transcript_text = "\n".join(entry["transcript"])
        call_type = infer_call_type(transcript_text)

        print(f"Processing {call_id} ({call_type})...")

        lines = parse_text_transcript(transcript_text)
        if not lines:
            print(f"  SKIPPED -- could not parse any lines for {call_id}")
            continue

        try:
            report = run_pipeline(
                call_id=call_id, call_date=call_date,
                call_type=call_type, lines=lines,
            )
        except Exception as e:
            print(f"  FAILED -- {e}")
            continue

        report_path = ROOT / f"report_{call_id}.json"
        report_path.write_text(json.dumps(report.model_dump(), indent=2), encoding="utf-8")

        transcript_path = UPLOAD_DIR / f"{call_id}.txt"
        transcript_path.write_text(transcript_text, encoding="utf-8")

        print(f"  -> saved {report_path.name} and {transcript_path.name}")
        print(f"  decisions={len(report.decisions)} action_items={len(report.action_items)} "
              f"triggers={[t.kind for t in report.special_triggers]} "
              f"human_review={len(report.human_review)}\n")

    print("Done. Refresh the dashboard (or restart the backend) to see the new calls.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_batch.py <path-to-batch.json>")
        sys.exit(1)
    main(sys.argv[1])

