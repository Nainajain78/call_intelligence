"""
Run this once to see which Gemini models your API key actually has access
to. Point CALL_INTEL_MODEL (in core/llm_client.py's default, or as an env
var) at one of the names printed here if gemini-3.6-flash 404s.

Run:
    python list_models.py
"""
import os
from google import genai

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise SystemExit('Set GEMINI_API_KEY first: $env:GEMINI_API_KEY="your-key"')

client = genai.Client(api_key=api_key)
print("Models available to this key that support generateContent:\n")
for m in client.models.list():
    actions = getattr(m, "supported_actions", None) or []
    if not actions or "generateContent" in actions:
        print(" ", m.name)