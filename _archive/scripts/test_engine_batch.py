import logging
from src.engine.golden_dataset_generator.orchestrator import GoldenDatasetOrchestrator

logging.getLogger("Step01_Ingest").setLevel(logging.WARNING)
logging.getLogger("Step03_Vectorization").setLevel(logging.WARNING)
logging.getLogger("Step07_KDARanking").setLevel(logging.WARNING)

def main():
    print("🚀 Initializing Engine for Batch of 4...")
    orchestrator = GoldenDatasetOrchestrator()
    
    emails = [
        {
            "id": "test_batch_1_sales",
            "text": "Hey David, noticed you're scaling the engineering team at Acme Corp. We built a tool that cuts AWS bills by 30%. Any interest in a 10 min chat next Tuesday?"
        },
        {
            "id": "test_batch_2_apology",
            "text": "So sorry I missed our lunch today! Totally lost track of time in a meeting. Can we reschedule for next week? Lunch is on me this time!"
        },
        {
            "id": "test_batch_3_data",
            "text": "Here are the details for the offsite: We need 3 vegan meals, 2 gluten-free. Flight arrives at 10 AM on Delta 442. Also tell John to bring the projector."
        },
        {
            "id": "test_batch_4_resign",
            "text": "Dear Sarah, Please accept this email as formal notice of my resignation, effective two weeks from today on October 15th. Thank you for the opportunity."
        }
    ]
    
    for idx, em in enumerate(emails, 1):
        print(f"\n[TEST {idx}/4] Ingesting Email ID: {em['id']}")
        try:
            champion = orchestrator.run_pipeline(
                raw_email_text=em["text"].strip(),
                email_id=em['id'],
                output_path=f"data/test_{em['id']}.jsonl"
            )
            print(f"✅ {em['id']} COMPLETE! Final Prompt:")
            print("-" * 50)
            print(champion.final_prompt_text)
            print("-" * 50)
        except Exception as e:
            print(f"❌ Error on {em['id']}: {e}")

if __name__ == "__main__":
    main()
