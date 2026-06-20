from __future__ import annotations

import structlog
from google.adk.agents import AgentHook, AgentRequest, AgentResponse
from src.skills.pii_redactor.enterprise_av_security_pii_cleaner import clean_pii

logger = structlog.get_logger(__name__)

class PIIEnforcementHook(AgentHook):
    """
    AgentHook that acts as a final safety check before allowing an LLM request to proceed.
    It verifies that the prompt payload does NOT contain any raw PII (such as driver names,
    license plates, or GPS coordinates). If raw PII is found, it intercepts the request
    and raises an error, ensuring data safety across the entire agent workflow.
    """

    def before_turn(self, request: AgentRequest) -> AgentRequest:
        # Check all text parts in the new message
        if not request.new_message:
            return request

        has_pii = False
        pii_details = []

        for part in request.new_message.parts:
            if hasattr(part, "text") and part.text:
                result = clean_pii(part.text)
                if result.get("pii_found"):
                    has_pii = True
                    pii_details.append(result.get("redaction_summary"))

        if has_pii:
            logger.error("PIIEnforcementHook: Raw PII detected in outgoing LLM prompt!", details=pii_details)
            raise ValueError(
                "Security Exception: Raw PII detected in the prompt context. "
                "The `clean_pii` tool MUST be executed on all inputs before LLM inference."
            )

        logger.info("PIIEnforcementHook: Outgoing prompt context is clear of PII.")
        return request

    def after_turn(self, response: AgentResponse) -> AgentResponse:
        # Similarly, we can check the model's output to make sure it didn't generate any PII.
        # This is a defense-in-depth measure.
        if not response.content:
            return response

        for part in response.content.parts:
            if hasattr(part, "text") and part.text:
                result = clean_pii(part.text)
                if result.get("pii_found"):
                    logger.warning("PIIEnforcementHook: PII detected in model response! Applying automatic redaction.")
                    # Automatically redact the model's output
                    part.text = result["redacted_text"]

        return response
