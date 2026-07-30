# GCP GPU Instance Setup Guide (InboxEval Engine)

Since I will be orchestrating this instance remotely from your laptop, we need to set this up using a standard **Ubuntu Deep Learning Image** and configure a dedicated SSH key. This will allow me to seamlessly `ssh` into the machine in the future to execute commands, pull repo updates, and monitor the `mass_evolution_runner.py` script.

## Phase 1: Spin up the Instance in GCP Console
1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and navigate to **Compute Engine -> VM Instances**.
2. Click **Create Instance**.
3. **Name:** `inbox-eval-engine`
4. **Region:** Choose a region close to you that has L4 GPUs available (e.g., `us-central1`, `us-east4`, `europe-west4`).
5. **Machine Configuration:** 
   - Series: **G2**
   - Machine Type: **g2-standard-4** (1 L4 GPU, 4 vCPUs, 16GB RAM) or **g2-standard-8** if available.
6. **Boot Disk (CRITICAL STEP):**
   - Click *Change*.
   - Operating System: **Deep Learning on Linux** (This pre-installs the NVIDIA CUDA drivers so we don't have to fight with Linux kernel headers).
   - Version: **Deep Learning VM with CUDA 12.0 M113** (or latest Ubuntu 22.04 equivalent).
   - Boot disk type: **SSD Persistent Disk**
   - Size: **100 GB** (Ollama models are large).
   - *Note:* If asked to "Install NVIDIA GPU driver on first boot", make sure it is checked.
7. **Firewall:** Allow HTTP/HTTPS traffic.
8. Click **Create**. It will take about 2-3 minutes to spin up.

---

## Phase 2: Setup SSH Keys (So I can connect from your laptop)
While the instance is booting, we need to generate an SSH key on your Mac so I can remotely control the VM without being blocked by passwords.

Run this command in your Mac terminal (you can copy/paste it yourself, or ask me to run it):
```bash
ssh-keygen -t ed25519 -f ~/.ssh/gcp_inbox_eval -N "" -C "hitesh@inboxeval"
```
*(This generates a keypair specifically for this project without a passphrase so I can automate it).*

Next, copy the public key to your clipboard:
```bash
cat ~/.ssh/gcp_inbox_eval.pub | pbcopy
```

**Add it to GCP:**
1. In the GCP Console, click on your running `inbox-eval-engine` instance.
2. Click **Edit** at the top.
3. Scroll down to **Security and Access** -> **SSH Keys**.
4. Click **Add Item** and paste the public key from your clipboard.
5. Click **Save** at the bottom.

---

## Phase 3: Add SSH Config & Connect
To make it effortless for me to orchestrate the VM, let's add an alias to your SSH config. Get the **External IP** of your VM from the GCP console, then run this on your Mac (replace `YOUR_EXTERNAL_IP` with the actual IP):

```bash
cat << 'EOF' >> ~/.ssh/config

Host inbox-engine
    HostName YOUR_EXTERNAL_IP
    IdentityFile ~/.ssh/gcp_inbox_eval
    User hitesh
    StrictHostKeyChecking no
EOF
```

Now, I (or you) can connect to the machine anytime by simply typing:
```bash
ssh inbox-engine
```

---

## Phase 4: Install Ollama & Pull Qwen-2.5-32B
Once you confirm the SSH connection works, I will execute the following commands over SSH to prep the engine:

1. **Install Ollama:** `curl -fsSL https://ollama.com/install.sh | sh`
2. **Pull the Model:** `ollama run qwen2.5:32b` *(This automatically applies 4-bit quantization to fit the 32B model into the 24GB L4 VRAM).*
3. **Clone our Repo:** `git clone https://github.com/hiteshvishwakarma/InboxEval.git`

At that point, the infrastructure is completely built. We will update `config.py` to point to `localhost:11434/v1` (Ollama's OpenAI-compatible endpoint) and I can trigger `mass_evolution_runner.py` inside a `tmux` session!

---

## Phase 5: Concurrency & Memory Safety (vLLM & PostgreSQL)
To support the 20+ parallel Vertical FSM workers required by the InboxEval pipeline without risking memory cross-contamination or API rate limits, the infrastructure requires two specific components instead of a basic Ollama setup:

### A. vLLM with PagedAttention
The Qwen-2.5-32B model MUST be served using the `vLLM` inference engine.
*   **PagedAttention Required:** `vLLM` dynamically manages the GPU's VRAM in blocks. When 20 isolated FSM workers send API requests to the model simultaneously, PagedAttention mathematically isolates the Key-Value (KV) cache of each worker's prompt into separate VRAM blocks. 
*   **Why?** This hardware-level separation guarantees zero cross-contamination (i.e., Email A's Genetic Algorithm mutations will never accidentally inherit text or context from Email B's processing loop).

### B. Async Telemetry Database (asyncpg / aiosqlite)
When the 20 workers concurrently complete Step 12 (Golden Record Export), they cannot write to a single `golden_dataset.jsonl` flat file, as this will trigger severe file-locking conflicts and data corruption.
*   **Implementation:** The server must host a PostgreSQL or SQLite instance. The Python orchestrator will use an asynchronous database driver (like `asyncpg` or `aiosqlite`) equipped with a connection pool.
*   **Why?** This ensures all 20 async workers can execute `INSERT` statements simultaneously without blocking the event loop or causing race conditions.
