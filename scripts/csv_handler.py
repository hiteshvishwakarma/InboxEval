import json
import csv
import sys
import os

def json_to_csv(json_path, csv_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    # The 12 parameters in order
    params = [
        "instruction_adherence", "factual_accuracy", "professionalism", 
        "tone_appropriateness", "human_likeness", "persona_adherence", 
        "spam_safety", "deliverability", "formatting", "structure", 
        "conciseness", "intent_clarity"
    ]
    
    headers = ["id", "prompt", "context", "target_persona", "type", "email_text"] + params
    
    rows = []
    for item in data:
        for email_case in item.get("emails_to_grade", []):
            row = {
                "id": item["id"],
                "prompt": item["prompt"],
                "context": item["context"],
                "target_persona": item.get("target_persona", ""),
                "type": email_case["type"],
                "email_text": email_case["email_text"]
            }
            # Add the expected scores
            scores = email_case.get("expected_scores", {})
            for p in params:
                row[p] = scores.get(p, "")
                
            rows.append(row)
            
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Successfully converted {json_path} to {csv_path}")

def csv_to_json(csv_path, json_path):
    # This will read the CSV and reconstruct the nested JSON
    data_dict = {}
    
    params = [
        "instruction_adherence", "factual_accuracy", "professionalism", 
        "tone_appropriateness", "human_likeness", "persona_adherence", 
        "spam_safety", "deliverability", "formatting", "structure", 
        "conciseness", "intent_clarity"
    ]
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_id = int(row["id"])
            if item_id not in data_dict:
                data_dict[item_id] = {
                    "id": item_id,
                    "prompt": row["prompt"],
                    "context": row["context"],
                    "target_persona": row.get("target_persona", ""),
                    "emails_to_grade": []
                }
                
            scores = {}
            for p in params:
                # Convert string scores back to int if possible
                val = row[p]
                try:
                    scores[p] = int(val) if val.strip() else 0
                except ValueError:
                    scores[p] = 0
                    
            data_dict[item_id]["emails_to_grade"].append({
                "type": row["type"],
                "email_text": row["email_text"],
                "expected_scores": scores
            })
            
    # Convert dict values to a list
    final_json = list(data_dict.values())
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(final_json, f, indent=4)
        
    print(f"Successfully converted {csv_path} to {json_path}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python csv_handler.py [to_csv|to_json] input_file output_file")
        sys.exit(1)
        
    mode = sys.argv[1]
    input_file = sys.argv[2]
    output_file = sys.argv[3]
    
    if mode == "to_csv":
        json_to_csv(input_file, output_file)
    elif mode == "to_json":
        csv_to_json(input_file, output_file)
    else:
        print("Invalid mode. Use to_csv or to_json")
