# ROI Calculator Modal Component

**Version:** v2.5
**Type:** Modal (Overlay)
**Trigger:** Tab 4 (Compounding Dashboard)
**Status:** ✅ Component Created (Integration pending)

---

## Overview

The ROI Calculator is an interactive modal that allows prospects to input their SOC-specific metrics and see projected savings when deploying the SOC Copilot. This is a key sales enablement tool.

### Key Features

- **Real-time calculation** - Results update automatically as user adjusts sliders (300ms debounce)
- **Animated counters** - Numbers animate smoothly when values change
- **Two-column layout** - Inputs on left, results on right
- **Responsive design** - Works on desktop and tablet
- **Export capability** - Placeholder for PDF export

---

## Files Created

### 1. `frontend/src/types/roi.ts`

TypeScript type definitions matching backend Pydantic models:

```typescript
export interface ROIRequest {
  alerts_per_day: number
  analysts: number
  avg_salary: number
  current_mttr_minutes: number
  current_auto_close_pct: number
  avg_escalation_cost: number
}

export interface ROIResponse {
  inputs_echo: ROIRequest
  projected: {
    auto_close_pct: number
    mttr_minutes: number
    alerts_auto_handled_daily: number
    analyst_hours_freed_monthly: number
  }
  savings: {
    analyst_time_annual: number
    escalation_cost_annual: number
    compliance_annual: number
    total_annual: number
    payback_weeks: number
    roi_multiple: number
  }
  narrative: string
}
```

### 2. `frontend/src/components/ROICalculator.tsx`

Main modal component (~650 lines):

**Key Sections:**
- `useCountUp` hook - Animates numbers with ease-out easing
- API functions - Fetch defaults and calculate ROI
- Input controls - 6 sliders/text inputs for SOC metrics
- Results display - Animated metrics, savings breakdown, narrative
- Footer - Export and close buttons

### 3. `frontend/src/lib/api.ts` (updated)

Added two new API functions:
- `getROIDefaults()` - Fetch default slider values
- `calculateROI(inputs)` - Calculate projected savings

---

## Component Structure

### Props

```typescript
interface ROICalculatorModalProps {
  isOpen: boolean
  onClose: () => void
}
```

### State

- `inputs` - Current slider/input values (ROIRequest)
- `result` - Calculation results (ROIResponse | null)
- `loading` - Loading state during calculation
- `error` - Error message if calculation fails

### Lifecycle

1. **On mount (when isOpen becomes true):**
   - Fetch defaults from `GET /api/roi/defaults`
   - Set input values to defaults
   - Calculate ROI with default values
   - Display results

2. **On input change:**
   - Update local state immediately
   - Debounce 300ms
   - Call `POST /api/roi/calculate`
   - Animate results to new values

3. **On close:**
   - Modal dismisses
   - State persists (doesn't reset)

---

## Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  ROI Calculator                                            [X]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌───────────────────┬───────────────────────────────────────┐  │
│  │ Your Environment  │ Projected Impact                      │  │
│  │                   │                                       │  │
│  │ Alerts/day [====] │ ┌──────┬──────┐                      │  │
│  │ Analysts   [====] │ │ 35%→ │ 18→  │                      │  │
│  │ Salary     [$___] │ │  89% │ 4.5m │                      │  │
│  │ MTTR       [====] │ └──────┴──────┘                      │  │
│  │ Auto-close [====] │ ┌──────┬──────┐                      │  │
│  │ Escalation [$___] │ │ 445  │ 1822 │                      │  │
│  │                   │ │ /day │ /mo  │                      │  │
│  │                   │ └──────┴──────┘                      │  │
│  │                   │                                       │  │
│  │                   │ ┌─────────────────────────────────┐  │  │
│  │                   │ │ ANNUAL SAVINGS                  │  │  │
│  │                   │ │ $1,079,800                      │  │  │
│  │                   │ │ Payback: 6 weeks | ROI: 9.0x   │  │  │
│  │                   │ └─────────────────────────────────┘  │  │
│  │                   │                                       │  │
│  │                   │ Breakdown:                            │  │
│  │                   │ • Analyst time: $894K (83%)           │  │
│  │                   │ • Escalation: $146K (13%)             │  │
│  │                   │ • Compliance: $40K (4%)               │  │
│  │                   │                                       │  │
│  │                   │ "Based on your 500 alerts/day..."     │  │
│  └───────────────────┴───────────────────────────────────────┘  │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                   [Export PDF]  [Close]          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Styling

### Theme

Matches existing demo aesthetic:
- **Background:** `bg-slate-900`
- **Cards:** `bg-slate-800` with `border-slate-700`
- **Accents:** Purple and blue gradients
- **Text:** White headings, slate-300 labels, slate-400 secondary

### Key Classes

```tsx
// Modal backdrop
className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"

// Modal container
className="bg-slate-900 rounded-lg shadow-2xl max-w-5xl w-full"

// Input slider
className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"

// Large savings card
className="bg-gradient-to-br from-purple-500/20 to-blue-500/20 border border-purple-500/30"

// Metric card
className="bg-slate-800 border border-slate-700 rounded-lg p-4"
```

### Icons

Uses Lucide React icons:
- `Calculator` - Modal header
- `Users` - "Your Environment" section
- `TrendingUp` - "Projected Impact" section
- `DollarSign` - Savings card
- `Clock` - Payback metric
- `ChevronRight` - Before/after arrows
- `Download` - Export button
- `X` - Close button
- `AlertCircle` - Error display

---

## Input Controls

| Input | Type | Range | Default | Display |
|-------|------|-------|---------|---------|
| Alerts per day | Slider | 50-50,000 | 500 | Value as number |
| SOC analysts | Slider | 1-200 | 8 | Value as number |
| Avg analyst salary | Text | $40K-$250K | $85,000 | $ prefix |
| Current MTTR | Slider | 1-120 min | 18 | Value + "min" |
| Current auto-close % | Slider | 0-95% | 35% | Percentage |
| Avg escalation cost | Text | $50-$1,000 | $150 | $ prefix |

### Slider Styling

All sliders use:
- Blue accent color (`accent-blue-500`)
- Gray track (`bg-slate-700`)
- Current value displayed above
- Min/max labels below

### Text Input Styling

Salary and escalation cost use:
- Dollar sign prefix (`$`) positioned absolutely
- Dark background (`bg-slate-700`)
- Blue focus border (`focus:border-blue-500`)
- Number input with step increments

---

## Results Display

### Top Section - Metric Cards (2x2 Grid)

Four cards showing projected improvements:

1. **Auto-close rate:** "35% → 89%" with green arrow
2. **MTTR:** "18 min → 4.5 min" with green arrow
3. **Alerts auto-handled:** "445/day" (blue)
4. **Analyst hours freed:** "1,822/mo" (purple)

### Middle Section - Annual Savings (Large Card)

Prominent purple gradient card:
- Large animated number: "$1,079,800"
- Payback period: "6 weeks"
- ROI multiple: "9.0x"

### Bottom Section - Breakdown

Three-line breakdown with percentages:
- Analyst time savings (typically 80-85%)
- Escalation cost savings (typically 13-15%)
- Compliance savings (typically 3-4%)

### Narrative

Italicized CFO-ready paragraph explaining the calculation in plain English.

---

## Animation

### Counter Animation

Uses `useCountUp` hook (from CompoundingTab):
- **Duration:** 1000ms for metrics, 1500ms for total savings
- **Easing:** Cubic ease-out (fast start, slow finish)
- **Precision:**
  - 0 decimals for counts and dollars
  - 1 decimal for MTTR
  - 2 decimals for percentages

### Trigger

Animations trigger when:
- Initial results load
- User changes any input (after debounce)

### Smooth Transitions

All animated values smoothly interpolate from previous to new value, creating a polished feel.

---

## API Integration

### On Mount

```typescript
GET /api/roi/defaults
→ {
    status: "success",
    defaults: {
      alerts_per_day: 500,
      analysts: 8,
      ...
    }
  }
```

### On Input Change (Debounced)

```typescript
POST /api/roi/calculate
Body: {
  alerts_per_day: 500,
  analysts: 8,
  avg_salary: 85000,
  current_mttr_minutes: 18,
  current_auto_close_pct: 0.35,
  avg_escalation_cost: 150
}

→ {
    inputs_echo: { ... },
    projected: {
      auto_close_pct: 0.89,
      mttr_minutes: 4.5,
      alerts_auto_handled_daily: 445,
      analyst_hours_freed_monthly: 1822
    },
    savings: {
      analyst_time_annual: 894000,
      escalation_cost_annual: 145800,
      compliance_annual: 40000,
      total_annual: 1079800,
      payback_weeks: 6,
      roi_multiple: 9.0
    },
    narrative: "Based on your 500 alerts/day..."
  }
```

---

## Usage Example (Next Step - Prompt 7C)

To integrate into Tab 4 (CompoundingTab.tsx):

```typescript
import ROICalculatorModal from '../components/ROICalculator'

export default function CompoundingTab() {
  const [showROI, setShowROI] = useState(false)

  return (
    <div>
      {/* Existing tab content */}

      <button onClick={() => setShowROI(true)}>
        Calculate Your ROI
      </button>

      {/* Modal */}
      <ROICalculatorModal
        isOpen={showROI}
        onClose={() => setShowROI(false)}
      />
    </div>
  )
}
```

---

## Error Handling

### Validation

Backend validates:
- All inputs within min/max ranges
- Current auto-close < 89% (can't improve if already at target)

### Display

Errors shown in red alert box above results:
```tsx
<div className="bg-red-500/10 border border-red-500/30">
  <AlertCircle /> {error}
</div>
```

### Recovery

User can adjust inputs to fix validation errors. Calculator retries automatically after debounce.

---

## Export Feature (Placeholder)

Currently logs to console and shows alert:

```typescript
const handleExport = () => {
  console.log('[ROI] Export to PDF requested')
  console.log('[ROI] Inputs:', inputs)
  console.log('[ROI] Results:', result)
  alert('PDF export not yet implemented')
}
```

**Future implementation:**
- Generate PDF with inputs and results
- Include company logo/branding
- Save/email to prospect

---

## Testing Checklist

### Manual Testing

- [ ] Modal opens when triggered
- [ ] Defaults load correctly
- [ ] All 6 inputs are interactive
- [ ] Sliders show current value
- [ ] Text inputs accept numbers
- [ ] Results update after 300ms
- [ ] Numbers animate smoothly
- [ ] Breakdown percentages add to 100%
- [ ] Narrative updates correctly
- [ ] Export logs to console
- [ ] Close button dismisses modal
- [ ] Backdrop click dismisses modal
- [ ] ESC key dismisses modal (if implemented)

### Edge Cases

- [ ] Very small SOC (50 alerts/day, 1 analyst)
- [ ] Very large SOC (10,000 alerts/day, 50 analysts)
- [ ] Current auto-close already high (>85%)
- [ ] Very low current auto-close (5%)
- [ ] Rapid slider changes (test debounce)
- [ ] Invalid inputs (negative, out of range)

### Visual Testing

- [ ] Modal is centered
- [ ] Two columns stack on mobile
- [ ] All text is readable
- [ ] Icons align properly
- [ ] Cards have consistent spacing
- [ ] Gradient card stands out
- [ ] Green arrows visible in metric cards

---

## Performance Considerations

### Debouncing

300ms debounce prevents excessive API calls:
- User can rapidly adjust slider
- Only final value triggers calculation
- Reduces backend load

### Animation Performance

Uses `requestAnimationFrame` for smooth 60fps:
- Efficient JavaScript animation
- No heavy CSS transitions
- Cancelable on unmount

### State Management

Simple local state:
- No Redux/Zustand needed
- Component self-contained
- Cleans up on unmount

---

## Future Enhancements (v3+)

- [ ] PDF export implementation
- [ ] Email results to prospect
- [ ] Save calculation for later
- [ ] Compare multiple scenarios side-by-side
- [ ] Sensitivity analysis (best/worst case)
- [ ] Industry benchmarking
- [ ] Custom compliance savings input
- [ ] Multi-year projection
- [ ] Integration with CRM (Salesforce)

---

## File Sizes

| File | Lines | Purpose |
|------|-------|---------|
| `roi.ts` | ~50 | TypeScript types |
| `ROICalculator.tsx` | ~650 | Modal component |
| `api.ts` (additions) | ~15 | API functions |

**Total:** ~715 lines of new code

---

*ROI Calculator Component Documentation | v2.5 | February 2026*
