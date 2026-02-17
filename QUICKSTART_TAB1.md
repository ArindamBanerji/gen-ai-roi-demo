# Quick Start Guide - Tab 1 (SOC Analytics)

## What This Tab Proves

**"Instant answers with provenance showing exactly where the data came from."**

This tab demonstrates:
1. **Natural language queries** - Ask questions in plain English
2. **Metric matching** - AI recognizes MTTR, FP rate, auto-close queries
3. **Governed metrics** - Every metric has a contract (owner, definition, version)
4. **Provenance** - Full transparency on data sources and freshness
5. **Rule sprawl detection** - Identifies deprecated rules still active
6. **Immediate SOC value** - No training needed, works Day 1

---

## Setup (Already Done)

Tab 1 uses **mock data** - no BigQuery setup required!

### Backend Already Has:
- ✅ 6 security metrics (MTTR, auto-close, FP rate, etc.)
- ✅ Keyword-based matching
- ✅ Mock data generators
- ✅ Rule sprawl detection

### Just Restart Backend:

```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

---

## Testing Tab 1

### 1. Open Browser

Navigate to: http://localhost:5173

Click on **Tab 1: SOC Analytics**

### 2. See Query Input

```
┌─────────────────────────────────────────────┐
│ Ask a security question:                   │
│ ┌─────────────────────────────────────────┐│
│ │ 🔍 e.g., What was MTTR last week...    ││
│ └─────────────────────────────────────────┘│
│                                             │
│ Try these examples:                         │
│ [What's our MTTR by severity?]             │
│ [Show me auto-close rate trend]            │
│ [What's our false positive rate?]          │
└─────────────────────────────────────────────┘
```

### 3. Test Query 1: MTTR by Severity

**Type or click:** "What's our MTTR by severity?"

**Expected Result:**

#### Answer Panel (Left, 2/3 width)
- **Matched**: mttr_by_severity • Confidence: 96%
- **Bar Chart** showing:
  - Critical: 8.2 min
  - High: 14.7 min
  - Medium: 45.3 min
  - Low: 4.2h (252 min)

#### Governance Panel (Right, 1/3 width)

**Metric Contract:**
```
Name: MTTR by Severity (v2.1)
Owner: soc_analytics@company.com
Status: active ✓
Definition: Mean time to respond (close) by alert severity level
```

**Provenance:**
```
Sources:
  - Splunk SIEM
  - ServiceNow ITSM

Freshness: 1.2 hours ago ✓

Query Preview:
SELECT severity, AVG(resolution_time_minutes)
FROM soc.alerts
WHERE created_at > TIMESTAMP_SUB(...)
GROUP BY severity
```

**No sprawl alert** (only appears for FP rate query)

---

### 4. Test Query 2: Auto-Close Rate

**Type or click:** "Show me auto-close rate trend"

**Expected Result:**

#### Answer Panel
- **Matched**: auto_close_rate • Confidence: 96%
- **Line Chart** showing 7 days:
  - Day 1: 68.0%
  - Day 2: 71.5%
  - Day 3: 75.0%
  - ...
  - Day 7: 89.0%
- **Upward trend** (shows compounding improvement!)

#### Governance Panel
```
Sources:
  - Splunk SIEM
  - SOC Copilot Decision Log

Freshness: 30 minutes ago ✓
```

---

### 5. Test Query 3: False Positive Rate (WITH SPRAWL ALERT)

**Type or click:** "What's our false positive rate?"

**Expected Result:**

#### Answer Panel
- **Matched**: fp_rate_by_rule • Confidence: 96%
- **Bar Chart** showing:
  - anomalous_login: 12.5%
  - phishing_email: 8.3%
  - malware_detection: 5.1%
  - data_exfiltration: 3.2%
  - **anomalous_login_legacy: 45.8%** ← The problem!

#### Rule Sprawl Alert (APPEARS BELOW)

```
⚠️ DETECTION RULE SPRAWL DETECTED

Duplicate Rule: anomalous_login_legacy
Deprecated: 2025-12-01
Still Active In: 3 pipelines

Monthly Alert Impact: 2,400 alerts
Est. Analyst Cost: $18K/mo

Removing this deprecated rule would save:
~80 alerts/day and reduce analyst workload by ~8 hours/week

[View Details]  [Deprecate Now]
```

**This is the wow moment** - the system detects wasteful rules automatically!

---

## All Available Queries

### Supported Metrics:

| Query Examples | Metric ID | Chart Type |
|----------------|-----------|------------|
| "What's our MTTR by severity?" | mttr_by_severity | Bar |
| "Show me auto-close rate" | auto_close_rate | Line |
| "What's our false positive rate?" | fp_rate_by_rule | Bar |
| "Show escalation rate" | escalation_rate | Line |
| "How's our MTTD?" | mttd_by_source | Bar |
| "Show analyst efficiency" | analyst_efficiency | Bar |

### Try These Variations:

- "What was MTTR last week?"
- "Show me FP rate by rule"
- "How many alerts are we auto-closing?"
- "What's our incident escalation rate?"
- "Show detection time by source"
- "How efficient are our analysts?"

All work! The keyword matching is flexible.

---

## Key Features to Verify

### ✅ Natural Language Matching
- [ ] Can type question or click example
- [ ] Enter key works
- [ ] Query button works
- [ ] Different phrasings match same metric

### ✅ Chart Display
- [ ] Bar chart for MTTR (4 bars)
- [ ] Line chart for auto-close (7 points, upward trend)
- [ ] Tooltips show formatted values
- [ ] Data points table below chart

### ✅ Governance Panel
- [ ] Metric Contract shows name, owner, version, status
- [ ] Provenance shows sources (2+ systems)
- [ ] Freshness indicator (green < 2hrs, yellow 2-6hrs)
- [ ] Query preview shows SQL snippet

### ✅ Rule Sprawl Alert
- [ ] Only appears for FP rate query
- [ ] Shows deprecated rule with high FP rate (45.8%)
- [ ] Shows impact: 2,400 alerts/month, $18K cost
- [ ] Shows savings if deprecated: 80 alerts/day

---

## Value Propositions (For Demo)

### For CISOs:

1. **No training needed** - Natural language, works Day 1
2. **Governed metrics** - Every metric has owner and contract
3. **Full auditability** - See exactly where data comes from
4. **Cost savings** - Rule sprawl detection finds waste ($18K/month!)
5. **Trust** - Provenance = no black box

### For VCs:

1. **Immediate value** - Unlike other AI solutions that need months
2. **Network effect** - More queries → better matching
3. **Metric marketplace potential** - Could sell metric packs
4. **Enterprise wedge** - Start with analytics, expand to full platform

---

## API Endpoints (for testing)

### Query Metric
```bash
curl -X POST http://localhost:8000/api/soc/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is our MTTR by severity?"}'
```

Expected: Full result with chart data, provenance, no sprawl alert

### List Available Metrics
```bash
curl http://localhost:8000/api/soc/metrics
```

Expected: Array of 6 metrics with example questions

---

## Troubleshooting

### Issue: Query returns 404 "Could not match question"

**Cause**: Question doesn't match any metric keywords

**Fix**: Try one of the example questions first, or use keywords:
- "MTTR" or "response time"
- "auto close" or "false positive"
- "escalation" or "incident"

### Issue: Chart not rendering

**Check**:
1. Browser console for errors
2. Recharts library installed: `npm install` in frontend folder
3. Data structure matches expected format

### Issue: Sprawl alert not appearing

**Expected**: Only shows for FP rate queries
- Try: "What's our false positive rate?"
- Should match: fp_rate_by_rule
- Then sprawl alert appears

---

## Demo Script (10 seconds)

1. **"Watch this"** → Type "What's our MTTR by severity?"
2. **Click Query** → Chart appears in <1 second
3. **Point to governance** → "See the provenance? Splunk + ServiceNow"
4. **Point to freshness** → "1.2 hours ago - trustworthy"
5. **Ask FP rate** → "What's our false positive rate?"
6. **Sprawl alert appears** → "Whoa! Deprecated rule costing $18K/month!"
7. **Deliver soundbite** → **"Instant answers with full provenance."**

---

## Architecture Highlight

```
┌─────────────────────────────────────────┐
│  Natural Language Query                 │
│  "What's our MTTR?"                     │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  Keyword Matching                       │
│  "mttr" → mttr_by_severity             │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  Mock Data Generator                    │
│  (In production: BigQuery)              │
│  Returns: [{label, value}]              │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  Governance Enrichment                  │
│  - Metric contract                      │
│  - Provenance (sources + freshness)    │
│  - Rule sprawl check                    │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  Frontend Rendering                     │
│  - Recharts visualization               │
│  - Governance panel                     │
│  - Sprawl alert (if detected)           │
└─────────────────────────────────────────┘
```

---

## Files Created for Tab 1

1. ✅ `backend/app/routers/soc.py` (~500 lines)
   - POST /api/soc/query
   - GET /api/soc/metrics
   - Metric registry (6 metrics)
   - Keyword matching logic
   - Mock data generators
   - Provenance builder
   - Rule sprawl detector

2. ✅ `frontend/src/components/tabs/SOCAnalyticsTab.tsx` (~476 lines)
   - Natural language input
   - Example question chips
   - Recharts integration (Bar + Line)
   - Metric contract panel
   - Provenance panel
   - Rule sprawl alert

3. ✅ `backend/app/main.py` (updated)
   - Registered SOC router

---

**Status**: ✅ Tab 1 Complete - SOC Analytics with Governed Metrics

**Next**: Tab 4 (Compounding Dashboard) - The final 15%

---

## The Key Differentiator for Tab 1:

> **"Your SOC spends hours building dashboards. We give instant answers with provenance."**

Traditional BI tools:
- Take days to build dashboards
- Black box - where did data come from?
- No governance
- No rule sprawl detection

Our SOC Analytics:
- ✅ Natural language - ask anything
- ✅ Instant answers
- ✅ Full provenance
- ✅ Metric contracts
- ✅ Automatic problem detection (sprawl)
- ✅ Works Day 1
