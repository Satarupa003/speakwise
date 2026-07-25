import os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("GEMINI_API_KEY", "")
print(f"Key loaded: ...{key[-6:] if key else 'EMPTY!'} (length {len(key)})")

import google.generativeai as genai
genai.configure(api_key=key)

print("\n--- Models available to this key ---")
try:
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            print(" ", m.name)
except Exception as e:
    print("list_models failed:", e)

print("\n--- Test generation ---")
for name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-flash-lite", "gemini-flash-latest"]:
    try:
        r = genai.GenerativeModel(name).generate_content("Say OK")
        print(f"  {name}: SUCCESS → {r.text.strip()[:20]}")
        break
    except Exception as e:
        print(f"  {name}: FAILED → {str(e)[:100]}")