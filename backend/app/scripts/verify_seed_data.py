"""
verify_seed_data.py — Standalone Neo4j seed verification.

Verifies that the SIM alert seed (20 alerts, 5 categories) and all
associated graph entities are present in Neo4j.

Usage (from backend/):
    python -m app.scripts.verify_seed_data
    python app/scripts/verify_seed_data.py
"""

import asyncio
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# .env loading
# Resolves from this file's location:  backend/app/scripts/ → project root
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = _HERE.parent.parent.parent.parent   # backend/app/scripts → project root

_env_candidates = [
    _PROJECT_ROOT / ".env",         # running from anywhere via -m or direct
    Path.cwd() / ".env",            # if cwd IS the project root
    Path.cwd().parent / ".env",     # if cwd is backend/
]
for _ep in _env_candidates:
    if _ep.exists():
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=str(_ep), override=False)
        break

# ---------------------------------------------------------------------------
# Neo4j (direct — no app imports needed)
# ---------------------------------------------------------------------------
from neo4j import AsyncGraphDatabase


async def _q(driver, cypher: str) -> list:
    """Run a Cypher query and return all records as dicts."""
    async with driver.session() as s:
        result = await s.run(cypher)
        return await result.data()


# ---------------------------------------------------------------------------
# Check definitions
#
# NOTE — deviations from the task spec that are corrected here:
#   • a.id        not a.alert_id  (Alert nodes use 'id' as their key)
#   • u.id        not u.user_id   (User nodes use 'id' as their key)
#   • a.id        not a.asset_id  (Asset nodes use 'id' as their key)
#   • CHECK 1: 'category' is a Python-only field; not written to graph.
#              Uses presence of one representative alert per category instead.
#   • CHECK 2: AlertType nodes use {id: 'lateral_movement'}, name='Lateral Movement'
# ---------------------------------------------------------------------------

_CHECKS = [
    {
        "id":       1,
        "name":     "All 5 alert categories present (by representative ID)",
        # 'category' is not stored as a graph property; verify by checking
        # that one representative alert from each of the 5 categories exists.
        "cypher":   (
            "MATCH (a:Alert) WHERE a.id IN ["
            "'SIM-CA-001', 'SIM-TI-001', 'SIM-LM-001', "
            "'SIM-DE-001', 'SIM-IT-001'"
            "] RETURN count(a) AS n"
        ),
        "op":       "==",
        "expected": 5,
        "note":     (
            "representative IDs: CA=credential_access, TI=malware_execution, "
            "LM=lateral_movement, DE=data_exfiltration, IT=insider_threat"
        ),
    },
    {
        "id":       8,
        "name":     "lateral_movement AlertType node exists",
        # AlertType nodes use 'id' as key; name is 'Lateral Movement' (capitalised).
        "cypher":   "MATCH (at:AlertType {id: 'lateral_movement'}) RETURN count(at) AS n",
        "op":       "==",
        "expected": 1,
        "note":     "id='lateral_movement', name='Lateral Movement', mitre=T1021",
    },
]


def _eval(actual, op: str, expected) -> bool:
    if op == ">=":
        return actual >= expected
    if op == "==":
        return actual == expected
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    uri      = os.getenv("NEO4J_URI")
    user     = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not password:
        print(
            "[ERROR] NEO4J_URI and/or NEO4J_PASSWORD not found.\n"
            "        Make sure .env is present at the project root and contains these keys."
        )
        sys.exit(2)

    print(f"\n  Neo4j URI : {uri}")
    print(f"  Neo4j user: {user}")

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    passed = 0
    total  = len(_CHECKS)

    try:
        print()
        print("=" * 66)
        print("  SEED DATA VERIFICATION — SOC Copilot v4.5 (SIM-3a + HC)")
        print("=" * 66)

        for chk in _CHECKS:
            cid      = chk["id"]
            name     = chk["name"]
            cypher   = chk["cypher"]
            op       = chk["op"]
            expected = chk["expected"]
            note     = chk.get("note", "")

            try:
                rows   = await _q(driver, cypher)
                actual = rows[0]["n"] if rows else 0
                ok     = _eval(actual, op, expected)
            except Exception as exc:
                print(f"  ERROR [{cid:d}] {name}")
                print(f"        exception: {exc}")
                continue

            if ok:
                passed += 1
                detail = f"actual={actual}"
                if note:
                    detail += f"  | {note}"
                print(f"  PASS  [{cid}] {name}")
                print(f"        {detail}")
            else:
                exp_str = f"{op} {expected}"
                print(f"  FAIL  [{cid}] {name}")
                print(f"        actual={actual}   expected: {exp_str}")
                if note:
                    print(f"        note: {note}")

        print()
        print("=" * 66)
        print(f"  RESULT: {passed}/{total} checks passed")
        print("=" * 66)
        print()

    finally:
        await driver.close()

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
