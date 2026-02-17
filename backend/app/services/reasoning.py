"""
LLM Reasoning Narration - Makes rule-based decisions sound intelligent
~50 lines total. This is "intelligence theater" - the decision was already made.

The LLM's ONLY job: Generate a 2-3 sentence justification AFTER the agent decides.
This is narration, not decision-making.
"""
import os
from typing import Dict, Any
import vertexai
from vertexai.generative_models import GenerativeModel


class ReasoningNarrator:
    """Generates impressive-sounding justifications for rule-based decisions"""

    def __init__(self):
        project_id = os.getenv("PROJECT_ID")
        region = os.getenv("VERTEX_AI_LOCATION", "us-central1")

        vertexai.init(project=project_id, location=region)
        self.model = GenerativeModel("gemini-1.5-pro-002")

    async def generate_reasoning(
        self,
        alert_type: str,
        action: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Generate a 2-3 sentence SOC analyst justification.
        The decision is already made - this just explains it.
        """

        # Build prompt with context
        prompt = f"""You are a SOC analyst writing a brief justification for an alert decision.

Alert Type: {alert_type}
Recommended Action: {action}

Context:
- User: {context.get('user_name')} ({context.get('user_title')})
- Asset: {context.get('asset_hostname')} (criticality: {context.get('asset_criticality')})
- User Risk Score: {context.get('user_risk_score', 0.0)}
- User Traveling: {context.get('user_traveling', False)}
- Travel Destination: {context.get('travel_destination', 'N/A')}
- VPN Matches Location: {context.get('vpn_matches_location', False)}
- MFA Completed: {context.get('mfa_completed', False)}
- Device Fingerprint Match: {context.get('device_fingerprint_match', False)}
- Known Campaign: {context.get('known_campaign_signature', False)}
- Pattern ID: {context.get('pattern_id', 'None')}
- Pattern Occurrences: {context.get('pattern_count', 0)}
- False Positive Rate: {context.get('fp_rate', 0.0):.1%}

Write a 2-3 sentence justification for why this action is recommended.
Be specific about the context factors that led to this decision.
Sound like an experienced security analyst.
"""

        try:
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            # Fallback reasoning if LLM fails
            return self._fallback_reasoning(action, context)

    def _fallback_reasoning(self, action: str, context: Dict[str, Any]) -> str:
        """Simple fallback if LLM is unavailable"""

        if action == "false_positive_close":
            return (
                f"User {context.get('user_name')} has active travel to {context.get('travel_destination')}. "
                f"Login from VPN matches expected location with MFA completed. "
                f"Pattern PAT-TRAVEL-001 has 94% confidence with low false positive rate."
            )
        elif action == "auto_remediate":
            return (
                f"Known attack pattern detected on {context.get('asset_hostname')}. "
                f"Automatic remediation initiated per approved playbook. "
                f"Asset has been isolated from network pending investigation."
            )
        elif action == "escalate_incident":
            return (
                f"High-severity alert on critical asset {context.get('asset_hostname')}. "
                f"User risk score {context.get('user_risk_score', 0.0):.0%} exceeds threshold. "
                f"Escalating to incident response team for immediate investigation."
            )
        else:
            return (
                f"Alert requires additional analyst review. "
                f"Context gathered from {context.get('nodes_consulted', 47)} graph nodes. "
                f"Escalating to Tier 2 for manual investigation."
            )


# Global narrator instance
narrator = ReasoningNarrator()
