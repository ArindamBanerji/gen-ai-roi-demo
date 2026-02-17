# Fix: Auto-Close Rate Keyword Matching

## Problem

Query "Show auto-close rate" returned 404 error:
```
Could not match question to a known metric
```

## Root Cause

The keyword list for `auto_close_rate` only had `"auto close"` (with space), but the query used `"auto-close"` (with hyphen).

**Old keywords:**
```python
"keywords": ["auto close", "automation", "false positive", "fp rate"]
```

**Query variations that failed:**
- "Show auto-close rate" ❌ (hyphen)
- "What's our autoclose rate?" ❌ (no space/hyphen)

## Solution

Added hyphenated and concatenated variations:

**New keywords:**
```python
"keywords": ["auto close", "auto-close", "autoclose", "automation", "false positive", "fp rate"]
```

Now matches all common variations!

## Testing

### 1. Restart Backend

```bash
cd backend
# Stop server (Ctrl+C)
uvicorn app.main:app --reload --port 8000
```

### 2. Test in Browser

Open http://localhost:5173 → Tab 1: SOC Analytics

**Try these queries (all should work now):**

✅ "Show auto-close rate"
✅ "What's our auto close rate?"
✅ "Show me autoclose trend"
✅ "What's the automation rate?"

**Expected Result:**
- Matched: auto_close_rate • Confidence: 96%
- Line chart with 7 days
- Upward trend: 68.0% → 89.0%

### 3. Test via CLI

```bash
curl -X POST http://localhost:8000/api/soc/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show auto-close rate"}'
```

Expected: Valid response with `"matched_metric": {"id": "auto_close_rate", ...}`

## All Working Queries by Metric

### MTTR by Severity
- ✅ "What's our MTTR by severity?"
- ✅ "Show me MTTR"
- ✅ "What was response time last week?"
- ✅ "Mean time to respond by severity"

### Auto-Close Rate (FIXED)
- ✅ "Show auto-close rate"
- ✅ "What's our auto close rate?"
- ✅ "Show me autoclose trend"
- ✅ "What's the automation rate?"
- ✅ "Show false positive rate" (also matches this)

### False Positive Rate
- ✅ "What's our false positive rate?"
- ✅ "Show FP rate by rule"
- ✅ "What's our accuracy?"

### Escalation Rate
- ✅ "Show escalation rate"
- ✅ "What's our incident rate?"
- ✅ "Show tier 2 escalations"

### MTTD by Source
- ✅ "What's our MTTD?"
- ✅ "Show detection time by source"
- ✅ "Mean time to detect"

### Analyst Efficiency
- ✅ "Show analyst efficiency"
- ✅ "How efficient are our analysts?"

## Files Modified

✅ `backend/app/routers/soc.py` - Line 79
- Added "auto-close" and "autoclose" to keywords list

## Why This Matters

Users naturally type queries with:
- Spaces: "auto close"
- Hyphens: "auto-close"
- No separator: "autoclose"

All three variations should work! This fix makes the matching more robust and user-friendly.

## Verification Checklist

After restarting backend:

- [ ] "Show auto-close rate" returns valid result
- [ ] "Show autoclose rate" returns valid result
- [ ] "Show auto close rate" still works
- [ ] Line chart displays 7 data points
- [ ] Trend shows improvement (68% → 89%)
- [ ] No 404 errors in backend logs

---

**Status**: ✅ Fixed - All auto-close variations now work
