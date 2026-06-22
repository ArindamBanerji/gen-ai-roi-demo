"""
Quick test script for policy conflict endpoints.
Run this while the backend server is running on port 8001.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

BASE_URL = "/api"

def test_policy_check():
    """Test GET /api/alert/policy-check"""
    print("\n" + "="*60)
    print("TEST 1: Policy Check for ALERT-7823 (should conflict)")
    print("="*60)

    response = client.get(f"{BASE_URL}/alert/policy-check?alert_id=ALERT-7823")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Has conflict: {data['has_conflict']}")
        print(f"Policies applied: {[p['id'] for p in data['policies_applied']]}")

        if data['has_conflict'] and data['resolution']:
            print(f"Winner: {data['resolution']['winning_policy']}")
            print(f"Loser: {data['resolution']['losing_policy']}")
            print(f"Audit ID: {data['resolution']['audit_id']}")
            print(f"Action adjusted: {data['resolution']['original_action']} -> {data['resolution']['action_adjusted']}")

        assert data['has_conflict'], "ALERT-7823 should have a conflict!"
        print("[OK] Test 1 PASSED")
    else:
        print(f"[FAIL] Test 1 FAILED: {response.text}")


def test_policy_check_no_conflict():
    """Test GET /api/alert/policy-check for alert with no conflict"""
    print("\n" + "="*60)
    print("TEST 2: Policy Check for ALERT-7824 (no conflict)")
    print("="*60)

    response = client.get(f"{BASE_URL}/alert/policy-check?alert_id=ALERT-7824")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Has conflict: {data['has_conflict']}")
        print(f"Policies applied: {[p['id'] for p in data['policies_applied']]}")

        assert not data['has_conflict'], "ALERT-7824 should NOT have a conflict!"
        print("[OK] Test 2 PASSED")
    else:
        print(f"[FAIL] Test 2 FAILED: {response.text}")


def test_policy_history():
    """Test GET /api/alert/policy-history"""
    print("\n" + "="*60)
    print("TEST 3: Policy Conflict History")
    print("="*60)

    response = client.get(f"{BASE_URL}/alert/policy-history")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Total conflicts resolved: {data['total_count']}")

        for i, conflict in enumerate(data['conflicts'], 1):
            print(f"\nConflict {i}:")
            print(f"  Audit ID: {conflict['audit_id']}")
            print(f"  Winner: {conflict['winning_policy']}")
            print(f"  Loser: {conflict['losing_policy']}")

        print("[OK] Test 3 PASSED")
    else:
        print(f"[FAIL] Test 3 FAILED: {response.text}")


def test_reset():
    """Test POST /api/alerts/reset"""
    print("\n" + "="*60)
    print("TEST 4: Reset All Demo State")
    print("="*60)

    response = client.post(f"{BASE_URL}/alerts/reset")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Message: {data['message']}")
        print(f"Alerts reset: {data['reset_count']}")
        print("[OK] Test 4 PASSED")
    else:
        print(f"[FAIL] Test 4 FAILED: {response.text}")
