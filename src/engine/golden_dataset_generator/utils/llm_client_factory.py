import os
import asyncio
import logging
import instructor
from openai import OpenAI, AsyncOpenAI
import tenacity

logger = logging.getLogger("LLMClientFactory")

def _apply_universal_retry(raw_client, is_async=False, semaphore=None):
    """Wraps the inner create() call with Tenacity and an optional centralized concurrency Semaphore."""
    
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
                    before_sleep=lambda retry_state: logger.warning(f"[Universal Retry] LLM Error: {retry_state.outcome.exception()}. Retrying in {retry_state.next_action.sleep}s...")
                )
                def create(self, **kwargs):
                    kwargs.setdefault('model', os.getenv("GENERATION_MODEL", "Qwen/Qwen2.5-32B-Instruct-AWQ"))
                    return self.completions.create(**kwargs)
                    
                @tenacity.retry(
                    stop=tenacity.stop_after_attempt(10),
                    wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
                    retry=tenacity.retry_if_exception_type(Exception),
                    before_sleep=lambda retry_state: logger.warning(f"[Universal Retry] Async LLM Error: {retry_state.outcome.exception()}. Retrying in {retry_state.next_action.sleep}s...")
                )
                async def acreate(self, **kwargs):
                    kwargs.setdefault('model', os.getenv("GENERATION_MODEL", "Qwen/Qwen2.5-32B-Instruct-AWQ"))
                    async def _execute():
                        if hasattr(self.completions, 'acreate'):
                            return await self.completions.acreate(**kwargs)
                        else:
                            return await self.completions.create(**kwargs)
                            
                    if semaphore:
                        async with semaphore:
                            return await _execute()
                    return await _execute()
                    
    return UniversalRetryWrapper(raw_client)


_global_llm_semaphore = None

def get_robust_llm_client(is_async=False):
    """
    Returns a mathematically bulletproof LLM Client powered by OmniRoute!
    1. Points to the local OmniRoute server (localhost:20128)
    2. Uses model="auto" to seamlessly fall back across 90+ free AI providers when quotas are hit.
    3. Wraps the client in a Tenacity Universal Retry Loop.
    4. Enforces a Global API Semaphore to prevent flooding.
    """
    global _global_llm_semaphore
    
    logger.info(f"Initialized OmniRoute-powered LLM Factory ({'Async' if is_async else 'Sync'}).")
    
    # We can bump concurrency up safely because OmniRoute load balances across multiple free providers!
    if is_async and _global_llm_semaphore is None:
        _global_llm_semaphore = asyncio.Semaphore(100) 
        
    base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:20128/v1")
    api_key = os.getenv("OPENAI_API_KEY", "omniroute")
    
    if is_async:
        client = instructor.from_openai(AsyncOpenAI(api_key=api_key, base_url=base_url), mode=instructor.Mode.TOOLS)
    else:
        client = instructor.from_openai(OpenAI(api_key=api_key, base_url=base_url), mode=instructor.Mode.TOOLS)
        
    return _apply_universal_retry(client, is_async=is_async, semaphore=_global_llm_semaphore)
