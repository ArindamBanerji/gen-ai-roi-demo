# Scripts Directory

This directory contains utility scripts for development, testing, data management, and demo operations.

## Purpose

Place utility scripts here for:

- **Data Seeding** - Scripts to populate databases with demo data
- **Testing Utilities** - Tools for automated testing and validation
- **Demo Reset** - Scripts to reset demo state between presentations
- **Data Generation** - Mock data generators
- **Migration Scripts** - Database schema updates and data migrations
- **Performance Testing** - Load testing and benchmarking tools
- **Batch Operations** - Bulk data processing scripts

## Typical Files

### Data Seeding Scripts
```
seed_neo4j.py                      # Main Neo4j seeding (currently in backend/)
seed_bigquery.py                   # BigQuery table population
seed_firestore.py                  # Firestore collection seeding
seed_all.sh                        # Run all seeding scripts
```

### Testing Scripts
```
test_all_tabs.py                   # Automated tab testing
validate_demo_data.py              # Verify demo data integrity
health_check.py                    # API health check script
load_test.py                       # Performance testing
```

### Demo Management
```
reset_demo.sh                      # Reset to Week 1 state
backup_demo_state.py               # Save current demo state
restore_demo_state.py              # Restore saved demo state
generate_demo_report.py            # Demo metrics and stats
```

### Data Generators
```
generate_alerts.py                 # Create test alert data
generate_evolution_events.py       # Create evolution history
generate_patterns.py               # Create attack patterns
generate_users.py                  # Create user data
```

### Migration Scripts
```
migrations/
  ├── 001_initial_schema.py        # Initial Neo4j schema
  ├── 002_add_travel_context.py   # Add travel nodes
  └── 003_evolution_events.py     # Add evolution tracking
```

## Script Usage Guide

### Data Seeding

#### Seed Neo4j Database

**File:** `seed_neo4j.py` (currently in `backend/`)

**Purpose:** Populate Neo4j with demo data (5 alerts, 3 users, 3 assets, patterns).

**Usage:**
```bash
cd ../../backend
python seed_neo4j.py
```

**Expected Output:**
```
✓ Created users (3)
✓ Created assets (3)
✓ Created alert types (4)
✓ Created patterns (1)
✓ Created playbooks (4)
✓ Created alerts (5)
✓ Created travel context (1)
Neo4j seeding complete!
```

**Environment Required:**
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`

#### Seed All Databases

**File:** `seed_all.sh`

**Purpose:** Run all seeding scripts in correct order.

**Usage:**
```bash
cd support/scripts
./seed_all.sh
```

**Script Template:**
```bash
#!/bin/bash
set -e

echo "Seeding all databases..."

# 1. Neo4j
echo "→ Seeding Neo4j..."
cd ../../backend
python seed_neo4j.py

# 2. BigQuery (if using real data)
# echo "→ Seeding BigQuery..."
# python support/scripts/seed_bigquery.py

# 3. Firestore (if using real data)
# echo "→ Seeding Firestore..."
# python support/scripts/seed_firestore.py

echo "✓ All databases seeded!"
```

### Testing Scripts

#### Validate Demo Data

**File:** `validate_demo_data.py`

**Purpose:** Verify demo data integrity before presentation.

**Usage:**
```bash
cd support/scripts
python validate_demo_data.py
```

**Checks:**
- [ ] Neo4j connection works
- [ ] 5 alerts exist
- [ ] PAT-TRAVEL-001 pattern has 127 occurrences
- [ ] John Smith has travel to Singapore
- [ ] All alert types have playbooks
- [ ] Backend health check passes
- [ ] Frontend accessible

**Script Template:**
```python
#!/usr/bin/env python3
"""
Validate demo data integrity
"""
import sys
from neo4j import GraphDatabase
import os
import requests

def validate_neo4j():
    """Check Neo4j data"""
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )

    with driver.session() as session:
        # Check alert count
        result = session.run("MATCH (a:Alert) RETURN count(a) as count")
        count = result.single()["count"]
        assert count == 5, f"Expected 5 alerts, found {count}"
        print("✓ Alerts: 5")

        # Check pattern occurrences
        result = session.run("""
            MATCH (p:AttackPattern {id: 'PAT-TRAVEL-001'})
            RETURN p.occurrence_count as count
        """)
        count = result.single()["count"]
        assert count == 127, f"Expected 127 occurrences, found {count}"
        print("✓ Pattern occurrences: 127")

    driver.close()

def validate_backend():
    """Check backend health"""
    response = requests.get("http://localhost:8000/health")
    assert response.status_code == 200
    print("✓ Backend health check passed")

def validate_frontend():
    """Check frontend accessible"""
    response = requests.get("http://localhost:5173")
    assert response.status_code == 200
    print("✓ Frontend accessible")

if __name__ == "__main__":
    try:
        print("Validating demo data...\n")
        validate_neo4j()
        validate_backend()
        validate_frontend()
        print("\n✓ All validations passed!")
    except Exception as e:
        print(f"\n✗ Validation failed: {e}")
        sys.exit(1)
```

#### Health Check Script

**File:** `health_check.py`

**Purpose:** Quick health check for all services.

**Usage:**
```bash
python support/scripts/health_check.py
```

**Checks:**
- Backend API (GET /)
- All 4 tab endpoints
- Neo4j connection
- Environment variables

### Demo Management

#### Reset Demo State

**File:** `reset_demo.sh`

**Purpose:** Reset demo to Week 1 state for repeated presentations.

**Usage:**
```bash
cd support/scripts
./reset_demo.sh
```

**Operations:**
1. Call POST /api/demo/reset
2. Re-seed Neo4j with fresh data
3. Clear browser local storage (manual)
4. Verify reset completed

**Script Template:**
```bash
#!/bin/bash
set -e

echo "Resetting demo to Week 1 state..."

# 1. Call API reset
echo "→ Calling API reset endpoint..."
curl -X POST http://localhost:8000/api/demo/reset

# 2. Re-seed Neo4j
echo "→ Re-seeding Neo4j..."
cd ../../backend
python seed_neo4j.py

# 3. Restart backend
echo "→ Restarting backend..."
# (Manual step - user needs to restart)

echo "✓ Demo reset complete!"
echo "→ Please clear browser cache and reload frontend"
```

### Data Generators

#### Generate Test Alerts

**File:** `generate_alerts.py`

**Purpose:** Create additional test alerts beyond the 5 demo alerts.

**Usage:**
```bash
python support/scripts/generate_alerts.py --count 20
```

**Options:**
- `--count N` - Number of alerts to generate
- `--type TYPE` - Alert type filter
- `--severity LEVEL` - Severity filter

**Script Template:**
```python
#!/usr/bin/env python3
"""
Generate test alerts
"""
import argparse
from neo4j import GraphDatabase
import os
from datetime import datetime, timedelta
import random

ALERT_TYPES = ["anomalous_login", "phishing", "malware_detection", "data_exfiltration"]
SEVERITIES = ["critical", "high", "medium", "low"]

def generate_alerts(count, alert_type=None, severity=None):
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )

    with driver.session() as session:
        for i in range(count):
            alert_id = f"TEST-{8000 + i}"
            type_ = alert_type or random.choice(ALERT_TYPES)
            sev = severity or random.choice(SEVERITIES)

            session.run("""
                CREATE (a:Alert {
                    id: $id,
                    type: $type,
                    severity: $severity,
                    timestamp: datetime(),
                    status: 'pending'
                })
            """, id=alert_id, type=type_, severity=sev)

            print(f"✓ Created alert: {alert_id} ({type_}, {sev})")

    driver.close()
    print(f"\n✓ Generated {count} test alerts")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate test alerts")
    parser.add_argument("--count", type=int, default=10, help="Number of alerts")
    parser.add_argument("--type", choices=ALERT_TYPES, help="Alert type")
    parser.add_argument("--severity", choices=SEVERITIES, help="Severity level")

    args = parser.parse_args()
    generate_alerts(args.count, args.type, args.severity)
```

## Script Development Guidelines

### Writing Good Scripts

**1. Use Shebangs:**
```python
#!/usr/bin/env python3
```

**2. Add Docstrings:**
```python
"""
Script name and purpose

Usage:
    python script.py [options]

Examples:
    python script.py --help
    python script.py --count 10
"""
```

**3. Parse Arguments:**
```python
import argparse

parser = argparse.ArgumentParser(description="Script description")
parser.add_argument("--option", type=str, help="Option help")
args = parser.parse_args()
```

**4. Handle Errors:**
```python
try:
    operation()
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
```

**5. Provide Feedback:**
```python
print("→ Starting operation...")
print("✓ Operation complete!")
print("✗ Operation failed")
```

### Script Structure Template

```python
#!/usr/bin/env python3
"""
Script name and purpose

Usage:
    python script.py [options]
"""
import sys
import os
import argparse

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument("--option", type=str, help="Option help")
    args = parser.parse_args()

    try:
        print("→ Starting operation...")

        # Do work here

        print("✓ Operation complete!")
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Shell Script Template

```bash
#!/bin/bash
set -e  # Exit on error
set -u  # Exit on undefined variable

# Script name and purpose
# Usage: ./script.sh [options]

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}→ Starting operation...${NC}"

# Do work here

echo -e "${GREEN}✓ Operation complete!${NC}"
```

## Common Script Patterns

### Database Connection
```python
from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

with driver.session() as session:
    result = session.run("MATCH (n) RETURN count(n)")
    count = result.single()[0]
    print(f"Nodes: {count}")

driver.close()
```

### API Call
```python
import requests

response = requests.post(
    "http://localhost:8000/api/endpoint",
    json={"field": "value"}
)

if response.status_code == 200:
    print("✓ Success")
else:
    print(f"✗ Error: {response.status_code}")
```

### File Operations
```python
import json

# Read JSON
with open("data.json", "r") as f:
    data = json.load(f)

# Write JSON
with open("output.json", "w") as f:
    json.dump(data, f, indent=2)
```

### Environment Variables
```python
import os
from dotenv import load_dotenv

load_dotenv()

neo4j_uri = os.getenv("NEO4J_URI")
if not neo4j_uri:
    raise ValueError("NEO4J_URI not set")
```

## Script Dependencies

### Python Requirements

Create `requirements-scripts.txt`:
```
neo4j==5.14.0
requests==2.31.0
python-dotenv==1.0.0
```

Install:
```bash
pip install -r support/scripts/requirements-scripts.txt
```

### Shell Dependencies

Ensure these are installed:
- `bash` - Shell interpreter
- `curl` - HTTP client
- `jq` - JSON processor (optional)

## Testing Scripts

Before committing scripts:

1. **Test with sample data**
2. **Handle edge cases** (empty databases, network errors)
3. **Add error messages** that help users debug
4. **Document environment requirements**
5. **Make idempotent** (safe to run multiple times)

## Related Documentation

- [Setup Guide](../setup/README.md) - Environment setup
- [Main README](../README.md) - Support directory overview
- [Project Structure](../../PROJECT_STRUCTURE.md) - Code organization

---

**Maintainer:** Development Team
**Last Updated:** February 6, 2026
