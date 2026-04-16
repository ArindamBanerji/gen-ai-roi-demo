"""Remove TestHardResetRequiresConfirm from test_graph_contract_stress.py.

The class tests hard_reset_all() which doesn't exist.
StateManager has hard_reset(preserve_learning=False), not hard_reset_all(confirm=).
"""
import os

path = os.path.join("backend", "tests", "test_graph_contract_stress.py")
with open(path, "r") as f:
    lines = f.readlines()

# Find the class boundaries
start = None
end = None
for i, line in enumerate(lines):
    if "class TestHardResetRequiresConfirm" in line:
        # Include the comment header above (3 lines: # ===, # Hard reset..., # ===)
        start = max(0, i - 3)
    if start is not None and i > start + 3:
        # End at the next class or section header
        if line.startswith("# ===") or (line.startswith("class ") and i != start + 3):
            end = i
            break

if start is not None and end is not None:
    removed = lines[start:end]
    print("Removing lines " + str(start + 1) + "-" + str(end) + ":")
    for l in removed:
        print("  " + l.rstrip())
    new_lines = lines[:start] + lines[end:]
    with open(path, "w") as f:
        f.writelines(new_lines)
    print("\nDone. Removed " + str(len(removed)) + " lines.")
elif start is not None:
    # Class is at the end of the file
    removed = lines[start:]
    print("Removing lines " + str(start + 1) + " to end:")
    for l in removed:
        print("  " + l.rstrip())
    new_lines = lines[:start]
    with open(path, "w") as f:
        f.writelines(new_lines)
    print("\nDone. Removed " + str(len(removed)) + " lines.")
else:
    print("TestHardResetRequiresConfirm not found — already removed?")
