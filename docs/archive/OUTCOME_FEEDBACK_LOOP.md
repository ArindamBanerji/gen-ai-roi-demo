# Outcome Feedback Loop

**Version:** v2.5
**Status:** ✅ Backend Implemented
**Purpose:** Answer the CISO question: "What happens when the system is wrong?"

---

## Overview

The Outcome Feedback Loop allows users to report whether a decision outcome was correct or incorrect. The system then updates the graph accordingly, demonstrating self-correction in action.

### Key Concept

Traditional SIEMs log decisions but don't learn from mistakes. Our system:
- **Accepts feedback** - User reports if decision was right or wrong
- **Updates the graph** - Pattern confidence, edge weights, precedent counts adjust
- **Self-corrects** - If wrong, routes next N similar alerts to manual review
- **Shows transparency** - Every change is logged and explained

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  User clicks "This was correct" or "This was incorrect"    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  POST /api/alert/outcome                                    │
│  Body: { alert_id, decision_id, outcome }                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  services/feedback.py: process_outcome()                    │
│  • Validates feedback hasn't been given yet                 │
│  • Calculates graph updates (asymmetric: negative > positive)│
│  • Generates narrative explaining what changed              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Graph Updates Applied (simulated in demo)                  │
│  • Pattern confidence: +0.3 (correct) / -6.0 (incorrect)   │
│  • Edge weights: +0.02 (correct) / -0.05 (incorrect)       │
│  • Precedent count: +1 (correct only)                      │
│  • Override next N alerts: null (correct) / 5 (incorrect)  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Frontend displays:                                         │
│  • Graph updates table (entity, field, before, after)      │
│  • Consequence banner (what happened)                       │
│  • Narrative (plain English explanation)                    │
│  • Next alerts override notice (if incorrect)               │
└─────────────────────────────────────────────────────────────┘
```

---

## Files Created/Modified

### Created

**backend/app/services/feedback.py** (~260 lines)
- Core feedback processing logic
- In-memory state tracking (simulated)
- Asymmetric update calculations
- Narrative generation

### Modified

**backend/app/routers/triage.py** (+90 lines)
- Added imports for feedback service
- `POST /api/alert/outcome` - Report outcome
- `GET /api/alert/outcome/status` - Check if feedback given

**backend/app/models/schemas.py** (+7 lines)
- Added `OutcomeRequest` model

---

## API Reference

### POST /api/alert/outcome

Report whether a decision outcome was correct or incorrect.

**Request:**
```json
{
  "alert_id": "ALERT-7823",
  "decision_id": "DEC-7823-001",
  "outcome": "correct"  // or "incorrect"
}
```

**Response (Correct Outcome):**
```json
{
  "alert_id": "ALERT-7823",
  "outcome": "correct",
  "graph_updates": [
    {
      "entity": "PAT-TRAVEL-001",
      "field": "confidence",
      "before": 0.94,
      "after": 0.943,
      "direction": "strengthened"
    },
    {
      "entity": "User->TravelContext",
      "field": "weight",
      "before": 0.91,
      "after": 0.93,
      "direction": "strengthened"
    },
    {
      "entity": "PAT-TRAVEL-001",
      "field": "precedent_count",
      "before": 127,
      "after": 128,
      "direction": "strengthened"
    }
  ],
  "consequence": "Pattern strengthened. Added to precedent library.",
  "next_alerts_override": null,
  "narrative": "Decision confirmed correct. Pattern PAT-TRAVEL-001 confidence increased to 94.3% (+0.3 points). This decision has been added to the precedent library (128 validated decisions). The system is now slightly more confident in auto-closing similar travel login anomalies."
}
```

**Response (Incorrect Outcome):**
```json
{
  "alert_id": "ALERT-7823",
  "outcome": "incorrect",
  "graph_updates": [
    {
      "entity": "PAT-TRAVEL-001",
      "field": "confidence",
      "before": 0.94,
      "after": 0.88,
      "direction": "weakened"
    },
    {
      "entity": "User->TravelContext",
      "field": "weight",
      "before": 0.91,
      "after": 0.86,
      "direction": "weakened"
    }
  ],
  "consequence": "Pattern weakened. Threshold review triggered. Next 5 similar alerts routed to Tier 2.",
  "next_alerts_override": {
    "action": "escalate_tier2",
    "count": 5,
    "reason": "Confidence drop after incorrect outcome"
  },
  "narrative": "Decision outcome negative. Pattern PAT-TRAVEL-001 confidence dropped to 88.0% (-6.0 points). The system has triggered a threshold review and will route the next 5 travel login alerts to Tier 2 analysts for manual review. This is self-correction in action — the system learned from this mistake and adjusted its behavior."
}
```

---

### GET /api/alert/outcome/status

Check if feedback has been given for an alert.

**Query Parameters:**
- `alert_id` (required): Alert identifier

**Request:**
```
GET /api/alert/outcome/status?alert_id=ALERT-7823
```

**Response (No Feedback Yet):**
```json
{
  "has_feedback": false,
  "can_modify": true
}
```

**Response (Feedback Already Given):**
```json
{
  "has_feedback": true,
  "outcome": "correct",
  "timestamp": "2026-02-18T10:30:00Z",
  "can_modify": false
}
```

---

## Feedback Logic

### Asymmetric Updates

**Key Principle:** Negative feedback hits harder than positive feedback.

| Metric | Correct (+) | Incorrect (-) | Ratio |
|--------|-------------|---------------|-------|
| **Pattern Confidence** | +0.3 points | -6.0 points | 1:20 |
| **Edge Weight** | +0.02 | -0.05 | 1:2.5 |
| **Precedent Count** | +1 | (no change) | - |

**Rationale:**
- **Security-first**: False negatives (missed threats) are worse than false positives
- **Cautious learning**: System should be quick to doubt itself, slow to become overconfident
- **CISO trust**: Demonstrates the system prioritizes safety over efficiency

---

### Correct Outcome Logic

```python
# Pattern confidence: small increase
old_confidence = 0.94
new_confidence = min(0.94 + 0.003, 0.99)  # +0.3 points, cap at 99%

# Edge weight: small increase
old_weight = 0.91
new_weight = min(0.91 + 0.02, 0.99)  # +2 points, cap at 99%

# Precedent count: increment
precedent_count = 127 + 1  # Now 128

# No override
next_alerts_override = null
```

**Result:**
- Pattern slightly strengthened
- System marginally more confident
- Decision added to precedent library
- No behavior change for next alerts

---

### Incorrect Outcome Logic

```python
# Pattern confidence: large decrease
old_confidence = 0.94
new_confidence = max(0.94 - 0.06, 0.50)  # -6 points, floor at 50%

# Edge weight: moderate decrease
old_weight = 0.91
new_weight = max(0.91 - 0.05, 0.50)  # -5 points, floor at 50%

# Precedent count: no change (don't add bad decisions)

# Override next 5 alerts
next_alerts_override = {
  "action": "escalate_tier2",
  "count": 5,
  "reason": "Confidence drop after incorrect outcome"
}
```

**Result:**
- Pattern significantly weakened
- System much less confident
- Threshold review triggered
- Next 5 similar alerts route to Tier 2 (manual review)

---

## State Management

### In-Memory State (Demo)

**Pattern Confidence:**
```python
PATTERN_CONFIDENCE = {
    "PAT-TRAVEL-001": 0.94,
    "PAT-PHISH-001": 0.89,
}
```

**Edge Weights:**
```python
EDGE_WEIGHTS = {
    "User->TravelContext": 0.91,
    "User->PhishingCampaign": 0.87,
}
```

**Precedent Counts:**
```python
PRECEDENT_COUNTS = {
    "PAT-TRAVEL-001": 127,
    "PAT-PHISH-001": 89,
}
```

**Feedback Given:**
```python
FEEDBACK_GIVEN = {
    "ALERT-7823": {
        "decision_id": "DEC-7823-001",
        "outcome": "correct",
        "timestamp": "2026-02-18T10:30:00Z",
        "graph_updates": [...]
    }
}
```

### Production Implementation

In production, this would:
- Write to Neo4j graph database
- Update (:AttackPattern) node properties
- Update relationship weights
- Create (:FeedbackEvent) nodes
- Link via `[:PROVIDED_FEEDBACK]` relationship
- Query history for analysis

---

## Supported Alerts

### ALERT-7823 (Travel Login Anomaly)

**Pattern:** PAT-TRAVEL-001
**Edge:** User->TravelContext
**Type:** anomalous_login

**Initial State:**
- Confidence: 94%
- Edge weight: 0.91
- Precedent count: 127

**After Correct:**
- Confidence: 94.3% (+0.3)
- Edge weight: 0.93 (+0.02)
- Precedent count: 128 (+1)

**After Incorrect:**
- Confidence: 88% (-6.0)
- Edge weight: 0.86 (-0.05)
- Override: Next 5 to Tier 2

---

### ALERT-7824 (Phishing)

**Pattern:** PAT-PHISH-001
**Edge:** User->PhishingCampaign
**Type:** phishing

**Initial State:**
- Confidence: 89%
- Edge weight: 0.87
- Precedent count: 89

**After Correct:**
- Confidence: 89.3% (+0.3)
- Edge weight: 0.89 (+0.02)
- Precedent count: 90 (+1)

**After Incorrect:**
- Confidence: 83% (-6.0)
- Edge weight: 0.82 (-0.05)
- Override: Next 5 to Tier 2

---

## Error Handling

### Validation Errors (400)

**Invalid outcome:**
```json
{
  "detail": "Invalid outcome: maybe. Must be 'correct' or 'incorrect'."
}
```

**Feedback already given:**
```json
{
  "detail": "Feedback already provided for ALERT-7823. Outcome cannot be changed."
}
```

### Server Errors (500)

```json
{
  "detail": "Failed to process outcome: [error details]"
}
```

---

## Frontend Integration (v2.5 Next Step)

### Expected UI

**Location:** Tab 3 (Alert Triage), after decision is made

**Initial State:**
```
┌──────────────────────────────────────────┐
│ Decision Applied: false_positive_close   │
│ Confidence: 92%                          │
│                                          │
│ Was this decision correct?               │
│ [✓ Correct] [✗ Incorrect]               │
└──────────────────────────────────────────┘
```

**After Clicking "✓ Correct":**
```
┌──────────────────────────────────────────┐
│ ✅ Feedback recorded: Correct            │
│                                          │
│ Graph Updates:                           │
│ • PAT-TRAVEL-001 confidence: 94% → 94.3% │
│ • User->Travel edge: 0.91 → 0.93         │
│ • Precedent count: 127 → 128             │
│                                          │
│ 💡 Pattern strengthened. Added to        │
│    precedent library.                    │
└──────────────────────────────────────────┘
```

**After Clicking "✗ Incorrect":**
```
┌──────────────────────────────────────────┐
│ ⚠️ Feedback recorded: Incorrect          │
│                                          │
│ Graph Updates:                           │
│ • PAT-TRAVEL-001 confidence: 94% → 88%   │
│ • User->Travel edge: 0.91 → 0.86         │
│                                          │
│ 🔴 Pattern weakened. Threshold review    │
│    triggered. Next 5 similar alerts      │
│    routed to Tier 2 for manual review.  │
│                                          │
│ This is self-correction in action.      │
└──────────────────────────────────────────┘
```

---

## Testing

### Test Correct Outcome

```bash
# 1. Check status (should be no feedback)
curl "http://localhost:8001/api/alert/outcome/status?alert_id=ALERT-7823"

# 2. Submit correct outcome
curl -X POST http://localhost:8001/api/alert/outcome \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": "ALERT-7823",
    "decision_id": "DEC-7823-001",
    "outcome": "correct"
  }'

# 3. Verify feedback recorded
curl "http://localhost:8001/api/alert/outcome/status?alert_id=ALERT-7823"

# Expected: has_feedback=true, outcome="correct"
```

### Test Incorrect Outcome

```bash
# Submit incorrect outcome for phishing alert
curl -X POST http://localhost:8001/api/alert/outcome \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": "ALERT-7824",
    "decision_id": "DEC-7824-001",
    "outcome": "incorrect"
  }'

# Expected: next_alerts_override with count=5
```

### Test Duplicate Feedback (Should Fail)

```bash
# Try to submit feedback again for same alert
curl -X POST http://localhost:8001/api/alert/outcome \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": "ALERT-7823",
    "decision_id": "DEC-7823-001",
    "outcome": "incorrect"
  }'

# Expected: 400 error, "Feedback already provided"
```

---

## Demo Talking Points

### For CISOs

**Q: "What happens when the system is wrong?"**

**A:**
> "Great question. Watch this. I'm going to tell the system this decision was incorrect."
>
> *[Clicks "✗ Incorrect"]*
>
> "See what happened? The pattern confidence dropped from 94% to 88% — that's a 6-point hit. The system immediately triggered a threshold review and will now route the next 5 similar travel alerts to Tier 2 analysts for manual review. This is self-correction in action."
>
> "Notice the asymmetry: correct feedback adds 0.3 points, but incorrect feedback subtracts 6 points. That's by design — in security, we'd rather be cautious than overconfident."

**Q: "How do you prevent the system from getting worse over time?"**

**A:**
> "The precedent library. Every correct outcome adds to the library — you can see it went from 127 to 128 validated decisions. Incorrect outcomes don't get added. Over time, the precedent library becomes a high-quality training set that compounds value."

**Q: "Is this transparent enough for audit?"**

**A:**
> "Absolutely. Every change is logged: which pattern, which field, before value, after value, who provided the feedback, when. The graph stores the full provenance. Your auditors can trace any decision back through the entire chain."

---

## Future Enhancements (v3+)

### Advanced Feedback

- [ ] **Partial feedback** - "Correct action, wrong reasoning"
- [ ] **Severity adjustment** - "Correct but should have escalated faster"
- [ ] **Root cause annotation** - "Missed this context variable"

### Analytics

- [ ] **Feedback rate dashboard** - What % of decisions get feedback?
- [ ] **Pattern quality score** - Precedent count ÷ total occurrences
- [ ] **Analyst agreement rate** - Do multiple analysts agree on outcome?

### Advanced Self-Correction

- [ ] **Automatic threshold adjustment** - Dynamic confidence thresholds
- [ ] **Pattern deprecation** - Retire low-quality patterns
- [ ] **Ensemble voting** - Multiple patterns must agree for high-confidence

### Integration

- [ ] **SOAR integration** - Feedback from automated playbook results
- [ ] **SIEM correlation** - Cross-reference with actual incident outcomes
- [ ] **Threat intel feeds** - External validation of pattern accuracy

---

*Outcome Feedback Loop Documentation | v2.5 | February 2026*
