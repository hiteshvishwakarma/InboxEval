import logging
import asyncio
from typing import List
from src.engine.golden_dataset_generator.schemas import HumanEmail
from src.engine.golden_dataset_generator.config import config
from ..schemas import PersonaProfileV2

logger = logging.getLogger("EngineV2_Step02_PersonaExtractAndCache")

async def extract_persona_v2(email: HumanEmail, llm_client=None) -> PersonaProfileV2:
    """
    Step 02 & 04 (Horizontal Batch Phase): Extracts Persona Profile AND 
    pre-caches 5 dynamic prompting strategies in 1 single LLM extraction call.
    Bypasses Step 04 LLM API call entirely during vertical execution.
    """
    logger.info(f"Extracting Persona V2 & Pre-Caching Prompting Strategies for Email ID: {email.id}")

    prompt = f"""
SYSTEM INSTRUCTIONS (STATIC PREFIX):
Analyze the provided email and extract a detailed Persona Profile AND 5 diverse Prompting Strategies.

REQUIREMENTS:
1. 'nlp_task': MUST be EXACTLY ONE of: ['Zero-Shot Drafting', 'Data Extraction', 'Thread Summarization', 'Tone Translation'].
2. 'formality_scale': MUST be EXACTLY ONE of: ['Hyper-Casual', 'Casual', 'Semi-Professional', 'Professional', 'Hyper-Formal'].
3. 'prompting_strategies': Generate 5 diverse strategies this specific persona might use when typing into AI (e.g., 'The Lazy Minimalist', 'The Micro-Manager', 'The Bullet-Point Thinker', 'The Conversationalist', 'The Rushed Executive').

--- DYNAMIC INPUT DATA ---
Raw Email Text: {email.raw_text}
"""

    if llm_client:
        res = llm_client.chat.completions.create(
            model=config.FAST_CLASSIFICATION_MODEL,
            response_model=PersonaProfileV2,
            messages=[{"role": "user", "content": prompt}]
        )
        persona = await res if asyncio.iscoroutine(res) else res
        return persona
    else:
        # Mock fallback for offline tests
        return PersonaProfileV2(
            intent="Request Information",
            sentiment="Neutral",
            nlp_task="Zero-Shot Drafting",
            domain="Corporate Communication",
            format="Standard Email",
            power_dynamic="Peer to Peer",
            formality_scale="Semi-Professional",
            behavioral_quirks=["Direct", "Concise"],
            evidence_quotes=["Please review"],
            prompting_strategies=[
                "The Lazy Minimalist (One sentence command)",
                "The Micro-Manager (Provides every detail)",
                "The Conversationalist (Talks to AI like human)",
                "The Bullet-Point Thinker (Strictly structured)",
                "The Rushed Executive (Fragmented thoughts)"
            ],
            typology_classification="Corporate_Peer_ZeroShot"
        )
