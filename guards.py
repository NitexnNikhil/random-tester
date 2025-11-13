import re
from typing import Optional, List, Set
from dataclasses import dataclass


@dataclass
class GuardResult:
    """Result of a guardrail check"""
    is_blocked: bool
    reason: Optional[str] = None
    category: Optional[str] = None


class ContentGuardrail:
    """
    Enhanced content guardrail with fine-tuned accuracy.
    """
    
    def __init__(self):
        # HIGH-RISK keywords: Block with just 1 match
        self.high_risk_keywords = {
            "violence": [
                "kill", "murder", "assassinate", "execute", "slaughter",
                "torture", "abuse", "assault", "attack", "shoot", "stab",
                "bomb", "explosive", "weapon", "gun", "knife", "poison"
            ],
            "illegal_activities": [
                "hack", "crack password", "exploit vulnerability", "backdoor",
                "steal", "robbery", "fraud", "scam", "launder money",
                "counterfeit", "forge", "piracy", "traffick", "smuggle",
                "insider trading", "embezzle"
            ],
            "medical_advice": [
                "diagnose", "diagnosis", "prescription", "prescribe",
                "medication dosage", "medicine dosage", "drug dosage",
                "medical treatment", "cure for", "treatment for",
                "disease", "illness", "symptoms", "condition",
                "surgery recommendation", "operation advice"
            ],
            "self_harm": [
                "suicide", "kill myself", "end my life", "self harm",
                "cut myself", "hurt myself", "overdose"
            ]
        }
        
        # MEDIUM-RISK keywords: Block with 2+ matches
        self.medium_risk_keywords = {
            "financial_advice": [
                "invest", "stock tip", "guaranteed return", "quick profit",
                "financial advice", "portfolio", "trading strategy",
                "tax evasion", "tax avoidance", "crypto pump"
            ],
            "personal_info_requests": [
                "credit card", "password", "bank account", "pin",
                "ssn", "social security", "driver license",
                "passport number", "api key", "secret key"
            ]
        }
        
        # Exact phrases that should be blocked immediately
        self.blocked_phrases = [
            "how to make a bomb",
            "how to make explosives",
            "how to hack",
            "how to steal",
            "bypass security",
            "how to kill",
            "commit suicide",
            "end my life",
            "hurt myself"
        ]
        
        # Regex patterns for sensitive information
        self.sensitive_patterns = [
            (r'\b\d{3}-\d{2}-\d{4}\b', "SSN"),  # SSN pattern
            (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', "Credit Card"),  # Credit card
            (r'\b[A-Z]{2}\d{6,8}\b', "Passport"),  # Passport pattern
        ]
    
    def check(self, text: str) -> GuardResult:
        """
        Enhanced check with fine-tuned sensitivity.
        """
        text_lower = text.lower().strip()
        
        # 1. Check for exact blocked phrases (highest priority)
        for phrase in self.blocked_phrases:
            if phrase in text_lower:
                return GuardResult(
                    is_blocked=True,
                    reason=f"Contains blocked phrase: '{phrase}'",
                    category="blocked_phrase"
                )
        
        # 2. Check HIGH-RISK keywords (block with 1 match)
        for category, keywords in self.high_risk_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return GuardResult(
                        is_blocked=True,
                        reason=f"Contains high-risk keyword: '{keyword}'",
                        category=category
                    )
        
        # 3. Check MEDIUM-RISK keywords (block with 2+ matches)
        for category, keywords in self.medium_risk_keywords.items():
            matched_keywords = [kw for kw in keywords if kw in text_lower]
            if len(matched_keywords) >= 2:
                return GuardResult(
                    is_blocked=True,
                    reason=f"Contains multiple medium-risk keywords: {matched_keywords[:3]}",
                    category=category
                )
        
        # 4. Check for sensitive information patterns
        for pattern, pattern_name in self.sensitive_patterns:
            if re.search(pattern, text):
                return GuardResult(
                    is_blocked=True,
                    reason=f"Contains sensitive information: {pattern_name}",
                    category="sensitive_info"
                )
        
        # Content passes all checks
        return GuardResult(is_blocked=False)
    
    def get_decline_message(self, category: Optional[str] = None) -> str:
        """
        Get an appropriate decline message based on the blocked category.
        """
        decline_messages = {
            "violence": "I can't answer questions about violence or harmful activities. Is there anything else I can help you with?",
            "illegal_activities": "I can't provide information about illegal activities. Is there something else you'd like to know?",
            "personal_info_requests": "I can't help with sharing or storing sensitive personal information. What else can I assist you with?",
            "medical_advice": "I can't provide medical advice or diagnose conditions. Please consult a healthcare professional for medical concerns. Is there anything else I can help with?",
            "financial_advice": "I can't provide specific financial or investment advice. Please consult a licensed financial advisor. Is there something else you'd like to discuss?",
            "self_harm": "I'm concerned about what you're sharing. If you're in crisis, please reach out to a mental health professional or crisis hotline. Is there something else I can help you with?",
            "blocked_phrase": "I can't answer that question. Is there anything else you need help with?",
            "sensitive_info": "I detected sensitive information in your message. Please don't share personal details like credit cards, passwords, or SSNs. How else can I help?",
        }
        
        return decline_messages.get(
            category,
            "I can't answer that question. Is there anything else you need to ask?"
        )
    
    def add_high_risk_keyword(self, category: str, keyword: str) -> None:
        """Add a new high-risk keyword (blocks with 1 match)"""
        if category in self.high_risk_keywords:
            self.high_risk_keywords[category].append(keyword.lower())
        else:
            self.high_risk_keywords[category] = [keyword.lower()]
    
    def add_medium_risk_keyword(self, category: str, keyword: str) -> None:
        """Add a new medium-risk keyword (blocks with 2+ matches)"""
        if category in self.medium_risk_keywords:
            self.medium_risk_keywords[category].append(keyword.lower())
        else:
            self.medium_risk_keywords[category] = [keyword.lower()]
    
    def add_blocked_phrase(self, phrase: str) -> None:
        """Add a new exact phrase to block"""
        self.blocked_phrases.append(phrase.lower())
