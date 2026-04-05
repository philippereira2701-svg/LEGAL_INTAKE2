import re
from typing import Dict, Any, List, Tuple
import bleach

class RuleEngine:
    """Deterministic logic layer that runs BEFORE Gemini AI"""

    DISQUALIFIERS = [
        ("incident_days_ago > 1095", "Statute of limitations likely expired (3+ years)"),
        ("already_represented == True", "Ethical conflict: Client already has an attorney"),
        ("incident_country not in ['US', 'USA', 'United States']", "Jurisdiction: Incident occurred outside the United States"),
        ("no_damages", "No documented medical treatment or bills")
    ]

    INJECTION_PATTERNS = [
        r"ignore (all |previous |prior )?instructions",
        r"you are now",
        r"new persona",
        r"system prompt",
        r"disregard",
        r"act as",
        r"pretend you",
        r"forget everything",
        r"jailbreak",
        r"DAN mode"
    ]

    def sanitize_input(self, text: str) -> Tuple[str, bool]:
        """Strip HTML, limit length, and detect prompt injection attempts"""
        if not text:
            return "", False
            
        # Limit to 2000 characters
        sanitized = text[:2000]
        
        # Remove HTML tags
        sanitized = bleach.clean(sanitized, tags=[], strip=True)
        
        # Normalize whitespace
        sanitized = " ".join(sanitized.split())
        
        # Detect injection
        injection_detected = False
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                injection_detected = True
                break
        
        # Flag if >30% ALL CAPS (common in spam/aggressive inputs)
        alpha_chars = [c for c in sanitized if c.isalpha()]
        if len(alpha_chars) > 20:
            caps_count = sum(1 for c in alpha_chars if c.isupper())
            if caps_count / len(alpha_chars) > 0.3:
                # We don't necessarily reject for caps, but it might be a flag
                pass

        return sanitized, injection_detected

    def run_disqualifiers(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check for hard 'No' conditions"""
        # Incident Days Ago
        days_ago = data.get('incident_days_ago', 0)
        if days_ago > 1095:
            return True, "Statute of limitations expired"
            
        # Already Represented
        if data.get('already_represented') is True:
            return True, "Client already represented"
            
        # Jurisdiction (assuming US for this MVP unless country is explicitly provided and not US)
        country = data.get('incident_country', 'US')
        if country.upper() not in ['US', 'USA', 'UNITED STATES']:
            return True, "Outside US jurisdiction"
            
        # Damages
        has_treatment = data.get('medical_treatment_received', False)
        hospitalized = data.get('hospitalized', False)
        bills = str(data.get('estimated_medical_bills', '0')).lower()
        if not has_treatment and not hospitalized and bills in ['0', 'none', 'nothing', 'null', '']:
            return True, "No documented damages"
            
        return False, ""

    def apply_modifiers(self, gemini_score: int, data: Dict[str, Any]) -> int:
        """Adjust Gemini's score based on deterministic factors"""
        modifiers = 0
        
        if data.get('police_report_filed') is True:
            modifiers += 2
        
        if data.get('hospitalized') is True:
            modifiers += 2
            
        bills = str(data.get('estimated_medical_bills', '')).lower()
        if 'surgery' in bills or 'er' in bills or 'emergency' in bills:
            modifiers += 1
            
        days_ago = data.get('incident_days_ago', 0)
        if days_ago > 730:
            modifiers -= 3
        elif days_ago > 365:
            modifiers -= 2
            
        desc_len = len(data.get('incident_description', ''))
        if desc_len > 200:
            modifiers += 1
        elif desc_len < 50:
            modifiers -= 1
            
        # Clamp score between 1 and 10
        final_score = max(1, min(10, gemini_score + modifiers))
        return final_score

    def process(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Full rule engine pipeline"""
        # 1. Sanitize
        desc, injection = self.sanitize_input(form_data.get('incident_description', ''))
        form_data['incident_description'] = desc
        
        # 2. Check Disqualifiers
        is_disqualified, reason = self.run_disqualifiers(form_data)
        
        if injection or is_disqualified:
            return {
                "is_disqualified": True,
                "reason": "Prompt injection detected" if injection else reason,
                "injection_risk_detected": injection,
                "rule_engine_score": 1,
                "final_score": 1,
                "ai_tier": "REJECT",
                "recommended_action": "REJECT_IMMEDIATELY"
            }
            
        return {
            "is_disqualified": False,
            "injection_risk_detected": False,
            "rule_engine_score": 5 # Base starting point for modifiers
        }
