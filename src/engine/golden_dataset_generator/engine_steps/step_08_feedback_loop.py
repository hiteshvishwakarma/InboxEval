import logging
from ..schemas import KDAMatrix, HumanEmail, DPBCThresholds, JudgeFeedback
from ..config import config

logger = logging.getLogger("Step08_FeedbackLoop")

def generate_feedback_loop(kda: KDAMatrix, human_email: HumanEmail, dpbc: DPBCThresholds, llm_client=None) -> JudgeFeedback:
    """
    Step 8: Closed Feedback Loop.
    Extracts the winning generation and asks the LLM Judge to explicitly critique 
    why it failed to perfectly mirror the human email's DPBC targets.
    """
    if not kda.evaluations:
        raise ValueError("Cannot generate feedback: KDA Matrix has no evaluations.")
        
    logger.info(f"Generating feedback loop for KDA Gen {kda.generation_num}...")
    
    # 1. Extract Target
    winner = next(e for e in kda.evaluations if e.mutation_id == kda.overall_winner_mutation_id)
    
    # Cost-Saving Edge Case
    if winner.overall_delta < 0.05:
        logger.info("Winner has converged perfectly. Bypassing LLM feedback.")
        return JudgeFeedback(
            kda_matrix_id=f"kda_gen_{kda.generation_num}",
            feedback_text="Delta minimized. Prompt has converged perfectly."
        )

    # 2. Feedback Prompt
    feedback_prompt = f"""
    You are the Head Linguistic Judge. 
    Compare the Original Human Email to the Synthetic Generation.
    
    Original Email: {human_email.raw_text}
    Synthetic Email: {winner.synthetic_text}
    
    The Synthetic Email achieved an error delta of {winner.overall_delta:.2f}.
    Identify exactly why it failed to achieve a perfect 0.0 Delta. 
    Analyze its Tone, Conciseness, and Factual Accuracy. Be brutally honest.
    """
    
    if llm_client:
        from pydantic import BaseModel
        class FeedbackResult(BaseModel):
            feedback_text: str
            
        result = llm_client.chat.completions.create(
            model=config.DEFAULT_GENERATION_MODEL,
            response_model=FeedbackResult,
            messages=[{"role": "user", "content": feedback_prompt}]
        )
        feedback_text = result.feedback_text
        
    else:
        # Mocking feedback for architecture build
        feedback_text = (
            "The generated email was far too polite and verbose. The original human email was "
            "aggressive and brief. The prompt failed to enforce a strict character limit and "
            "did not push the sentiment hard enough into the 'Angry' domain."
        )
    
    # 3. Assembly
    return JudgeFeedback(
        kda_matrix_id=f"kda_gen_{kda.generation_num}",
        feedback_text=feedback_text
    )
