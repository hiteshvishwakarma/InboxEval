import os

class EngineConfig:
    # Model Configurations
    DEFAULT_GENERATION_MODEL = os.getenv("GENERATION_MODEL", "Qwen/Qwen2.5-32B-Instruct-AWQ")
    FAST_CLASSIFICATION_MODEL = os.getenv("CLASSIFICATION_MODEL", "Qwen/Qwen2.5-32B-Instruct-AWQ")
    
    # Genetic Algorithm Parameters
    NUM_CHALLENGERS_PER_GENERATION = int(os.getenv("NUM_CHALLENGERS_PER_GENERATION", "4"))
    EARLY_STOP_PLATEAU_LIMIT = int(os.getenv("EARLY_STOP_PLATEAU_LIMIT", "3"))
    
    # Evaluation Constants
    PERSONA_DEVIATION_PENALTY = float(os.getenv("PERSONA_DEVIATION_PENALTY", "5.0"))
    FAILED_EVALUATION_DELTA = float(os.getenv("FAILED_EVALUATION_DELTA", "3996.0"))
    FAILED_PENALTY_DELTA = float(os.getenv("FAILED_PENALTY_DELTA", "999.0"))
    FAILED_SCORE = float(os.getenv("FAILED_SCORE", "0.0"))
    
    # Default Target Thresholds (DPBC)
    DEFAULT_TONE_TARGET = float(os.getenv("DEFAULT_TONE_TARGET", "8.5"))
    DEFAULT_CONCISENESS_TARGET = float(os.getenv("DEFAULT_CONCISENESS_TARGET", "9.0"))
    DEFAULT_ACCURACY_TARGET = float(os.getenv("DEFAULT_ACCURACY_TARGET", "9.5"))
    
config = EngineConfig()
