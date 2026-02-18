# Outcome Feedback Frontend Integration

**Version:** v2.5
**Status:** ✅ Complete
**Purpose:** UI for Loop 3: Learning from Results

---

## Overview

The Outcome Feedback panel allows users to report whether a decision outcome was correct or incorrect. It appears in Tab 3 (Alert Triage) after the closed-loop execution completes, demonstrating self-correction in action.

---

## Files Created/Modified

### Created

**frontend/src/components/OutcomeFeedback.tsx** (~300 lines)
- Self-contained feedback component
- Props: alertId, decisionId, isVisible
- Three states: initial (buttons), result (after feedback), already given (read-only)

### Modified

**frontend/src/lib/api.ts** (+20 lines)
- Added `getOutcomeStatus(alertId)` - GET /api/alert/outcome/status
- Added `reportOutcome(alertId, decisionId, outcome)` - POST /api/alert/outcome

**frontend/src/components/tabs/AlertTriageTab.tsx** (+5 lines)
- Added OutcomeFeedback import
- Added component after closed loop section
- Passes alertId, decisionId, isVisible props

---

## Component Structure

### Props

```typescript
interface OutcomeFeedbackProps {
  alertId: string        // e.g., "ALERT-7823"
  decisionId: string     // e.g., "DEC-7823-001" from closedLoop.evidence.decision_id
  isVisible: boolean     // Show only after closed loop executes
}
```

### State

```typescript
const [hasFeedback, setHasFeedback] = useState(false)
const [loading, setLoading] = useState(false)
const [submitting, setSubmitting] = useState(false)
const [result, setResult] = useState<OutcomeResponse | null>(null)
```

### Flow

1. **On Mount:** Call `GET /api/alert/outcome/status?alert_id={alertId}`
   - If `has_feedback: true` → show "already given" message
   - If `has_feedback: false` → show two buttons

2. **User Clicks Button:**
   - "Confirmed Correct" → `POST /api/alert/outcome` with `outcome: "correct"`
   - "Incorrect — Real Threat" → `POST /api/alert/outcome` with `outcome: "incorrect"`

3. **After Response:**
   - Display graph updates table
   - Show consequence banner (green for correct, amber for incorrect)
   - If incorrect: show next_alerts_override (escalate next 5 to Tier 2)
   - Display narrative in italics
   - Disable both buttons (feedback is immutable)

---

## Visual Design

### Header
- Purple gradient background
- Clock icon
- Title: "OUTCOME FEEDBACK (Loop 3: Learning from Results)"
- Subtitle: "24 hours later — was this decision correct?"

### Initial State (Buttons)
```
┌─────────────────────────────────────────────────────┐
│ Report the outcome to help the system learn.       │
│                                                     │
│ ┌────────────────────┐  ┌─────────────────────────┐│
│ │ ✓ Confirmed Correct│  │ ✗ Incorrect — Real Threat│
│ │   (green)          │  │   (red)                  ││
│ └────────────────────┘  └─────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

### After Correct Outcome
```
┌─────────────────────────────────────────────────────┐
│ ✓ Outcome: Correct (green banner)                  │
│ Pattern strengthened. Added to precedent library.   │
│                                                     │
│ Graph Updates:                                      │
│ ┌───────────────────────────────────────────────┐ │
│ │ PAT-TRAVEL-001 | confidence | 94.0% → 94.3% ↗│ │
│ │ User->Travel   | weight     | 91.0% → 93.0% ↗│ │
│ │ PAT-TRAVEL-001 | precedent  | 127   → 128   ↗│ │
│ └───────────────────────────────────────────────┘ │
│                                                     │
│ "Pattern PAT-TRAVEL-001 confidence increased to     │
│  94.3%. Added to precedent library (128 validated   │
│  decisions). System is now more confident."         │
│                                                     │
│ "The system gets more confident with every          │
│  validation." (italic callout)                      │
└─────────────────────────────────────────────────────┘
```

### After Incorrect Outcome
```
┌─────────────────────────────────────────────────────┐
│ ⚠ Outcome: Incorrect (amber banner)                │
│ Pattern weakened. Threshold review triggered.       │
│ Next 5 similar alerts routed to Tier 2.            │
│                                                     │
│ Graph Updates:                                      │
│ ┌───────────────────────────────────────────────┐ │
│ │ PAT-TRAVEL-001 | confidence | 94.0% → 88.0% ↘│ │
│ │ User->Travel   | weight     | 91.0% → 86.0% ↘│ │
│ └───────────────────────────────────────────────┘ │
│                                                     │
│ ⚠ Threshold Review Triggered (amber box)           │
│ Next 5 similar alerts will be routed to Tier 2     │
│ analysts for manual review.                         │
│ Reason: Confidence drop after incorrect outcome     │
│                                                     │
│ "Pattern PAT-TRAVEL-001 confidence dropped to       │
│  88.0% (-6.0 points). System triggered threshold    │
│  review and will route next 5 similar alerts to     │
│  Tier 2. This is self-correction in action."        │
│                                                     │
│ "This is self-correction in action — the system     │
│  learned from this mistake." (italic callout)       │
└─────────────────────────────────────────────────────┘
```

---

## Styling

### Color Scheme

**Correct Outcome:**
- Background: `bg-green-900/20`
- Border: `border-green-500/50`
- Text: `text-green-300`
- Icon: CheckCircle (green)

**Incorrect Outcome:**
- Background: `bg-amber-900/20`
- Border: `border-amber-500/50`
- Text: `text-amber-300`
- Icon: AlertTriangle (amber)

**Graph Updates:**
- Strengthened: TrendingUp icon (green)
- Weakened: TrendingDown icon (red)

### Icons Used

- `Clock` - Header icon
- `CheckCircle` - Correct button and outcome
- `XCircle` - Incorrect button
- `AlertTriangle` - Threshold review warning
- `TrendingUp` - Strengthened metric
- `TrendingDown` - Weakened metric

---

## Integration in AlertTriageTab

### Location

Added after the closed loop execution section (after line 758):

```tsx
{/* Outcome Feedback (v2.5 - Loop 3) */}
{closedLoop && selectedAlert && (
  <OutcomeFeedback
    alertId={selectedAlert.id}
    decisionId={closedLoop.evidence.decision_id}
    isVisible={!!closedLoop}
  />
)}
```

### Visibility Logic

- Only renders when `closedLoop` is not null
- Only renders when `selectedAlert` is not null
- `isVisible` prop is `true` when closed loop has executed

### Data Flow

```
AlertTriageTab
├── selectedAlert.id → OutcomeFeedback.alertId
├── closedLoop.evidence.decision_id → OutcomeFeedback.decisionId
└── !!closedLoop → OutcomeFeedback.isVisible
```

---

## API Integration

### GET /api/alert/outcome/status

**Called on mount to check if feedback already given**

```typescript
const status = await getOutcomeStatus(alertId)
// Response: { has_feedback: boolean, can_modify: boolean }
```

### POST /api/alert/outcome

**Called when user clicks correct/incorrect button**

```typescript
const response = await reportOutcome(alertId, decisionId, outcome)
// Request: { alert_id, decision_id, outcome: "correct" | "incorrect" }
// Response: { alert_id, outcome, graph_updates, consequence,
//            next_alerts_override?, narrative }
```

---

## Demo Flow

### Scenario 1: Correct Outcome (ALERT-7823)

1. User selects ALERT-7823 (John Smith, traveling, high risk)
2. Graph analysis shows both policies apply (conflict)
3. Recommendation: escalate_tier2 (POL-ESCALATE-HIGH-RISK wins)
4. User clicks "Apply Recommendation"
5. Closed loop executes (4 steps animate)
6. **Outcome Feedback panel appears**
7. User clicks "Confirmed Correct"
8. Backend returns:
   - Pattern confidence: 94% → 94.3% (+0.3)
   - Edge weight: 91% → 93% (+2)
   - Precedent count: 127 → 128 (+1)
9. UI shows green banner: "Pattern strengthened"
10. Narrative: "System is now more confident"

### Scenario 2: Incorrect Outcome (ALERT-7823)

1. (Steps 1-6 same as above)
2. User clicks "Incorrect — Real Threat"
3. Backend returns:
   - Pattern confidence: 94% → 88% (-6.0)
   - Edge weight: 91% → 86% (-5)
   - Next 5 alerts override: escalate_tier2
4. UI shows amber banner: "Pattern weakened"
5. UI shows threshold review warning box
6. Narrative: "Self-correction in action"

---

## Demo Talking Points

### For CISOs

**Q: "What happens when the system is wrong?"**

**A:**
> "Watch this. I'm going to tell the system this decision was incorrect."
>
> *[Clicks "Incorrect — Real Threat"]*
>
> "See what happened? The pattern confidence dropped from 94% to 88% — that's a 6-point hit. The system immediately triggered a threshold review and will now route the next 5 similar travel alerts to Tier 2 analysts for manual review."
>
> "Notice the asymmetry: correct feedback adds 0.3 points, but incorrect feedback subtracts 6 points. That's by design — in security, we'd rather be cautious than overconfident."

**Q: "How do you prevent the system from getting worse over time?"**

**A:**
> "The precedent library. Every correct outcome adds to the library — you can see it went from 127 to 128 validated decisions. Incorrect outcomes don't get added. Over time, the precedent library becomes a high-quality training set."

**Q: "Is this transparent enough for audit?"**

**A:**
> "Absolutely. Every change is logged: which pattern, which field, before value, after value. The graph stores the full provenance. Your auditors can trace any decision back through the entire chain."

---

## Error Handling

### Network Errors

- Display alert: "Failed to report outcome. Please try again."
- Console log: `[OutcomeFeedback] Failed to report outcome: {error}`

### Already Given

- Show message: "Feedback has already been provided for this alert."
- Disable buttons
- Display: "Outcomes are immutable once recorded."

### Loading States

- Initial check: "Checking feedback status..."
- Submitting: "Reporting outcome..." (below buttons)

---

## Accessibility

### Keyboard Navigation

- Both buttons are focusable
- Enter/Space activates button
- Tab moves between buttons

### Screen Readers

- Clear button labels: "Confirmed Correct", "Incorrect — Real Threat"
- Status messages announce outcome
- Table data properly structured

### Color Blindness

- Not relying solely on color
- Icons supplement color (CheckCircle, XCircle, AlertTriangle)
- Text labels make meaning clear

---

## Testing Checklist

### Visual Testing
- [ ] Panel appears after closed loop executes
- [ ] Two buttons visible initially
- [ ] Green/red styling correct
- [ ] Graph updates table renders
- [ ] Consequence banner displays
- [ ] Narrative text readable
- [ ] Icons render correctly

### Interaction Testing
- [ ] Clicking "Confirmed Correct" works
- [ ] Clicking "Incorrect" works
- [ ] Buttons disable after click
- [ ] Result displays correctly
- [ ] Threshold warning shows for incorrect
- [ ] Can't submit feedback twice

### API Testing
- [ ] Status check on mount
- [ ] Correct outcome POST works
- [ ] Incorrect outcome POST works
- [ ] Error handling works
- [ ] Already-given state works

### Edge Cases
- [ ] No decision ID (shouldn't happen)
- [ ] Network timeout
- [ ] Backend returns 400/500
- [ ] Rapid button clicks (debouncing)

---

## Future Enhancements (v3+)

### Advanced Feedback
- [ ] **Partial feedback** - "Correct action, wrong reasoning"
- [ ] **Severity adjustment** - "Correct but should have escalated faster"
- [ ] **Root cause annotation** - "Missed this context variable"

### Visualization
- [ ] **Graph diff animation** - Show before/after side-by-side
- [ ] **Impact simulation** - "If 10 more incorrect, then..."
- [ ] **Historical trends** - Pattern confidence over time chart

### UX Improvements
- [ ] **Undo within 5 minutes** - Allow correction if mistaken
- [ ] **Notes field** - Add optional analyst notes
- [ ] **Confidence slider** - "Very certain" vs "Somewhat certain"

---

*Outcome Feedback Frontend Documentation | v2.5 | February 2026*
