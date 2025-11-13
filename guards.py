import re
from typing import Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class GuardResult:
    """Result of a guardrail check"""
    is_blocked: bool
    reason: Optional[str] = None
    category: Optional[str] = None
    confidence: float = 1.0  # Confidence score 0-1


class ContentGuardrail:
    """
    Advanced content guardrail with regex-based precision matching.
    """
    
    def __init__(self):
        # Compile HIGH-RISK regex patterns with word boundaries
        self.high_risk_patterns = {
            "violence": [
                (r'\b(kill|murder|assassinate|execute|slaughter)\s+(someone|people|person|him|her|them)\b', 0.95),
                (r'\bhow\s+to\s+(kill|murder|harm|hurt|attack)\b', 1.0),
                (r'\b(torture|abuse|assault|attack)\s+(someone|people|person)\b', 0.95),
                (r'\b(shoot|stab|poison|strangle)\s+(someone|him|her|them)\b', 0.95),
                (r'\bmake\s+(bomb|explosive|weapon)\b', 1.0),
                (r'\b(gun|knife|weapon)\s+to\s+(kill|hurt|harm|attack)\b', 0.95),
            ],
            "illegal_activities": [
                (r'\bhow\s+to\s+(hack|crack|steal|rob|fraud|scam)\b', 1.0),
                (r'\b(steal|rob)\s+(money|from|credit|password)\b', 0.95),
                (r'\b(hack|crack)\s+(into|password|account|system)\b', 0.95),
                (r'\b(bypass|circumvent)\s+(security|authentication|verification)\b', 0.90),
                (r'\b(launder|laundering)\s+money\b', 0.95),
                (r'\b(counterfeit|forge|fake)\s+(money|documents|id|passport)\b', 0.95),
                (r'\b(illegal|illicit)\s+(drugs|weapons|trade)\b', 0.90),
            ],
            "medical_advice": [
                (r'\b(diagnose|diagnosis)\s+(my|me|this)\b', 0.95),
                (r'\bwhat\s+(disease|illness|condition)\s+(do\s+i|am\s+i)\b', 0.90),
                (r'\b(prescription|prescribe|medication)\s+(for|dosage|how\s+much)\b', 0.95),
                (r'\b(cure|treat|treatment)\s+for\s+(my|cancer|disease|illness)\b', 0.90),
                (r'\bshould\s+i\s+take\s+(medication|medicine|drug|pills)\b', 0.90),
                (r'\b(surgery|operation)\s+(advice|recommendation|should\s+i)\b', 0.90),
                (r'\bhow\s+(much|many)\s+(medication|medicine|dosage|pills)\b', 0.85),
            ],
            "self_harm": [
                (r'\b(kill|end|harm|hurt)\s+myself\b', 1.0),
                (r'\b(commit|committing)\s+suicide\b', 1.0),
                (r'\b(self\s+harm|self-harm|cutting\s+myself)\b', 1.0),
                (r'\bhow\s+to\s+(die|suicide|overdose)\b', 1.0),
                (r'\bwant\s+to\s+(die|kill\s+myself|end\s+(my\s+)?life)\b', 1.0),
            ]
        }
        
        # Compile MEDIUM-RISK patterns (require contextual matches)
        self.medium_risk_patterns = {
            "financial_advice": [
                (r'\b(invest|investing)\s+.{0,20}(guaranteed|sure|certain)\s+(return|profit)\b', 0.90),
                (r'\bshould\s+i\s+invest\s+in\s+\b', 0.80),
                (r'\b(stock|crypto)\s+tip(s)?\b', 0.85),
                (r'\b(tax\s+evasion|evade\s+tax|avoid\s+paying\s+tax)\b', 0.95),
                (r'\bguaranteed\s+(return|profit|money)\b', 0.85),
            ],
            "personal_info_requests": [
                (r'\b(tell|give|share|store)\s+.{0,15}(password|credit\s+card|ssn|social\s+security)\b', 0.90),
                (r'\b(remember|save|store)\s+my\s+(password|pin|credit)\b', 0.90),
            ]
        }
        
        # Context-aware blocklist with word boundaries
        self.context_keywords = {
            "violence": [
                r'\b(kill|killing|murder|harm|hurt|attack|assault)\b',
                r'\b(bomb|explosive|weapon|gun|knife|poison)\b',
            ],
            "illegal": [
                r'\b(hack|hacking|crack|steal|stealing|fraud|scam)\b',
                r'\b(illegal|illicit|criminal|unlawful)\b',
            ],
            "medical": [
                r'\b(diagnose|diagnosis|prescription|prescribe|medication|treatment)\b',
                r'\b(disease|illness|symptoms|condition|surgery|operation)\b',
            ],
        }
        
        # WHITELIST: Common false positives to exclude
        self.whitelist_patterns = [
            r'\b(killing\s+it|killing\s+time|killer\s+app|killer\s+feature)\b',  # Common expressions
            r'\b(hack\s+together|life\s+hack|growth\s+hack)\b',  # Tech jargon
            r'\b(code\s+is\s+killing|bug\s+is\s+killing)\b',  # Developer speak
            r'\b(air\s+condition|weather\s+condition|market\s+condition)\b',  # Non-medical condition
            r'\b(steal\s+the\s+show|steal\s+the\s+spotlight)\b',  # Idioms
        ]
        
        # Sensitive data patterns with word boundaries
        self.sensitive_patterns = [
            (r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b', "SSN"),  # SSN
            (r'\b(?:\d{4}[-\s]?){3}\d{4}\b', "Credit Card"),  # Credit card
            (r'\b[A-Z]{2}\d{6,8}\b', "Passport"),  # Passport
            (r'\b(?:api[_-]?key|secret[_-]?key|access[_-]?token)[\s:=]+[\w\-]{20,}\b', "API Key"),
        ]
        
        # Compile all patterns for performance
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile all regex patterns for better performance"""
        self.compiled_high_risk = {}
        for category, patterns in self.high_risk_patterns.items():
            self.compiled_high_risk[category] = [
                (re.compile(pattern, re.IGNORECASE), confidence) 
                for pattern, confidence in patterns
            ]
        
        self.compiled_medium_risk = {}
        for category, patterns in self.medium_risk_patterns.items():
            self.compiled_medium_risk[category] = [
                (re.compile(pattern, re.IGNORECASE), confidence) 
                for pattern, confidence in patterns
            ]
        
        self.compiled_context = {}
        for category, patterns in self.context_keywords.items():
            self.compiled_context[category] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        
        self.compiled_whitelist = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.whitelist_patterns
        ]
        
        self.compiled_sensitive = [
            (re.compile(pattern), name) for pattern, name in self.sensitive_patterns
        ]
    
    def _check_whitelist(self, text: str) -> bool:
        """Check if text matches whitelist patterns (false positives)"""
        for pattern in self.compiled_whitelist:
            if pattern.search(text):
                return True
        return False
    
    def check(self, text: str) -> GuardResult:
        """
        Advanced check with regex precision and context awareness.
        """
        text = text.strip()
        text_lower = text.lower()
        
        # Skip if whitelisted (common false positives)
        if self._check_whitelist(text_lower):
            return GuardResult(is_blocked=False)
        
        # 1. HIGH-RISK PATTERN CHECK (most specific, highest priority)
        for category, patterns in self.compiled_high_risk.items():
            for pattern, confidence in patterns:
                match = pattern.search(text_lower)
                if match:
                    return GuardResult(
                        is_blocked=True,
                        reason=f"Matched high-risk pattern in '{match.group()}'",
                        category=category,
                        confidence=confidence
                    )
        
        # 2. MEDIUM-RISK PATTERN CHECK
        for category, patterns in self.compiled_medium_risk.items():
            for pattern, confidence in patterns:
                match = pattern.search(text_lower)
                if match:
                    return GuardResult(
                        is_blocked=True,
                        reason=f"Matched medium-risk pattern in '{match.group()}'",
                        category=category,
                        confidence=confidence
                    )
        
        # 3. CONTEXT-BASED KEYWORD CHECK (requires 2+ matches from same category)
        for category, patterns in self.compiled_context.items():
            matches = []
            for pattern in patterns:
                found = pattern.findall(text_lower)
                matches.extend(found)
            
            # Require at least 2 different keywords from the same category
            if len(set(matches)) >= 2:
                category_map = {
                    "violence": "violence",
                    "illegal": "illegal_activities",
                    "medical": "medical_advice"
                }
                return GuardResult(
                    is_blocked=True,
                    reason=f"Multiple context keywords detected: {matches[:3]}",
                    category=category_map.get(category, category),
                    confidence=0.75
                )
        
        # 4. SENSITIVE INFORMATION PATTERN CHECK
        for pattern, pattern_name in self.compiled_sensitive:
            if pattern.search(text):
                return GuardResult(
                    is_blocked=True,
                    reason=f"Contains sensitive information: {pattern_name}",
                    category="sensitive_info",
                    confidence=0.95
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
            "self_harm": "I'm concerned about what you're sharing. If you're in crisis, please reach out to a mental health professional or call 988 (Suicide and Crisis Lifeline). Is there something else I can help you with?",
            "sensitive_info": "I detected sensitive information in your message. Please don't share personal details like credit cards, passwords, or SSNs. How else can I help?",
        }
        
        return decline_messages.get(
            category,
            "I can't answer that question. Is there anything else you need to ask?"
        )
    
    def add_high_risk_pattern(self, category: str, pattern: str, confidence: float = 0.90) -> None:
        """Add a new high-risk regex pattern"""
        if category not in self.high_risk_patterns:
            self.high_risk_patterns[category] = []
        self.high_risk_patterns[category].append((pattern, confidence))
        # Recompile patterns
        self._compile_patterns()
    
    def add_whitelist_pattern(self, pattern: str) -> None:
        """Add a pattern to whitelist (prevent false positives)"""
        self.whitelist_patterns.append(pattern)
        self.compiled_whitelist.append(re.compile(pattern, re.IGNORECASE))
