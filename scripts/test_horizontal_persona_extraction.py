import asyncio
import sqlite3
import os
import json
import logging
from src.engine_v2.golden_dataset_generator_v2.schemas import PersonaProfileV2
from src.engine.golden_dataset_generator.config import config
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestHorizontalExtraction")

# We will use the existing PersonaProfileV2 model to extract exactly the fields the engine expects
async def test_extract_persona():
    # 1. Fetch 1 pending email from local DB
    db_path = "data/pipeline.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, clean_text FROM raw_emails WHERE status = 'backtranslated' LIMIT 1;")
    row = cursor.fetchone()
    
    if not row:
        logger.error("No pending emails found in local database!")
        return
        
    email_id = row['id']
    raw_text = row['clean_text']
    logger.info(f"Testing extraction for Email ID: {email_id}")
    
    # 2. Prepare prompt (Identical to Step 02 in Engine v2)
    prompt = f"""
SYSTEM INSTRUCTIONS (STATIC PREFIX):
Analyze the provided email and extract a detailed Persona Profile AND 5 diverse Prompting Strategies.

REQUIREMENTS:
1. 'nlp_task': MUST be EXACTLY ONE of: ['Zero-Shot Drafting', 'Data Extraction', 'Thread Summarization', 'Tone Translation'].
2. 'formality_scale': MUST be EXACTLY ONE of: ['Hyper-Casual', 'Casual', 'Semi-Professional', 'Professional', 'Hyper-Formal'].
3. 'prompting_strategies': Generate 5 diverse strategies this specific persona might use when typing into AI (e.g., 'The Lazy Minimalist', 'The Micro-Manager', 'The Bullet-Point Thinker', 'The Conversationalist', 'The Rushed Executive').

--- DYNAMIC INPUT DATA ---
Raw Email Text: {raw_text}
"""

    # 3. Call LLM (In Production GCP this will be the VLLM instance)
    llm_client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "mock-key")
    )
    
    try:
        logger.info(f"Calling LLM Model: {config.FAST_CLASSIFICATION_MODEL}")
        # Note: If running locally without vLLM, this will fail unless we use a real OpenAI key or mock it.
        # But we will write the exact Pydantic strict-JSON extraction code here.
        import instructor
        client = instructor.from_openai(llm_client)
        
        persona = await client.chat.completions.create(
            model=config.FAST_CLASSIFICATION_MODEL,
            response_model=PersonaProfileV2,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # 4. Show what we would save to the DB
        logger.info("✅ Extraction Successful! Here is the JSON that will be saved to SQLite:")
        print(json.dumps(persona.model_dump(), indent=2))
        
        # 5. Show the SQL UPDATE statement
        sql_update = f"""
        UPDATE raw_emails 
        SET 
            nlp_task = '{persona.nlp_task}',
            formality_scale = '{persona.formality_scale}',
            sentiment = '{persona.sentiment.replace("'", "''")}',
            domain = '{persona.domain.replace("'", "''")}',
            prompting_strategies = '{json.dumps(persona.prompting_strategies).replace("'", "''")}',
            target_persona = '{persona.model_dump_json().replace("'", "''")}'
        WHERE id = {email_id};
        """
        logger.info(f"SQL UPDATE Command that will be run:\n{sql_update}")
        
    except Exception as e:
        logger.error(f"LLM Call Failed (Expected if vLLM is offline locally): {e}")

if __name__ == "__main__":
    asyncio.run(test_extract_persona())
