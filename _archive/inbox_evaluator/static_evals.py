import re
from typing import Dict, Any

class StaticEvaluator:
    """
    Handles deterministic, non-LLM evaluations like spam detection and basic formatting.
    This saves API costs and runs in milliseconds.
    """
    
    # Common spam trigger words
    SPAM_TRIGGERS = [
        "free money", "click here", "urgent", "act now", "winner",
        "guarantee", "no strings attached", "risk-free", "buy direct"
    ]
    
    def __init__(self):
        pass
        
    def evaluate(self, email_text: str) -> Dict[str, Any]:
        """
        Runs all static checks and returns a scorecard.
        """
        email_lower = email_text.lower()
        
        # 1. Spam Check
        spam_hits = [word for word in self.SPAM_TRIGGERS if word in email_lower]
        spam_score = "High Risk" if len(spam_hits) > 1 else "Low Risk"
        
        # 2. Link Density Check (too many links often means spam)
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', email_lower)
        link_density = "High" if len(urls) > 3 else "Normal"
        
        # 3. Basic Formatting (Does it look like an email?)
        # A very basic check: Does it have line breaks suggesting paragraphs?
        has_paragraphs = "\n\n" in email_text
        
        return {
            "spam_score": spam_score,
            "spam_triggers_found": spam_hits,
            "link_density": link_density,
            "has_basic_formatting": has_paragraphs
        }

if __name__ == "__main__":
    # Quick test
    evaluator = StaticEvaluator()
    bad_email = "URGENT!!! Click here to get your free money now! http://spam.com http://spam2.com http://spam3.com http://spam4.com"
    print(evaluator.evaluate(bad_email))
