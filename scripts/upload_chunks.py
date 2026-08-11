import os
import sys
import time
import subprocess

def main():
    chunks = sorted([f for f in os.listdir(".") if f.startswith("data_chunk_")])
    total = len(chunks)
    print(f"🚀 Uploading {total} chunks (10MB each) to GCP VM...")
    
    for idx, chunk in enumerate(chunks, 1):
        success = False
        attempts = 0
        while not success and attempts < 5:
            attempts += 1
            print(f"[{idx}/{total}] Uploading {chunk} (Attempt {attempts})...", flush=True)
            cmd = ["scp", "-o", "ConnectTimeout=10", chunk, f"inbox-engine:~/InboxEval/data_chunks/{chunk}"]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0:
                success = True
            else:
                print(f"⚠️ Attempt {attempts} failed for {chunk}. Retrying in 2s...", flush=True)
                time.sleep(2)
                
        if not success:
            print(f"❌ Failed to upload {chunk} after 5 attempts!", flush=True)
            sys.exit(1)
            
    print("\n🎉 All 10MB chunks uploaded successfully to GCP VM!", flush=True)
    print("Reassembling & extracting archive on GCP VM...", flush=True)
    
    reassemble_cmd = [
        "ssh", "inbox-engine",
        "cd ~/InboxEval/data_chunks && cat data_chunk_* > ~/InboxEval/data_backup.tar.gz && cd ~/InboxEval && tar -xzvf data_backup.tar.gz && rm -rf data_chunks data_backup.tar.gz"
    ]
    res = subprocess.run(reassemble_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode == 0:
        print("✅ SUCCESS: Data reassembled and extracted on GCP VM!")
        print(res.stdout[:500])
    else:
        print("❌ Reassembly error:", res.stderr)

if __name__ == "__main__":
    main()
