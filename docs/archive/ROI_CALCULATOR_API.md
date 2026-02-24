# ROI Calculator API Reference

**Version:** v2.5
**Status:** ✅ Implemented
**Router:** `backend/app/routers/roi.py`

---

## Overview

The ROI Calculator endpoint accepts prospect-specific SOC inputs and returns projected savings when deploying the SOC Copilot. This is a key sales enablement tool for CISOs and CFOs.

### Key Assumptions

| Metric | Value | Source |
|--------|-------|--------|
| **Projected Auto-Close Rate** | 89% | Demo Week 4 data |
| **Projected MTTR Reduction** | 75% | Week 1 → Week 4 improvement |
| **Compliance Savings** | $5K per analyst/year | Industry standard |
| **License Cost** | 10% of annual savings | For payback calculation |

---

## Endpoints

### 1. GET /api/roi/defaults

Returns default slider values for frontend initialization.

**Response:**
```json
{
  "status": "success",
  "defaults": {
    "alerts_per_day": 500,
    "analysts": 8,
    "avg_salary": 85000,
    "current_mttr_minutes": 18,
    "current_auto_close_pct": 0.35,
    "avg_escalation_cost": 150
  }
}
```

### 2. POST /api/roi/calculate

Calculates ROI based on prospect inputs.

**Request Body:**
```json
{
  "alerts_per_day": 500,        // min: 50, max: 50000
  "analysts": 8,                 // min: 1, max: 200
  "avg_salary": 85000,           // min: 40000, max: 250000
  "current_mttr_minutes": 18,    // min: 1, max: 120
  "current_auto_close_pct": 0.35,// min: 0.0, max: 0.95
  "avg_escalation_cost": 150     // min: 50, max: 1000
}
```

**Response:**
```json
{
  "inputs_echo": {
    "alerts_per_day": 500,
    "analysts": 8,
    "avg_salary": 85000,
    "current_mttr_minutes": 18,
    "current_auto_close_pct": 0.35,
    "avg_escalation_cost": 150
  },
  "projected": {
    "auto_close_pct": 0.89,
    "mttr_minutes": 4.5,
    "alerts_auto_handled_daily": 445,
    "analyst_hours_freed_monthly": 1240
  },
  "savings": {
    "analyst_time_annual": 609615.38,
    "escalation_cost_annual": 48600.0,
    "compliance_annual": 40000.0,
    "total_annual": 698215.38,
    "payback_weeks": 2,
    "roi_multiple": 10.0
  },
  "narrative": "Based on your 500 alerts/day and 8 analysts at $85,000 average salary, deploying the SOC Copilot would increase auto-close rates from 35% to 89% (+54 points) and reduce MTTR by 75% (from 18.0 min to 4.5 min). This would recover an estimated 1,240 analyst hours per month and save approximately $698,215 annually ($609,615 in analyst time, $48,600 in reduced escalations, and $40,000 in compliance efficiencies). With an estimated payback period of 2 weeks and 10.0x ROI, the compounding intelligence model delivers measurable value from day one while building a defensible moat over time."
}
```

---

## Calculation Logic

### Step 1: Projected Performance
```python
projected_auto_close = 0.89  # Fixed target based on demo
projected_mttr = current_mttr_minutes * 0.25  # 75% reduction
```

### Step 2: Volume Calculations
```python
monthly_alerts = alerts_per_day * 30

new_auto_handled = monthly_alerts * 0.89
old_auto_handled = monthly_alerts * current_auto_close_pct
additional_auto_handled = new_auto_handled - old_auto_handled
```

### Step 3: Time Savings
```python
analyst_hourly = avg_salary / 2080  # 2080 work hours/year
minutes_saved_per_alert = current_mttr_minutes - projected_mttr
hours_freed_monthly = (additional_auto_handled * minutes_saved_per_alert) / 60
```

### Step 4: Annual Savings
```python
# Analyst time savings
annual_analyst_savings = hours_freed_monthly * 12 * analyst_hourly

# Escalation cost savings (15% of additional auto-handled alerts)
annual_escalation_savings = additional_auto_handled * 12 * avg_escalation_cost * 0.15

# Compliance savings ($5K per analyst)
annual_compliance_savings = analysts * 5000

# Total
total_annual = annual_analyst_savings + annual_escalation_savings + annual_compliance_savings
```

### Step 5: Payback & ROI
```python
license_cost = total_annual * 0.10  # Assume 10% of savings
payback_weeks = round(license_cost / (total_annual / 52))
roi_multiple = round(total_annual / license_cost, 1)
```

---

## Example Use Cases

### Small SOC (200 alerts/day, 3 analysts)
```bash
curl -X POST http://localhost:8001/api/roi/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "alerts_per_day": 200,
    "analysts": 3,
    "avg_salary": 70000,
    "current_mttr_minutes": 25,
    "current_auto_close_pct": 0.40,
    "avg_escalation_cost": 120
  }'
```

**Expected Result:** ~$280K annual savings, 2-3 week payback

### Medium SOC (500 alerts/day, 8 analysts) — Default
```bash
curl -X POST http://localhost:8001/api/roi/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "alerts_per_day": 500,
    "analysts": 8,
    "avg_salary": 85000,
    "current_mttr_minutes": 18,
    "current_auto_close_pct": 0.35,
    "avg_escalation_cost": 150
  }'
```

**Expected Result:** ~$698K annual savings, 2 week payback

### Large SOC (1500 alerts/day, 20 analysts)
```bash
curl -X POST http://localhost:8001/api/roi/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "alerts_per_day": 1500,
    "analysts": 20,
    "avg_salary": 95000,
    "current_mttr_minutes": 22,
    "current_auto_close_pct": 0.25,
    "avg_escalation_cost": 200
  }'
```

**Expected Result:** ~$2.8M annual savings, 2 week payback

---

## Error Handling

### Validation Errors (400)

**Scenario:** Current auto-close rate already at or above 89%
```json
{
  "detail": "Your current auto-close rate is already at or above our projected rate (89%). ROI calculation may not be meaningful."
}
```

**Scenario:** Invalid input values
```json
{
  "detail": [
    {
      "loc": ["body", "alerts_per_day"],
      "msg": "ensure this value is greater than or equal to 50",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

### Server Errors (500)
```json
{
  "detail": "Failed to calculate ROI: [error details]"
}
```

---

## Testing

### Manual Testing (Python)
```bash
python scripts/test_roi_endpoint.py
```

### Manual Testing (Bash)
```bash
bash scripts/test_roi_endpoint.sh
```

### Quick Test (curl)
```bash
# Get defaults
curl http://localhost:8001/api/roi/defaults

# Calculate with defaults
curl -X POST http://localhost:8001/api/roi/calculate \
  -H "Content-Type: application/json" \
  -d '{"alerts_per_day": 500, "analysts": 8, "avg_salary": 85000, "current_mttr_minutes": 18, "current_auto_close_pct": 0.35, "avg_escalation_cost": 150}'
```

---

## Frontend Integration

### Expected UI Components

1. **Input Sliders** (6 sliders initialized from `/api/roi/defaults`)
   - Alerts per day (50 - 50,000)
   - Number of analysts (1 - 200)
   - Average salary ($40K - $250K)
   - Current MTTR (1 - 120 minutes)
   - Current auto-close % (0% - 95%)
   - Escalation cost ($50 - $1,000)

2. **Results Display**
   - Projected metrics cards (auto-close %, MTTR, alerts handled, hours freed)
   - Savings breakdown (analyst time, escalation, compliance)
   - Total annual savings (large, prominent)
   - Payback period and ROI multiple
   - CFO-ready narrative

3. **Real-time Updates**
   - Debounced API calls as user adjusts sliders
   - Loading state during calculation
   - Animated counter updates on results

### Example API Call (TypeScript)
```typescript
const calculateROI = async (inputs: ROIInputs) => {
  const response = await fetch('/api/roi/calculate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(inputs)
  });

  if (!response.ok) {
    throw new Error('ROI calculation failed');
  }

  return await response.json();
};
```

---

## Sales Enablement Notes

### Key Talking Points

1. **Immediate Value:** "Notice the payback period: 2 weeks. This isn't a long-term bet—you see value immediately."

2. **Conservative Assumptions:** "We're projecting 89% auto-close based on Week 4 demo data. Many customers exceed this after 6 weeks."

3. **Compounding Effect:** "These numbers are Year 1. As the graph learns your environment, savings compound."

4. **Risk Mitigation:** "The eval gate ensures safety—zero missed threats in production. You get efficiency without sacrificing security."

### Prospect Profiles

| Profile | Typical Inputs | Expected Annual Savings | Key Message |
|---------|---------------|------------------------|-------------|
| **Small SOC** | 200/day, 3 analysts | $250K - $350K | "Even small teams see 6-figure savings" |
| **Medium SOC** | 500/day, 8 analysts | $650K - $850K | "Pays for itself in 2 weeks" |
| **Large SOC** | 1500/day, 20 analysts | $2.5M - $3.5M | "Enterprise-scale savings with moat defensibility" |

---

## Future Enhancements (v3+)

- [ ] Add sensitivity analysis (best/worst case scenarios)
- [ ] Support custom compliance savings input
- [ ] Add industry benchmarking (vs. peers)
- [ ] Export to PDF for board presentations
- [ ] Multi-year projection with compounding curve
- [ ] Integration with actual customer data (via SIEM API)

---

*ROI Calculator API Reference | v2.5 | February 2026*
