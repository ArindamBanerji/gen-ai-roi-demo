# Quick Start Guide - Tab 3 (Alert Triage)

## What This Tab Proves

**"A SIEM stops at detect. We close the loop."**

This tab demonstrates:
1. **Graph-based reasoning** - 47 nodes consulted for context
2. **Intelligent recommendations** - AI-driven triage decisions
3. **Closed-loop execution** - 4-step verification from decision → KPI impact
4. **Full auditability** - Decision traces captured in Neo4j

---

## Setup (First Time)

### 1. Re-seed Database (Add More Alerts)

```bash
cd backend
python seed_neo4j.py
```

This now creates **5 alerts** for the queue:
- ALERT-7823: anomalous_login (medium) - Singapore travel
- ALERT-7822: phishing (high) - suspicious link
- ALERT-7821: malware_detection (critical) - prod server
- ALERT-7820: anomalous_login (low) - unusual time
- ALERT-7819: phishing (medium) - suspicious attachment

### 2. Restart Backend

```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Expected output:
```
✓ Connected to Neo4j
INFO:     Application startup complete.
```

### 3. Frontend (if not running)

```bash
cd frontend
npm run dev
```

---

## Testing Tab 3

### 1. Open Browser

Navigate to: http://localhost:5173

Click on **Tab 3: Alert Triage**

### 2. Alert Queue (Left Sidebar)

You should see:
```
┌─ Alert Queue [5] ──┐
│ ALERT-7823  MEDIUM │  ← Auto-selected
│ ALERT-7822  HIGH   │
│ ALERT-7821  CRITICAL│
│ ALERT-7820  LOW    │
│ ALERT-7819  MEDIUM │
└────────────────────┘
```

### 3. Click on ALERT-7823

**Expected Flow:**

#### A. Selected Alert Details
```
Type: anomalous login
Source: Singapore
Asset: LAPTOP-JSMITH
User: John Smith
```

#### B. Security Context Graph
- Displays **6-7 nodes** as colored boxes:
  - 🔴 Alert (ALERT-7823)
  - 🔵 User (John Smith)
  - 🟢 Asset (LAPTOP-JSMITH)
  - 🟣 TravelContext (Singapore)
  - 🟡 AttackPattern (PAT-TRAVEL-001)
  - ⚪ Playbook (PB-LOGIN-FP)

**Key Facts:**
- [TravelContext] User traveling to Singapore
- [AttackPattern] Pattern PAT-TRAVEL-001 matched (127 occurrences)
- [Alert] MFA authentication completed

#### C. Recommendation Panel
```
✓ FALSE POSITIVE CLOSE
Confidence: 88-92%

Reasoning:
"User John Smith has active travel to Singapore..."

[Apply Recommendation] button
```

### 4. Click "Apply Recommendation"

**Watch the Closed Loop Animation:**

The panel will animate through 4 steps (800ms each):

```
✓ CLOSED LOOP (What SIEMs don't do)

1. ✓ EXECUTED
   Alert ALERT-7823 marked as resolved
   Target: Splunk SIEM

2. ✓ VERIFIED
   Outcome confirmed via API status check

3. ✓ EVIDENCE
   Decision trace DEC-XXXX captured
   47 nodes consulted

4. ✓ KPI IMPACT
   This resolution: MTTR ↓4.2 minutes
   Previous: 15.3 min → New: 11.1 min

"A SIEM stops at detect. We close the loop."
```

After 3.2 seconds:
- Alert queue refreshes (ALERT-7823 removed)
- Next alert auto-selected

---

## Testing Other Alerts

### ALERT-7822 (Phishing - High)
- **Expected**: Escalate to Tier 2 or Auto-remediate
- **Graph**: No travel context
- **Reasoning**: "Suspicious link clicked without known campaign"

### ALERT-7821 (Malware - Critical)
- **Expected**: Escalate Incident
- **Graph**: Critical server (SRV-DB-PROD-01)
- **Reasoning**: "Critical asset compromised, immediate incident response"

### ALERT-7820 (Login - Low)
- **Expected**: Auto-close or Tier 2
- **Graph**: Local login, no travel
- **Reasoning**: "Unusual time but local location"

---

## Key Features to Verify

### ✅ Alert Queue
- [ ] Shows 5 alerts with color-coded severity badges
- [ ] Click on alert auto-analyzes
- [ ] Selected alert highlighted with blue left border

### ✅ Graph Visualization
- [ ] Shows 6-7 colored node boxes
- [ ] Each node shows type + label + properties
- [ ] Displays "[47 nodes] [5 subgraphs] [1-3 patterns]"
- [ ] Key Facts section lists relevant context

### ✅ Recommendation Panel
- [ ] Shows action with confidence %
- [ ] LLM-generated reasoning (2-3 sentences)
- [ ] Pattern ID shown if applicable
- [ ] "Apply Recommendation" button enabled

### ✅ Closed Loop Execution
- [ ] 4 steps animate sequentially
- [ ] Each step shows green checkmark when complete
- [ ] KPI impact shows MTTR reduction
- [ ] Soundbite appears at bottom
- [ ] Alert queue refreshes after execution

---

## API Endpoints (for testing)

### Get Alert Queue
```bash
curl http://localhost:8000/api/alerts/queue
```

Expected: Array of 5 alerts

### Analyze Alert
```bash
curl -X POST http://localhost:8000/api/alert/analyze \
  -H "Content-Type: application/json" \
  -d '{"alert_id": "ALERT-7823"}'
```

Expected: Full analysis with graph_data

### Execute Action
```bash
curl -X POST http://localhost:8000/api/action/execute \
  -H "Content-Type: application/json" \
  -d '{"alert_id": "ALERT-7823"}'
```

Expected: Closed loop result with 4 steps

---

## Troubleshooting

### Issue: Alert queue is empty

**Fix:**
```bash
cd backend
python seed_neo4j.py
```

### Issue: Graph shows no nodes

**Possible causes:**
1. Alert not found in Neo4j
2. Relationships not created

**Fix:**
Run seed script again. Check backend logs for Neo4j errors.

### Issue: Recommendation says "escalate_incident" for ALERT-7823

**This means:**
- Travel logic isn't working
- Check faithfulness scoring
- See `FIX_TRAVEL_LOGIC.md` and `FIX_FAITHFULNESS_SCORE.md`

### Issue: Closed loop doesn't animate

**Check:**
1. Browser console for JavaScript errors
2. Backend logs for API errors
3. Make sure `executeAction` API returns valid data

### Issue: Alert queue doesn't refresh after execution

**This is normal** - The refresh happens after 3.2 seconds. If alert still shows, check:
```bash
# Query Neo4j directly
MATCH (a:Alert {id: 'ALERT-7823'}) RETURN a.status
# Should be 'resolved'
```

---

## What Makes This Different From SIEMs

| Traditional SIEM | Our SOC Copilot (Tab 3) |
|------------------|-------------------------|
| Shows alert | Shows alert **+ 47 nodes of context** |
| Detection rule fires | Graph traversal **finds patterns** |
| Analyst manually triages | AI **recommends action** with reasoning |
| **Stops at detection** | **Closes the loop** with 4-step verification |
| No decision audit | **Decision trace** captured in graph |
| No KPI attribution | Shows **MTTR impact** per decision |

---

## Demo Flow (15 seconds)

1. **Point to alert queue** (3 alerts visible)
2. **Click ALERT-7823** → Graph lights up
3. **Show recommendation** → "False positive close, 92% confidence"
4. **Click Apply** → Watch 4 steps animate
5. **Point to KPI** → "MTTR down 4.2 minutes"
6. **Deliver soundbite** → "A SIEM stops at detect. We close the loop."

---

## Architecture Highlight

```
┌─────────────────────────────────────────┐
│  Alert Queue (5 alerts pending)         │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  Security Graph (Neo4j)                 │
│  - 47 nodes consulted                   │
│  - 5 subgraphs traversed                │
│  - Pattern matching                     │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  Agent Decision                         │
│  - Rule-based logic                     │
│  - LLM narration                        │
│  - Pattern confidence                   │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  Closed Loop Execution                  │
│  1. EXECUTED   → Splunk SIEM            │
│  2. VERIFIED   → Outcome confirmed      │
│  3. EVIDENCE   → Decision trace saved   │
│  4. KPI IMPACT → MTTR improvement       │
└─────────────────────────────────────────┘
```

---

## Files Created for Tab 3

1. ✅ `backend/app/routers/triage.py` (~400 lines)
   - GET /api/alerts/queue
   - POST /api/alert/analyze
   - POST /api/action/execute
   - Graph data extraction

2. ✅ `frontend/src/components/tabs/AlertTriageTab.tsx` (~518 lines)
   - Alert queue sidebar
   - Graph visualization (simple colored boxes)
   - Recommendation panel
   - Closed loop animation

3. ✅ `backend/seed_neo4j.py` (updated)
   - Added 4 more alerts
   - Added 2 more users
   - Added 1 more asset (critical server)
   - Added more alert types

4. ✅ `backend/app/main.py` (updated)
   - Registered triage router

---

**Status**: ✅ Tab 3 Complete - Alert Triage with Closed Loop
**Next**: Tab 1 (SOC Analytics) or Tab 4 (Compounding Dashboard)

---

**The Key Differentiator for Tab 3:**
> "Every SOC shows you what happened. We show you what happened, **why it happened**, what we did, **and the impact it had**. That's the closed loop."
