import csv
import os
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Find any GROQ_API_KEY in the environment
groq_key = None
for key, value in os.environ.items():
    if key.startswith("GROQ_API_KEY_") and value:
        groq_key = value
        break

if not groq_key:
    raise ValueError("No Groq API key found in .env")

# Initialize Groq Client
client = Groq(api_key=groq_key)

INPUT_CSV = "data/evaluation_dataset.csv"
OUTPUT_CSV = "data/evaluation_dataset_populated.csv"

def generate_email(prompt: str, model: str) -> str:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"ERROR: {str(e)}"

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"Error: {INPUT_CSV} not found.")
        return

    with open(INPUT_CSV, "r") as f:
        reader = list(csv.DictReader(f))

    fieldnames = ["Email_ID", "Email_Body", "Generated_Prompt", "Llama_3_70B", "Llama_3_8B", "Mixtral_8x7B", "Friends_Feedback"]

    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for idx, row in enumerate(reader):
            prompt = row.get("Generated_Prompt", "").strip()
            print(f"Processing ID {row.get('Email_ID')} ({idx+1}/{len(reader)})...")
            
            if prompt:
                # Generate 3 variants using 3 different Groq open-source models
                llama_70b = generate_email(prompt, "llama-3.3-70b-versatile")
                llama_8b = generate_email(prompt, "llama-3.1-8b-instant")
                mixtral = generate_email(prompt, "mixtral-8x7b-32768")
                
                # Sleep to prevent rapid rate-limiting on Groq
                time.sleep(2)
            else:
                llama_70b, llama_8b, mixtral = "", "", ""

            writer.writerow({
                "Email_ID": row.get("Email_ID", ""),
                "Email_Body": row.get("Email_Body", ""),
                "Generated_Prompt": prompt,
                "Llama_3_70B": llama_70b,
                "Llama_3_8B": llama_8b,
                "Mixtral_8x7B": mixtral,
                "Friends_Feedback": ""
            })

    print(f"\nSuccessfully populated variants into {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
