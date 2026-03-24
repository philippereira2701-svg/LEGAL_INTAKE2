import os
import json
import re
from pydantic import BaseModel, Field
from typing import List, Literal
from google import genai
from dotenv import load_dotenv

load_dotenv()

class ScoringPillar(BaseModel):
    score: int = Field(..., description="Score from 0 to 10")
    reasoning: str = Field(..., description="Brief explanation")

class IntakeScoringResult(BaseModel):
    lead_score: int
    liability: ScoringPillar
    damages: ScoringPillar
    statute_of_limitations: ScoringPillar
    summary: str
    red_flags: List[str]
    tier: Literal["BOOK NOW", "ATTORNEY REVIEW", "BORDERLINE", "LIKELY DECLINE", "REJECT"]
    recommended_action: Literal["AUTO_BOOK", "SOFT_REJECT", "MANUAL_REVIEW"]

class IntakeScorer:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        # Try these models in order
        self.models = ["gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-2.0-flash"]

    def _get_heuristic_score(self, data: str) -> IntakeScoringResult:
        """Fail-safe: Basic keyword-based triage if AI is unavailable."""
        data_lower = data.lower()
        score = 5 # Default
        flags = []
        
        # Heuristic detection
        if any(w in data_lower for w in ["hospital", "surgery", "broken", "fracture", "icu", "death"]):
            score += 3
        if any(w in data_lower for w in ["drunk", "dui", "rear-ended", "red light"]):
            score += 2
        if "lawyer" in data_lower or "attorney" in data_lower:
            flags.append("Already represented?")
            
        score = min(score, 10)
        
        return IntakeScoringResult(
            lead_score=score,
            liability=ScoringPillar(score=score, reasoning="Heuristic Analysis (AI Fallback)"),
            damages=ScoringPillar(score=score, reasoning="Heuristic Analysis (AI Fallback)"),
            statute_of_limitations=ScoringPillar(score=10, reasoning="Recent event assumed"),
            summary="[AI OFFLINE] Heuristic scan performed. High-priority keywords detected.",
            red_flags=flags,
            tier="BOOK NOW" if score >= 8 else "ATTORNEY REVIEW",
            recommended_action="AUTO_BOOK" if score >= 8 else "MANUAL_REVIEW"
        )

    def score_lead(self, lead_data: str) -> IntakeScoringResult:
        if not self.client:
            return self._get_heuristic_score(lead_data)

        prompt = f"Triage this legal lead for a Personal Injury firm. Return JSON only.\n\nDATA:\n{lead_data}"
        
        # Try multiple models to bypass quota/404 issues
        for model_id in self.models:
            try:
                response = self.client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config={
                        'response_mime_type': 'application/json',
                        'response_schema': IntakeScoringResult,
                    }
                )
                return IntakeScoringResult.model_validate_json(response.text)
            except Exception as e:
                print(f"Model {model_id} failed: {e}")
                continue # Try next model
        
        # If all AI models fail, use the Heuristic Engine
        print("All AI models exhausted. Falling back to Heuristic Engine.")
        return self._get_heuristic_score(lead_data)
