"""
Call Intelligence Dashboard -- backend.

Serves the dashboard UI and exposes the pipeline over HTTP:
  GET  /                          -> dashboard page
  GET  /api/calls                 -> list of all calls + their report stats
  GET  /api/calls/<call_id>       -> full report + transcript for one call
  POST /api/upload                -> run the REAL pipeline on a pasted transcript
  GET  /api/search?q=...          -> keyword search across all transcripts

Reads/writes report_<call_id>.json files in the project root (same files
test_full_pipeline.py produces), and keeps uploaded calls in
uploaded_calls.json so they persist across restarts.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from flask import Flask, jsonify, render_template, request

from core.transcription import parse_text_transcript
from core.orchestrator import run_pipeline
from core.search import TranscriptSearchIndex
from data.fake_transcripts import ALL_FAKE_CALLS

app = Flask(__name__)

ROOT = Path(__file__).parent
UPLOADED_CALLS_FILE = ROOT / "uploaded_calls.json"


def load_uploaded_calls():
    if not UPLOADED_CALLS_FILE.exists():
        return []
    try:
        return json.loads(UPLOADED_CALLS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_uploaded_calls(calls):
    UPLOADED_CALLS_FILE.write_text(json.dumps(calls, indent=2), encoding="utf-8")


def all_known_calls():
    """Fake seed calls + anything uploaded through the dashboard."""
    return ALL_FAKE_CALLS + load_uploaded_calls()


def calls_by_id():
    return {c["call_id"]: c for c in all_known_calls()}


def report_path(call_id: str) -> Path:
    return ROOT / f"report_{call_id}.json"


def load_report(call_id: str):
    p = report_path(call_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def get_triggers(report: dict):
    """Supports both 'special_triggers' and 'triggers' key names."""
    if not report:
        return []
    return report.get("special_triggers", report.get("triggers", []))


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/calls")
def list_calls():
    out = []
    for call in all_known_calls():
        report = load_report(call["call_id"])
        stripped = call["transcript"].strip().splitlines()
        preview = stripped[0][:90] if stripped else ""

        if report:
            out.append({
                "call_id": call["call_id"],
                "call_date": call["call_date"],
                "call_type": call["call_type"],
                "preview": preview,
                "tag": report.get("tag", ""),
                "summary": report.get("summary", ""),
                "decision_count": len(report.get("decisions", [])),
                "action_item_count": len(report.get("action_items", [])),
                "blocker_count": len(report.get("blockers", [])),
                "human_review_count": len(report.get("human_review", [])),
                "compliance_flags": report.get("compliance_flags", []),
                "triggers": [t.get("kind") for t in get_triggers(report)],
                "analyzed": True,
            })
        else:
            out.append({
                "call_id": call["call_id"],
                "call_date": call["call_date"],
                "call_type": call["call_type"],
                "preview": preview,
                "tag": None,
                "summary": None,
                "decision_count": 0,
                "action_item_count": 0,
                "blocker_count": 0,
                "human_review_count": 0,
                "compliance_flags": [],
                "triggers": [],
                "analyzed": False,
            })
    return jsonify(out)


@app.route("/api/calls/<call_id>")
def get_call(call_id):
    call = calls_by_id().get(call_id)
    if not call:
        return jsonify({"error": f"No call found with id '{call_id}'."}), 404

    lines = parse_text_transcript(call["transcript"])
    report = load_report(call_id)

    return jsonify({
        "call_id": call_id,
        "call_date": call["call_date"],
        "call_type": call["call_type"],
        "transcript_lines": [l.model_dump() for l in lines],
        "report": report,  # may be null if not yet analyzed
    })


@app.route("/api/upload", methods=["POST"])
def upload_call():
    """
    Runs the REAL pipeline (parse_text_transcript + run_pipeline) on a
    pasted transcript. Audio upload is not wired to a transcription
    backend yet -- see note in the response if audio is submitted.
    """
    data = request.get_json(force=True, silent=True) or {}
    transcript_text = data.get("transcript_text", "").strip()
    call_id = data.get("call_id", "").strip()
    call_date = data.get("call_date", "").strip()
    call_type = data.get("call_type", "support").strip()
    customer_id = data.get("customer_id") or None

    if not transcript_text:
        return jsonify({"error": "transcript_text is required. Audio transcription is "
                                  "not wired to a backend yet -- paste a text transcript "
                                  "instead (see core/transcription.py transcribe_audio())."}), 400
    if not call_id:
        return jsonify({"error": "call_id is required."}), 400
    if not call_date:
        return jsonify({"error": "call_date is required (YYYY-MM-DD)."}), 400

    if not os.environ.get("GROQ_API_KEY") and not os.environ.get("GEMINI_API_KEY") \
       and not os.environ.get("ANTHROPIC_API_KEY"):
        return jsonify({"error": "No LLM API key is set in this terminal session."}), 400

    lines = parse_text_transcript(transcript_text)
    if not lines:
        return jsonify({"error": "Could not parse any lines from that transcript. "
                                  "Expected format: '1: Speaker: text' per line."}), 400

    try:
        report = run_pipeline(
            call_id=call_id, call_date=call_date, call_type=call_type,
            lines=lines, customer_id=customer_id,
        )
    except Exception as e:
        return jsonify({"error": f"Pipeline failed: {e}"}), 500

    report_path(call_id).write_text(json.dumps(report.model_dump(), indent=2), encoding="utf-8")

    uploaded = load_uploaded_calls()
    uploaded = [c for c in uploaded if c["call_id"] != call_id]  # replace if re-uploaded
    uploaded.append({
        "call_id": call_id, "call_date": call_date, "call_type": call_type,
        "customer_id": customer_id, "transcript": transcript_text,
    })
    save_uploaded_calls(uploaded)

    return jsonify(report.model_dump())


@app.route("/api/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    idx = TranscriptSearchIndex()
    for call in all_known_calls():
        idx.add_call(call["call_id"], call["call_date"], parse_text_transcript(call["transcript"]))

    results = idx.search(query, top_k=20)
    return jsonify(results)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
