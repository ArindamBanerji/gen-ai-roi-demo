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

# SANITY CHECKS
print("\n--- SANITY CHECK ---")
warnings = 0

# Tab 1: no "unknown" alert types
tab1_types = [t.get("type","") for t in
    tabs.get("tab_1",{}).get("content",{}).get("top_alert_types",[])]
unknowns = [t for t in tab1_types if t == "unknown"]
if unknowns:
    print(f"[SANITY] Tab 1 alert types: WARNING — found unknown types: {unknowns}")
    warnings += 1
else:
    print(f"[SANITY] Tab 1 alert types: PASS — {tab1_types}")

# Tab 2: decision_count_glossary present
if "decision_count_glossary" in tabs.get("tab_2",{}).get("content",{}):
    print("[SANITY] Tab 2 glossary: PASS")
else:
    print("[SANITY] Tab 2 glossary: WARNING — missing")
    warnings += 1

# Tab 3: recommendation present
if "recommendation" in tabs.get("tab_3",{}).get("content",{}):
    print("[SANITY] Tab 3 recommendation: PASS")
else:
    print("[SANITY] Tab 3 recommendation: WARNING — missing")
    warnings += 1

# Tab 4: roi_methodology present
if "roi_methodology" in tabs.get("tab_4",{}).get("content",{}):
    print("[SANITY] Tab 4 ROI methodology: PASS")
else:
    print("[SANITY] Tab 4 ROI methodology: WARNING — missing")
    warnings += 1

# Tab 5: flywheel_claim present
w2 = tabs.get("tab_5",{}).get("content",{}).get(
    "what_system_knows",{}).get("flywheel_claim","")
if w2:
    print("[SANITY] Tab 5 W2 flywheel: PASS")
else:
    print("[SANITY] Tab 5 W2 flywheel: WARNING — missing")
    warnings += 1

print(f"\n[SANITY] Overall: {'PASS (5/5)' if warnings == 0 else f'WARNING ({warnings}/5 checks failed)'}")
if warnings > 0:
    print("Do NOT refresh Drive file — fix backend first.")
else:
    print("Drive file refreshed. Colab Batch E can run.")
