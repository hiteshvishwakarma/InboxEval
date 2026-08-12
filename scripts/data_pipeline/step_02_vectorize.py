import json
import os

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Please install vector deps: pip install chromadb sentence-transformers")
    exit(1)

INPUT_FILE = "data/01_backtranslated.jsonl"
OUTPUT_FILE = "data/02_golden_foundation.jsonl"
DB_DIR = "data/chroma_db"

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Missing {INPUT_FILE}. Run step 01 first.")
        exit(1)
        
    print("Initializing ChromaDB (Local SQLite)...")
    chroma_client = chromadb.PersistentClient(path=DB_DIR)
    collection = chroma_client.get_or_create_collection(name="enron_emails")
    
    print("Loading lightweight embedding model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Read the whole backtranslated dataset
    docs = []
    ids = []
    metadata = []
    
    print("Parsing backtranslated emails...")
    with open(INPUT_FILE, 'r') as f:
        for line in f:
            item = json.loads(line)
            docs.append(item['emails_to_grade'][0]['email_text'])
            ids.append(str(item['id']))
            
            # Storing the JSON as metadata so we can fetch it easily via vector search later
            metadata.append({
                "prompt": item.get('prompt', ''),
                "source": item.get('source', '')
            })
            
    print(f"Loaded {len(docs)} emails. Vectorizing now...")
    
    # SentenceTransformers is fast enough to batch process thousands on a CPU
    embeddings = model.encode(docs, show_progress_bar=True, batch_size=32)
    
    print("Pushing molecular vectors to ChromaDB...")
    # Chroma handles batched insertion
    batch_size = 5000
    for i in range(0, len(docs), batch_size):
        end = min(i + batch_size, len(docs))
        collection.add(
            embeddings=embeddings[i:end].tolist(),
            documents=docs[i:end],
            metadatas=metadata[i:end],
            ids=ids[i:end]
        )
        
    # We also copy it to the final foundation JSONL for the Evolutionary Engine
    print(f"Writing final dataset to {OUTPUT_FILE}...")
    with open(INPUT_FILE, 'r') as fin, open(OUTPUT_FILE, 'w') as fout:
        for line in fin:
            fout.write(line)
            
    print("Step 02 Complete! Vector namespace populated.")

if __name__ == "__main__":
    main()
