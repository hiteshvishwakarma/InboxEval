import json
import logging
from src.engine.golden_dataset_generator.orchestrator import GoldenDatasetOrchestrator

# Reduce logging noise to just see our print statements clearly
logging.getLogger("Step01_Ingest").setLevel(logging.WARNING)
logging.getLogger("Step03_Vectorization").setLevel(logging.WARNING)
logging.getLogger("Step07_KDARanking").setLevel(logging.WARNING)

def main():
    print("🚀 Initializing Engine with your Groq API keys...")
    orchestrator = GoldenDatasetOrchestrator()
    
    # Let's use a very human, slightly aggressive email to see how the Engine handles it
    test_email_text = """
John,
Where the hell is the Q3 report? You said it would be on my desk by Monday. It is now Thursday. I am getting extremely tired of these constant delays. Send it to me in the next 10 minutes or we are having a very different conversation.
- Mark
    """
    
    email_id = "test_run_1"
    
    print("\n[TEST] Ingesting raw email and starting the 12-Step Pipeline...")
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
        print(f"Final Elo Delta: {champion.elo_delta:.2f}")
        print("\nTHE FINAL GENERATED PROMPT:")
        print("-" * 50)
        print(champion.final_prompt_text)
        print("-" * 50)
        
    except Exception as e:
        print(f"\n❌ Error running pipeline: {e}")

if __name__ == "__main__":
    main()
