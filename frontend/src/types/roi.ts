/**
 * TypeScript types for ROI Calculator
 * Matches backend Pydantic models
 */

export interface ROIRequest {
  alerts_per_day: number
  analysts: number
  avg_salary: number
  current_mttr_minutes: number
  current_auto_close_pct: number
  avg_escalation_cost: number
}

export interface ROIDefaults {
  alerts_per_day: number
  analysts: number
  avg_salary: number
  current_mttr_minutes: number
  current_auto_close_pct: number
  avg_escalation_cost: number
}

export interface ROIProjected {
  auto_close_pct: number
  mttr_minutes: number
  alerts_auto_handled_daily: number
  analyst_hours_freed_monthly: number
}

export interface ROISavings {
  analyst_time_annual: number
  escalation_cost_annual: number
  compliance_annual: number
  total_annual: number
  payback_weeks: number
  roi_multiple: number
}

export interface ROIResponse {
  inputs_echo: ROIRequest
  projected: ROIProjected
  savings: ROISavings
  narrative: string
}
