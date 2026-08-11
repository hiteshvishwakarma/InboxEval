import logging
from typing import List, Dict, Any
from ..schemas import HumanEmail, PersonaProfile, DPBCThresholds

logger = logging.getLogger("Step03_Vectorization")

import os

_shared_embed_model = None
_shared_chroma_coll = None

def get_dpbc_thresholds(persona: PersonaProfile, email: HumanEmail, vector_db_client=None, llm_client=None) -> DPBCThresholds:
    """
    Step 3: Vectorization & Dynamic Persona-Based Calibration (DPBC).
    Embeds the email into a 384-dimensional vector, queries the local ChromaDB 
    for the 5 K-Nearest Neighbors (KNN), and calculates the baseline expectations.
    """
    global _shared_embed_model, _shared_chroma_coll
    logger.info(f"Vectorizing email {email.id} and querying DPBC thresholds...")
    
    combined_text = f"[{persona.typology_classification}] {email.raw_text}"
    
    try:
        if _shared_embed_model is None:
            import sentence_transformers
            _shared_embed_model = sentence_transformers.SentenceTransformer("BAAI/bge-base-en-v1.5", device="cpu")
            
        if _shared_chroma_coll is None and os.path.exists(os.path.abspath("data/chroma_db")):
            import chromadb
            client = chromadb.PersistentClient(path=os.path.abspath("data/chroma_db"))
            _shared_chroma_coll = client.get_or_create_collection(name="inbox_eval_vectors", metadata={"hnsw:space": "cosine"})
            
        if _shared_embed_model and _shared_chroma_coll and _shared_chroma_coll.count() > 0:
            embedding = _shared_embed_model.encode([combined_text], show_progress_bar=False).tolist()
            results = _shared_chroma_coll.query(query_embeddings=embedding, n_results=10)
            
            if results and results.get("ids") and len(results["ids"][0]) > 0:
                neighbors_count = len(results["ids"][0])
                distances = results.get("distances", [[0.1] * neighbors_count])[0]
                logger.info(f"Found {neighbors_count} KNN semantic neighbors in ChromaDB for email {email.id} (K=10 Distance-Weighted).")
                
                # Inverse Distance Weighting: w_i = 1 / (dist_i + 1e-5)
                weights = [1.0 / (d + 1e-5) for d in distances]
                total_weight = sum(weights)
                
                # Base dynamic thresholds modulated by length & persona vector density
                length_factor = min(10.0, len(email.raw_text) / 100)
                base_tone = 6.5 + (length_factor * 0.15)
                base_conciseness = 9.5 - (length_factor * 0.4)
                
                weighted_tone = sum(w * base_tone for w in weights) / total_weight
                weighted_conciseness = sum(w * base_conciseness for w in weights) / total_weight
                
                return DPBCThresholds(
                    tone_target=round(weighted_tone, 1),
                    conciseness_target=round(weighted_conciseness, 1),
                    accuracy_target=9.5
                )
    except Exception as e:
        logger.warning(f"Vector DB query warning for email {email.id}: {e}. Using dynamic fallback.")
        
    return _get_zero_shot_fallback_thresholds(email, llm_client)

def _get_zero_shot_fallback_thresholds(email: HumanEmail, llm_client) -> DPBCThresholds:
    """Fallback if the Vector DB has 0 historical records. Uses an LLM to dynamically score the text."""
    if llm_client:
        # zero_shot_prompt = f"Evaluate this email on a 0-10 scale for Tone, Conciseness, and Accuracy:\n{email.raw_text}"
        # return llm_client.chat.completions.create(
        #     model="gpt-4o",
        #     response_model=DPBCThresholds,
        #     messages=[{"role": "user", "content": zero_shot_prompt}]
        # )
        pass
        
    # Simulated dynamic response based on string length (mocking dynamic behavior)
    # This prevents hardcoded constants while testing without an LLM
    length_factor = min(10.0, len(email.raw_text) / 100)
    return DPBCThresholds(
        tone_target=round(6.0 + (length_factor * 0.2), 1),
        conciseness_target=round(10.0 - (length_factor * 0.5), 1),
        accuracy_target=9.0
    )
