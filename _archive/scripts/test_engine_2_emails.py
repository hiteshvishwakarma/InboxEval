import logging
from src.engine.golden_dataset_generator.orchestrator import GoldenDatasetOrchestrator

logging.getLogger("Step01_Ingest").setLevel(logging.WARNING)
logging.getLogger("Step03_Vectorization").setLevel(logging.WARNING)
logging.getLogger("Step07_KDARanking").setLevel(logging.WARNING)

def run_test(orchestrator, email_id, test_email_text):
    print("\n" + "*"*60)
    print(f"🚀 Running Pipeline for: {email_id}")
    print("*"*60)
    print(f"RAW EMAIL:\n{test_email_text.strip()}\n")
    
    try:
        champion = orchestrator.run_pipeline(
            raw_email_text=test_email_text.strip(),
            email_id=email_id,
            output_path=f"data/test_{email_id}.jsonl"
        )
        
        print("\n" + "="*50)
        print(f"🎉 ENGINE RUN COMPLETE FOR {email_id}!")
        print("="*50)
        print(f"Final Champion ID: {champion.id}")
        print("\nTHE FINAL GENERATED PROMPT:")
        print("-" * 50)
        print(champion.final_prompt_text)
        print("-" * 50)
        
    except Exception as e:
        print(f"\n❌ Error running pipeline for {email_id}: {e}")


def main():
    print("🚀 Initializing Engine with your Groq API keys...")
    orchestrator = GoldenDatasetOrchestrator()
    
    email_1 = """
Hey team,
Just pushing a quick update. We deployed v2.1.4 last night. The payment gateway bug should be fixed, and customers can now use Amex again. Let me know if you see any weird latency spikes on the dashboard.
- Sarah, DevOps
    """
    
    email_2 = """
URGENT: Container 409A Delay
To the logistics team: We just got word from the port authority that our shipment of lithium batteries is held up in customs due to the new tariff regulations. We need someone to immediately forward the clearance forms to the broker. If this isn't released by Friday, we miss the Q3 assembly deadline.
- Mark
    """
    
    run_test(orchestrator, "email_1_saas_patch", email_1)
    run_test(orchestrator, "email_2_b2b_logistics", email_2)

if __name__ == "__main__":
    main()
