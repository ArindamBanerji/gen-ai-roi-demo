"""
Quick test script for policy conflict endpoints.
Run this while the backend server is running on port 8001.
"""
import requests

BASE_URL = "http://localhost:8001/api"

def test_policy_check():
    """Test GET /api/alert/policy-check"""
    print("\n" + "="*60)
    print("TEST 1: Policy Check for ALERT-7823 (should conflict)")
    print("="*60)

    response = requests.get(f"{BASE_URL}/alert/policy-check?alert_id=ALERT-7823")
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
        print("✓ Test 1 PASSED")
    else:
        print(f"✗ Test 1 FAILED: {response.text}")


def test_policy_check_no_conflict():
    """Test GET /api/alert/policy-check for alert with no conflict"""
    print("\n" + "="*60)
    print("TEST 2: Policy Check for ALERT-7824 (no conflict)")
    print("="*60)

    response = requests.get(f"{BASE_URL}/alert/policy-check?alert_id=ALERT-7824")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Has conflict: {data['has_conflict']}")
        print(f"Policies applied: {[p['id'] for p in data['policies_applied']]}")

        assert not data['has_conflict'], "ALERT-7824 should NOT have a conflict!"
        print("✓ Test 2 PASSED")
    else:
        print(f"✗ Test 2 FAILED: {response.text}")


def test_policy_history():
    """Test GET /api/alert/policy-history"""
    print("\n" + "="*60)
    print("TEST 3: Policy Conflict History")
    print("="*60)

    response = requests.get(f"{BASE_URL}/alert/policy-history")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Total conflicts resolved: {data['total_count']}")

        for i, conflict in enumerate(data['conflicts'], 1):
            print(f"\nConflict {i}:")
            print(f"  Audit ID: {conflict['audit_id']}")
            print(f"  Winner: {conflict['winning_policy']}")
            print(f"  Loser: {conflict['losing_policy']}")

        print("✓ Test 3 PASSED")
    else:
        print(f"✗ Test 3 FAILED: {response.text}")


def test_reset():
    """Test POST /api/alerts/reset"""
    print("\n" + "="*60)
    print("TEST 4: Reset All Demo State")
    print("="*60)

    response = requests.post(f"{BASE_URL}/alerts/reset")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Message: {data['message']}")
        print(f"Alerts reset: {data['reset_count']}")
        print("✓ Test 4 PASSED")
    else:
        print(f"✗ Test 4 FAILED: {response.text}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("POLICY CONFLICT ENDPOINT TESTS")
    print("="*60)
    print("Make sure backend is running on port 8001")
    print()

    try:
        test_policy_check()
        test_policy_check_no_conflict()
        test_policy_history()
        test_reset()

        print("\n" + "="*60)
        print("ALL TESTS PASSED!")
        print("="*60)

    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Could not connect to backend.")
        print("Make sure the server is running: cd backend && uvicorn app.main:app --port 8001")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
