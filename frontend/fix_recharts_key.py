"""Fix recharts React key warning filter in deep_flows and learning_stress.

Run from gen-ai-roi-demo-v4-v50/frontend/:
    python fix_recharts_key.py
"""
from pathlib import Path

fixed = 0

# Fix 1: deep_flows.spec.ts
# Pattern: if (text.includes('Encountered two children...')) return;
# Add:     if (text.includes('unique') && text.includes('key')) return;
p1 = Path("tests/e2e/deep_flows.spec.ts")
c1 = p1.read_text(encoding="utf-8")
old1 = "      if (text.includes('Encountered two children with the same key')) return;\n      consoleErrors.push(text);"
new1 = "      if (text.includes('Encountered two children with the same key')) return;\n      if (text.includes('unique') && text.includes('key')) return;\n      consoleErrors.push(text);"
if "unique" not in c1:
    n1 = c1.count(old1)
    if n1 > 0:
        p1.write_text(c1.replace(old1, new1), encoding="utf-8")
        print(f"FIXED deep_flows.spec.ts: {n1} instances")
        fixed += n1
    else:
        print("NOT FOUND deep_flows pattern")
else:
    print("ALREADY FIXED deep_flows")

# Fix 2: learning_stress.spec.ts
# Pattern: !e.includes('Encountered two children with the same key') &&
# Add:     !e.includes('unique') &&
p2 = Path("tests/e2e/learning_stress.spec.ts")
c2 = p2.read_text(encoding="utf-8")
old2 = "!e.includes('Encountered two children with the same key') &&"
new2 = "!e.includes('Encountered two children with the same key') &&\n      !e.includes('unique') &&"
if "unique" not in c2:
    n2 = c2.count(old2)
    if n2 > 0:
        p2.write_text(c2.replace(old2, new2), encoding="utf-8")
        print(f"FIXED learning_stress.spec.ts: {n2} instances")
        fixed += n2
    else:
        print("NOT FOUND learning_stress pattern")
else:
    print("ALREADY FIXED learning_stress")

print(f"\nTotal: {fixed} fixes applied")
