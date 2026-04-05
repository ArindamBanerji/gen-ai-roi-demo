# scripts/collect_tab_content.py
# Run from repo root: python scripts/collect_tab_content.py
# Requires: backend running at localhost:8000

import requests, json, sys
from pathlib import Path

BASE = "http://localhost:8000"
DRIVE_PATH = Path(r"G:\My Drive\public-files\gen-ai-roi\experiments\tab_content.json")

tabs = {}
for n in range(1, 6):
    url = f"{BASE}/api/soc/tab/{n}/content"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            print(f"  Tab {n}: WARNING — empty response")
        else:
            tabs[f"tab_{n}"] = data
            print(f"  Tab {n}: OK — {len(str(data))} chars")
    except Exception as e:
        print(f"  Tab {n}: ERROR — {e}")
        sys.exit(1)

DRIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(DRIVE_PATH, "w") as f:
    json.dump(tabs, f, indent=2)

print(f"\nSaved: {DRIVE_PATH}")
print(f"Total tabs: {len(tabs)}/5")
print("Colab can now load: G:\My Drive\public-files\gen-ai-roi\experiments\tab_content.json")
