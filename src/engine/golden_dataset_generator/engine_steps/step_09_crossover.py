import uuid
import logging
from typing import Dict, Any

from ..schemas import KDAMatrix, JudgeFeedback, SuperPrompt, EvaluatedEmail, PersonaProfile
from ..config import config

logger = logging.getLogger("Step09_PolygenicCrossover")

def generate_super_prompt(kda: KDAMatrix, feedback: JudgeFeedback, persona: PersonaProfile, llm_client=None) -> SuperPrompt:
    """
    Step 9: Polygenic Crossover.
    Executes a Multi-Parent crossover. Merges the base structure of the overall winner 
    with the isolated winning traits of the parameter winners, while applying the Judge's feedback.
    """
    logger.info(f"Executing Polygenic Crossover for Gen {kda.generation_num}...")

    # 1. Retrieve Donor DNA
    eval_dict: Dict[str, EvaluatedEmail] = {e.mutation_id: e for e in kda.evaluations}
    
    # We retrieve the actual prompt texts from the evaluations
    base_winner_id = kda.overall_winner_mutation_id
    tone_winner_id = kda.best_tone_mutation_id
    conciseness_winner_id = kda.best_conciseness_mutation_id
    accuracy_winner_id = kda.best_accuracy_mutation_id
    
    overall_winner_eval = eval_dict[base_winner_id]
    
    # Extract actual prompt strings
    base_prompt_text = eval_dict[base_winner_id].prompt_text
    tone_prompt_text = eval_dict[tone_winner_id].prompt_text
    conciseness_prompt_text = eval_dict[conciseness_winner_id].prompt_text
    accuracy_prompt_text = eval_dict[accuracy_winner_id].prompt_text
    
    # 2. Edge Case: Convergence Bypass
    if "converged perfectly" in feedback.feedback_text:
        logger.info("Feedback indicates perfect convergence. Bypassing crossover LLM.")
        return SuperPrompt(
            id=f"Super_P_Gen_{kda.generation_num}_{uuid.uuid4().hex[:4]}",
            base_mutation_id=base_winner_id,
            injected_traits={"all": base_winner_id},
            final_prompt_text=base_prompt_text,
            elo_delta=overall_winner_eval.overall_delta,
            is_champion=True
        )

    # Map task category to valid verbs for Pydantic instruction
    category_verbs = {
        "Zero-Shot Drafting": "'Write', 'Draft', or 'Generate'",
        "Data Extraction": "'Extract', 'List', or 'Find'",
        "Thread Summarization": "'Summarize', 'Brief', or 'Catch me up'",
        "Tone Translation": "'Rewrite', 'Translate', or 'Make this sound'"
    }
    required_verbs = category_verbs.get(persona.nlp_task, "'Write', 'Draft', or 'Generate'")

    # 3. Polygenic Crossover Prompt
    crossover_prompt = f"""
    You are an Evolutionary Prompt Engineer.
    Your task is to breed a new 'Super Prompt' by combining the best traits of multiple parents, 
    while explicitly fixing the flaws identified by the Judge.
    
    BASE STRUCTURE PROMPT:
    {base_prompt_text}
    
    TONE DONOR PROMPT:
    {tone_prompt_text}
    
    CONCISENESS DONOR PROMPT:
    {conciseness_prompt_text}
    
    ACCURACY DONOR PROMPT:
    {accuracy_prompt_text}
    
    JUDGE FEEDBACK TO FIX: {feedback.feedback_text}
    
    CRITICAL CONSTRAINT: You must output a strict instructional command.
    Your 'action_command' MUST begin with EXACTLY ONE of the following verbs: {required_verbs}. Do not use any other verbs. (This is a {persona.nlp_task} task in the {persona.domain} domain, structured as a {persona.format}).
    Your 'context_details' MUST retain the authentic, natural humanness of the DONOR prompts, ensuring they align with these atomic traits:
    - Intent: {persona.intent}
    - Sentiment: {persona.sentiment}
    - Power Dynamic: {persona.power_dynamic}
    - Formality: {persona.formality_scale}
    - Quirks: {', '.join(persona.behavioral_quirks)}
    
    ANTI-META LEAK CONSTRAINT: You must NEVER refer to "the original email", "the reference text", or "the provided text" in your prompt. The person typing this prompt is generating the thought from scratch. Do not break the fourth wall.
    FACTUAL INJECTION CONSTRAINT: You must explicitly list all core entities, objects, and specific claims (e.g., deleted documents, specific dates) that must be included in the generated email so the AI knows exactly what facts to use without referring to a source text.
    Do not over-engineer or roboticize the context. Let the natural human tone and detail-level of the donors dictate the prompt's structure.
    """
    
    if llm_client:
        from pydantic import BaseModel, Field
        class CrossoverResult(BaseModel):
            action_command: str = Field(..., description="The instructional command, MUST start with verbs like 'Write an email', 'Draft a response', etc.")
            context_details: str = Field(..., description="The actual context, details, and persona constraints for the email.")
            
        result = llm_client.chat.completions.create(
            model=config.DEFAULT_GENERATION_MODEL,
            response_model=CrossoverResult,
            messages=[{"role": "user", "content": crossover_prompt}]
        )
        final_prompt_text = f"{result.action_command} {result.context_details}"
        
    else:
        # Mocking the generated Super Prompt text
        final_prompt_text = (
            f"Mocked Super Prompt resulting from polygenic crossover of Base: {base_winner_id}, "
            f"Tone: {tone_winner_id}, Conciseness: {conciseness_winner_id}. Fixed Judge Feedback."
        )

    # 4. Final Assembly
    super_prompt = SuperPrompt(
        id=f"Super_P_Gen_{kda.generation_num}_{uuid.uuid4().hex[:4]}",
        base_mutation_id=base_winner_id,
        injected_traits={
            "tone": tone_winner_id,
            "conciseness": conciseness_winner_id,
            "accuracy": accuracy_winner_id
        },
        final_prompt_text=final_prompt_text,
        elo_delta=overall_winner_eval.overall_delta,  # Inherit for the start of the next generation
        is_champion=True
    )
    
    return super_prompt
