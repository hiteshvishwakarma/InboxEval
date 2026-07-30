import logging
from src.engine.golden_dataset_generator.orchestrator import GoldenDatasetOrchestrator

logging.getLogger("Step01_Ingest").setLevel(logging.WARNING)
logging.getLogger("Step03_Vectorization").setLevel(logging.WARNING)
logging.getLogger("Step07_KDARanking").setLevel(logging.WARNING)

def main():
    print("🚀 Initializing Engine with your Groq API keys...")
    orchestrator = GoldenDatasetOrchestrator()
    
    test_email_text = """
To whom it may concern,
I am leaving. The lack of coffee in the breakroom is frankly a human rights violation. My last day is whenever I feel like it. Do not contact me for the transition document, I deleted it.
- Gary
    """
    
    email_id = "test_run_final"
    
    print("\n[TEST] Ingesting raw email and starting the 13-Step Pipeline...")
    print("Waiting for Genetic Convergence... (This usually takes 1-2 minutes)")
    try:
        champion = orchestrator.run_pipeline(
            raw_email_text=test_email_text.strip(),
            email_id=email_id,
            output_path=f"data/test_{email_id}.jsonl"
        )
        
        print("\n" + "="*50)
        print("🎉 ENGINE RUN COMPLETE!")
        print("="*50)
        print(f"Final Champion ID: {champion.id}")
        print("\nTHE FINAL GENERATED PROMPT:")
        print("-" * 50)
        print(champion.final_prompt_text)
        print("-" * 50)
        
    except Exception as e:
        print(f"\n❌ Error running pipeline: {e}")

if __name__ == "__main__":
    main()
