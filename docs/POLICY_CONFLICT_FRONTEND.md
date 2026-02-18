# Policy Conflict Frontend Integration

**Version:** v2.5
**Status:** ✅ Complete
**Purpose:** Show policy conflict detection and resolution in Tab 3

---

## Overview

The Policy Conflict panel shows when multiple policies apply to an alert and conflict with each other. It appears in Tab 3 (Alert Triage) between the Situation Analyzer and Recommendation sections, demonstrating priority-based conflict resolution.

---

## Files Created/Modified

### Created

**frontend/src/components/PolicyConflict.tsx** (~290 lines)
- Self-contained policy conflict component
- Props: alertId, isVisible
- Two display modes: simple (no conflict) vs full panel (conflict detected)

### Modified

**frontend/src/lib/api.ts** (+10 lines)
- Added `checkPolicyConflict(alertId)` - GET /api/alert/policy-check

**frontend/src/components/tabs/AlertTriageTab.tsx** (+4 lines)
- Added PolicyConflict import
- Added component between Situation Analyzer and Recommendation
- Passes alertId from selectedAlert, isVisible when analysis exists

---

## Component Structure

### Props

```typescript
interface PolicyConflictProps {
  alertId: string        // e.g., "ALERT-7823"
  isVisible: boolean     // Show only after analysis completes
}
```

### State

```typescript
const [loading, setLoading] = useState(false)
const [data, setData] = useState<PolicyConflictData | null>(null)
```

### Data Model

```typescript
interface PolicyConflictData {
  alert_id: string
  has_conflict: boolean
  policies_applied: PolicyDefinition[]
  conflicting_policies: PolicyDefinition[]
  resolution: PolicyResolution | null
}

interface PolicyDefinition {
  id: string              // "POL-ESCALATE-HIGH-RISK"
  name: string            // "Escalate High-Risk Users"
  description: string
  action: string          // "escalate_tier2"
  priority: number        // 1 = highest
  scope: string           // "high_risk_users"
}

interface PolicyResolution {
  winning_policy: string  // "POL-ESCALATE-HIGH-RISK"
  losing_policy: string   // "POL-AUTO-CLOSE-TRAVEL"
  reason: string
  action_adjusted: string // "escalate_tier2"
  original_action: string // "false_positive_close"
  audit_id: string        // "CON-2026-0847"
  narrative: string
}
```

---

## Visual Design

### No Conflict (Simple One-Liner)

```
┌───────────────────────────────────────────────────┐
│ ✓ Policies evaluated: Escalate High-Risk Users.  │
│   No conflicts detected.                          │
└───────────────────────────────────────────────────┘
```

- Green checkmark icon (ShieldCheck)
- Single line of text
- Subtle, doesn't take up much space

### Conflict Detected (Full Panel)

```
┌─────────────────────────────────────────────────────────┐
│ ⚠ POLICY CONFLICT DETECTED                              │
│ Multiple policies apply with different actions...       │
├─────────────────────────────────────────────────────────┤
│ ┌──────────────────────┐  ┌──────────────────────────┐ │
│ │ POL-AUTO-CLOSE...    │  │ POL-ESCALATE-HIGH-RISK  │ │
│ │ [LOSES]              │  │ [★ WINNER]              │ │
│ │                      │  │                          │ │
│ │ Priority: 3          │  │ Priority: 1              │ │
│ │ Action: false_pos... │  │ Action: escalate_tier2   │ │
│ │ (red card)           │  │ (green card)             │ │
│ └──────────────────────┘  └──────────────────────────┘ │
│                                                         │
│ ⚖ RESOLUTION                                           │
│ Escalate High-Risk Users takes precedence              │
│ Action adjusted: escalate_tier2 (was: false_positive)  │
│ Audit ID: CON-2026-0847                                │
│                                                         │
│ "Policy POL-ESCALATE-HIGH-RISK (priority 1) conflicts  │
│  with POL-AUTO-CLOSE-TRAVEL (priority 3). Resolution:  │
│  higher-priority policy wins..."                       │
│                                                         │
│ "Security-first principle: When policies conflict,     │
│  the higher-priority policy always wins..."            │
└─────────────────────────────────────────────────────────┘
```

---

## Styling

### Color Scheme

**Header (Conflict Detected):**
- Background: `bg-amber-900/30`
- Border: `border-amber-500/50`
- Text: `text-amber-300`
- Icon: AlertTriangle (amber)

**Losing Policy Card:**
- Background: `bg-red-900/20`
- Border: `border-red-500/30`
- Text: `text-red-300`
- Badge: "LOSES" (red)

**Winning Policy Card:**
- Background: `bg-green-900/20`
- Border: `border-green-500/50` (thicker, 2px)
- Text: `text-green-300`
- Badge: "★ WINNER" with Award icon (green)

**Resolution Box:**
- Background: `bg-amber-900/20`
- Border: `border-amber-500/30`
- Icon: Scale (amber)

**Security Principle Callout:**
- Background: `bg-green-900/10`
- Border: `border-green-500/30`
- Text: `text-green-300` (italic, centered)

### Icons Used

- `AlertTriangle` - Header (conflict warning)
- `Shield` - Policy cards
- `ShieldCheck` - No conflict (green checkmark)
- `Award` - Winner badge
- `Scale` - Resolution box (justice scales)

---

## Integration in AlertTriageTab

### Location

Added between Situation Analyzer and Recommendation (after line 601):

```tsx
{/* Situation Analyzer Panel */}
{analysis && analysis.situation_analysis && (
  <div>...</div>
)}

{/* Policy Conflict (v2.5) */}
{analysis && selectedAlert && (
  <PolicyConflict
    alertId={selectedAlert.id}
    isVisible={!!analysis}
  />
)}

{/* Recommendation Panel */}
{analysis && (
  <div>...</div>
)}
```

### Visibility Logic

- Only renders when `analysis` exists (alert has been analyzed)
- Only renders when `selectedAlert` exists
- `isVisible` prop is `true` when analysis is complete

### Data Flow

```
AlertTriageTab
├── selectedAlert.id → PolicyConflict.alertId
└── !!analysis → PolicyConflict.isVisible
```

---

## API Integration

### GET /api/alert/policy-check

**Called on mount when isVisible becomes true**

```typescript
const result = await checkPolicyConflict(alertId)
// Response: PolicyConflictData
```

**Example Response (No Conflict):**
```json
{
  "alert_id": "ALERT-7824",
  "has_conflict": false,
  "policies_applied": [
    {
      "id": "POL-REMEDIATE-KNOWN-PHISH",
      "name": "Auto-Remediate Known Phishing",
      "description": "...",
      "action": "auto_remediate",
      "priority": 2,
      "scope": "all_users"
    }
  ],
  "conflicting_policies": [],
  "resolution": null
}
```

**Example Response (Conflict):**
```json
{
  "alert_id": "ALERT-7823",
  "has_conflict": true,
  "policies_applied": [
    {
      "id": "POL-AUTO-CLOSE-TRAVEL",
      "name": "Auto-Close Travel Anomalies",
      "action": "false_positive_close",
      "priority": 3,
      ...
    },
    {
      "id": "POL-ESCALATE-HIGH-RISK",
      "name": "Escalate High-Risk Users",
      "action": "escalate_tier2",
      "priority": 1,
      ...
    }
  ],
  "conflicting_policies": [...],
  "resolution": {
    "winning_policy": "POL-ESCALATE-HIGH-RISK",
    "losing_policy": "POL-AUTO-CLOSE-TRAVEL",
    "reason": "Policy POL-ESCALATE-HIGH-RISK (priority 1) takes precedence...",
    "action_adjusted": "escalate_tier2",
    "original_action": "false_positive_close",
    "audit_id": "CON-2026-0847",
    "narrative": "..."
  }
}
```

---

## Demo Flow

### Scenario 1: No Conflict (ALERT-7824 - Phishing)

1. User selects ALERT-7824 (phishing alert)
2. Clicks "Analyze Alert"
3. Situation Analyzer shows phishing situation
4. **Policy Conflict shows:** "Policies evaluated: Auto-Remediate Known Phishing. ✓ No conflicts detected."
5. Recommendation shows: auto_remediate

### Scenario 2: Conflict (ALERT-7823 - High Risk + Traveling)

1. User selects ALERT-7823 (John Smith, high risk, traveling)
2. Clicks "Analyze Alert"
3. Situation Analyzer shows travel login anomaly
4. **Policy Conflict shows:**
   - Header: "⚠ POLICY CONFLICT DETECTED"
   - Two cards side by side:
     - Left: POL-AUTO-CLOSE-TRAVEL (Priority 3) [LOSES]
     - Right: POL-ESCALATE-HIGH-RISK (Priority 1) [★ WINNER]
   - Resolution box:
     - "Escalate High-Risk Users takes precedence"
     - "Action adjusted: escalate_tier2 (was: false_positive_close)"
     - Audit ID: CON-2026-XXXX
   - Narrative explaining the resolution
5. Recommendation shows: escalate_tier2 (matches winning policy)

---

## Layout in Tab 3

```
┌─────────────────────────────────────────────┐
│ Alert Queue Sidebar                         │
│ ...                                         │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Graph Analysis (47 nodes)                   │
│ ...                                         │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Situation Analyzer (Loop 1)                 │
│ Travel Login Anomaly | 94% confidence       │
│ ...                                         │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐ ← NEW
│ ⚠ POLICY CONFLICT DETECTED                  │
│ [Losing Policy] vs [Winner Policy]          │
│ Resolution: Winner takes precedence         │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Recommendation                              │
│ Action: escalate_tier2                      │
│ [Apply Recommendation]                      │
└─────────────────────────────────────────────┘
```

---

## Demo Talking Points

### For CISOs

**Q: "What happens when two policies conflict?"**

**A:**
> "Great question. Watch what happens with this alert. John Smith is a high-risk user who's traveling to London. We have two policies that apply:"
>
> *[Points to left card]*
> "Policy 1: Auto-close travel anomalies when the user is traveling and VPN matches. Priority 3."
>
> *[Points to right card]*
> "Policy 2: Escalate ALL alerts for users with risk score above 0.80. Priority 1 — highest priority."
>
> *[Points to resolution]*
> "See the conflict? One policy says auto-close, the other says escalate. The system resolves this by priority: Policy 2 wins. The action is adjusted from 'false_positive_close' to 'escalate_tier2'."
>
> "This is logged with an audit ID (CON-2026-0847) for compliance. Every conflict resolution is traceable."

**Q: "Why not just remove conflicting policies?"**

**A:**
> "Conflicts aren't always bad — they show your security posture is thorough. Both policies are valid in isolation. The key is having a transparent, deterministic way to resolve conflicts when they occur."
>
> "Notice the 'security-first' principle at the bottom: When policies conflict, the higher-priority policy always wins. This ensures no security gaps."

**Q: "Can analysts override this?"**

**A:**
> "Yes. This is a recommendation, not a mandate. The analyst can see both policies, understand why the conflict was resolved this way, and make the final call. We're augmenting human decision-making, not replacing it."

---

## Error Handling

### Network Errors

- Console log: `[PolicyConflict] Failed to check policy conflict: {error}`
- UI: Component returns null (graceful degradation)

### Loading States

- Shows: "Checking policy conflicts..." (gray text, centered)

### Missing Data

- If `data` is null: returns null (no display)
- If no conflict and no policies: returns null

---

## Accessibility

### Keyboard Navigation

- N/A (read-only display component)

### Screen Readers

- Policy cards have clear structure
- Winning policy marked with "WINNER" badge
- Resolution text is clear and descriptive

### Color Blindness

- Not relying solely on color
- Icons supplement color (Shield, Award, Scale)
- Text labels make meaning clear (LOSES, WINNER)

---

## Testing Checklist

### Visual Testing
- [ ] Panel appears after alert analysis
- [ ] No conflict: single green line displays
- [ ] Conflict: full panel with two cards
- [ ] Losing card is red-tinted
- [ ] Winning card is green-tinted with WINNER badge
- [ ] Resolution box displays correctly
- [ ] Narrative text readable
- [ ] Security principle callout displays

### Interaction Testing
- [ ] Component loads when analysis completes
- [ ] API call happens on mount
- [ ] Loading state displays briefly
- [ ] No conflict scenario works (ALERT-7824)
- [ ] Conflict scenario works (ALERT-7823)

### Edge Cases
- [ ] No alert selected (component hidden)
- [ ] Analysis not complete (component hidden)
- [ ] Network timeout
- [ ] Backend returns error

---

## Future Enhancements (v3+)

### Advanced Conflict Resolution
- [ ] **Manual override** - Analyst can pick losing policy
- [ ] **Conflict history** - Show past conflicts for this alert type
- [ ] **Policy editor** - Adjust priorities inline

### Visualization
- [ ] **Policy tree** - Show all policies and their priorities
- [ ] **Conflict heatmap** - Which policies conflict most often
- [ ] **Impact simulation** - "If I change priority, what happens?"

### Analytics
- [ ] **Conflict rate dashboard** - Track conflicts over time
- [ ] **Resolution accuracy** - Were resolutions correct?
- [ ] **Policy effectiveness** - Which policies win/lose most

---

*Policy Conflict Frontend Documentation | v2.5 | February 2026*
