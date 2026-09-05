import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Optional
import json
import shutil
import re
from datetime import date

from core.transcription import parse_text_transcript
from core.orchestrator import run_pipeline


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="Call Intelligence API",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

REPORT_DIR = BASE_DIR
UPLOAD_DIR = BASE_DIR / "uploaded_calls"

UPLOAD_DIR.mkdir(exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

def safe_filename(filename: str) -> str:
    filename = Path(filename).name
    filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
    return filename


def get_call_id_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    if stem.startswith("call_"):
        return stem
    return f"call_{stem}"


def load_json_report(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Invalid JSON report: {path.name}")


def save_json_report(call_id: str, report: dict):
    report_path = REPORT_DIR / f"report_{call_id}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return report_path


def find_transcript_file(call_id: str) -> Optional[Path]:
    possible_dirs = [UPLOAD_DIR, BASE_DIR / "data"]
    normalized_id = call_id.lower().replace("call_", "")
    for directory in possible_dirs:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".txt", ".transcript", ".text"}:
                continue
            stem = path.stem.lower()
            if normalized_id in stem:
                return path
    return None


def read_transcript_lines(call_id: str):
    path = find_transcript_file(call_id)
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_lines = f.readlines()
    except Exception:
        return {}

    result = {}
    for raw in raw_lines:
        line = raw.strip()
        if not line:
            continue
        match = re.match(r"^\s*(\d+)\s*:\s*(.*)$", line)
        if match:
            number = int(match.group(1))
            text = match.group(2).strip()
            result[number] = text
    return result


def add_source_excerpts(report: dict):
    call_id = report.get("call_id")
    transcript_lines = read_transcript_lines(call_id)
    if not transcript_lines:
        return report

    sections = [
        "decisions", "action_items", "blockers",
        "compliance_flags", "special_triggers", "human_review",
    ]

    for section in sections:
        items = report.get(section, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            source_lines = item.get("source_lines", [])
            excerpts = []
            for line_number in source_lines:
                try:
                    number = int(line_number)
                except (TypeError, ValueError):
                    continue
                if number in transcript_lines:
                    excerpts.append({"line": number, "text": transcript_lines[number]})
            item["source_excerpts"] = excerpts

    return report


def calculate_summary(report: dict):
    compliance = report.get("compliance_flags", [])
    red = sum(1 for item in compliance if str(item.get("severity", "")).lower() == "red")
    yellow = sum(1 for item in compliance if str(item.get("severity", "")).lower() == "yellow")
    green = sum(1 for item in compliance if str(item.get("severity", "")).lower() == "green")
    reviews = report.get("human_review", [])

    return {
        "decisions": len(report.get("decisions", [])),
        "action_items": len(report.get("action_items", [])),
        "blockers": len(report.get("blockers", [])),
        "human_review": len(reviews),
        "compliance_flags": len(compliance),
        "red_flags": red,
        "yellow_flags": yellow,
        "green_flags": green,
        "triggers": len(report.get("special_triggers", [])),
    }


def infer_call_type(transcript_text: str, fallback: str) -> str:
    if fallback and fallback != "general":
        return fallback
    t = transcript_text.lower()
    if any(k in t for k in ["loan", "overdue", "balance", "payment plan",
                             "settlement", "mortgage", "underwriting", "collections"]):
        return "collections"
    if any(k in t for k in ["discount", "proposal", "contract", "pricing"]):
        return "sales"
    if any(k in t for k in ["standup", "sprint", "deploy", "pr is up"]):
        return "standup"
    return "support"


def normalize_transcript_field(value) -> Optional[str]:
    """Transcript field may be a single string ('1: A: hi\\n2: B: hi') or a
    list of per-line strings (['1: A: hi', '2: B: hi']). Normalize to one string."""
    if value is None:
        return None
    if isinstance(value, list):
        return "\n".join(str(v) for v in value)
    if isinstance(value, str):
        return value
    return None


def run_one_call(call_id: str, call_date: str, call_type: str, transcript_text: str) -> dict:
    """Runs the real pipeline on one transcript and persists the outputs
    exactly where the dashboard expects them."""
    lines = parse_text_transcript(transcript_text)
    if not lines:
        raise ValueError(f"Could not parse any lines for '{call_id}'. "
                          f"Expected format: '1: Speaker: text' per line.")

    report = run_pipeline(
        call_id=call_id, call_date=call_date,
        call_type=call_type, lines=lines, customer_id=None,
    )
    report_data = report.model_dump() if hasattr(report, "model_dump") else report

    transcript_destination = UPLOAD_DIR / f"{call_id}.txt"
    transcript_destination.write_text(transcript_text, encoding="utf-8")

    report_data = add_source_excerpts(report_data)
    save_json_report(call_id, report_data)
    report_data["_dashboard_stats"] = calculate_summary(report_data)
    return report_data


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def root():
    return {"status": "online", "message": "Call Intelligence API is running"}


# ============================================================
# GET ALL CALLS
# ============================================================

@app.get("/api/calls")
def get_calls():
    reports = []
    for file in sorted(REPORT_DIR.glob("report_*.json")):
        try:
            data = load_json_report(file)
            reports.append({
                "call_id": data.get("call_id", file.stem.replace("report_", "")),
                "call_date": data.get("call_date"),
                "call_type": data.get("call_type"),
                "tag": data.get("tag", "Unknown"),
                "summary": data.get("summary", ""),
                "decision_count": len(data.get("decisions", [])),
                "action_item_count": len(data.get("action_items", [])),
                "blocker_count": len(data.get("blockers", [])),
                "human_review_count": len(data.get("human_review", [])),
                "compliance_count": len(data.get("compliance_flags", [])),
                "trigger_count": len(data.get("special_triggers", [])),
                "sentiment": data.get("sentiment", {}),
                "_file_mtime": file.stat().st_mtime,
            })
        except Exception as e:
            print(f"Could not load {file}: {e}")

    # Sort newest-first: primarily by call_date (from the transcript itself),
    # then by file modification time as a tie-breaker so calls sharing the
    # same date/title (e.g. re-tested "v2" variants) still order predictably
    # by when they were actually analyzed, rather than jumping around.
    reports.sort(
        key=lambda r: (r.get("call_date") or "", r.get("_file_mtime") or 0),
        reverse=True,
    )
    for r in reports:
        r.pop("_file_mtime", None)

    return reports


# ============================================================
# GET ONE COMPLETE CALL
# ============================================================

@app.get("/api/calls/{call_id}")
def get_call(call_id: str):
    report_path = REPORT_DIR / f"report_{call_id}.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail=f"Report not found for {call_id}")

    report = load_json_report(report_path)
    report = add_source_excerpts(report)
    report["_dashboard_stats"] = calculate_summary(report)
    return report


# ============================================================
# GET TRANSCRIPT
# ============================================================

@app.get("/api/calls/{call_id}/transcript")
def get_transcript(call_id: str):
    transcript_lines = read_transcript_lines(call_id)
    if not transcript_lines:
        raise HTTPException(status_code=404, detail="Original transcript not found")
    return {
        "call_id": call_id,
        "lines": [{"line": n, "text": t} for n, t in sorted(transcript_lines.items())],
    }


# ============================================================
# UPLOAD + RUN PIPELINE
# Handles: plain .txt transcripts, single-call JSON, AND
# multi-call batch JSON arrays (like [{call_id, date, transcript}, ...]).
# ============================================================

@app.post("/api/analyze")
async def analyze_call(
    file: UploadFile = File(...),
    call_type: str = Form("general"),
    call_date: Optional[str] = Form(None),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    filename = safe_filename(file.filename)
    extension = Path(filename).suffix.lower()

    if extension not in {".txt", ".text", ".transcript", ".json"}:
        raise HTTPException(
            status_code=400,
            detail="Currently supported: .txt, .text, .transcript and .json",
        )

    destination = UPLOAD_DIR / filename
    try:
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save upload: {e}")

    default_call_date = call_date or date.today().isoformat()
    processed = []
    errors = []

    # -------------------- .txt / .text / .transcript --------------------
    if extension != ".json":
        try:
            transcript_text = destination.read_text(encoding="utf-8")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not read uploaded file: {e}")

        call_id = get_call_id_from_filename(filename)
        resolved_type = infer_call_type(transcript_text, call_type)
        try:
            report_data = run_one_call(call_id, default_call_date, resolved_type, transcript_text)
            processed.append(call_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI pipeline failed for '{call_id}': {e}")

        return {
            "success": True,
            "message": "Call analyzed successfully",
            "call_id": call_id,
            "processed_call_ids": processed,
            "report": report_data,
        }

    # -------------------------- .json --------------------------
    try:
        raw_text = destination.read_text(encoding="utf-8-sig")
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Uploaded JSON is invalid: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read uploaded file: {e}")

    # Case 1: a batch -- a list of call objects
    if isinstance(parsed, list):
        if not parsed:
            raise HTTPException(status_code=400, detail="Uploaded JSON array is empty.")

        for i, entry in enumerate(parsed):
            if not isinstance(entry, dict):
                errors.append(f"Item {i}: not an object, skipped.")
                continue

            transcript_text = normalize_transcript_field(
                entry.get("transcript") or entry.get("text") or entry.get("conversation")
            )
            if not transcript_text:
                errors.append(f"Item {i}: no 'transcript' field found, skipped.")
                continue

            entry_call_id = entry.get("call_id") or get_call_id_from_filename(f"{filename}_{i}")
            entry_call_date = entry.get("date") or entry.get("call_date") or default_call_date
            resolved_type = infer_call_type(transcript_text, entry.get("call_type") or call_type)

            try:
                run_one_call(entry_call_id, entry_call_date, resolved_type, transcript_text)
                processed.append(entry_call_id)
            except Exception as e:
                errors.append(f"{entry_call_id}: {e}")

        if not processed:
            raise HTTPException(status_code=500, detail=f"No calls could be processed. Errors: {errors}")

        return {
            "success": True,
            "message": f"Processed {len(processed)} of {len(parsed)} calls.",
            "processed_call_ids": processed,
            "errors": errors,
        }

    # Case 2: a single call object -- {"transcript": ..., "call_id": ..., ...}
    elif isinstance(parsed, dict):
        transcript_text = normalize_transcript_field(
            parsed.get("transcript") or parsed.get("text") or parsed.get("conversation")
        )
        if not transcript_text:
            raise HTTPException(
                status_code=400,
                detail="JSON must contain a 'transcript' (string or list of lines), 'text', or 'conversation' field.",
            )

        call_id = parsed.get("call_id") or get_call_id_from_filename(filename)
        resolved_call_date = parsed.get("date") or parsed.get("call_date") or default_call_date
        resolved_type = infer_call_type(transcript_text, parsed.get("call_type") or call_type)

        try:
            report_data = run_one_call(call_id, resolved_call_date, resolved_type, transcript_text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI pipeline failed for '{call_id}': {e}")

        return {
            "success": True,
            "message": "Call analyzed successfully",
            "call_id": call_id,
            "processed_call_ids": [call_id],
            "report": report_data,
        }

    else:
        raise HTTPException(status_code=400, detail="Uploaded JSON must be an object or an array of objects.")


# ============================================================
# LEGACY UPLOAD ENDPOINT
# ============================================================

@app.post("/api/upload")
async def upload_call(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    filename = safe_filename(file.filename)
    destination = UPLOAD_DIR / filename

    try:
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    return {"message": "File uploaded successfully", "filename": filename}
