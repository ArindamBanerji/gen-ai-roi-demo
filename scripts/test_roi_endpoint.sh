#!/bin/bash
# Test script for ROI Calculator endpoint
# Usage: bash scripts/test_roi_endpoint.sh
# Requires: Backend running on port 8001

echo "Testing ROI Calculator Endpoint..."
echo ""

# Test 1: Get defaults
echo "1. GET /api/roi/defaults"
curl -s http://localhost:8001/api/roi/defaults | python -m json.tool
echo ""
echo "---"
echo ""

# Test 2: Calculate ROI with default values
echo "2. POST /api/roi/calculate (default values)"
curl -s -X POST http://localhost:8001/api/roi/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "alerts_per_day": 500,
    "analysts": 8,
    "avg_salary": 85000,
    "current_mttr_minutes": 18,
    "current_auto_close_pct": 0.35,
    "avg_escalation_cost": 150
  }' | python -m json.tool
echo ""
echo "---"
echo ""

# Test 3: Calculate ROI with custom values (larger SOC)
echo "3. POST /api/roi/calculate (larger SOC: 1500 alerts/day, 20 analysts)"
curl -s -X POST http://localhost:8001/api/roi/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "alerts_per_day": 1500,
    "analysts": 20,
    "avg_salary": 95000,
    "current_mttr_minutes": 22,
    "current_auto_close_pct": 0.25,
    "avg_escalation_cost": 200
  }' | python -m json.tool
echo ""
echo "---"
echo ""

# Test 4: Calculate ROI with custom values (smaller SOC)
echo "4. POST /api/roi/calculate (smaller SOC: 200 alerts/day, 3 analysts)"
curl -s -X POST http://localhost:8001/api/roi/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "alerts_per_day": 200,
    "analysts": 3,
    "avg_salary": 70000,
    "current_mttr_minutes": 25,
    "current_auto_close_pct": 0.40,
    "avg_escalation_cost": 120
  }' | python -m json.tool
echo ""

echo "✅ ROI Calculator tests complete"
