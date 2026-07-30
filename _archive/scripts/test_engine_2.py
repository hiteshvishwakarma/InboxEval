import logging
from src.engine.golden_dataset_generator.orchestrator import GoldenDatasetOrchestrator

logging.getLogger("Step01_Ingest").setLevel(logging.WARNING)
logging.getLogger("Step03_Vectorization").setLevel(logging.WARNING)
logging.getLogger("Step07_KDARanking").setLevel(logging.WARNING)

def main():
    print("🚀 Initializing Engine for Email #2...")
    orchestrator = GoldenDatasetOrchestrator()
    
    test_email_text = """
Hey team, 
Just a reminder that the Q3 marketing budget needs to be finalized by Friday at 5 PM EST. Please ensure that the vendor invoices for the social media campaign are submitted to accounts payable. Also, Sandra is out sick today so route all budget approvals directly to me.
Thanks,
Sarah
    """
    
    email_id = "test_run_2"
    
    print("\n[TEST] Ingesting raw email and starting the 12-Step Pipeline...")
    try:
        champion = orchestrator.run_pipeline(
            raw_email_text=test_email_text.strip(),
            email_id=email_id,
            output_path=f"data/test_{email_id}.jsonl"
        )
        
        print("\n" + "="*50)
        print("🎉 ENGINE RUN COMPLETE FOR EMAIL #2!")
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
