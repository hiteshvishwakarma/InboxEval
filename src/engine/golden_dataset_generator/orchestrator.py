import os
import json
import asyncio
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
        
        from dotenv import load_dotenv
        load_dotenv()
        self.llm_client = llm_client
        if not self.llm_client:
            from .utils.llm_client_factory import get_robust_llm_client
            self.llm_client = get_robust_llm_client(is_async=True)
            if not self.llm_client:
                logger.warning("Running without LLM client.")
                
    async def run_pipeline(self, email_id: int, original_email_text: str, persona: PersonaProfile, dpbc: DPBCThresholds) -> SuperPrompt:
        """
        Executes the vertical FSM loop (Steps 4-12) asynchronously.
        Steps 0-3 must be completed horizontally before this is invoked.
        """
        logger.info(f"Starting Vertical Pipeline for email ID {email_id}...")

        # Initialize Telemetry State inside lexical scope (Async-Safe)
        state = GenerationState(human_email_id=str(email_id))
        tracer = TraceLogger(str(email_id))
        
        # We wrap the original email into a HumanEmail object for backwards compatibility
        human_email = HumanEmail(id=str(email_id), raw_text=original_email_text)

        # ==========================================
        # PHASE 2: GENESIS
        # ==========================================
        # Step 4: Dynamic Context-Aware Persona Synthesis
        # In a fully async system, engine steps should ideally be async too. Assuming the underlying clients use acreate().
        dynamic_personas: List[str] = await self._step_04_synthesize_personas(human_email, persona)
        
        # Step 5: Genesis Mutation
        current_mutations: List[PromptMutation] = await self._step_05_genesis_mutation(human_email, persona, dynamic_personas)
        
        tracer.log_step("Step04_PersonaSynthesis", -1, {"persona": persona.model_dump()}, {"dynamic_personas": dynamic_personas})
        tracer.log_step("Step05_GenesisMutation", 0, {"dynamic_personas": dynamic_personas}, {"mutations": current_mutations})

        # ==========================================
        # PHASE 3 & 4: EVOLUTION LOOP
        # ==========================================
        MAX_GENERATIONS = 10
        
        while state.current_generation < MAX_GENERATIONS and not state.is_converged:
            logger.info(f"--- Running Generation {state.current_generation} for {email_id} ---")
            
            # Step 6: Forward Generation & Dual-Scoring
            evaluations: List[EvaluatedEmail] = await self._step_06_evaluate(current_mutations, human_email, dpbc)
            tracer.log_step("Step06_Evaluate", state.current_generation, {"mutations": current_mutations}, {"evaluations": evaluations})
            
            # Step 7: KDA Matrix & Ranking
            kda_matrix: KDAMatrix = self._step_07_kda_ranking(evaluations, state.current_generation)
            tracer.log_step("Step07_KDARanking", state.current_generation, {"evaluations": evaluations}, kda_matrix)
            
            # Step 8: Closed Feedback Loop
            feedback: JudgeFeedback = await self._step_08_feedback_loop(kda_matrix, human_email, dpbc)
            tracer.log_step("Step08_FeedbackLoop", state.current_generation, {"kda_matrix": kda_matrix.model_dump()}, feedback)
            
            # Step 9: Polygenic Crossover
            super_prompt: SuperPrompt = await self._step_09_crossover(kda_matrix, feedback, persona)
            tracer.log_step("Step09_PolygenicCrossover", state.current_generation, {"kda_matrix": kda_matrix.model_dump(), "feedback": feedback.model_dump()}, super_prompt)
            state.reigning_champion = super_prompt

            # Step 11: Early Stopping / Plateau Detection
            if self._step_11_check_convergence(kda_matrix, state):
                win_delta = min((e.overall_delta for e in kda_matrix.evaluations), default=0.0)
                logger.info(f"Convergence reached for {email_id}. Champion locked: {super_prompt.id} (Delta: {win_delta:.2f}). Breaking loop.")
                break
            
            # Step 10: Elitism (Carry over champion, mutate 4 new challengers)
            current_mutations = await self._step_10_elitism(super_prompt, state.current_generation + 1)
            tracer.log_step("Step10_Elitism", state.current_generation, {"champion": super_prompt.model_dump()}, {"mutations": current_mutations})
            
            state.current_generation += 1
            await asyncio.sleep(0.1) # Yield to event loop

        # ==========================================
        # PHASE 5: COMMIT
        # ==========================================
        if state.reigning_champion:
            return state.reigning_champion
        else:
            raise RuntimeError(f"Pipeline failed to generate a champion for {email_id}.")

    # ---------------------------------------------------------
    # PIPELINE NODE EXECUTORS
    # ---------------------------------------------------------
    def _step_01_ingest(self, text: str, email_id: str) -> HumanEmail:
        from .engine_steps.step_01_ingest import ingest_raw_email
        return ingest_raw_email(text, email_id)
        
    async def _step_02_extract_persona(self, email: HumanEmail) -> PersonaProfile:
        from .engine_steps.step_02_persona_extract import extract_persona
        return await extract_persona(email, llm_client=self.llm_client)
        
    def _step_03_get_dpbc_thresholds(self, persona: PersonaProfile, email: HumanEmail) -> DPBCThresholds:
        from .engine_steps.step_03_vectorization import get_dpbc_thresholds
        return get_dpbc_thresholds(persona, email, vector_db_client=None, llm_client=self.llm_client)
        
    async def _step_04_synthesize_personas(self, email: HumanEmail, persona: PersonaProfile) -> List[str]:
        from .engine_steps.step_04_persona_synthesis import synthesize_dynamic_personas
        return await synthesize_dynamic_personas(email, persona, llm_client=self.llm_client)
        
    async def _step_05_genesis_mutation(self, email: HumanEmail, persona: PersonaProfile, dynamic_personas: List[str]) -> List[PromptMutation]:
        from .engine_steps.step_05_genesis_mutation import generate_genesis_mutations
        return await generate_genesis_mutations(email, persona, dynamic_personas, llm_client=self.llm_client)
        
    async def _step_06_evaluate(self, mutations: List[PromptMutation], email: HumanEmail, dpbc: DPBCThresholds) -> List[EvaluatedEmail]:
        from .engine_steps.step_06_evaluator import evaluate_mutations
        return await evaluate_mutations(mutations, email, dpbc, llm_client=self.llm_client)
        
    def _step_07_kda_ranking(self, evals: List[EvaluatedEmail], gen_num: int) -> KDAMatrix:
        from .engine_steps.step_07_kda_ranking import calculate_kda_ranking
        return calculate_kda_ranking(evals, gen_num)
        
    def _step_11_check_convergence(self, kda: KDAMatrix, state: GenerationState) -> bool:
        from .engine_steps.step_11_early_stop import check_convergence
        return check_convergence(kda, state)
        
    async def _step_08_feedback_loop(self, kda: KDAMatrix, email: HumanEmail, dpbc: DPBCThresholds) -> JudgeFeedback:
        from .engine_steps.step_08_feedback_loop import generate_feedback_loop
        return await generate_feedback_loop(kda, email, dpbc, llm_client=self.llm_client)
        
    async def _step_09_crossover(self, kda: KDAMatrix, feedback: JudgeFeedback, persona: PersonaProfile) -> SuperPrompt:
        from .engine_steps.step_09_crossover import generate_super_prompt
        return await generate_super_prompt(kda, feedback, persona, llm_client=self.llm_client)
        
    async def _step_10_elitism(self, champion: SuperPrompt, next_gen_num: int) -> List[PromptMutation]:
        from .engine_steps.step_10_elitism import execute_elitism_loop
        return await execute_elitism_loop(champion, next_gen_num, llm_client=self.llm_client)
        
    def _step_12_golden_record_export(self, champion: SuperPrompt, email: HumanEmail, output_path: str):
        from .engine_steps.step_12_golden_record_export import export_golden_record
        export_golden_record(champion, email, output_path)
