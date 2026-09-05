"""
Step 2: Ingestion & transcription. parse_text_transcript() assigns stable
line numbers to already-transcribed text. transcribe_audio() is a stub for
a real diarization/STT provider (AssemblyAI, Deepgram, Whisper+pyannote).
"""
from __future__ import annotations
import re
from typing import List
from core.schema import TranscriptLine


def parse_text_transcript(raw_text: str) -> List[TranscriptLine]:
    lines: List[TranscriptLine] = []
    pattern = re.compile(r"^\s*(?:(\d+)\s*:\s*)?([A-Za-z0-9_ ]{1,30}?):\s*(.+)$")
    auto_no = 0
    for raw_line in raw_text.strip().splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        m = pattern.match(raw_line)
        if not m:
            continue
        line_no_str, speaker, text = m.groups()
        auto_no += 1
        line_no = int(line_no_str) if line_no_str else auto_no
        lines.append(TranscriptLine(line_no=line_no, speaker=speaker.strip(), text=text.strip()))
    return lines


def transcribe_audio(audio_path: str) -> List[TranscriptLine]:
    raise NotImplementedError(
        "Wire this up to a diarization/STT provider (AssemblyAI, Deepgram, "
        "Whisper+pyannote, etc.)."
    )


def render_transcript_for_prompt(lines: List[TranscriptLine]) -> str:
    return "\n".join(f"{l.line_no}: {l.speaker}: {l.text}" for l in lines)