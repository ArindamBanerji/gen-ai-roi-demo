"""
ROI Calculator API - v2.5 Feature
Accepts prospect-specific SOC inputs and returns projected savings.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Dict, Any


router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class ROIRequest(BaseModel):
    """ROI Calculator input parameters"""
    alerts_per_day: int = Field(
        default=500,
        ge=50,
        le=50000,
        description="Number of security alerts per day"
    )
    analysts: int = Field(
        default=8,
        ge=1,
        le=200,
        description="Number of SOC analysts"
    )
    avg_salary: float = Field(
        default=85000,
        ge=40000,
        le=250000,
        description="Average analyst salary (USD)"
    )
    current_mttr_minutes: float = Field(
        default=18,
        ge=1,
        le=120,
        description="Current mean time to respond (minutes)"
    )
    current_auto_close_pct: float = Field(
        default=0.35,
        ge=0.0,
        le=0.95,
        description="Current auto-close percentage (0.0-0.95)"
    )
    avg_escalation_cost: float = Field(
        default=150,
        ge=50,
        le=1000,
        description="Average cost per escalation (USD)"
    )

    @validator('current_auto_close_pct')
    def validate_percentage(cls, v):
        """Ensure percentage is in valid range"""
        if v < 0.0 or v > 0.95:
            raise ValueError("current_auto_close_pct must be between 0.0 and 0.95")
        return v


class ROIResponse(BaseModel):
    """ROI Calculator results"""
    inputs_echo: Dict[str, Any]
    projected: Dict[str, Any]
    savings: Dict[str, Any]
    narrative: str


# ============================================================================
# Helper Functions
# ============================================================================

def calculate_roi(inputs: ROIRequest) -> ROIResponse:
    """
    Calculate ROI based on prospect inputs.

    Assumptions:
    - Projected auto-close rate: 89% (based on Week 4 demo data)
    - Projected MTTR: 25% of current (75% reduction)
    - Escalation rate: 12% of manually-handled alerts escalate to Tier 2
    - Compliance savings: $5K per analyst annually
    - License cost: $15K per analyst seat, minimum $50K
    """

    # Projected performance (based on demo Week 4 data)
    projected_auto_close = 0.89
    projected_mttr = inputs.current_mttr_minutes * 0.25

    # Monthly and daily volumes
    monthly_alerts = inputs.alerts_per_day * 30

    # Additional alerts auto-handled
    new_auto_handled = monthly_alerts * projected_auto_close
    old_auto_handled = monthly_alerts * inputs.current_auto_close_pct
    additional_auto_handled = new_auto_handled - old_auto_handled

    # Time savings
    analyst_hourly = inputs.avg_salary / 2080  # 2080 work hours/year
    minutes_saved_per_alert = inputs.current_mttr_minutes - projected_mttr
    hours_freed_monthly = (additional_auto_handled * minutes_saved_per_alert) / 60

    # Annual savings calculations
    annual_analyst_savings = hours_freed_monthly * 12 * analyst_hourly

    # Escalation savings: 12% of manually-handled alerts get escalated
    # Note: additional_auto_handled is monthly, so we calculate monthly escalations avoided
    escalation_rate = 0.12
    monthly_escalations_avoided = additional_auto_handled * escalation_rate
    annual_escalation_savings = monthly_escalations_avoided * inputs.avg_escalation_cost

    annual_compliance_savings = inputs.analysts * 5000

    total_annual = annual_analyst_savings + annual_escalation_savings + annual_compliance_savings

    # Payback and ROI (realistic license cost: $15K per analyst seat, min $50K)
    estimated_annual_license = max(inputs.analysts * 15000, 50000)
    payback_weeks = round((estimated_annual_license / total_annual) * 52) if total_annual > 0 else 0
    roi_multiple = round(total_annual / estimated_annual_license, 1) if estimated_annual_license > 0 else 0

    # Build response
    inputs_echo = {
        "alerts_per_day": inputs.alerts_per_day,
        "analysts": inputs.analysts,
        "avg_salary": inputs.avg_salary,
        "current_mttr_minutes": inputs.current_mttr_minutes,
        "current_auto_close_pct": inputs.current_auto_close_pct,
        "avg_escalation_cost": inputs.avg_escalation_cost
    }

    projected = {
        "auto_close_pct": projected_auto_close,
        "mttr_minutes": round(projected_mttr, 1),
        "alerts_auto_handled_daily": round(inputs.alerts_per_day * projected_auto_close),
        "analyst_hours_freed_monthly": round(hours_freed_monthly)
    }

    savings = {
        "analyst_time_annual": round(annual_analyst_savings, 2),
        "escalation_cost_annual": round(annual_escalation_savings, 2),
        "compliance_annual": round(annual_compliance_savings, 2),
        "total_annual": round(total_annual, 2),
        "payback_weeks": payback_weeks,
        "roi_multiple": roi_multiple
    }

    # Generate CFO-ready narrative
    narrative = generate_narrative(inputs, projected, savings)

    return ROIResponse(
        inputs_echo=inputs_echo,
        projected=projected,
        savings=savings,
        narrative=narrative
    )


def generate_narrative(inputs: ROIRequest, projected: Dict, savings: Dict) -> str:
    """Generate a CFO-ready narrative summary"""

    # Format currency values
    total_annual_fmt = f"${savings['total_annual']:,.0f}"
    analyst_savings_fmt = f"${savings['analyst_time_annual']:,.0f}"

    # Format percentages
    current_auto_pct = int(inputs.current_auto_close_pct * 100)
    projected_auto_pct = int(projected['auto_close_pct'] * 100)
    improvement_pct = projected_auto_pct - current_auto_pct

    # Calculate MTTR reduction percentage
    mttr_reduction_pct = int((1 - (projected['mttr_minutes'] / inputs.current_mttr_minutes)) * 100)

    narrative = (
        f"Based on your {inputs.alerts_per_day:,} alerts/day and {inputs.analysts} analysts "
        f"at ${inputs.avg_salary:,.0f} average salary, deploying the SOC Copilot would increase "
        f"auto-close rates from {current_auto_pct}% to {projected_auto_pct}% (+{improvement_pct} points) "
        f"and reduce MTTR by {mttr_reduction_pct}% (from {inputs.current_mttr_minutes:.1f} min to "
        f"{projected['mttr_minutes']:.1f} min). This would recover an estimated "
        f"{projected['analyst_hours_freed_monthly']:,} analyst hours per month and save approximately "
        f"{total_annual_fmt} annually ({analyst_savings_fmt} in analyst time, "
        f"${savings['escalation_cost_annual']:,.0f} in reduced escalations, and "
        f"${savings['compliance_annual']:,.0f} in compliance efficiencies). "
        f"With an estimated payback period of {savings['payback_weeks']} weeks and "
        f"{savings['roi_multiple']}x ROI, the compounding intelligence model delivers "
        f"measurable value from day one while building a defensible moat over time."
    )

    return narrative


# ============================================================================
# GET /api/roi/defaults - Default Values
# ============================================================================

@router.get("/roi/defaults")
async def get_roi_defaults():
    """
    Get default slider values for ROI calculator initialization.
    Frontend uses these to populate the form on load.
    """
    try:
        defaults = {
            "alerts_per_day": 500,
            "analysts": 8,
            "avg_salary": 85000,
            "current_mttr_minutes": 18,
            "current_auto_close_pct": 0.35,
            "avg_escalation_cost": 150
        }

        return {
            "status": "success",
            "defaults": defaults
        }

    except Exception as e:
        print(f"[ERROR] Failed to get ROI defaults: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get defaults: {str(e)}"
        )


# ============================================================================
# POST /api/roi/calculate - Calculate ROI
# ============================================================================

@router.post("/roi/calculate")
async def calculate_roi_endpoint(request: ROIRequest):
    """
    Calculate ROI based on prospect-specific SOC inputs.

    Accepts current SOC metrics and returns projected savings with:
    - Increased auto-close rate (89% target)
    - Reduced MTTR (75% reduction)
    - Annual savings broken down by category
    - Payback period and ROI multiple
    - CFO-ready narrative summary

    Example request:
    ```json
    {
        "alerts_per_day": 500,
        "analysts": 8,
        "avg_salary": 85000,
        "current_mttr_minutes": 18,
        "current_auto_close_pct": 0.35,
        "avg_escalation_cost": 150
    }
    ```
    """
    try:
        print(f"[ROI] Calculating ROI for {request.alerts_per_day} alerts/day, "
              f"{request.analysts} analysts")

        # Validate inputs
        if request.current_auto_close_pct >= 0.89:
            raise HTTPException(
                status_code=400,
                detail="Your current auto-close rate is already at or above our projected rate (89%). "
                       "ROI calculation may not be meaningful."
            )

        # Calculate ROI
        result = calculate_roi(request)

        print(f"[ROI] Calculated total annual savings: ${result.savings['total_annual']:,.0f}")

        return result.dict()

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] ROI calculation failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate ROI: {str(e)}"
        )
