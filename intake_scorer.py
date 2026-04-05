import os
import json
import re
from pydantic import BaseModel, Field
from typing import List, Literal
from google import genai
from dotenv import load_dotenv
from logger import logger

load_dotenv()

class ScoringPillar(BaseModel):
    score: int = Field(ge=0, le=10)
    reasoning: str

class IntakeScoringResult(BaseModel):
    lead_score: int = Field(ge=0, le=10)
    liability: ScoringPillar
    damages: ScoringPillar
    statute_of_limitations: ScoringPillar
    summary: str
    red_flags: List[str]
    tier: Literal["BOOK NOW", "ATTORNEY REVIEW", "BORDERLINE", "DECLINE"]
    recommended_action: Literal["AUTO_BOOK", "MANUAL_REVIEW", "SEND_REJECTION"]

class IntakeScorer:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.models = ["gemini-1.5-flash", "gemini-2.0-flash"]

    def _get_heuristic_score(self, data: str) -> IntakeScoringResult:
        """Fail-safe: Basic keyword-based triage."""
        logger.warning("AI OFFLINE: Initializing Heuristic Fallback Engine.")
        data_lower = data.lower()
        score = 5 
        flags = []
        
        if any(w in data_lower for w in ["hospital", "surgery", "broken", "fracture", "death"]): score += 3
        if any(w in data_lower for w in ["drunk", "dui", "rear-ended"]): score += 2
        if "lawyer" in data_lower: flags.append("Potential dual representation")
            
        return IntakeScoringResult(
            lead_score=min(score, 10),
            liability=ScoringPillar(score=score, reasoning="Heuristic Scan"),
            damages=ScoringPillar(score=score, reasoning="Heuristic Scan"),
            statute_of_limitations=ScoringPillar(score=10, reasoning="Recent"),
            summary="[HEURISTIC] Automated keyword-based triage completed.",
            red_flags=flags,
            tier="ATTORNEY REVIEW",
            recommended_action="MANUAL_REVIEW"
        )

    def score_lead(self, lead_data: str) -> IntakeScoringResult:
        if not self.client:
            return self._get_heuristic_score(lead_data)

        system_instruction = (
            "You are a Senior Personal Injury Intake Specialist for LEGAL_PRJ. Analyze the provided lead data "
            "rigorously for three pillars: 1. Liability (who is at fault?), 2. Damages (severity of injury/loss), "
            "and 3. Statute of Limitations (jurisdictional deadlines). "
            "Identify red flags such as: already represented, user at fault, no injury, or old incident. "
            "Return structured JSON matching the provided schema."
        )

        prompt = f"{system_instruction}\n\nCLIENT DATA:\n{lead_data}"
        
        for model_id in self.models:
            try:
                logger.info(f"AI INFERENCE | Model:{model_id} | Attempting Triage")
                response = self.client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config={
                        'response_mime_type': 'application/json',
                        'response_schema': IntakeScoringResult,
                    }
                )
                result = IntakeScoringResult.model_validate_json(response.text)
                logger.info(f"AI SUCCESS | Score:{result.lead_score} | Tier:{result.tier}")
                return result
            except Exception as e:
                logger.error(f"AI FAILURE | Model:{model_id} | Error:{str(e)}")
                continue
        
        return self._get_heuristic_score(lead_data)
