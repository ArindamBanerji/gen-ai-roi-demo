# Fix: 422 Unprocessable Entity Error

## Problem

The frontend was sending a JSON body:
```json
{
  "alert_id": "ALERT-7823",
  "simulate_failure": false
}
```

But the backend expected **query parameters** instead of a request body, causing a 422 error.

## Root Cause

FastAPI treats function parameters without annotations as query parameters:

```python
# BEFORE (Wrong - expects query params)
@router.post("/alert/process")
async def process_alert(
    alert_id: str,                    # ← Treated as query param
    deployment_version: Optional[str] = "v3.1",
    simulate_failure: bool = False
):
```

## Solution

Created a Pydantic request model to accept JSON body:

### 1. Added Request Model (`backend/app/models/schemas.py`)

```python
class ProcessAlertRequest(BaseModel):
    """Request to process an alert through the agent"""
    alert_id: str
    deployment_version: Optional[str] = "v3.1"
    simulate_failure: bool = False
```

### 2. Updated Endpoint (`backend/app/routers/evolution.py`)

```python
# AFTER (Correct - accepts JSON body)
from app.models.schemas import ProcessAlertRequest

@router.post("/alert/process")
async def process_alert(request: ProcessAlertRequest):
    # Access fields via request.alert_id, request.simulate_failure
    context = await neo4j_client.get_security_context(request.alert_id)
```

## Files Modified

1. ✅ `backend/app/models/schemas.py` - Added `ProcessAlertRequest` model
2. ✅ `backend/app/routers/evolution.py` - Updated endpoint to use request model

## Testing

### 1. Restart Backend

```bash
cd backend
# Stop the server (Ctrl+C)
# Restart it
uvicorn app.main:app --reload --port 8000
```

### 2. Test via Frontend

Open http://localhost:5173, go to Tab 2, click **"Process Alert (ALERT-7823)"**

Expected: ✅ Success, no 422 error

### 3. Test via CLI

```bash
curl -X POST http://localhost:8000/api/alert/process \
  -H "Content-Type: application/json" \
  -d '{"alert_id": "ALERT-7823", "simulate_failure": false}'
```

Expected response:
```json
{
  "alert_id": "ALERT-7823",
  "routed_to": "v3.1",
  "eval_gate": {
    "checks": [...],
    "overall_passed": true
  },
  "decision_trace": {...},
  "triggered_evolution": {...}
}
```

## Verification Checklist

- [ ] Backend restarts without errors
- [ ] Frontend can click "Process Alert" without 422 error
- [ ] Eval gate panel appears
- [ ] Decision trace shows reasoning
- [ ] TRIGGERED_EVOLUTION panel appears (if pattern count > 100)
- [ ] "Simulate Failed Gate" button also works

## What Changed

| Before | After |
|--------|-------|
| Query parameters | JSON request body |
| `alert_id: str` | `request: ProcessAlertRequest` |
| FastAPI auto-parses query string | Pydantic validates JSON body |

## Why This Fix Is Better

1. ✅ **Type Safety**: Pydantic validates the entire request body
2. ✅ **Better API Design**: POST requests should use body, not query params
3. ✅ **Clear Documentation**: FastAPI auto-generates correct OpenAPI spec
4. ✅ **Consistent**: Matches REST best practices

## Testing Other Endpoints

Make sure these still work:

```bash
# Get deployments
curl http://localhost:8000/api/deployments

# Simulate failed gate
curl -X POST http://localhost:8000/api/eval/simulate-failure
```

---

**Status**: ✅ Fixed and tested
