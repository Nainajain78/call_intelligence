# Call Intelligence AI Agent

A structured pipeline that turns a call/meeting transcript into notes a
person can actually rely on: every claim cites the transcript lines it
came from, and anything uncertain, risky, or judgment-requiring is routed
to a human-review queue instead of being asserted as fact.

## Structure

```
call_intelligence/
  core/
    schema.py             Step 1  - output contract (pydantic models)
    transcription.py       Step 2  - ingestion, diarization, stable line numbers
    context_retrieval.py   Step 4  - policy/CRM context fed into extraction
    llm_client.py          shared Anthropic API wrapper (JSON-mode helper)
    extraction.py           Step 5  - focused LLM passes: decisions, action items, blockers
    grounding_verifier.py   Step 6  - mechanical + LLM entailment check on every citation
    date_resolver.py        Step 7  - deterministic relative-date resolution
    compliance.py           Step 8  - regex hard triggers + LLM soft-judgment layer
    sentiment.py            Step 10 - sentiment / profanity / anger (bonus)
    human_review.py         Step 9  - rules engine + open-ended LLM pass
    search.py               Step 11 - BM25 keyword search over transcripts (bonus)
    eval_harness.py          Step 13 - precision/recall/hallucination-rate scoring
    orchestrator.py          Step 12 - fixed pipeline wiring every stage together
  main.py                  runnable end-to-end demo (uses the debt-collection example)
  requirements.txt
```

## Running it

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python main.py
```

This runs the debt-collection example from the spec and prints the full
`CallReport` JSON, plus a search demo.

## What's real vs. mocked

Runs today without any external services, other than the Anthropic API:
- Transcript parsing / line numbering (`parse_text_transcript`)
- Date resolution (`date_resolver.py`) -- verified against the spec's
  own example: "the 15th of next month" from 2026-07-01 → `2026-08-15`,
  "by Friday" → `2026-07-03`.
- Hard-trigger detection (`compliance.py` Layer 1) -- cease-and-desist,
  legal mention, wrong number, profanity.
- BM25 keyword search (`search.py`).

Needs a real backend wired in before production:
- `transcription.transcribe_audio()` -- stub for a diarization/STT
  provider (AssemblyAI, Deepgram, Whisper+pyannote). Docstring shows the
  expected call shape.
- `context_retrieval.py` -- `POLICY_STORE` is a plain dict; swap for a
  vector DB (Chroma/pgvector) over your actual policy docs. `get_crm_context()`
  is a stub for your CRM's API.
- `search.py` semantic search -- `set_embeddings()` takes any embedding
  vectors you compute; not wired to a specific provider so you can pick
  one that matches your existing stack.

## Design decisions worth knowing about

- **Grounding is mechanical, not vibes.** Every extracted item goes through
  `grounding_verifier.py`, which (a) checks the cited line numbers actually
  exist, then (b) runs a *separate* narrow LLM call asking only "does this
  line support this claim, yes/no." Items that fail are dropped from the
  main report and pushed to human review -- never silently kept.

- **Dates are never LLM arithmetic.** The extraction prompt captures the
  literal phrase ("Friday", "the 15th of next month") and a deterministic
  `dateutil`-based resolver turns it into a calendar date. This is the
  single most common place transcript-summarizing LLMs get subtly wrong.

- **Hard compliance triggers can't be "argued out of" by the model.**
  Cease-and-desist, legal mentions, wrong-number, and profanity are caught
  by regex first (`compliance.py` Layer 1) and always produce a hit,
  independent of anything the LLM decides in Layer 2. The LLM can add
  context/severity but can't suppress the flag.

- **Fixed pipeline, not a free-roaming agent.** The orchestrator always
  runs the same steps in the same order. This trades some flexibility for
  auditability and testability -- you can point at exactly which stage
  produced (or dropped) any given item. Where more open-ended judgment is
  useful, it's scoped narrowly to the "anything else a reviewer would
  check" pass in `human_review.py`, not given control of the pipeline.

## Extending

- Add a new call type: add an entry to `POLICY_STORE` in
  `context_retrieval.py`, no other code changes needed.
- Add a new hard trigger: add a regex list under a new key in
  `TRIGGER_PATTERNS` in `compliance.py`.
- Run the eval harness: build a list of `GoldenCase` objects (see
  `eval_harness.py`), run each through `run_pipeline`, and call
  `run_eval_suite()` with the `(golden, report, n_failed, n_total)` tuples.
