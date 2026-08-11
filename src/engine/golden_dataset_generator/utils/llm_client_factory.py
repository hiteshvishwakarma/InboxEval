"""
LLM client factory.

Backends (env ``LLM_BACKEND``):
  - ``openai`` / ``omniroute`` / ``vllm`` (default): OPENAI_BASE_URL + Tenacity
    (OmniRoute on Mac, vLLM on GCP — same path as before).
  - ``groq``: DynamicGroqRotator over GROQ_API_KEY* + Step-01 models.

Step 01 diversity backtranslate uses DynamicGroqRotator directly; Engine
orchestrators keep calling get_robust_llm_client().
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional

import instructor
import tenacity
from openai import AsyncOpenAI, OpenAI

logger = logging.getLogger("LLMClientFactory")

_global_llm_semaphore = None
_instructor_clients_sync: dict = {}
_instructor_clients_async: dict = {}


def _backend() -> str:
    return os.getenv("LLM_BACKEND", "openai").strip().lower()


def _apply_universal_retry(raw_client, is_async=False, semaphore=None):
    """Wrap create() with Tenacity + optional concurrency semaphore (OpenAI-compatible path)."""

    class UniversalRetryWrapper:
        def __init__(self, client):
            self.raw_client = client
            self.chat = self.ChatWrapper(client.chat)

        class ChatWrapper:
            def __init__(self, chat):
                self.completions = self.CompletionsWrapper(chat.completions)

            class CompletionsWrapper:
                def __init__(self, completions):
                    self.completions = completions

                @tenacity.retry(
                    stop=tenacity.stop_after_attempt(10),
                    wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
                    retry=tenacity.retry_if_exception_type(Exception),
                    before_sleep=lambda retry_state: logger.warning(
                        "[Universal Retry] LLM Error: %s. Retrying in %ss...",
                        retry_state.outcome.exception(),
                        retry_state.next_action.sleep,
                    ),
                )
                def create(self, **kwargs):
                    kwargs.setdefault(
                        "model",
                        os.getenv("GENERATION_MODEL", "Qwen/Qwen2.5-32B-Instruct-AWQ"),
                    )
                    return self.completions.create(**kwargs)

                @tenacity.retry(
                    stop=tenacity.stop_after_attempt(10),
                    wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
                    retry=tenacity.retry_if_exception_type(Exception),
                    before_sleep=lambda retry_state: logger.warning(
                        "[Universal Retry] Async LLM Error: %s. Retrying in %ss...",
                        retry_state.outcome.exception(),
                        retry_state.next_action.sleep,
                    ),
                )
                async def acreate(self, **kwargs):
                    kwargs.setdefault(
                        "model",
                        os.getenv("GENERATION_MODEL", "Qwen/Qwen2.5-32B-Instruct-AWQ"),
                    )

                    async def _execute():
                        if hasattr(self.completions, "acreate"):
                            return await self.completions.acreate(**kwargs)
                        return await self.completions.create(**kwargs)

                    if semaphore:
                        async with semaphore:
                            return await _execute()
                    return await _execute()

    return UniversalRetryWrapper(raw_client)


def _instructor_client(api_key: str, is_async: bool):
    from .dynamic_groq_rotator import GROQ_BASE_URL

    cache = _instructor_clients_async if is_async else _instructor_clients_sync
    if api_key not in cache:
        if is_async:
            raw = AsyncOpenAI(api_key=api_key, base_url=GROQ_BASE_URL, timeout=120.0)
        else:
            raw = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL, timeout=120.0)
        cache[api_key] = instructor.from_openai(raw, mode=instructor.Mode.TOOLS)
    return cache[api_key]


class _SyncRotatingCompletions:
    def __init__(self, rotator):
        self.rotator = rotator

    def create(self, **kwargs: Any):
        from .dynamic_groq_rotator import CRITICAL_LLM_FAILURE

        last_err: Optional[Exception] = None
        for _ in range(self.rotator.max_attempts()):
            n = next(self.rotator._counter)
            api_key, model, key_i, _ = self.rotator._pick(n)
            call_kwargs = dict(kwargs)
            call_kwargs["model"] = model
            client = _instructor_client(api_key, is_async=False)
            try:
                return client.chat.completions.create(**call_kwargs)
            except Exception as e:
                logger.warning("Groq sync fail key#%s model=%s: %s", key_i, model, e)
                last_err = e
                continue
        raise CRITICAL_LLM_FAILURE(f"Groq rotation exhausted: {last_err}")


class _AsyncRotatingCompletions:
    def __init__(self, rotator, semaphore=None):
        self.rotator = rotator
        self.semaphore = semaphore

    async def create(self, **kwargs: Any):
        from .dynamic_groq_rotator import CRITICAL_LLM_FAILURE

        last_err: Optional[Exception] = None
        for _ in range(self.rotator.max_attempts()):
            n = next(self.rotator._counter)
            api_key, model, key_i, _ = self.rotator._pick(n)
            call_kwargs = dict(kwargs)
            call_kwargs["model"] = model
            client = _instructor_client(api_key, is_async=True)

            async def _execute():
                return await client.chat.completions.create(**call_kwargs)

            try:
                if self.semaphore:
                    async with self.semaphore:
                        return await _execute()
                return await _execute()
            except Exception as e:
                logger.warning("Groq async fail key#%s model=%s: %s", key_i, model, e)
                last_err = e
                continue
        raise CRITICAL_LLM_FAILURE(f"Groq rotation exhausted: {last_err}")

    acreate = create


class _ChatWrapper:
    def __init__(self, completions):
        self.completions = completions


class _GroqUniversalWrapper:
    def __init__(self, completions):
        self.chat = _ChatWrapper(completions)


def _get_groq_client(is_async: bool):
    global _global_llm_semaphore
    from .dynamic_groq_rotator import (
        STEP_01_MODELS,
        get_default_rotator,
        load_groq_api_keys,
    )

    keys = load_groq_api_keys()
    if not keys:
        raise ValueError(
            "LLM_BACKEND=groq but no GROQ_API_KEY / GROQ_API_KEY_* in environment"
        )

    logger.info(
        "Initialized Groq DynamicRotator LLM Factory (%s) — %s keys, models=%s",
        "Async" if is_async else "Sync",
        len(keys),
        list(STEP_01_MODELS)[:4],
    )
    rotator = get_default_rotator()
    if is_async:
        if _global_llm_semaphore is None:
            _global_llm_semaphore = asyncio.Semaphore(
                int(os.getenv("GROQ_CONCURRENCY", "8"))
            )
        completions = _AsyncRotatingCompletions(rotator, _global_llm_semaphore)
    else:
        completions = _SyncRotatingCompletions(rotator)
    return _GroqUniversalWrapper(completions)


def get_robust_llm_client(is_async: bool = False):
    """
    Instructor-compatible LLM client.

    Default: OPENAI_BASE_URL (OmniRoute / vLLM) + Tenacity.
    Set LLM_BACKEND=groq for DynamicGroqRotator over free-tier Groq keys.
    """
    global _global_llm_semaphore

    backend = _backend()
    if backend in ("groq", "dynamic_groq", "rotator"):
        return _get_groq_client(is_async=is_async)

    logger.info(
        "Initialized OpenAI-compatible LLM Factory (%s) base=%s",
        "Async" if is_async else "Sync",
        os.getenv("OPENAI_BASE_URL", "http://localhost:20128/v1"),
    )

    if is_async and _global_llm_semaphore is None:
        _global_llm_semaphore = asyncio.Semaphore(
            int(os.getenv("LLM_CONCURRENCY", "100"))
        )

    base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:20128/v1")
    api_key = os.getenv("OPENAI_API_KEY", "omniroute")

    if is_async:
        client = instructor.from_openai(
            AsyncOpenAI(api_key=api_key, base_url=base_url),
            mode=instructor.Mode.TOOLS,
        )
    else:
        client = instructor.from_openai(
            OpenAI(api_key=api_key, base_url=base_url),
            mode=instructor.Mode.TOOLS,
        )

    return _apply_universal_retry(
        client, is_async=is_async, semaphore=_global_llm_semaphore
    )
