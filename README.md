# Call Intelligence AI Agent

A call/meeting intelligence system that turns a transcript into structured, trustworthy notes -- decisions, action items, blockers, compliance flags, and a human-review queue -- where every claim points back to the exact transcript line it came from, and anything uncertain is flagged for a human instead of being stated as fact.

Live demo: https://call-intelligence-lovat.vercel.app

## The core idea

Handing a transcript straight to an LLM and asking for a summary is fast, but unreliable -- models invent action items that were never agreed, guess at dates, and state serious things with full confidence and no proof. This project is built around one rule instead: nothing is asserted without a citation, and nothing uncertain is guessed at.

Every decision, action item, and compliance observation this system produces carries the exact line number(s) it is based on. If a claim cannot be traced back to a specific line, it does not make it into the final report -- it is dropped and routed to human review instead.

## What it produces, for every call

- A short tag and plain-language summary
- Decisions that were actually made
- Action items, each with an owner, a due date worked out from the conversation, and the exact lines it came from
- Blockers stopping progress
- Compliance observations marked Red, Yellow, or Green
- Sentiment analysis -- overall tone, anger, profanity detection
- Special triggers -- cease-and-desist requests, legal threats, regulatory complaints, wrong numbers
- A human-review queue for anything unclear, risky, or beyond what software should decide on its own
- Search across every transcript line

## Project structure

call_intelligence/
  core/                         The AI pipeline itself
    schema.py                   Data contract, every item must carry source_lines
    transcription.py            Parses raw text into numbered transcript lines
    context_retrieval.py        Pulls relevant policy/CRM context by call type
    llm_client.py                Single point of contact with the LLM provider
    extraction.py                Extracts decisions, action items, blockers
    grounding_verifier.py        Double-checks every citation is actually true
    date_resolver.py             Turns "by Friday" into a real calendar date
    compliance.py                Regex hard triggers plus LLM judgment layer
    sentiment.py                 Tone, anger, profanity detection
    human_review.py              Decides what needs a human to look at it
    search.py                    Keyword search across all transcripts
    eval_harness.py              Scores output against known-correct answers
    orchestrator.py              Runs every stage above, in a fixed order

  data/
    fake_transcripts.py          Sample test calls covering all call types and edge cases
    golden_cases.py               Hand-written correct answers for testing

  dashboard/
    backend/                     FastAPI server exposing the pipeline over HTTP
    frontend/                    React and Vite dashboard UI

  test_offline.py                Fast tests, no API calls, checks parsing, dates, regex
  test_full_pipeline.py          Full tests, runs the real LLM pipeline and scores it
  main.py                        Simple CLI demo using the spec worked example
  requirements.txt

## How to run it locally

### 1. Install dependencies

pip install -r requirements.txt

### 2. Get an API key

This project supports Groq (recommended, generous free tier), Google Gemini, or Anthropic Claude. Only core/llm_client.py needs to match whichever provider you use.

For Groq (default setup), set the environment variable GROQ_API_KEY to your key before running anything.

### 3. Run the offline tests first, no API cost

python test_offline.py

This checks transcript parsing, date math, compliance regex triggers, and search, all deterministic and free. Should show 33 passed, 0 failed.

### 4. Run the full pipeline demo

python main.py

This runs the spec own worked example, a debt-collection call, through the complete pipeline and prints the full structured report as JSON.

### 5. Run the test suite against sample calls

python test_full_pipeline.py

Runs 6 sample transcripts through the real pipeline and scores the output, precision, recall, hallucination rate, against hand-written correct answers.

## Running the dashboard locally

Terminal 1, backend:
cd dashboard/backend
pip install -r requirements.txt
set GROQ_API_KEY to your key
uvicorn main:app --reload --port 8000

Terminal 2, frontend:
cd dashboard/frontend
npm install
npm run dev

Open http://localhost:5173 -- you will see a sidebar of analyzed calls, click any one for the full breakdown (summary, decisions, action items, compliance, sentiment, human review), click View Transcript to see the original conversation, and click Analyze Call to upload a new transcript and run the real pipeline on it.

## What is real vs what is a stub

Fully working today:
- Transcript parsing and stable line numbering
- Date resolution, verified exactly against the spec own example: "the 15th of next month" from a 2026-07-01 call resolves to 2026-08-15, "by Friday" resolves to 2026-07-03
- Hard-trigger detection by regex: cease-and-desist, legal mention, regulatory complaint, wrong number, profanity, these always fire independent of any LLM judgment
- A deterministic recording-disclosure compliance check
- Two-pass grounding verification, a mechanical line-existence check plus an independent LLM entailment check with context-window support
- BM25 keyword search across transcripts
- Full dashboard with upload, transcript viewer, and citation click-through

Documented stubs, not wired to a real backend:
- transcription.transcribe_audio() expects a real speech-to-text and diarization provider such as Whisper, AssemblyAI, or Deepgram; currently only accepts pre-transcribed text
- context_retrieval.py POLICY_STORE is a plain dictionary for now, swap for a real vector database over your actual policy documents at scale
- search.py semantic search, set_embeddings() accepts any embedding vectors, not tied to a specific provider

## Key design decisions

Grounding is mechanical, not requested. Every extracted item is checked twice: once to confirm the cited line numbers actually exist, and once with a separate, independent LLM call asking only whether this specific line supports this specific claim, yes or no. Anything that fails is dropped from the main report and routed to human review, never silently kept.

Dates are never LLM arithmetic. The model only extracts the literal phrase someone said, such as "by Friday." A separate deterministic Python function resolves that into an actual calendar date, since this is exactly the kind of thing LLMs get subtly wrong.

Hard compliance triggers cannot be argued out of. Cease-and-desist, legal threats, regulatory complaints, wrong numbers, and profanity are caught by regex first and always produce a flag, regardless of what the LLM softer judgment layer decides.

Fixed pipeline, not a free-roaming agent. Every call runs through the same stages in the same order, trading some flexibility for auditability. You can always point at exactly which stage produced or dropped any given piece of output.

## Extending this project

- Add a new call type: add an entry to POLICY_STORE in context_retrieval.py
- Add a new hard trigger: add a regex list under a new key in TRIGGER_PATTERNS in compliance.py
- Add more test cases: add transcripts to data/fake_transcripts.py and their expected answers to data/golden_cases.py, then run test_full_pipeline.py
- Swap the LLM provider: edit only core/llm_client.py, every other module calls it through one shared interface, so no other file needs to change
