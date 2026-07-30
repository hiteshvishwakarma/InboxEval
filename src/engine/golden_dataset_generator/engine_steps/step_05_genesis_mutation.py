import uuid
import logging
from typing import List
from ..schemas import HumanEmail, PersonaProfile, PromptMutation
from ..config import config

logger = logging.getLogger("Step05_GenesisMutation")

def generate_genesis_mutations(email: HumanEmail, persona: PersonaProfile, dynamic_personas: List[str], llm_client=None) -> List[PromptMutation]:
    """
    Step 5: Genesis Mutation.
    Takes the 5 dynamically synthesized personas from Step 4 and uses an LLM
    to generate 5 distinct Base Prompts (Generation 0) strictly adhering to those personas.
    """
    logger.info(f"Generating Genesis Mutations based on {len(dynamic_personas)} personas for email {email.id}...")
    
    mutations: List[PromptMutation] = []
    
    # Map task category to valid verbs for Pydantic instruction
    category_verbs = {
        "Zero-Shot Drafting": "'Write', 'Draft', or 'Generate'",
        "Data Extraction": "'Extract', 'List', or 'Find'",
        "Thread Summarization": "'Summarize', 'Brief', or 'Catch me up'",
        "Tone Translation": "'Rewrite', 'Translate', or 'Make this sound'"
    }
    required_verbs = category_verbs.get(persona.nlp_task, "'Write', 'Draft', or 'Generate'")

    for index, p_strategy in enumerate(dynamic_personas):
        mutation_prompt = f"""
        You are implementing the following Prompting Strategy: '{p_strategy}'. 
        Write the prompt you would type into an AI to generate the following email:
        {email.raw_text}
        
        CRITICAL CONSTRAINT: You must output a strict instructional command.
        Your 'action_command' MUST begin with EXACTLY ONE of the following verbs: {required_verbs}. Do not use any other verbs. (This is a {persona.nlp_task} task in the {persona.domain} domain, structured as a {persona.format}).
        Your 'context_details' MUST reflect the authentic humanness of your strategy '{p_strategy}', inheriting these atomic traits of the human:
        - Intent: {persona.intent}
        - Sentiment: {persona.sentiment}
        - Power Dynamic: {persona.power_dynamic}
        - Formality: {persona.formality_scale}
        - Quirks: {', '.join(persona.behavioral_quirks)}
        
        ANTI-META LEAK CONSTRAINT: You must NEVER refer to "the original email", "the reference text", or "the provided text" in your prompt. The person typing this prompt is generating the thought from scratch. Do not break the fourth wall.
        Write the details naturally. Do not over-engineer it; let your assigned prompting strategy dictate how much or how little detail is provided.
        """
        
        generated_prompt_text = ""
        try:
            if llm_client:
                from pydantic import BaseModel, Field
                class GenesisResult(BaseModel):
                    action_command: str = Field(..., description="The instructional command, MUST start with verbs like 'Write an email', 'Draft a response', etc.")
                    context_details: str = Field(..., description="The actual context, details, and persona constraints for the email.")
                    
                result = llm_client.chat.completions.create(
                    model=config.DEFAULT_GENERATION_MODEL,
                    response_model=GenesisResult,
                    messages=[{"role": "user", "content": mutation_prompt}]
                )
                generated_prompt_text = f"{result.action_command} {result.context_details}"
            
            else:
                if not generated_prompt_text:
                    # Mocking the LLM generation for the prompt text
                    generated_prompt_text = f"Mocked prompt text generated using strategy {p_strategy} to achieve intent: {persona.intent}"
        except Exception as e:
            logger.error(f"LLM failed to generate prompt for strategy '{p_strategy}': {e}. Skipping to avoid polluting gene pool.")
            continue
            
        mutation = PromptMutation(
            id=f"mut_gen0_{index}_{uuid.uuid4().hex[:4]}",
            typology_persona=p_strategy,
            prompt_text=generated_prompt_text,
            generation_num=0
        )
        mutations.append(mutation)
        
    return mutations
