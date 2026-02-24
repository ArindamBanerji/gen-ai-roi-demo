# Bug Fix: Stale Closure in Outcome Feedback Guard

**Date:** February 18, 2026
**Component:** AlertTriageTab.tsx
**Issue:** Ref-based guard to prevent stale closure bug
**Status:** ✅ Fixed

---

## Problem Description

### Previous Fix Didn't Work

The initial fix used a state-based guard:
```typescript
if (data.alerts.length > 0 && !(selectedAlert && closedLoop)) {
  setSelectedAlert(data.alerts[0])
}
```

**Problem:** Stale closure bug

When `loadAlertQueue()` is defined, it captures the values of `selectedAlert` and `closedLoop` from that moment. When the function runs later (via `setTimeout(loadAlertQueue, 3200)`), it uses the **old captured values**, not the current state.

### Timeline of the Bug

```
T=0ms:    User clicks "Apply Recommendation"
          - selectedAlert = ALERT-7823
          - closedLoop = null (not set yet)

T=10ms:   executeActionHandler runs
          - Calls: setClosedLoop(data)
          - Schedules: setTimeout(loadAlertQueue, 3200)
          - NOTE: loadAlertQueue captures closedLoop as null at this point

T=50ms:   React updates state
          - closedLoop = { receipt, verification, ... }

T=3200ms: loadAlertQueue runs
          - Uses CAPTURED closedLoop = null (stale!)
          - Guard: !(ALERT-7823 && null) → !false → true ✅
          - Auto-selects first alert (BUG!)
          - OutcomeFeedback panel disappears
```

### Why State Doesn't Work

JavaScript closures capture variables by **reference at definition time**. Even though `closedLoop` state updates, the function `loadAlertQueue` was already defined with a closure that captured the old value.

---

## Solution: Use a Ref

### Why Refs Work

Unlike state, refs are **mutable containers**. When you access `ref.current`, you always get the **current value**, not a captured snapshot.

```typescript
// State (captured snapshot)
const [closedLoop, setClosedLoop] = useState(null)
// loadAlertQueue captures: closedLoop = null

// Ref (always current)
const preserveFeedbackRef = useRef(false)
// loadAlertQueue accesses: preserveFeedbackRef.current (always current)
```

---

## Implementation

### Step 1: Import useRef

**Location:** Line 1

```typescript
import { useState, useEffect, useRef } from 'react'
```

### Step 2: Add Ref Declaration

**Location:** After state declarations (line 123)

```typescript
const [loading, setLoading] = useState(false)
const [executing, setExecuting] = useState(false)
const [activeStep, setActiveStep] = useState(0)
const [resetting, setResetting] = useState(false)

// Ref to preserve feedback panel visibility (avoids stale closure bug)
const preserveFeedbackRef = useRef(false)
```

### Step 3: Set Ref in Execute Handler

**Location:** executeActionHandler (line 201)

```typescript
const executeActionHandler = async () => {
  if (!selectedAlert || !analysis) return

  setExecuting(true)
  setClosedLoop(null)

  try {
    const data = await executeAction(selectedAlert.id)
    setClosedLoop(data)

    // Preserve feedback panel visibility when queue reloads
    preserveFeedbackRef.current = true  // ← NEW

    // Animate steps
    for (let i = 0; i < 4; i++) {
      setTimeout(() => setActiveStep(i + 1), i * 800)
    }

    // Refresh alert queue
    setTimeout(loadAlertQueue, 3200)
  } catch (error) {
    console.error('Failed to execute action:', error)
  } finally {
    setTimeout(() => setExecuting(false), 3200)
  }
}
```

### Step 4: Use Ref in Load Queue Logic

**Location:** loadAlertQueue (line 155-163)

**Before:**
```typescript
if (data.alerts.length > 0 && !(selectedAlert && closedLoop)) {
  setSelectedAlert(data.alerts[0])
}
```

**After:**
```typescript
// Only auto-select first alert on initial load or manual refresh
// Don't auto-select if preserveFeedbackRef is true (user just executed action, needs to give feedback)
// Using ref avoids stale closure bug where closedLoop state is captured as null
if (data.alerts.length > 0 && !preserveFeedbackRef.current) {
  setSelectedAlert(data.alerts[0])
  console.log('[AlertTriageTab] Selected first alert:', data.alerts[0])
} else if (data.alerts.length === 0) {
  console.log('[AlertTriageTab] No alerts in response')
} else if (preserveFeedbackRef.current) {
  console.log('[AlertTriageTab] Skipped auto-select (preserving feedback state)')
}
```

### Step 5: Clear Ref on Manual Selection

**Location:** handleAlertSelect (line 220)

```typescript
const handleAlertSelect = (alert: Alert) => {
  // Clear feedback preservation when user manually selects a different alert
  preserveFeedbackRef.current = false
  setSelectedAlert(alert)
  analyzeAlertHandler(alert)
}
```

---

## How It Works Now

### Timeline with Ref

```
T=0ms:    User clicks "Apply Recommendation"
          - preserveFeedbackRef.current = false

T=10ms:   executeActionHandler runs
          - Calls: setClosedLoop(data)
          - Sets: preserveFeedbackRef.current = true ✅
          - Schedules: setTimeout(loadAlertQueue, 3200)

T=50ms:   React updates state
          - closedLoop = { receipt, verification, ... }

T=3200ms: loadAlertQueue runs
          - Checks: preserveFeedbackRef.current (reads true!) ✅
          - Guard: !true → false ❌
          - Skips auto-select
          - OutcomeFeedback panel stays visible ✅
```

### Key Difference

- **State:** `closedLoop` was captured as `null` when setTimeout was called
- **Ref:** `preserveFeedbackRef.current` is evaluated when loadAlertQueue runs, getting the **current** value of `true`

---

## Scenarios

### Scenario 1: Initial Page Load ✅

**State:**
- preserveFeedbackRef.current = false (initial)

**Action:** Page loads, fetches alerts

**Guard Check:** `!false` → `true` ✅

**Result:** Auto-selects first alert

---

### Scenario 2: After Executing Action ✅ (THE FIX)

**State:**
- preserveFeedbackRef.current = true (set in executeActionHandler)

**Action:** Queue reloads after 3.2 seconds

**Guard Check:** `!true` → `false` ❌

**Result:** Skips auto-select, feedback panel stays visible

---

### Scenario 3: Manual Alert Selection ✅

**State:**
- preserveFeedbackRef.current = false (cleared in handleAlertSelect)

**Action:** User clicks different alert in sidebar

**Guard Check:** `!false` → `true` ✅

**Result:** Normal selection behavior

---

### Scenario 4: User Gives Feedback Then Selects New Alert ✅

**State:**
- preserveFeedbackRef.current = true (after execution)
- User provides feedback (correct/incorrect)
- User clicks different alert

**Action:** handleAlertSelect runs

**Side Effect:** Sets preserveFeedbackRef.current = false

**Result:** User can freely navigate after giving feedback

---

## Why This Approach is Better

### Comparison

| Approach | Captures State | Works with setTimeout | Complexity |
|----------|----------------|----------------------|------------|
| State Guard | ✓ (bug) | ❌ Stale closure | Low |
| Ref Guard | ❌ (good!) | ✅ Always current | Low |
| Callback Deps | Maybe | Maybe | High |
| Event Emitter | No capture | Maybe | Very High |

### Ref Advantages

1. **Simple:** One line to set, one line to check
2. **Reliable:** Always reads current value
3. **No re-renders:** Changing ref.current doesn't trigger re-render
4. **Explicit:** Clear intent with naming (preserveFeedbackRef)

---

## Testing

### Manual Test Steps

1. **Initial Load:**
   - Load Tab 3
   - **Verify:** First alert auto-selected
   - **Console:** "Selected first alert: ALERT-XXXX"

2. **Execute Action:**
   - Select ALERT-7823
   - Analyze → Apply Recommendation
   - Wait for closed loop (4 steps)
   - **Verify:** OutcomeFeedback panel appears
   - **Console:** "Skipped auto-select (preserving feedback state)"
   - **Verify:** Panel stays visible for 3+ seconds

3. **Give Feedback:**
   - Click "Confirmed Correct"
   - **Verify:** Graph updates display
   - **Verify:** Panel shows result

4. **Manual Selection:**
   - Click different alert in sidebar
   - **Verify:** New alert loads normally
   - **Verify:** OutcomeFeedback panel gone (correct behavior)

### Console Output

**Expected on action execution:**
```
[AlertTriageTab] Set alerts state to: [...]
[AlertTriageTab] Skipped auto-select (preserving feedback state)
```

**Not expected (bug):**
```
[AlertTriageTab] Selected first alert: ALERT-7824  ← Bug if this appears
```

---

## Technical Deep Dive

### JavaScript Closures

A closure is created when a function is defined:

```javascript
const [count, setCount] = useState(0)

// Closure captures count=0
const logCount = () => {
  console.log(count)  // Will always log 0
}

setCount(1)
logCount()  // Logs: 0 (not 1!)
```

### Why setTimeout Makes It Worse

```javascript
const [count, setCount] = useState(0)

const logCountLater = () => {
  setTimeout(() => {
    console.log(count)  // Captures current count
  }, 1000)
}

logCountLater()  // Captures count=0
setCount(1)      // Updates to 1
// After 1 second: logs 0 (stale!)
```

### How Refs Solve It

```javascript
const countRef = useRef(0)

const logCountLater = () => {
  setTimeout(() => {
    console.log(countRef.current)  // Reads current value
  }, 1000)
}

logCountLater()         // Schedules read
countRef.current = 1    // Updates ref
// After 1 second: logs 1 (correct!)
```

---

## Alternative Solutions Considered

### Option 1: useCallback with Dependencies ❌

```typescript
const loadAlertQueue = useCallback(async () => {
  // ... logic
}, [selectedAlert, closedLoop])  // Re-creates function when deps change
```

**Problem:** Doesn't help with setTimeout — the function is still captured at call time

### Option 2: useEffect Dependency ❌

```typescript
useEffect(() => {
  loadAlertQueue()
}, [closedLoop])
```

**Problem:** Runs on every state change, not just when queue needs reload

### Option 3: Event Emitter ❌

```typescript
emitter.on('queue-reload', () => {
  if (!preserveFeedback) {
    setSelectedAlert(alerts[0])
  }
})
```

**Problem:** Over-engineered, adds complexity

### Option 4: Ref (CHOSEN) ✅

**Pros:**
- Simple to implement
- Always reads current value
- No re-render overhead
- Clear intent

**Cons:** None for this use case

---

## Related Patterns

### When to Use Refs vs State

| Use Case | Use Ref | Use State |
|----------|---------|-----------|
| Trigger re-render | ❌ | ✅ |
| Store DOM reference | ✅ | ❌ |
| Preserve value across renders | ✅ | ✅ |
| Access in closures/timeouts | ✅ | ❌ (stale) |
| Need previous value | ✅ | ❌ |

### Common Ref Patterns

```typescript
// 1. Preserve previous value
const prevCountRef = useRef()
useEffect(() => {
  prevCountRef.current = count
}, [count])

// 2. Store mutable flag
const isSubscribedRef = useRef(true)

// 3. Store interval/timeout ID
const intervalRef = useRef()
intervalRef.current = setInterval(...)

// 4. Store latest callback (avoids stale closure)
const callbackRef = useRef(callback)
callbackRef.current = callback
```

---

## Lessons Learned

### 1. State + setTimeout = Danger

When combining state with setTimeout, always consider stale closures.

### 2. Refs for Flags

For boolean flags that need to be checked in async callbacks, use refs.

### 3. Debug with Logs

Console logs showing state at critical points help identify closure bugs.

### 4. Name Refs Clearly

`preserveFeedbackRef` clearly communicates purpose vs generic `flagRef`.

---

## Verification

**Before Fix:**
- ❌ Feedback panel disappears after ~3 seconds
- ❌ Console shows auto-select happening
- ❌ User cannot give feedback

**After Fix:**
- ✅ Feedback panel stays visible
- ✅ Console shows "Skipped auto-select"
- ✅ User can give feedback
- ✅ Manual selection still works
- ✅ Initial load auto-selects

---

*Stale Closure Bug Fix | AlertTriageTab Ref Pattern | v2.5 | February 2026*
