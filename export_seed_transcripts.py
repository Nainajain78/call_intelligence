"""
One-time script: writes each seed transcript in data/fake_transcripts.py
out to uploaded_calls/<call_id>.txt, so the dashboard backend's
find_transcript_file() can locate them and show real source excerpts
for the original 6 calls (not just newly uploaded ones).
"""
from pathlib import Path
from data.fake_transcripts import ALL_FAKE_CALLS

out_dir = Path("uploaded_calls")
out_dir.mkdir(exist_ok=True)

for call in ALL_FAKE_CALLS:
    path = out_dir / f"{call['call_id']}.txt"
    path.write_text(call["transcript"].strip(), encoding="utf-8")
    print(f"Wrote {path}")
