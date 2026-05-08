# scripts/collect_tab_content.py
# Run from repo root: python scripts/collect_tab_content.py
# Requires: SOC backend running at localhost:8001
# Optional: S2P backend running at localhost:8002 (for Tab 6)
#
# v2: Added Tab 7 (Evidence Room / Governance) collection + AE Summary
#     Updated sanity checks for all 7 tabs

import requests, json, sys
from pathlib import Path

SOC_BASE = "http://localhost:8001"
S2P_BASE = "http://localhost:8002"
DRIVE_PATH = Path(r"G:\My Drive\public-files\gen-ai-roi\experiments\tab_content.json")

tabs = {}

# ============================================================================
# Tabs 1-5: SOC backend tab content endpoints (required)
# ============================================================================
for n in range(1, 6):
    url = f"{SOC_BASE}/api/soc/tab/{n}/content"
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

# ============================================================================
# Tab 6: S2P Preview (optional — S2P backend may not be running)
# ============================================================================
tab6_ok = False
try:
    resp = requests.get(f"{SOC_BASE}/api/soc/tab/6/content", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data:
        tabs["tab_6"] = data
        tab6_ok = True
        print(f"  Tab 6: OK (SOC endpoint) — {len(str(data))} chars")
except Exception:
    pass  # Try S2P backend fallback

if not tab6_ok:
    s2p_panels = {}
    s2p_endpoints = {
        "queue": f"{S2P_BASE}/api/s2p/preview/queue",
        "conservation": f"{S2P_BASE}/api/s2p/preview/conservation",
        "compounding": f"{S2P_BASE}/api/s2p/preview/compounding",
        "suppliers": f"{S2P_BASE}/api/s2p/preview/suppliers",
        "config": f"{S2P_BASE}/api/s2p/preview/config",
    }
    s2p_errors = 0
    for panel_name, url in s2p_endpoints.items():
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            s2p_panels[panel_name] = resp.json()
        except Exception as e:
            s2p_errors += 1
            s2p_panels[panel_name] = {"error": str(e)}

    if s2p_errors == 0:
        tabs["tab_6"] = {"content": s2p_panels, "source": "s2p_preview_aggregated"}
        tab6_ok = True
        print(f"  Tab 6: OK (S2P aggregated) — {len(str(s2p_panels))} chars")
    elif s2p_errors < len(s2p_endpoints):
        tabs["tab_6"] = {"content": s2p_panels, "source": "s2p_preview_partial"}
        tab6_ok = True
        print(f"  Tab 6: PARTIAL — {s2p_errors}/{len(s2p_endpoints)} endpoints failed")
    else:
        print(f"  Tab 6: SKIP — S2P backend not running (non-fatal)")

# ============================================================================
# Tab 7: Evidence Room / Governance (aggregated from 4 endpoints)
# ============================================================================
tab7_ok = False
gov_panels = {}
gov_endpoints = {
    "evidence_room": f"{SOC_BASE}/api/soc/evidence-room",
    "governance_summary": f"{SOC_BASE}/api/governance/summary",
    "evolution_summary": f"{SOC_BASE}/api/evolution/summary",
    "evolution_recent": f"{SOC_BASE}/api/evolution/recent-events?limit=20",
}
gov_errors = 0
for panel_name, url in gov_endpoints.items():
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        gov_panels[panel_name] = resp.json()
    except Exception as e:
        gov_errors += 1
        gov_panels[panel_name] = {"error": str(e)}

if gov_errors == 0:
    tabs["tab_7"] = {"content": gov_panels, "source": "governance_aggregated"}
    tab7_ok = True
    print(f"  Tab 7: OK (Governance aggregated) — {len(str(gov_panels))} chars")
elif gov_errors < len(gov_endpoints):
    tabs["tab_7"] = {"content": gov_panels, "source": "governance_partial"}
    tab7_ok = True
    print(f"  Tab 7: PARTIAL — {gov_errors}/{len(gov_endpoints)} endpoints failed")
else:
    print(f"  Tab 7: ERROR — all governance endpoints failed")
    # Tab 7 is required (Evidence Room is a shipped feature)
    sys.exit(1)

# ============================================================================
# Save to Drive
# ============================================================================
DRIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(DRIVE_PATH, "w") as f:
    json.dump(tabs, f, indent=2)

total_tabs = 5 + (1 if tab6_ok else 0) + (1 if tab7_ok else 0)
total_expected = 7 if tab6_ok else 6
print(f"\nSaved: {DRIVE_PATH}")
print(f"Total tabs: {total_tabs}/{total_expected}")
print("Colab can now load: G:\\My Drive\\public-files\\gen-ai-roi\\experiments\\tab_content.json")

# ============================================================================
# SANITY CHECKS
# ============================================================================
print("\n--- SANITY CHECK ---")
warnings = 0
total_checks = 6  # base checks for tabs 1-5 + tab 7

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

# Tab 3: recommendation present and action is a real SOC action
_VALID_ACTIONS = {"escalate", "investigate", "suppress", "monitor"}
_tab3_rec = tabs.get("tab_3",{}).get("content",{}).get("recommendation",{})
_tab3_action = _tab3_rec.get("action","")
if _tab3_action in _VALID_ACTIONS:
    print(f"[SANITY] Tab 3 action: PASS — {_tab3_action}")
elif not _tab3_action:
    print("[SANITY] Tab 3 recommendation: WARNING — missing")
    warnings += 1
else:
    print(f"[SANITY] Tab 3 action: WARNING — unexpected action: {_tab3_action}")
    warnings += 1

# Tab 3: kernel_note contains DiagonalKernel
if "DiagonalKernel" in tabs.get("tab_3",{}).get("content",{}).get("kernel_note",""):
    print("[SANITY] Tab 3 DiagonalKernel: PASS")
else:
    print("[SANITY] Tab 3 DiagonalKernel: WARNING — missing")
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

# Tab 6: S2P Preview — conservation status and config present (optional)
if tab6_ok:
    total_checks += 1
    _tab6 = tabs.get("tab_6",{}).get("content",{})
    _conservation = _tab6.get("conservation",{})
    _config = _tab6.get("config",{})
    _has_conservation = bool(_conservation and
        (_conservation.get("status") or _conservation.get("conservation_status")))
    _has_config = bool(_config and
        (_config.get("version") or _config.get("tensor_shape") or
         _config.get("categories") or _config.get("config_version")))

    if _has_conservation and _has_config:
        print(f"[SANITY] Tab 6 S2P Preview: PASS — conservation + config present")
    elif _has_conservation or _has_config:
        present = "conservation" if _has_conservation else "config"
        missing = "config" if _has_conservation else "conservation"
        print(f"[SANITY] Tab 6 S2P Preview: WARNING — {present} OK, {missing} missing")
        warnings += 1
    else:
        print(f"[SANITY] Tab 6 S2P Preview: WARNING — conservation and config both missing")
        warnings += 1

# Tab 7: Evidence Room — all 4 panels present
total_checks += 4  # one check per panel
_tab7 = tabs.get("tab_7",{}).get("content",{})

# 7a: Evidence room — audit_trail + hash_chain
_er = _tab7.get("evidence_room",{})
if isinstance(_er, dict) and "error" not in _er and "audit_trail" in _er:
    print("[SANITY] Tab 7 evidence_room: PASS — audit_trail present")
else:
    print("[SANITY] Tab 7 evidence_room: WARNING — missing or error")
    warnings += 1

# 7b: Governance summary — sections with articles
_gs = _tab7.get("governance_summary",{})
if isinstance(_gs, dict) and "error" not in _gs and _gs.get("sections"):
    _articles = [s.get("article","") for s in _gs.get("sections",[])]
    print(f"[SANITY] Tab 7 governance_summary: PASS — {len(_articles)} articles")
else:
    print("[SANITY] Tab 7 governance_summary: WARNING — missing or error")
    warnings += 1

# 7c: Evolution summary — variants_generated count
_es = _tab7.get("evolution_summary",{})
if isinstance(_es, dict) and "error" not in _es and "variants_generated" in _es:
    _gen = _es.get("variants_generated", 0)
    _pro = _es.get("variants_promoted", 0)
    print(f"[SANITY] Tab 7 evolution_summary: PASS — {_gen} generated, {_pro} promoted")
else:
    print("[SANITY] Tab 7 evolution_summary: WARNING — missing or error")
    warnings += 1

# 7d: Evolution recent events — events array
_re = _tab7.get("evolution_recent",{})
if isinstance(_re, dict) and "error" not in _re and "events" in _re:
    _count = _re.get("count", 0)
    print(f"[SANITY] Tab 7 evolution_recent: PASS — {_count} events")
else:
    print("[SANITY] Tab 7 evolution_recent: WARNING — missing or error")
    warnings += 1

# Cross-tab consistency checks
total_checks += 6

def _as_dict(value):
    return value if isinstance(value, dict) else {}

def _as_list(value):
    return value if isinstance(value, list) else []

def _as_int(value, default=0):
    try:
        if isinstance(value, str):
            cleaned = "".join(ch for ch in value if ch.isdigit())
            return int(cleaned) if cleaned else default
        return int(value)
    except Exception:
        return default

def _as_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default

def _status(value):
    return str(value or "").upper()

def _tab_content(tab_name):
    return _as_dict(tabs.get(tab_name, {})).get("content", {})

def _sum_tab1_verified(tab1_content):
    for key in ("category_breakdown", "category_counts", "verified_by_category"):
        values = tab1_content.get(key)
        if isinstance(values, list):
            return sum(_as_int(item.get("count", item.get("cnt", item.get("n", 0)))) for item in values if isinstance(item, dict))
        if isinstance(values, dict):
            return sum(_as_int(v) for v in values.values())
    return _as_int(tab1_content.get("total_decisions") or tab1_content.get("verified_decisions"))

def _tab2_verified_total(tab2_content):
    for key in ("verified_decisions", "total_verified", "decision_count", "total_decisions"):
        if key in tab2_content:
            return _as_int(tab2_content.get(key))
    glossary = tab2_content.get("decision_count_glossary", {})
    if isinstance(glossary, dict):
        for key in ("verified_decisions", "total_verified", "decision_count"):
            if key in glossary:
                return _as_int(glossary.get(key))
    return 0

_tab1_content = _as_dict(_tab_content("tab_1"))
_tab2_content = _as_dict(_tab_content("tab_2"))
_tab5_content = _as_dict(_tab_content("tab_5"))
_er = _as_dict(_tab7.get("evidence_room", {}))
_audit_entries = _as_list(_as_dict(_er.get("audit_trail", {})).get("entries"))
_conservation = _as_dict(_er.get("conservation", {}))

# CX1: Tab 5 health vs Tab 7 conservation status
_tab5_health = _status(_as_dict(_tab5_content.get("what_system_knows", {})).get("health_status"))
_tab7_health = _status(_conservation.get("status"))
if _tab5_health and _tab7_health and _tab5_health == _tab7_health:
    print(f"[SANITY] CX1 health alignment: PASS — {_tab5_health}")
else:
    print(f"[SANITY] CX1 health alignment: WARNING — Tab5={_tab5_health or 'missing'}, Tab7={_tab7_health or 'missing'}")
    warnings += 1

# CX2: No unknown categories in Evidence Room audit entries
_unknown_audit_categories = [
    entry.get("category")
    for entry in _audit_entries
    if isinstance(entry, dict) and str(entry.get("category", "")).lower() == "unknown"
]
if _unknown_audit_categories:
    print(f"[SANITY] CX2 audit categories: WARNING — {len(_unknown_audit_categories)} unknown categories")
    warnings += 1
else:
    print("[SANITY] CX2 audit categories: PASS — no unknown categories")

# CX3: Audit trail timestamps spread
if _audit_entries:
    _timestamps = {
        str(entry.get("timestamp", ""))
        for entry in _audit_entries
        if isinstance(entry, dict) and entry.get("timestamp")
    }
    _required_spread = min(5, len(_audit_entries))
    if len(_timestamps) >= _required_spread:
        print(f"[SANITY] CX3 audit timestamp spread: PASS — {len(_timestamps)} unique timestamps")
    else:
        print(f"[SANITY] CX3 audit timestamp spread: WARNING — {len(_timestamps)}/{_required_spread} unique timestamps")
        warnings += 1
else:
    print("[SANITY] CX3 audit timestamp spread: WARNING — no audit entries")
    warnings += 1

# CX4: Evolution events present
_evolution_generated = _as_int(_as_dict(_tab7.get("evolution_summary", {})).get("variants_generated"))
_recent_event_count = _as_int(_as_dict(_tab7.get("evolution_recent", {})).get("count"))
if _evolution_generated > 0 or _recent_event_count > 0:
    print(f"[SANITY] CX4 evolution events: PASS — generated={_evolution_generated}, recent={_recent_event_count}")
else:
    print("[SANITY] CX4 evolution events: WARN-NONBLOCKING — no evolution events yet")

# CX5: Conservation status/product contradiction
_conservation_status = _status(_conservation.get("status"))
_product = _as_float(_conservation.get("product"))
if _conservation_status == "RED" and _product > 0:
    print(f"[SANITY] CX5 conservation contradiction: WARNING — RED with product={_product}")
    warnings += 1
else:
    print(f"[SANITY] CX5 conservation contradiction: PASS — status={_conservation_status or 'missing'}, product={_product}")

# CX6: Tab 1 verified sum <= Tab 2 total verified
_tab1_verified_sum = _sum_tab1_verified(_tab1_content)
_tab2_verified_total = _tab2_verified_total(_tab2_content)
if _tab1_verified_sum == 0:
    print("[SANITY] CX6 verified consistency: WARNING — Tab 1 verified sum is 0")
    warnings += 1
elif _tab2_verified_total and _tab1_verified_sum > _tab2_verified_total:
    print(f"[SANITY] CX6 verified consistency: WARNING — Tab1={_tab1_verified_sum} > Tab2={_tab2_verified_total}")
    warnings += 1
else:
    print(f"[SANITY] CX6 verified consistency: PASS — Tab1={_tab1_verified_sum}, Tab2={_tab2_verified_total}")

# ============================================================================
# Summary
# ============================================================================
passed = total_checks - warnings
print(f"\n[SANITY] Overall: {'PASS' if warnings == 0 else 'WARNING'} ({passed}/{total_checks} checks passed)")
if warnings > 0:
    print("Do NOT refresh Drive file — fix backend first.")
else:
    print("Drive file refreshed. Colab Batch E can run.")
if not tab6_ok:
    print("NOTE: Tab 6 (S2P Preview) skipped — start S2P backend on port 8002 for full coverage.")
