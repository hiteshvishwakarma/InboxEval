import os
import json
import asyncio
import logging
from typing import List, Optional
from src.engine.golden_dataset_generator.schemas import (
    HumanEmail, DPBCThresholds, PromptMutation,
    EvaluatedEmail, KDAMatrix, JudgeFeedback, SuperPrompt, GenerationState
)
from .schemas import PersonaProfileV3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GoldenDatasetOrchestratorV3")

class GoldenDatasetOrchestratorV3:
    """
    Master FSM Orchestrator for Engine v2.
    Executes the 4 Operational Phases asynchronously with only 3 LLM calls per generation loop:
    - Phase 1: Ingest & Persona Strategy Caching (Steps 1-4, 0 LLM calls in vertical run)
    - Phase 2: Batched Genesis Candidate Build (Step 5, 1 Batched LLM call)
    - Phase 3: Static-First Dual Scoring (Steps 6-7, 1 Batched LLM call with 0ms prefill cache hit)
    - Phase 4: Fused Critique & Genetic Crossover (Steps 8-12, 1 Fused LLM call)
    """

    def __init__(self, llm_client=None):
        from dotenv import load_dotenv
        load_dotenv()
        self.llm_client = llm_client
        if not self.llm_client:
            from src.engine.golden_dataset_generator.utils.llm_client_factory import get_robust_llm_client
            self.llm_client = get_robust_llm_client(is_async=True)

    async def run_pipeline_v3(self, email_id: int, original_email_text: str, persona: PersonaProfileV3, dpbc: DPBCThresholds) -> SuperPrompt:
        """Executes Engine v2 Vertical FSM Pipeline (Phases 2, 3, 4) asynchronously."""
        logger.info(f"Starting Engine v2 Vertical Pipeline for Email ID {email_id}...")

        state = GenerationState(human_email_id=str(email_id))
        human_email = HumanEmail(id=str(email_id), raw_text=original_email_text)

        # ==========================================
        # PHASE 2: BATCHED GENESIS (1 LLM Call)
        # ==========================================
        current_mutations: List[PromptMutation] = await self._step_05_batch_genesis(human_email, persona)

        # ==========================================
        # PHASES 3 & 4: EVOLUTION FSM LOOP
        # ==========================================
        MAX_GENERATIONS = 10

        while state.current_generation < MAX_GENERATIONS and not state.is_converged:
            logger.info(f"--- Running Engine v2 Generation {state.current_generation} for Email {email_id} ---")

            # Phase 3: Static-First Dual Scoring (1 LLM Call - 0ms Cache Hit)
            evaluations: List[EvaluatedEmail] = await self._step_06_static_evaluate(current_mutations, human_email, dpbc)
            
            # KDA Ranking (0 LLM Calls)
            kda_matrix: KDAMatrix = self._step_07_kda_ranking(evaluations, state.current_generation)

            # Phase 4: Fused Critique & Polygenic Crossover (1 LLM Call)
            feedback, super_prompt = await self._step_08_09_fused_crossover(kda_matrix, persona, human_email)
            state.reigning_champion = super_prompt

            # Plateau Convergence Check (0 LLM Calls)
            if self._step_11_check_convergence(kda_matrix, state):
                win_delta = min((e.overall_delta for e in kda_matrix.evaluations), default=0.0)
                logger.info(f"Engine v2 Convergence reached for Email {email_id}. Champion locked: {super_prompt.id} (Delta: {win_delta:.4f}).")
                break

            # Elitism Selection (0 LLM Calls)
            current_mutations = await self._step_10_elitism(super_prompt, state.current_generation + 1)
            state.current_generation += 1
            await asyncio.sleep(0.05)

        if state.reigning_champion:
            return state.reigning_champion
        else:
            raise RuntimeError(f"Engine v2 pipeline failed to generate champion for {email_id}.")

    # Node Executors

    async def _step_05_batch_genesis(self, email: HumanEmail, persona: PersonaProfileV3) -> List[PromptMutation]:
        from .engine_steps.step_05_batch_genesis import generate_batch_genesis_mutations
        return await generate_batch_genesis_mutations(email, persona, llm_client=self.llm_client)

    async def _step_06_static_evaluate(self, mutations: List[PromptMutation], email: HumanEmail, dpbc: DPBCThresholds) -> List[EvaluatedEmail]:
        from .engine_steps.step_06_static_evaluator import evaluate_mutations_v3
        return await evaluate_mutations_v3(mutations, email, dpbc, llm_client=self.llm_client)

    def _step_07_kda_ranking(self, evals: List[EvaluatedEmail], gen_num: int) -> KDAMatrix:
        from .engine_steps.step_07_kda_ranking import calculate_kda_ranking_v3
        return calculate_kda_ranking_v3(evals, gen_num)

    async def _step_08_09_fused_crossover(self, kda: KDAMatrix, persona: PersonaProfileV3, email: HumanEmail) -> tuple:
        from .engine_steps.step_08_09_fused_crossover import generate_fused_critique_and_crossover_v3
        return await generate_fused_critique_and_crossover_v3(kda, persona, email, llm_client=self.llm_client)

    def _step_11_check_convergence(self, kda: KDAMatrix, state: GenerationState) -> bool:
        from .engine_steps.step_11_early_stop import check_convergence_v3
        return check_convergence_v3(kda, state)

    async def _step_10_elitism(self, champion: SuperPrompt, next_gen_num: int) -> List[PromptMutation]:
        from .engine_steps.step_10_elitism import execute_elitism_loop_v3
        return await execute_elitism_loop_v3(champion, next_gen_num, llm_client=self.llm_client)

    def _step_12_golden_record_export(self, champion: SuperPrompt, email: HumanEmail, output_path: str):
        from .engine_steps.step_12_export import export_golden_record_v3
        export_golden_record_v3(champion, email, output_path)
