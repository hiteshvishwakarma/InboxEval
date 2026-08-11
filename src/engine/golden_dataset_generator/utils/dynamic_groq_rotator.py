"""
DynamicGroqRotator — 2D round-robin over Groq API keys + models.

Replaces OmniRoute for Step 01 / free-tier JSON workloads.
Loads every env var matching GROQ_API_KEY* (including GROQ_API_KEY_AMISHA, etc.).

Behavior (from docs/architecture_blueprint.md):
  - Advances key index and model index on a shared counter.
  - Retries up to N_keys * 2 attempts (non-skipping).
  - 429 / rate-limit → advance key; other API errors → advance model.
"""

from __future__ import annotations

import itertools
import logging
import os
import time
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger("DynamicGroqRotator")

# Step 01 native-JSON capable Groq models (empirical set from architecture + current Groq catalog)
STEP_01_MODELS: Sequence[str] = (
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class CRITICAL_LLM_FAILURE(RuntimeError):
    """Raised when all key×model attempts are exhausted."""


def load_groq_api_keys() -> List[str]:
    """Collect unique non-empty Groq keys from the environment."""
    keys: List[str] = []
    seen = set()
    for name, value in sorted(os.environ.items()):
        if not value:
            continue
        if name == "GROQ_API_KEY" or name.startswith("GROQ_API_KEY_"):
            if value not in seen:
                keys.append(value)
                seen.add(value)
    return keys


class DynamicGroqRotator:
    """Round-robin Groq client for chat completions."""

    def __init__(
        self,
        models: Optional[Sequence[str]] = None,
        keys: Optional[Sequence[str]] = None,
    ):
        self.keys = list(keys) if keys is not None else load_groq_api_keys()
        self.models = list(models) if models is not None else list(STEP_01_MODELS)
        if not self.keys:
            raise ValueError(
                "No GROQ_API_KEY / GROQ_API_KEY_* found in environment. "
                "Add at least one key to .env"
            )
        if not self.models:
            raise ValueError("Model list for DynamicGroqRotator is empty")
        self._counter = itertools.count(0)
        logger.info(
            "DynamicGroqRotator ready: %s keys × %s models",
            len(self.keys),
            len(self.models),
        )

    def _pick(self, n: int) -> tuple[str, str, int, int]:
        key_i = n % len(self.keys)
        model_i = n % len(self.models)
        return self.keys[key_i], self.models[model_i], key_i, model_i

    def max_attempts(self) -> int:
        return max(2, len(self.keys) * 2)

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float = 0.3,
        response_format: Optional[Dict[str, str]] = None,
        max_tokens: int = 800,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """
        Sync chat completion with key+model rotation.
        Returns OpenAI-shaped dict: {"choices":[{"message":{"content":...}}], "model": ...}
        """
        import httpx

        last_err: Optional[Exception] = None
        attempts = self.max_attempts()
        for _ in range(attempts):
            n = next(self._counter)
            api_key, model, key_i, model_i = self._pick(n)
            payload: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            }
            if response_format:
                payload["response_format"] = response_format
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            try:
                with httpx.Client(timeout=timeout) as http:
                    resp = http.post(
                        f"{GROQ_BASE_URL}/chat/completions",
                        json=payload,
                        headers=headers,
                    )
                if resp.status_code == 429:
                    logger.warning(
                        "429 rate limit key#%s model=%s — advancing", key_i, model
                    )
                    time.sleep(0.5)
                    last_err = RuntimeError(f"429 from {model}")
                    continue
                if resp.status_code >= 400:
                    logger.warning(
                        "HTTP %s key#%s model=%s: %s — advancing",
                        resp.status_code,
                        key_i,
                        model,
                        resp.text[:200],
                    )
                    last_err = RuntimeError(f"{resp.status_code} from {model}")
                    continue
                data = resp.json()
                data["_rotator_model"] = model
                data["_rotator_key_index"] = key_i
                return data
            except Exception as e:
                logger.warning("Rotator transport error key#%s model=%s: %s", key_i, model, e)
                last_err = e
                continue
        raise CRITICAL_LLM_FAILURE(
            f"Exhausted {attempts} Groq attempts. Last error: {last_err}"
        )

    async def achat_completion(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float = 0.3,
        response_format: Optional[Dict[str, str]] = None,
        max_tokens: int = 800,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """Async variant of chat_completion."""
        import httpx

        last_err: Optional[Exception] = None
        attempts = self.max_attempts()
        for _ in range(attempts):
            n = next(self._counter)
            api_key, model, key_i, model_i = self._pick(n)
            payload: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            }
            if response_format:
                payload["response_format"] = response_format
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            try:
                async with httpx.AsyncClient(timeout=timeout) as http:
                    resp = await http.post(
                        f"{GROQ_BASE_URL}/chat/completions",
                        json=payload,
                        headers=headers,
                    )
                if resp.status_code == 429:
                    logger.warning(
                        "429 rate limit key#%s model=%s — advancing", key_i, model
                    )
                    import asyncio

                    await asyncio.sleep(0.5)
                    last_err = RuntimeError(f"429 from {model}")
                    continue
                if resp.status_code >= 400:
                    logger.warning(
                        "HTTP %s key#%s model=%s: %s — advancing",
                        resp.status_code,
                        key_i,
                        model,
                        resp.text[:200],
                    )
                    last_err = RuntimeError(f"{resp.status_code} from {model}")
                    continue
                data = resp.json()
                data["_rotator_model"] = model
                data["_rotator_key_index"] = key_i
                return data
            except Exception as e:
                logger.warning("Rotator transport error key#%s model=%s: %s", key_i, model, e)
                last_err = e
                continue
        raise CRITICAL_LLM_FAILURE(
            f"Exhausted {attempts} Groq attempts. Last error: {last_err}"
        )


_default_rotator: Optional[DynamicGroqRotator] = None


def get_default_rotator() -> DynamicGroqRotator:
    global _default_rotator
    if _default_rotator is None:
        _default_rotator = DynamicGroqRotator()
    return _default_rotator
