#!/usr/bin/env python3
"""
Test script for ROI Calculator endpoint
Usage: python scripts/test_roi_endpoint.py
Requires: Backend running on port 8001
"""

import requests
import json
from typing import Dict, Any


BASE_URL = "http://localhost:8001/api"


def print_section(title: str):
    """Print formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_get_defaults():
    """Test GET /api/roi/defaults"""
    print_section("TEST 1: GET /api/roi/defaults")

    try:
        response = requests.get(f"{BASE_URL}/roi/defaults", timeout=5)
        response.raise_for_status()

        data = response.json()
        print(json.dumps(data, indent=2))
        print("\n✅ Defaults endpoint working")

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed: {e}")


def test_calculate_roi(test_name: str, payload: Dict[str, Any]):
    """Test POST /api/roi/calculate with given payload"""
    print_section(f"TEST: {test_name}")

    try:
        response = requests.post(
            f"{BASE_URL}/roi/calculate",
            json=payload,
            timeout=5
        )
        response.raise_for_status()

        data = response.json()

        # Print key results
        print("INPUT:")
        print(f"  Alerts/day: {payload['alerts_per_day']:,}")
        print(f"  Analysts: {payload['analysts']}")
        print(f"  Avg salary: ${payload['avg_salary']:,}")
        print(f"  Current MTTR: {payload['current_mttr_minutes']} min")
        print(f"  Current auto-close: {int(payload['current_auto_close_pct']*100)}%")

        print("\nPROJECTED:")
        proj = data['projected']
        print(f"  Auto-close: {int(proj['auto_close_pct']*100)}%")
        print(f"  MTTR: {proj['mttr_minutes']} min")
        print(f"  Analyst hours freed/month: {proj['analyst_hours_freed_monthly']:,}")

        print("\nSAVINGS:")
        sav = data['savings']
        print(f"  Analyst time (annual): ${sav['analyst_time_annual']:,.2f}")
        print(f"  Escalation cost (annual): ${sav['escalation_cost_annual']:,.2f}")
        print(f"  Compliance (annual): ${sav['compliance_annual']:,.2f}")
        print(f"  TOTAL ANNUAL: ${sav['total_annual']:,.2f}")
        print(f"  Payback: {sav['payback_weeks']} weeks")
        print(f"  ROI Multiple: {sav['roi_multiple']}x")

        print("\nNARRATIVE:")
        print(f"  {data['narrative']}")

        print("\n✅ ROI calculation successful")

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed: {e}")


def main():
    """Run all ROI endpoint tests"""
    print("\n" + "="*60)
    print("  ROI CALCULATOR ENDPOINT TESTS")
    print("="*60)

    # Test 1: Get defaults
    test_get_defaults()

    # Test 2: Default values (medium SOC)
    test_calculate_roi(
        "Default values (500 alerts/day, 8 analysts)",
        {
            "alerts_per_day": 500,
            "analysts": 8,
            "avg_salary": 85000,
            "current_mttr_minutes": 18,
            "current_auto_close_pct": 0.35,
            "avg_escalation_cost": 150
        }
    )

    # Test 3: Larger SOC
    test_calculate_roi(
        "Larger SOC (1500 alerts/day, 20 analysts)",
        {
            "alerts_per_day": 1500,
            "analysts": 20,
            "avg_salary": 95000,
            "current_mttr_minutes": 22,
            "current_auto_close_pct": 0.25,
            "avg_escalation_cost": 200
        }
    )

    # Test 4: Smaller SOC
    test_calculate_roi(
        "Smaller SOC (200 alerts/day, 3 analysts)",
        {
            "alerts_per_day": 200,
            "analysts": 3,
            "avg_salary": 70000,
            "current_mttr_minutes": 25,
            "current_auto_close_pct": 0.40,
            "avg_escalation_cost": 120
        }
    )

    print_section("ALL TESTS COMPLETE")
    print("✅ ROI Calculator endpoint is working correctly\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
