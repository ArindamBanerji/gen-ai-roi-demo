/**
 * Domain configuration for the frontend.
 * All domain-specific labels, colors, and numbers live here.
 * Components import from this file instead of hardcoding values.
 *
 * To switch domains: change this file (or make it dynamic in v4.5+).
 *
 * Values extracted verbatim from existing components — this is
 * centralisation, not redesign.
 */

export const domainConfig = {
  // Identity
  name: "soc",
  displayName: "SOC Copilot",
  version: "v3.2",
  triggerEntity: "Alert",
  triggerEntityPlural: "Alerts",

  // Tab labels — exact strings from App.tsx tabs array
  tabs: {
    analytics:   "SOC Analytics",
    evolution:   "Runtime Evolution",
    decision:    "Alert Triage",
    compounding: "Compounding",
  },

  // Business impact numbers (Tab 4)
  // Source of truth: backend/app/routers/metrics.py generate_compounding_data()
  // CompoundingTab reads these from the API; this object is the frontend reference.
  metrics: {
    hrsSavedMonthly:       847,
    costAvoidedQuarterly:  127000,
    mttrReductionPct:      75,
    backlogEliminated:     2400,
  },

  // Header — exact strings from App.tsx
  headerTitle:    "SOC Copilot Demo",
  headerSubtitle: "AI-Augmented Security Operations with Runtime Evolution",
} as const
