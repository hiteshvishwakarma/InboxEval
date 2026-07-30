import os
import json
import logging
from typing import List, Optional
from .schemas import (
    HumanEmail, PersonaProfile, DPBCThresholds, PromptMutation,
    EvaluatedEmail, KDAMatrix, JudgeFeedback, SuperPrompt, GenerationState
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GoldenDatasetOrchestrator")

class TraceLogger:
    def __init__(self, email_id: str):
        self.trace_file = f"data/traces/trace_{email_id}.jsonl"
        os.makedirs("data/traces", exist_ok=True)
        # Clear previous trace if it exists
        if os.path.exists(self.trace_file):
            os.remove(self.trace_file)
            
    def log_step(self, step_name: str, gen_num: int, inputs: dict, outputs: dict):
        # Convert pydantic models to dicts for serialization
        def serialize(obj):
            if hasattr(obj, "model_dump"): return obj.model_dump()
            if isinstance(obj, list): return [serialize(i) for i in obj]
            if isinstance(obj, dict): return {k: serialize(v) for k, v in obj.items()}
            return obj
            
        trace_entry = {
            "step": step_name,
            "generation": gen_num,
            "inputs": serialize(inputs),
            "outputs": serialize(outputs)
        }
        with open(self.trace_file, "a") as f:
            f.write(json.dumps(trace_entry) + "\n")

class GoldenDatasetOrchestrator:
    """
    The master traffic cop for Pipeline A.
    This class contains no LLM logic. It strictly manages the flow of Pydantic 
    data models between the 12 isolated engine steps.
    """
    
    def __init__(self, llm_client=None):
        # In a real environment, we would initialize DB connections here:
        # self.vector_db = VectorDBClient(...)
        # self.telemetry_db = RelationalDBClient(...)
        
        self.llm_client = llm_client
        if not self.llm_client:
            try:
                import os
                import instructor
                from groq import Groq
                from dotenv import load_dotenv
                
                load_dotenv()
                # Fetch all keys starting with GROQ_API_KEY_
                groq_keys = [val for key, val in os.environ.items() if key.startswith("GROQ_API_KEY_")]
                if groq_keys:
                    logger.info(f"Found {len(groq_keys)} Groq API keys. Initializing Rotator...")
                    
                    class GroqRotator:
                        def __init__(self, keys):
                            self.clients = [instructor.from_groq(Groq(api_key=key), mode=instructor.Mode.TOOLS) for key in keys]
                            self.current_idx = 0
                            
                            # Build the mock structure so self.llm_client.chat.completions.create works
                            class ChatRotator:
                                def __init__(self, parent_rotator):
                                    self.completions = self.CompletionsRotator(parent_rotator)
                                    
                                class CompletionsRotator:
                                    def __init__(self, parent_rotator):
                                        self.parent_rotator = parent_rotator
                                        
                                    def create(self, **kwargs):
                                        import time
                                        last_err = None
                                        
                                        # We will try up to 10 times for any error (429 or 400)
                                        max_attempts = 10
                                        for attempt in range(max_attempts):
                                            client = self.parent_rotator.clients[self.parent_rotator.current_idx]
                                            try:
                                                # Instructor internally handles retries, but we enforce it here too
                                                if 'max_retries' not in kwargs:
                                                    kwargs['max_retries'] = 3
                                                return client.chat.completions.create(**kwargs)
                                            except Exception as e:
                                                err_str = str(e).lower()
                                                last_err = e
                                                if "429" in err_str or "rate limit" in err_str or "connection" in err_str:
                                                    logger.warning(f"[Rotator] Key {self.parent_rotator.current_idx} hit Rate Limit or Connection Error. Swapping to next key...")
                                                    self.parent_rotator.current_idx = (self.parent_rotator.current_idx + 1) % len(self.parent_rotator.clients)
                                                    time.sleep(2) # Small buffer between swaps
                                                else:
                                                    # 400 Validation error (schema hallucination). Do not swap key, just retry.
                                                    logger.warning(f"[Rotator] Validation/Parse Error (400) on attempt {attempt+1}. Retrying... Error: {e}")
                                                    time.sleep(2)
                                        
                                        logger.error("Max retries exceeded for LLM call! Failing step.")
                                        raise last_err
                                        
                            self.chat = ChatRotator(self)
                            
                    self.llm_client = GroqRotator(groq_keys)
                    logger.info("Successfully initialized Groq API Key Rotator with instructor in TOOLS mode.")
                else:
                    logger.warning("GROQ_API_KEY not found in environment. Running without LLM client.")
            except ImportError as e:
                logger.warning(f"Could not import required libraries for Groq client ({e}). Running without LLM client.")
                
    def run_pipeline(self, raw_email_text: str, email_id: str = None, output_path: str = "data/golden_dataset.jsonl") -> SuperPrompt:
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
        
        # Initialize Telemetry State and Tracer
        state = GenerationState(human_email_id=human_email.id)
        tracer = TraceLogger(actual_id)
        
        # Log initial steps
        tracer.log_step("Step01_Ingest", -1, {"raw_text": raw_email_text}, human_email)
        tracer.log_step("Step02_PersonaExtract", -1, {"email_id": human_email.id}, persona)
        tracer.log_step("Step03_Vectorization", -1, {"persona": persona.model_dump()}, dpbc)
        tracer.log_step("Step04_PersonaSynthesis", -1, {"persona": persona.model_dump()}, {"dynamic_personas": dynamic_personas})
        tracer.log_step("Step05_GenesisMutation", 0, {"dynamic_personas": dynamic_personas}, {"mutations": current_mutations})

        # ==========================================
        # PHASE 3 & 4: EVOLUTION LOOP
        # ==========================================
        MAX_GENERATIONS = 10
        
        while state.current_generation < MAX_GENERATIONS and not state.is_converged:
            logger.info(f"--- Running Generation {state.current_generation} ---")
            
            # Step 6: Forward Generation & Dual-Scoring
            evaluations: List[EvaluatedEmail] = self._step_06_evaluate(current_mutations, human_email, dpbc)
            tracer.log_step("Step06_Evaluate", state.current_generation, {"mutations": current_mutations}, {"evaluations": evaluations})
            
            # Step 7: KDA Matrix & Ranking
            kda_matrix: KDAMatrix = self._step_07_kda_ranking(evaluations, state.current_generation)
            tracer.log_step("Step07_KDARanking", state.current_generation, {"evaluations": evaluations}, kda_matrix)
            
            # Step 11: Early Stopping / Plateau Detection
            # The orchestrator checks if the overall_delta hit ~0 or plateaued for N generations
            if self._step_11_check_convergence(kda_matrix, state):
                logger.info("Convergence or Plateau reached. Breaking loop.")
                break
                
            # Step 8: Closed Feedback Loop
            feedback: JudgeFeedback = self._step_08_feedback_loop(kda_matrix, human_email, dpbc)
            tracer.log_step("Step08_FeedbackLoop", state.current_generation, {"kda_matrix": kda_matrix.model_dump()}, feedback)
            
            # Step 9: Polygenic Crossover
            super_prompt: SuperPrompt = self._step_09_crossover(kda_matrix, feedback, persona)
            tracer.log_step("Step09_PolygenicCrossover", state.current_generation, {"kda_matrix": kda_matrix.model_dump(), "feedback": feedback.model_dump()}, super_prompt)
            state.reigning_champion = super_prompt
            
            # Step 10: Elitism (Carry over champion, mutate 4 new challengers)
            current_mutations = self._step_10_elitism(super_prompt, state.current_generation + 1)
            tracer.log_step("Step10_Elitism", state.current_generation, {"champion": super_prompt.model_dump()}, {"mutations": current_mutations})
            
            # Telemetry Logging would happen here (saving to PostgreSQL)
            state.current_generation += 1

        # ==========================================
        # PHASE 5: COMMIT
        # ==========================================
        # Step 12: Golden Record Export
        if state.reigning_champion:
            self._step_12_golden_record_export(state.reigning_champion, human_email, output_path)
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
        return extract_persona(email, llm_client=self.llm_client)
        
    def _step_03_get_dpbc_thresholds(self, persona: PersonaProfile, email: HumanEmail) -> DPBCThresholds:
        from .engine_steps.step_03_vectorization import get_dpbc_thresholds
        return get_dpbc_thresholds(persona, email, vector_db_client=None, llm_client=self.llm_client)
        
    def _step_04_synthesize_personas(self, email: HumanEmail, persona: PersonaProfile) -> List[str]:
        from .engine_steps.step_04_persona_synthesis import synthesize_dynamic_personas
        return synthesize_dynamic_personas(email, persona, llm_client=self.llm_client)
        
    def _step_05_genesis_mutation(self, email: HumanEmail, persona: PersonaProfile, dynamic_personas: List[str]) -> List[PromptMutation]:
        from .engine_steps.step_05_genesis_mutation import generate_genesis_mutations
        return generate_genesis_mutations(email, persona, dynamic_personas, llm_client=self.llm_client)
        
    def _step_06_evaluate(self, mutations: List[PromptMutation], email: HumanEmail, dpbc: DPBCThresholds) -> List[EvaluatedEmail]:
        from .engine_steps.step_06_evaluator import evaluate_mutations
        return evaluate_mutations(mutations, email, dpbc, llm_client=self.llm_client)
        
    def _step_07_kda_ranking(self, evals: List[EvaluatedEmail], gen_num: int) -> KDAMatrix:
        from .engine_steps.step_07_kda_ranking import calculate_kda_ranking
        return calculate_kda_ranking(evals, gen_num)
        
    def _step_11_check_convergence(self, kda: KDAMatrix, state: GenerationState) -> bool:
        from .engine_steps.step_11_early_stop import check_convergence
        return check_convergence(kda, state)
        
    def _step_08_feedback_loop(self, kda: KDAMatrix, email: HumanEmail, dpbc: DPBCThresholds) -> JudgeFeedback:
        from .engine_steps.step_08_feedback_loop import generate_feedback_loop
        return generate_feedback_loop(kda, email, dpbc, llm_client=self.llm_client)
        
    def _step_09_crossover(self, kda: KDAMatrix, feedback: JudgeFeedback, persona: PersonaProfile) -> SuperPrompt:
        from .engine_steps.step_09_crossover import generate_super_prompt
        return generate_super_prompt(kda, feedback, persona, llm_client=self.llm_client)
        
    def _step_10_elitism(self, champion: SuperPrompt, next_gen_num: int) -> List[PromptMutation]:
        from .engine_steps.step_10_elitism import execute_elitism_loop
        return execute_elitism_loop(champion, next_gen_num, llm_client=self.llm_client)
        
    def _step_12_golden_record_export(self, champion: SuperPrompt, email: HumanEmail, output_path: str):
        from .engine_steps.step_12_golden_record_export import export_golden_record
        export_golden_record(champion, email, output_path)
