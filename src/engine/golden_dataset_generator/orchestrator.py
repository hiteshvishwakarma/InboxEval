import logging
from typing import List, Optional
from .schemas import (
    HumanEmail, PersonaProfile, DPBCThresholds, PromptMutation,
    EvaluatedEmail, KDAMatrix, JudgeFeedback, SuperPrompt, GenerationState
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GoldenDatasetOrchestrator")

class GoldenDatasetOrchestrator:
    """
    The master traffic cop for Pipeline A.
    This class contains no LLM logic. It strictly manages the flow of Pydantic 
    data models between the 12 isolated engine steps.
    """
    
    def __init__(self):
        # In a real environment, we would initialize DB connections here:
        # self.vector_db = VectorDBClient(...)
        # self.telemetry_db = RelationalDBClient(...)
        pass

    def run_pipeline(self, raw_email_text: str, email_id: str = None) -> SuperPrompt:
        """Executes the full 12-step evolutionary pipeline."""
        logger.info("Starting Pipeline A for new raw email...")

        # ==========================================
        # PHASE 1: PREPARATION
        # ==========================================
        
        # Step 1: Ingestion
        import uuid
        actual_id = email_id if email_id else f"email_{uuid.uuid4().hex[:8]}"
        human_email: HumanEmail = self._step_01_ingest(raw_email_text, actual_id)
        
        # Step 2: Persona Extraction
        persona: PersonaProfile = self._step_02_extract_persona(human_email)
        
        # Step 3: Vectorization & DPBC Thresholds
        dpbc: DPBCThresholds = self._step_03_get_dpbc_thresholds(persona, human_email)

        # ==========================================
        # PHASE 2: GENESIS
        # ==========================================
        # Step 4: Dynamic Context-Aware Persona Synthesis
        dynamic_personas: List[str] = self._step_04_synthesize_personas(human_email, persona)
        
        # Step 5: Genesis Mutation
        current_mutations: List[PromptMutation] = self._step_05_genesis_mutation(human_email, persona, dynamic_personas)
        
        # Initialize Telemetry State
        state = GenerationState(human_email_id=human_email.id)

        # ==========================================
        # PHASE 3 & 4: EVOLUTION LOOP
        # ==========================================
        MAX_GENERATIONS = 10
        
        while state.current_generation < MAX_GENERATIONS and not state.is_converged:
            logger.info(f"--- Running Generation {state.current_generation} ---")
            
            # Step 6: Forward Generation & Dual-Scoring
            evaluations: List[EvaluatedEmail] = self._step_06_evaluate(current_mutations, human_email, dpbc)
            
            # Step 7: KDA Matrix & Ranking
            kda_matrix: KDAMatrix = self._step_07_kda_ranking(evaluations, state.current_generation)
            
            # Step 11: Early Stopping / Plateau Detection
            # The orchestrator checks if the overall_delta hit ~0 or plateaued for N generations
            if self._step_11_check_convergence(kda_matrix, state):
                logger.info("Convergence or Plateau reached. Breaking loop.")
                break
                
            # Step 8: Closed Feedback Loop
            feedback: JudgeFeedback = self._step_08_feedback_loop(kda_matrix, human_email, dpbc)
            
            # Step 9: Polygenic Crossover
            super_prompt: SuperPrompt = self._step_09_crossover(kda_matrix, feedback)
            state.reigning_champion = super_prompt
            
            # Step 10: Elitism (Carry over champion, mutate 4 new challengers)
            current_mutations = self._step_10_elitism(super_prompt, state.current_generation + 1)
            
            # Telemetry Logging would happen here (saving to PostgreSQL)
            state.current_generation += 1

        # ==========================================
        # PHASE 5: COMMIT
        # ==========================================
        # Step 12: Golden Record Export
        if state.reigning_champion:
            self._step_12_golden_record_export(state.reigning_champion, human_email)
            return state.reigning_champion
        else:
            raise RuntimeError("Pipeline failed to generate a champion.")

    # ---------------------------------------------------------
    # PIPELINE NODE EXECUTORS
    # ---------------------------------------------------------
    def _step_01_ingest(self, text: str, email_id: str) -> HumanEmail:
        from .engine_steps.step_01_ingest import ingest_raw_email
        return ingest_raw_email(text, email_id)
        
    def _step_02_extract_persona(self, email: HumanEmail) -> PersonaProfile:
        from .engine_steps.step_02_persona_extract import extract_persona
        return extract_persona(email, llm_client=None)
        
    def _step_03_get_dpbc_thresholds(self, persona: PersonaProfile, email: HumanEmail) -> DPBCThresholds:
        from .engine_steps.step_03_vectorization import get_dpbc_thresholds
        return get_dpbc_thresholds(persona, email, vector_db_client=None, llm_client=None)
        
    def _step_04_synthesize_personas(self, email: HumanEmail, persona: PersonaProfile) -> List[str]:
        from .engine_steps.step_04_persona_synthesis import synthesize_dynamic_personas
        return synthesize_dynamic_personas(email, persona, llm_client=None)
        
    def _step_05_genesis_mutation(self, email: HumanEmail, persona: PersonaProfile, dynamic_personas: List[str]) -> List[PromptMutation]:
        from .engine_steps.step_05_genesis_mutation import generate_genesis_mutations
        return generate_genesis_mutations(email, persona, dynamic_personas, llm_client=None)
        
    def _step_06_evaluate(self, mutations: List[PromptMutation], email: HumanEmail, dpbc: DPBCThresholds) -> List[EvaluatedEmail]:
        from .engine_steps.step_06_evaluator import evaluate_mutations
        return evaluate_mutations(mutations, email, dpbc, llm_client=None)
        
    def _step_07_kda_ranking(self, evals: List[EvaluatedEmail], gen_num: int) -> KDAMatrix:
        from .engine_steps.step_07_kda_ranking import calculate_kda_ranking
        return calculate_kda_ranking(evals, gen_num)
        
    def _step_11_check_convergence(self, kda: KDAMatrix, state: GenerationState) -> bool:
        from .engine_steps.step_11_early_stop import check_convergence
        return check_convergence(kda, state)
        
    def _step_08_feedback_loop(self, kda: KDAMatrix, email: HumanEmail, dpbc: DPBCThresholds) -> JudgeFeedback:
        from .engine_steps.step_08_feedback_loop import generate_feedback_loop
        return generate_feedback_loop(kda, email, dpbc, llm_client=None)
        
    def _step_09_crossover(self, kda: KDAMatrix, feedback: JudgeFeedback) -> SuperPrompt:
        from .engine_steps.step_09_crossover import generate_super_prompt
        return generate_super_prompt(kda, feedback, llm_client=None)
        
    def _step_10_elitism(self, champion: SuperPrompt, next_gen_num: int) -> List[PromptMutation]:
        from .engine_steps.step_10_elitism import execute_elitism_loop
        return execute_elitism_loop(champion, next_gen_num, llm_client=None)
        
    def _step_12_golden_record_export(self, champion: SuperPrompt, email: HumanEmail):
        from .engine_steps.step_12_golden_record_export import export_golden_record
        export_golden_record(champion, email)
