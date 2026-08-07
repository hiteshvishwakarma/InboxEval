# GCP GPU & vLLM Orchestration Guide (InboxEval 13-Step Engine)

## Executive Summary
This document provides the definitive, single-source-of-truth blueprint for hosting **`Qwen/Qwen2.5-32B-Instruct-AWQ`** on a Google Cloud Platform (GCP) G2 instance to power the InboxEval 13-Step Golden Dataset Evolutionary Engine. 

By leveraging an **NVIDIA L4 GPU (24GB VRAM)** with **vLLM PagedAttention**, the infrastructure supports 15–20 concurrent async FSM coroutines without Key-Value (KV) cache memory cross-contamination. Antigravity acts as the automated remote orchestrator over SSH.

---

## 1. Architecture Blueprint

```mermaid
flowchart TD
    subgraph Local_Mac["Local Laptop (Antigravity Orchestrator)"]
        A["mass_evolution_runner.py"] -->|"15-20 Async FSM Workers"| B["llm_client_factory.py"]
        B -->|"OpenAI Protocol / Instructor Pydantic Schemas"| C["vLLM Client"]
    end

    subgraph GCP_G2_VM["GCP G2 Instance (g2-standard-12)"]
        C -->|"HTTP Port 8000 / SSH Tunnel"| D["vLLM Server (vllm serve)"]
        D -->|"PagedAttention KV Cache Isolation"| E["NVIDIA L4 GPU (24GB VRAM)"]
        E -->|"AWQ 4-Bit Weights (~19.5GB)"| F["Qwen/Qwen2.5-32B-Instruct-AWQ"]
    end

    subgraph Database_Storage["Telemetry & Dataset Storage"]
        A -->|"Async Write / aiosqlite"| G[("pipeline.db (Golden Records)")]
    end
```

---

## 2. In-Depth Execution Steps

### Phase 1: VM Instance Configuration (GCP Console)
The instance is provisioned with high CPU RAM headroom to ensure PyTorch model loading and CPU vectorization (Step 02 `sentence-transformers`) run without host memory pressure.

* **Instance Name:** `inbox-eval-engine`
* **Region / Zone:** `us-central1` (or any zone with available L4 quota)
* **Machine Series:** **G2**
* **Machine Type:** **`g2-standard-12`** (12 vCPUs, 48 GB System RAM, 1x NVIDIA L4 GPU 24GB VRAM)
* **Boot Disk:**
  * **Operating System:** Deep Learning on Linux
  * **Version:** `Deep Learning VM with CUDA + Pytorch M132` (Ubuntu 22.04, CUDA 12.9)
  * **Disk Type & Size:** SSD Persistent Disk — **120 GB**
  * **GPU Driver:** Check *"Install NVIDIA GPU driver automatically on first boot"*
* **Firewall:** Allow HTTP & HTTPS traffic.

---

### Phase 2: Automated SSH Key Pairing & Config
To enable seamless remote execution by Antigravity from the local Mac:

1. **Generate Project Keypair on Mac:**
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/gcp_inbox_eval -N "" -C "hitesh@inboxeval"
   ```
2. **Add Public Key to GCP Console:**
   Copy `~/.ssh/gcp_inbox_eval.pub` into **VM Instance -> Edit -> SSH Keys**.
3. **Configure SSH Alias (`~/.ssh/config`):**
   ```sshconfig
   Host inbox-engine
       HostName <YOUR_VM_EXTERNAL_IP>
       IdentityFile ~/.ssh/gcp_inbox_eval
       User hitesh
       StrictHostKeyChecking no
   ```

---

### Phase 3: vLLM Server Deployment & Launch
Once SSH access is established, Antigravity executes the following commands on the remote VM:

1. **Verify GPU Status:**
   ```bash
   nvidia-smi
   ```
2. **Create Python Virtual Environment & Install vLLM:**
   ```bash
   python3 -m venv vllm-env
   source vllm-env/bin/activate
   pip install --upgrade pip
   pip install vllm instructor openai
   ```
3. **Start the vLLM OpenAI-Compatible API Server:**
   ```bash
   vllm serve Qwen/Qwen2.5-32B-Instruct-AWQ \
       --host 0.0.0.0 \
       --port 8000 \
       --quantization awq \
       --max-model-len 8192 \
       --gpu-memory-utilization 0.90 \
       --enable-auto-tool-choice \
       --tool-call-parser pythonic
   ```
   * **`--quantization awq`:** Compresses weights to ~19.5 GB VRAM.
   * **`--gpu-memory-utilization 0.90`:** Reserves 90% of 24GB VRAM (~21.6 GB) for weights + PagedAttention KV cache.
   * **`--enable-auto-tool-choice --tool-call-parser pythonic`:** Enables `instructor` native Pydantic schema structured outputs across Steps 01–12.

---

### Phase 4: InboxEval Engine Client Integration
Update `src/engine/golden_dataset_generator/config.py` and `utils/llm_client_factory.py` (or `.env` environment variables):

```env
OPENAI_BASE_URL=http://<YOUR_VM_EXTERNAL_IP>:8000/v1
OPENAI_API_KEY=vllm-dummy-key
GENERATION_MODEL=Qwen/Qwen2.5-32B-Instruct-AWQ
CLASSIFICATION_MODEL=Qwen/Qwen2.5-32B-Instruct-AWQ
```

---

### Phase 5: Mass Evolution & Golden Dataset Export
Run the 13-step evolutionary loop inside a `tmux` session to ensure uninterrupted execution:

```bash
# Launch mass evolution runner across 20 concurrent coroutines
python3 -m scripts.mass_evolution_runner
```
* **Step 01–03:** Ingestion, Backtranslation, Sentence-Transformers vectorization.
* **Step 04–06:** DPBC threshold calculation, adversarial persona synthesis, genesis mutations.
* **Step 07–11:** Reward hack evaluation, KDA matrix ranking, critique, crossover, elitism.
* **Step 12:** Convergence check & async export into `pipeline.db`.
