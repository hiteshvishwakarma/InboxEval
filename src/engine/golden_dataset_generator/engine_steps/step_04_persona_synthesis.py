import logging
from typing import List
from ..schemas import HumanEmail, PersonaProfile

logger = logging.getLogger("Step04_PersonaSynthesis")

def synthesize_dynamic_personas(email: HumanEmail, persona: PersonaProfile, llm_client=None) -> List[str]:
    """
    Step 4: Dynamic Context-Aware Persona Synthesis.
    Takes the email and its extracted Persona Profile to dynamically synthesize
    5 highly diverse 'Prompt Writer Personas' based on the specific context.
    """
    logger.info(f"Synthesizing dynamic personas for email {email.id}...")
    
    synthesis_prompt = f"""
    Analyze the following human email and its extracted Persona Profile.
    You must dynamically synthesize 5 highly diverse 'Prompt Writer Personas' who 
    could plausibly have written a prompt to generate this email. 
    Do NOT use a static list. Invent them based on the context.
    
    Email Intent: {persona.intent}
    Email Domain: {persona.domain}
    Raw Text: {email.raw_text}
    """
    
    # In production, the LLM would return a list of 5 synthesized personas
    personas: List[str] = []
    
    if llm_client:
        # personas = llm_client.chat(synthesis_prompt, response_model=List[str])
        pass
        
    if not personas:
        # Mocking the 5 synthesized personas if LLM is unavailable
        personas = [
            "The Stressed IT Manager (Structured)",
            "The Furious CEO (Minimalist)",
            "The Overwhelmed Procurement Officer (Over-Explainer)",
            "The Non-Native Operations Lead (Conversational)",
            "The Legal Threatener (Verbose)"
        ]
        
    # Edge Case: Array Size Constraint (Must be exactly 5)
    # Slice if too many
    if len(personas) > 5:
        personas = personas[:5]
        
    # Pad if too few
    while len(personas) < 5:
        personas.append("The Generic Assistant (Default)")
        
    return personas
