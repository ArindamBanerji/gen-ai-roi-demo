# Usage: python scripts/check_neo4j.py (from project root)

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

try:
    from neo4j import GraphDatabase
except ImportError:
    print("❌ neo4j package not installed. Run: pip install neo4j")
    sys.exit(1)


def find_and_load_env():
    """Find .env file - check backend/ directory from project root or parent if in scripts/"""
    # Try backend/.env from current directory (running from root)
    env_path = Path("backend/.env")
    if env_path.exists():
        load_dotenv(env_path)
        return True

    # Try ../backend/.env (running from scripts/ directory)
    env_path = Path("../backend/.env")
    if env_path.exists():
        load_dotenv(env_path)
        return True

    # Try .env in current directory (fallback)
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path)
        return True

    return False


def check_neo4j():
    """Check Neo4j connection and count alerts"""
    if not find_and_load_env():
        print("⚠️  .env not found — check path (expected: backend/.env)")
        sys.exit(1)

    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not password:
        print("⚠️  Missing NEO4J_URI or NEO4J_PASSWORD in .env")
        sys.exit(1)

    driver = None
    try:
        # Create driver with 5 second timeout
        driver = GraphDatabase.driver(
            uri,
            auth=(username, password),
            connection_timeout=5.0,
            max_connection_lifetime=5.0
        )

        # Verify connectivity and count alerts
        with driver.session() as session:
            result = session.run("MATCH (a:Alert) RETURN count(a) as count")
            record = result.single()
            alert_count = record["count"] if record else 0

            print("✅ Neo4j: RUNNING")
            print(f"   Alert count: {alert_count}")

    except Exception as e:
        print("❌ Neo4j: PAUSED or UNREACHABLE")
        print(f"   Error: {e}")
        sys.exit(1)

    finally:
        if driver:
            driver.close()


if __name__ == "__main__":
    check_neo4j()
