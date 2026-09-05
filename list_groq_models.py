"""
Lists models currently available to your Groq API key.
Run:
    $env:GROQ_API_KEY="your-key"
    python list_groq_models.py
"""
import os
from groq import Groq

api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise SystemExit('Set GROQ_API_KEY first: $env:GROQ_API_KEY="your-key"')

client = Groq(api_key=api_key)
models = client.models.list()
print("Models available to this key:\n")
for m in models.data:
    print(" ", m.id)
