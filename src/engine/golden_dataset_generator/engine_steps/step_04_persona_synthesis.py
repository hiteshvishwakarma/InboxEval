import logging
from typing import List
from ..schemas import HumanEmail, PersonaProfile
from ..config import config

logger = logging.getLogger("Step04_PersonaSynthesis")

async def synthesize_dynamic_personas(email: HumanEmail, persona: PersonaProfile, llm_client=None) -> List[str]:
    """
    Step 4: Dynamic Prompting Strategy Synthesis.
    Takes the deeply extracted Persona from Step 2 and generates 5 diverse 
    'Prompting Strategies' (e.g., Lazy, Control-Freak, Conversational) that THIS SPECIFIC PERSONA 
    might use when typing into ChatGPT.
    """
    logger.info(f"Synthesizing prompting strategies for email {email.id}...")
    
    synthesis_prompt = f"""
    Analyze the following extracted Persona Profile. 
    You must dynamically synthesize 5 highly diverse 'Prompting Strategies' that THIS EXACT PERSONA 
    would plausibly use when interacting with an AI to generate the email. 
    (e.g., 'The Lazy Minimalist Approach', 'The Over-Explainer Approach', 'The Conversational Chat Approach').
    Do NOT invent new people. Invent 5 ways this specific person might type a prompt.
    
    Email Intent: {persona.intent}
    Email Domain: {persona.domain}
    Format: {persona.format}
    Power Dynamic: {persona.power_dynamic}
    Formality: {persona.formality_scale}
    Sentiment: {persona.sentiment}
    Behavioral Quirks: {', '.join(persona.behavioral_quirks)}
    
    Raw Text: {email.raw_text}
    """
    
    import asyncio
    personas: List[str] = []
    
    from pydantic import BaseModel
    class PersonasList(BaseModel):
        personas: List[str]

    if llm_client:
        res = llm_client.chat.completions.create(
            model=config.DEFAULT_GENERATION_MODEL,
            response_model=PersonasList,
            messages=[{"role": "user", "content": synthesis_prompt}]
        )
        if asyncio.iscoroutine(res):
            response_data = await res
        else:
            response_data = res
        personas = response_data.personas
        
    else:
        if not personas:
            # Mocking the 5 synthesized prompting strategies if LLM is unavailable
            personas = [
                "The Lazy Minimalist (One sentence command)",
                "The Micro-Manager (Provides every tiny detail)",
                "The Conversationalist (Talks to the AI like a human)",
                "The Bullet-Point Thinker (Strictly structured)",
                "The Rushed Executive (Typos and fragmented thoughts)"
            ]
        
    # Edge Case: Array Size Constraint (Max 5, but allow fewer)
    # Slice if too many to prevent API waste
    if len(personas) > 5:
        personas = personas[:5]
        
    return personas
