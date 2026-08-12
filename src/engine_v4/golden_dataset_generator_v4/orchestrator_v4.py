import os
import json
import asyncio
import logging
from typing import List, Optional
from src.engine.golden_dataset_generator.schemas import (
    HumanEmail, DPBCThresholds, PromptMutation,
    EvaluatedEmail, KDAMatrix, JudgeFeedback, SuperPrompt, GenerationState
)
from .schemas import PersonaProfileV4
from .gpu_occupancy import fit_email_text, normalize_size

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GoldenDatasetOrchestratorV4")

class GoldenDatasetOrchestratorV4:
    """
    Master FSM Orchestrator for Engine v4.
    LLM calls are gated by gpu_occupancy.llm_slot for L4 tok/s saturation.
    """

    def __init__(self, llm_client=None):
        from dotenv import load_dotenv
        load_dotenv()
        self.llm_client = llm_client
        if not self.llm_client:
            from src.engine.golden_dataset_generator.utils.llm_client_factory import get_robust_llm_client
            self.llm_client = get_robust_llm_client(is_async=True)

    async def run_pipeline_v4(
        self,
        email_id: int,
        original_email_text: str,
        persona: PersonaProfileV4,
        dpbc: DPBCThresholds,
        size_category: Optional[str] = None,
    ) -> SuperPrompt:
        """Executes Engine v4 Vertical FSM Pipeline (Phases 2, 3, 4) asynchronously."""
        size = normalize_size(size_category)
        logger.info(
            "Starting Engine v4 Vertical Pipeline for Email ID %s (size=%s)...",
            email_id,
            size,
        )

        state = GenerationState(human_email_id=str(email_id))
        # Fit body for LLM context; original remains available to caller for DB export
        human_email = HumanEmail(
            id=str(email_id),
            raw_text=fit_email_text(original_email_text, size),
        )

        current_mutations: List[PromptMutation] = await self._step_05_batch_genesis(
            human_email, persona, size
        )

        MAX_GENERATIONS = 10

        while state.current_generation < MAX_GENERATIONS and not state.is_converged:
            logger.info(f"--- Running Engine v4 Generation {state.current_generation} for Email {email_id} ---")

            evaluations: List[EvaluatedEmail] = await self._step_06_static_evaluate(current_mutations, human_email, dpbc)
            kda_matrix: KDAMatrix = self._step_07_kda_ranking(evaluations, state.current_generation)
            feedback, super_prompt = await self._step_08_09_fused_crossover(kda_matrix, persona, human_email)

            if self._step_11_check_convergence(kda_matrix, state):
                win_delta = min((e.overall_delta for e in kda_matrix.evaluations), default=0.0)
                logger.info(f"Engine v4 Convergence reached for Email {email_id}. Champion locked: {super_prompt.id} (Delta: {win_delta:.4f}).")
                state.reigning_champion = super_prompt
                break

            state.reigning_champion = super_prompt
            current_mutations = await self._step_10_elitism(super_prompt, state.current_generation + 1)
            state.current_generation += 1
            await asyncio.sleep(0.05)

        if state.reigning_champion:
            return state.reigning_champion
        raise RuntimeError(f"Engine v4 pipeline failed to generate champion for {email_id}.")

    async def _step_05_batch_genesis(
        self, email: HumanEmail, persona: PersonaProfileV4, size_category: Optional[str] = None
    ) -> List[PromptMutation]:
        from .engine_steps.step_05_batch_genesis import generate_batch_genesis_mutations
        return await generate_batch_genesis_mutations(
            email, persona, llm_client=self.llm_client, size_category=size_category
        )

    async def _step_06_static_evaluate(self, mutations: List[PromptMutation], email: HumanEmail, dpbc: DPBCThresholds) -> List[EvaluatedEmail]:
        from .engine_steps.step_06_static_evaluator import evaluate_mutations_v4
        return await evaluate_mutations_v4(mutations, email, dpbc, llm_client=self.llm_client)

    def _step_07_kda_ranking(self, evals: List[EvaluatedEmail], gen_num: int) -> KDAMatrix:
        from .engine_steps.step_07_kda_ranking import calculate_kda_ranking_v4
        return calculate_kda_ranking_v4(evals, gen_num)

    async def _step_08_09_fused_crossover(self, kda: KDAMatrix, persona: PersonaProfileV4, email: HumanEmail) -> tuple:
        from .engine_steps.step_08_09_fused_crossover import generate_fused_critique_and_crossover_v4
        return await generate_fused_critique_and_crossover_v4(kda, persona, email, llm_client=self.llm_client)

    def _step_11_check_convergence(self, kda: KDAMatrix, state: GenerationState) -> bool:
        from .engine_steps.step_11_early_stop import check_convergence_v4
        return check_convergence_v4(kda, state)

    async def _step_10_elitism(self, champion: SuperPrompt, next_gen_num: int) -> List[PromptMutation]:
        from .engine_steps.step_10_elitism import execute_elitism_loop_v4
        return await execute_elitism_loop_v4(champion, next_gen_num, llm_client=self.llm_client)

