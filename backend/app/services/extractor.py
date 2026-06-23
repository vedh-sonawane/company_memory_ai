import json
import logging
from app.schemas.models import ExtractionResponse
from app.services.llm import get_llm_service

logger = logging.getLogger(__name__)

class ExtractorService:
    def __init__(self):
        # Dynamically load the LLM service configured in the environment
        try:
            self.llm_service = get_llm_service()
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {e}")
            self.llm_service = None

    def extract_from_text(self, text: str) -> ExtractionResponse:
        if not self.llm_service:
            # Re-initialize in case .env was updated/loaded late
            self.llm_service = get_llm_service()

        prompt = f"""
You are the extraction engine of Company Memory AI.
Your task is to analyze the following messy conversation transcript and extract two lists:
1. Tasks / Action Items: What must be done, who is assigned to do it (owner), and when it is due (deadline).
2. Decisions: Key strategic or operational decisions made, along with the context or rationale behind them.

Guidelines:
- "task": Capture the direct actionable summary. Ensure it is clear.
- "owner": The person assigned to do it. Extract their name or handle. If no owner is assigned, output an empty string "".
- "deadline": The due date or timeframe (e.g., "Friday", "2026-06-25"). If no deadline is specified, output an empty string "".
- "decision": A clean, concise statement of the decision.
- "context": The brief background or reason for that decision. If none, output an empty string "".
- Be conservative: do not hallucinate tasks or decisions that were not agreed upon or mentioned.
- If there are no tasks or decisions, return empty lists.

---
CONVERSATION TRANSCRIPT:
{text}
---
"""
        try:
            raw_result = self.llm_service.generate(prompt, ExtractionResponse)
            
            # Parse response depending on what LLM provider returned
            if isinstance(raw_result, str):
                data = json.loads(raw_result)
                return ExtractionResponse(**data)
            elif isinstance(raw_result, dict):
                return ExtractionResponse(**raw_result)
            elif isinstance(raw_result, ExtractionResponse):
                return raw_result
            else:
                raise ValueError(f"Unexpected response type from LLM service: {type(raw_result)}")
                
        except Exception as e:
            logger.error(f"Error during extraction pipeline: {e}", exc_info=True)
            raise e
