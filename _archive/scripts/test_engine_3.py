import logging
from src.engine.golden_dataset_generator.orchestrator import GoldenDatasetOrchestrator

logging.getLogger("Step01_Ingest").setLevel(logging.WARNING)
logging.getLogger("Step03_Vectorization").setLevel(logging.WARNING)
logging.getLogger("Step07_KDARanking").setLevel(logging.WARNING)

def main():
    print("🚀 Initializing Engine for Email #3...")
    orchestrator = GoldenDatasetOrchestrator()
    
    test_email_text = """
Fwd: Re: Server Migration
Hey boss, 
See the thread below. IT says they can't migrate the servers until we sign off on the new AWS costs. They need a decision by EOD. Can you approve this so we aren't blocked?
    """
    
    email_id = "test_run_3"
    
    print("\n[TEST] Ingesting raw email and starting the 12-Step Pipeline...")
    try:
        champion = orchestrator.run_pipeline(
            raw_email_text=test_email_text.strip(),
            email_id=email_id,
            output_path=f"data/test_{email_id}.jsonl"
        )
        
        print("\n" + "="*50)
        print("🎉 ENGINE RUN COMPLETE FOR EMAIL #3!")
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
