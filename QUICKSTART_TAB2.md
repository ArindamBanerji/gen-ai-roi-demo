# Quick Start Guide - Tab 2 (Runtime Evolution)

## Setup (One-Time)

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Make sure your `.env` file has these variables set:

```bash
PROJECT_ID=your-gcp-project
REGION=us-central1
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
VERTEX_AI_LOCATION=us-central1
```

### 3. Seed Neo4j Database

```bash
cd backend
python seed_neo4j.py
```

This creates:
- Alert ALERT-7823 (anomalous login from Singapore)
- User John Smith (VP Finance) with active travel to Singapore
- Pattern PAT-TRAVEL-001 (127 occurrences)
- All necessary relationships

### 4. Frontend Setup

```bash
cd frontend
npm install
```

---

## Running the Demo

### Terminal 1 - Backend

```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Expected output:
```
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8000
✓ Connected to Neo4j
```

### Terminal 2 - Frontend

```bash
cd frontend
npm run dev
```

Expected output:
```
VITE v6.0.3  ready in 200 ms
➜  Local:   http://localhost:5173/
```

---

## Testing Tab 2

### 1. Open Browser

Navigate to: http://localhost:5173

The app should open on **Tab 2: Runtime Evolution** (THE DIFFERENTIATOR)

### 2. Verify Deployment Registry

You should see:
- **v3.1** (active, 90% traffic) - 127 patterns, 73.2% auto-close rate
- **v3.2** (canary, 10% traffic) - 130 patterns, 71.8% auto-close rate

### 3. Click "Process Alert (ALERT-7823)"

Watch the magic happen:

#### Expected Flow:

1. **Eval Gate Panel** appears with 4 checks:
   - ✓ Faithfulness: 0.92 > 0.85 (PASS)
   - ✓ Safe Action: 1.00 = 1.00 (PASS)
   - ✓ Playbook Match: 0.94 > 0.80 (PASS)
   - ✓ SLA Compliance: 0.98 > 0.90 (PASS)
   - **Verdict: ALL GATES PASSED**

2. **Decision Trace** shows:
   - Input: ALERT-7823 (Singapore, 3:47 AM)
   - Context: **47 graph nodes** consulted
   - Decision: **false_positive_close** (92% confidence)
   - Reasoning: LLM-generated explanation about travel + VPN + MFA

3. **🔗 TRIGGERED_EVOLUTION Panel** (THE KEY) appears in purple:
   - Pattern PAT-TRAVEL-001 confidence: **91% → 94% (+3 pts)**
   - Event ID: EVO-XXXX
   - **"Splunk gets better rules. Our copilot gets SMARTER."**

### 4. Click "Simulate Failed Gate"

This demonstrates governance:

1. **Eval Gate Panel** shows:
   - ✓ Faithfulness: 0.92 (PASS)
   - ✗ **Safe Action: 0.00 < 1.00 (FAIL)** ← Critical asset protection
   - ✓ Playbook Match: 0.94 (PASS)
   - ✓ SLA Compliance: 0.92 (PASS)
   - **Verdict: BLOCKED**

2. **No TRIGGERED_EVOLUTION** - Agent didn't execute, so no learning

---

## Verification Checklist

- [ ] Deployment registry shows v3.1 (active) and v3.2 (canary)
- [ ] "Process Alert" button works without errors
- [ ] Eval gate shows 4 checks with scores
- [ ] Decision trace shows "47 nodes consulted"
- [ ] TRIGGERED_EVOLUTION panel appears with pattern confidence increase
- [ ] "Simulate Failed Gate" shows blocked execution
- [ ] Backend logs show Neo4j connection success
- [ ] No console errors in browser DevTools

---

## Troubleshooting

### "Alert ALERT-7823 not found"
```bash
cd backend
python seed_neo4j.py
```

### "Connection refused to Neo4j"
- Check NEO4J_URI in `.env`
- Verify Neo4j Aura instance is running
- Test connection: `neo4j+s://xxxxx.databases.neo4j.io`

### "Module not found" errors
```bash
cd backend
pip install -r requirements.txt
```

### Frontend can't reach backend
- Verify backend is running on port 8000
- Check Vite proxy config in `vite.config.ts`
- Open http://localhost:8000/health (should return `{"status": "healthy"}`)

### Vertex AI errors
- Check PROJECT_ID in `.env`
- Verify Vertex AI API is enabled in GCP
- Check service account has Vertex AI permissions
- Fallback reasoning will be used if Vertex AI fails

---

## API Endpoints (for testing)

### Get Deployments
```bash
curl http://localhost:8000/api/deployments
```

### Process Alert (CLI)
```bash
curl -X POST http://localhost:8000/api/alert/process \
  -H "Content-Type: application/json" \
  -d '{"alert_id": "ALERT-7823", "simulate_failure": false}'
```

### Simulate Failed Gate
```bash
curl -X POST http://localhost:8000/api/eval/simulate-failure
```

---

## Next Steps

Once Tab 2 is working:

1. **Tab 3: Alert Triage** - Graph visualization + closed loop
2. **Tab 1: SOC Analytics** - Metric queries + governance
3. **Tab 4: Compounding** - Week-over-week improvement

---

## The Key Differentiator

> **TRIGGERED_EVOLUTION**: (:Decision)-[:TRIGGERED_EVOLUTION]->(:EvolutionEvent)

This relationship is what separates memory from learning.

**Traditional SIEMs**: Alert → Detect → Log → (manual tuning)
**Our SOC Copilot**: Alert → Detect → Graph → **Automatic Evolution**

"When a competitor deploys, they start at zero. We start at 127 patterns. That's the moat."
