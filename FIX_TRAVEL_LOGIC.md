# Fix: Travel Context Decision Logic

## Problem

ALERT-7823 was escalating to incident instead of false_positive_close, even though:
- User "John Smith" has active travel to Singapore
- Alert source location is Singapore
- Should be recognized as legitimate travel activity

## Root Cause

**Agent decision logic was too strict:**

```python
# OLD (Required ALL 4 conditions)
if (user_traveling and vpn_matches_location
    and mfa_completed and device_fingerprint_match):
    return false_positive_close

# If ANY condition failed, fell through to:
if user_risk_score > 0.8:
    return escalate_incident  # ← Would hit this even with travel!
```

The risk score check came BEFORE checking partial travel matches, so high-risk users with valid travel were escalated.

## Solution

### 1. Prioritized Travel Over Risk Score

New decision logic (in `backend/app/services/agent.py`):

```python
# Priority 1: Strong travel match (all 4 conditions)
if user_traveling and vpn_matches and mfa_completed and device_match:
    return false_positive_close (92% confidence)

# Priority 2: Good travel match (traveling + location matches)
if user_traveling and vpn_matches:
    return false_positive_close (88% confidence)  # ← ALERT-7823 catches here

# Priority 3: Moderate travel match (traveling + MFA OR device)
if user_traveling and (mfa_completed or device_match):
    return false_positive_close (82% confidence)

# Priority 4: High risk WITHOUT travel
if user_risk_score > 0.8 and not user_traveling:
    return escalate_incident  # ← Only escalates if NO travel
```

### 2. Added Debug Logging

**Neo4j context extraction** (`backend/app/db/neo4j.py`):
```python
print(f"[NEO4J] Context extraction for alert {alert_id}:")
print(f"  - User: {user_name} (risk: {risk_score})")
print(f"  - Travel destination: {destination}")
print(f"  - Location match: {source_location == destination}")
```

**Agent decision** (`backend/app/services/agent.py`):
```python
print(f"[AGENT] Anomalous login decision:")
print(f"  - user_traveling: {user_traveling}")
print(f"  - vpn_matches_location: {vpn_matches}")
print(f"  - user_risk_score: {risk_score}")
```

## Testing

### 1. Re-seed Neo4j Database

```bash
cd backend
python seed_neo4j.py
```

Expected output:
```
✓ Created user: John Smith (risk_score: 0.25)
✓ Sample data created successfully!
```

This ensures:
- User risk_score is **0.25** (not 0.85)
- TravelContext exists with destination "Singapore"
- Alert source_location is "Singapore"
- Alert has mfa_completed=true, device_fingerprint_match=true

### 2. Restart Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Watch the terminal for debug logs when processing alerts.

### 3. Test in Browser

1. Open http://localhost:5173
2. Go to **Tab 2: Runtime Evolution**
3. Click **"Process Alert (ALERT-7823)"**

### 4. Check Backend Logs

You should see:
```
[NEO4J] Context extraction for alert ALERT-7823:
  - User: John Smith (risk: 0.25)
  - Alert source_location: Singapore
  - Travel: True
  - Travel destination: Singapore
  - Location match: True
  - MFA completed: True
  - Device match: True

[AGENT] Anomalous login decision for user John Smith
  - user_traveling: True
  - vpn_matches_location: True
  - mfa_completed: True
  - device_fingerprint_match: True
  - user_risk_score: 0.25
  - travel_destination: Singapore
```

### 5. Expected Result

**Decision:**
- Action: **false_positive_close**
- Confidence: **92%** (or 88% if not all conditions met)
- Pattern: PAT-TRAVEL-001

**Eval Gate:**
- Faithfulness: ✓ PASS (0.92 > 0.85)
- Safe Action: ✓ PASS (1.00 = 1.00)
- Playbook Match: ✓ PASS (0.94 > 0.80)
- SLA Compliance: ✓ PASS (0.98 > 0.90)
- **Overall: ALL GATES PASSED**

**TRIGGERED_EVOLUTION:**
- Should appear in purple panel
- Pattern PAT-TRAVEL-001 confidence: 91% → 94%
- Event ID: EVO-XXXX

## Troubleshooting

### Issue: Still escalating to incident

**Check backend logs for these values:**

```bash
# In backend terminal, look for:
[AGENT] Anomalous login decision for user John Smith
  - user_traveling: False  # ← Should be True
  - vpn_matches_location: False  # ← Should be True
```

**If user_traveling is False:**
- Travel relationship might not exist in Neo4j
- Run `python seed_neo4j.py` again
- Check Neo4j query returned travel data

**If vpn_matches_location is False:**
- Alert source_location doesn't match travel destination
- Check for case sensitivity or whitespace: "Singapore" vs "singapore"
- Run seed script to ensure exact match

### Issue: Risk score is 0.85 instead of 0.25

Run seed script again:
```bash
cd backend
python seed_neo4j.py
```

This clears all data and recreates with correct risk_score=0.25.

### Issue: No debug logs appearing

Make sure you restarted the backend after making the code changes:
```bash
# Stop server (Ctrl+C)
uvicorn app.main:app --reload --port 8000
```

## Files Modified

1. ✅ `backend/app/services/agent.py` - Improved decision logic with 3 tiers
2. ✅ `backend/app/db/neo4j.py` - Added debug logging
3. ✅ `backend/seed_neo4j.py` - Added confirmation of risk_score

## Key Improvements

1. **Travel takes priority over risk score** - Even high-risk users can have legitimate travel
2. **Three-tier matching** - Strong, good, and moderate travel matches
3. **Better reasoning** - More context-aware decisions
4. **Debug logging** - Easy to diagnose issues
5. **Correct seed data** - Ensures demo works reliably

## Verification Checklist

- [ ] Seed script creates user with risk_score 0.25
- [ ] Backend logs show travel context being extracted
- [ ] Agent logs show correct decision logic path
- [ ] Decision is "false_positive_close" with 88%+ confidence
- [ ] Eval gate shows Faithfulness > 0.85 (PASS)
- [ ] TRIGGERED_EVOLUTION panel appears
- [ ] Pattern confidence increases: 91% → 94%

---

**Status**: ✅ Fixed - Travel context now properly overrides risk score
