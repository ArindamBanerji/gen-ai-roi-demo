"""
verify_realistic_seed.py — Verify SEED-2 realistic data in Neo4j.

Checks that seed_realistic() ran successfully:
  200+ REAL users, 100+ REAL alerts, all 6 SOC categories, power-law
  distribution, planted suspicious users, and ThreatIntel nodes.

Usage (from backend/):
    python -m app.scripts.verify_realistic_seed
    python app/scripts/verify_realistic_seed.py
"""

import asyncio
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = _HERE.parent.parent.parent.parent  # scripts → app → backend → project root

_env_candidates = [
    _PROJECT_ROOT / ".env",
    Path.cwd() / ".env",
    Path.cwd().parent / ".env",
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


async def _q(driver, cypher: str, params: dict = None) -> list:
    """Run a Cypher query and return all records as dicts."""
    async with driver.session() as s:
        result = await s.run(cypher, params or {})
        return await result.data()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not password:
        print(
            "[ERROR] NEO4J_URI and/or NEO4J_PASSWORD not found.\n"
            "        Make sure .env is present at the project root."
        )
        sys.exit(2)

    print(f"\n  Neo4j URI : {uri}")
    print(f"  Neo4j user: {user}")

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    passed = 0
    total = 6

    try:
        print()
        print("=" * 66)
        print("  SEED-2 VERIFICATION — Realistic Data (200+ users)")
        print("=" * 66)

        # ── CHECK 1: User count >= 200 ─────────────────────────────────────
        rows = await _q(
            driver,
            "MATCH (u:User) WHERE u.user_id STARTS WITH 'REAL-' "
            "RETURN count(u) AS user_count",
        )
        user_count = rows[0]["user_count"] if rows else 0
        ok1 = user_count >= 200
        if ok1:
            passed += 1
            print(f"  PASS  [1] User count >= 200")
            print(f"        actual={user_count}")
        else:
            print(f"  FAIL  [1] User count >= 200")
            print(f"        actual={user_count}   expected: >= 200")

        # ── CHECK 2: Alert count >= 100 ────────────────────────────────────
        rows = await _q(
            driver,
            "MATCH (a:Alert) WHERE a.alert_id STARTS WITH 'REAL-' "
            "RETURN count(a) AS alert_count",
        )
        alert_count = rows[0]["alert_count"] if rows else 0
        ok2 = alert_count >= 100
        if ok2:
            passed += 1
            print(f"  PASS  [2] Alert count >= 100")
            print(f"        actual={alert_count}")
        else:
            print(f"  FAIL  [2] Alert count >= 100")
            print(f"        actual={alert_count}   expected: >= 100")

        # ── CHECK 3: All 6 SOC categories represented ──────────────────────
        from app.domains.soc.config import SOC_CATEGORIES

        rows = await _q(
            driver,
            "MATCH (a:Alert) WHERE a.alert_id STARTS WITH 'REAL-' "
            "RETURN DISTINCT a.category AS category",
        )
        found_cats = {r["category"] for r in rows if r["category"]}
        missing_cats = set(SOC_CATEGORIES) - found_cats
        ok3 = len(missing_cats) == 0
        if ok3:
            passed += 1
            print(f"  PASS  [3] All 6 SOC categories represented")
            print(f"        found={sorted(found_cats)}")
        else:
            print(f"  FAIL  [3] All 6 SOC categories represented")
            print(f"        missing={sorted(missing_cats)}")

        # ── CHECK 4: Power-law — top 10% of ALL REAL users have > 50% of alerts ─
        # "Top 10%" means 10% of the total REAL user population (200 users = 20).
        # We fetch per-user alert counts ordered descending, then sum the first 20.
        total_user_rows = await _q(
            driver,
            "MATCH (u:User) WHERE u.user_id STARTS WITH 'REAL-' "
            "RETURN count(u) AS n",
        )
        total_real_users = total_user_rows[0]["n"] if total_user_rows else 0

        alert_dist_rows = await _q(
            driver,
            "MATCH (a:Alert)-[:INVOLVES]->(u:User) "
            "WHERE a.alert_id STARTS WITH 'REAL-' AND u.user_id STARTS WITH 'REAL-' "
            "WITH u.user_id AS uid, count(a) AS cnt "
            "ORDER BY cnt DESC "
            "RETURN uid, cnt",
        )
        if alert_dist_rows and total_real_users > 0:
            total_al = sum(r["cnt"] for r in alert_dist_rows)
            top_n = max(1, total_real_users // 10)
            top_total = sum(r["cnt"] for r in alert_dist_rows[:top_n])
            share = top_total / total_al if total_al > 0 else 0.0
            ok4 = share > 0.50
            if ok4:
                passed += 1
                print(f"  PASS  [4] Power-law: top 10% users have > 50% of alerts")
                print(
                    f"        top {top_n}/{total_real_users} users hold "
                    f"{top_total}/{total_al} alerts ({share:.1%})"
                )
            else:
                print(f"  FAIL  [4] Power-law: top 10% users have > 50% of alerts")
                print(
                    f"        top {top_n}/{total_real_users} users hold "
                    f"{top_total}/{total_al} alerts ({share:.1%}), expected > 50%"
                )
        else:
            print(f"  FAIL  [4] Power-law: no alert-user relationships found")

        # ── CHECK 5: Planted suspicious users exist ────────────────────────
        rows = await _q(
            driver,
            "MATCH (u:User {user_id: 'REAL-USR-0001'}) "
            "RETURN u.access_level AS al, u.travel_frequency AS tf",
        )
        if rows and rows[0]["al"] == "privileged" and rows[0]["tf"] == "frequent":
            passed += 1
            print(f"  PASS  [5] Planted suspicious user REAL-USR-0001 verified")
            print(f"        access_level={rows[0]['al']}, travel_frequency={rows[0]['tf']}")
        else:
            al = rows[0]["al"] if rows else "NOT FOUND"
            tf = rows[0]["tf"] if rows else "NOT FOUND"
            print(f"  FAIL  [5] Planted suspicious user REAL-USR-0001")
            print(f"        access_level={al} (expected 'privileged'), "
                  f"travel_frequency={tf} (expected 'frequent')")

        # ── CHECK 6: ThreatIntel nodes created ────────────────────────────
        rows = await _q(
            driver,
            "MATCH (t:ThreatIntel) WHERE t.source IN ['CISA', 'GreyNoise', 'internal'] "
            "RETURN count(t) AS ti_count",
        )
        ti_count = rows[0]["ti_count"] if rows else 0
        ok6 = ti_count >= 20
        if ok6:
            passed += 1
            print(f"  PASS  [6] ThreatIntel nodes >= 20")
            print(f"        actual={ti_count}")
        else:
            print(f"  FAIL  [6] ThreatIntel nodes >= 20")
            print(f"        actual={ti_count}   expected: >= 20")

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
