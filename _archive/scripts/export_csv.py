import json
import csv

input_file = "data/temp_dataset.jsonl"
output_file = "data/evaluation_dataset.csv"

try:
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8', newline='') as f_out:
         
        writer = csv.writer(f_out)
        # Write headers
        writer.writerow(["Email_ID", "Email_Body", "Generated_Prompt", "Friends_Feedback"])
        
        count = 0
        for line in f_in:
            data = json.loads(line)
            email_id = data.get("email_id", "N/A")
            email_body = data.get("human_target_text", "")
            prompt = data.get("optimal_super_prompt", "")
            
            writer.writerow([email_id, email_body, prompt, ""])
            count += 1
            
    print(f"Successfully exported {count} records to {output_file}")
except Exception as e:
    print(f"Failed to export CSV: {e}")
