"""Diagnose SOC Playwright failures — check API shapes and data.

Run from anywhere:
    python soc_pw_diagnostic.py
"""
import urllib.request
import json

def fetch(url):
    try:
        r = urllib.request.urlopen(url, timeout=10)
        return r.getcode(), json.loads(r.read())
    except Exception as e:
        return 0, str(e)

print("=" * 60)
print("SOC PLAYWRIGHT DIAGNOSTIC")
print("=" * 60)

# 1. Evidence room audit trail shape
code, er = fetch("http://127.0.0.1:8001/api/soc/evidence-room")
print(f"\n=== evidence-room: HTTP {code}")
if isinstance(er, dict):
    print(f"  top keys: {sorted(er.keys())}")
    at = er.get("audit_trail", {})
    print(f"  audit_trail type: {type(at).__name__}")
    if isinstance(at, dict):
        print(f"  audit_trail keys: {sorted(at.keys())}")
        entries = at.get("entries", [])
        print(f"  entries count: {len(entries)}")
        print(f"  total: {at.get('total')}")
        if entries:
            print(f"  first entry keys: {sorted(entries[0].keys())}")
    elif isinstance(at, list):
        print(f"  audit_trail is list, len: {len(at)}")
    else:
        print(f"  audit_trail value: {str(at)[:200]}")

# 2. S2P preview suppliers
code2, sup = fetch("http://127.0.0.1:8001/api/s2p/preview/suppliers")
print(f"\n=== s2p suppliers: HTTP {code2}")
if isinstance(sup, dict):
    print(f"  top keys: {sorted(sup.keys())}")
    items = sup.get("suppliers", [])
elif isinstance(sup, list):
    print(f"  is list, len: {len(sup)}")
    items = sup
else:
    items = []
for s in items[:8]:
    name = s.get("name", s.get("supplier_name", "?"))
    otif = s.get("otif", "?")
    print(f"  {name}: otif={otif}")

# 3. S2P preview queue
code3, q = fetch("http://127.0.0.1:8001/api/s2p/preview/queue")
print(f"\n=== s2p queue: HTTP {code3}")
if isinstance(q, dict):
    print(f"  top keys: {sorted(q.keys())}")

# 4. Eval demo
code4, ev = fetch("http://127.0.0.1:8001/api/soc/eval/demo")
print(f"\n=== eval/demo: HTTP {code4}")
if code4 == 0:
    print(f"  error: {ev}")

# 5. S2P tab text on frontend
print(f"\n=== S2P Preview Tab content check")
code5, html = fetch("http://127.0.0.1:5173")
print(f"  frontend: HTTP {code5}")

# 6. Check what text the S2P preview tab actually shows
code6, tab = fetch("http://127.0.0.1:8001/api/s2p/preview/conservation")
print(f"\n=== s2p conservation: HTTP {code6}")
if isinstance(tab, dict):
    print(f"  keys: {sorted(tab.keys())}")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
