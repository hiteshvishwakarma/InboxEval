import logging
from ..schemas import HumanEmail, PersonaProfile
# NOTE: We will build the actual LLM Client wrapper in a later utility folder.
# For now, we mock the call assuming an Instructor/Pydantic-capable client.

logger = logging.getLogger("Step02_PersonaExtraction")

def extract_persona(email: HumanEmail, llm_client=None) -> PersonaProfile:
    """
    Step 2: Reverse Engineering & Persona Extraction.
    Analyzes the historical email to extract intent, domain, sentiment, and 
    a synthesized typology classification using an LLM.
    """
    logger.info(f"Extracting Persona for Email ID: {email.id}")
    
    extraction_prompt = f"""
    You are an expert linguistic analyst. Analyze the following human email.
    You must extract the underlying 'Persona' of the writer and classify it across a 3-Axis Multi-Dimensional Taxonomy.
    
    1. Intent: What is the primary goal? (e.g., 'Demand Refund', 'Cold Outreach')
    2. Sentiment: What is the emotional state? (e.g., 'Angry', 'Polite', 'Urgent')
    
    [THE 3-AXIS TAXONOMY]
    3. NLP Task: Classify into EXACTLY ONE of the following:
       - 'Zero-Shot Drafting': The human is writing a net-new email from scratch (e.g., sending an update, making a request, resigning). MOST EMAILS FALL HERE.
       - 'Data Extraction': The email contains a sprawling mess of data, and the goal is to pull out structured facts or lists.
       - 'Thread Summarization': The email is a long chain of replies/forwards that needs to be condensed.
       - 'Tone Translation': The email takes an existing highly unprofessional draft and rewrites it into corporate-speak (or vice versa).
    4. Domain: What industry or topic is this? (e.g., 'Gaming', 'SaaS Patch Notes', 'E-Commerce Refunds', 'High Finance')
    5. Format: What is the physical structure? (e.g., 'Newsletter Blast', 'Reply Chain', 'Cold Pitch', 'System Alert')
    
    [ATOMIC BEHAVIORAL MATRIX & EVIDENCE]
    6. Power Dynamic: Who is writing to whom? (e.g., 'Subordinate to Boss', 'Vendor to Client')
    7. Formality Scale: Rate it strictly (e.g., 'Hyper-Casual', 'Semi-Professional')
    8. Behavioral Quirks: List 1-3 specific psychological or stylistic traits (e.g., 'Passive-aggressive', 'Uses corporate buzzwords', 'Types in a rush').
    9. Evidence Quotes: For EVERY behavioral quirk you list, you MUST extract the exact verbatim substring from the email that proves it.
    
    10. Typology Classification: Create a specific persona tag (e.g., 'B2B_Hardware_Angry_Support')
    
    EMAIL TEXT:
    ---
    {email.raw_text}
    ---
    """
    
    # In production, this uses `instructor` to enforce the PersonaProfile Pydantic schema
    from ..config import config
    if llm_client:
        persona = llm_client.chat.completions.create(
            model=config.DEFAULT_GENERATION_MODEL, # Using Groq's fast LLaMA 3 model
            response_model=PersonaProfile,
            messages=[{"role": "user", "content": extraction_prompt}]
        )
        return persona
    
    # Fallback / Mock for testing before LLM client is hooked up
    logger.warning("No LLM Client provided. Returning mocked PersonaProfile.")
    return PersonaProfile(
        intent="Mock Intent",
        sentiment="Mock Sentiment",
        nlp_task="Zero-Shot Drafting",
        domain="Mock Domain",
        format="Mock Format",
        power_dynamic="Peer to Peer",
        formality_scale="Semi-Professional",
        behavioral_quirks=["Uses corporate buzzwords"],
        evidence_quotes=["'Let's circle back'"],
        typology_classification="Mock_Typology_Tag"
    )
