# GCP GPU Instance Setup Guide (InboxEval Engine)

Since I will be orchestrating this instance remotely from your laptop, we need to set this up using a standard **Ubuntu Deep Learning Image** and configure a dedicated SSH key. This will allow me to seamlessly `ssh` into the machine in the future to execute commands, pull repo updates, and monitor the `mass_evolution_runner.py` script.

## Phase 0: GCP Project Prerequisites
Before spinning up the VM, we must lay the foundation for a clean, isolated cloud environment.

1. **Activate Billing:** Go to [Billing](https://console.cloud.google.com/billing). You must link a billing account to activate your $300 free trial. Google will not auto-charge you when credits expire; they just pause services. This is required for identity verification.
2. **Create a New Project:** Go to [Project Create](https://console.cloud.google.com/projectcreate). Name it `inbox-eval`. 
   - *Why a new project?* It ensures isolated billing (you see exactly how many credits the Engine uses) and allows for 1-click cleanup when you're done.
3. **Select "No Organization":** On the same project creation page, leave the organization blank (or select "No Organization").
   - *Why No Org?* Corporate Organizations enforce strict default security policies (like blocking external IPs or SSH keys). "No Org" guarantees zero friction so we can SSH directly into the VM.
4. **Enable Compute Engine API:** Go to the [Compute Engine API Library](https://console.cloud.google.com/apis/library/compute.googleapis.com) and click **Enable**.

## Phase 1: Spin up the Instance in GCP Console
1. Go directly to [Create an Instance](https://console.cloud.google.com/compute/instancesAdd) (or navigate to Compute Engine -> VM Instances and click Create).
3. **Name:** `inbox-eval-engine`
4. **Region:** Choose a region close to you that has L4 GPUs available (e.g., `us-central1`, `us-east4`, `europe-west4`).
5. **Machine Configuration:** 
   - Series: **G2**
   - Machine Type: **g2-standard-4** (1 L4 GPU, 4 vCPUs, 16GB RAM)
   - *Why G2 over E2 or Cloud Run?* The `E2` series is CPU-only and would take days to process 15,000 LLM inferences. Cloud Run is serverless and would kill our stateful script after 60 minutes. The `G2` series provides a dedicated NVIDIA L4 GPU, crushing the batch processing in hours for ~$5.
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

## Phase 4: Install Ollama & Clone Repo (On the VM)
Once you confirm the SSH connection works, I will execute the following commands over SSH to prep the engine:

1. **Install Ollama:** `curl -fsSL https://ollama.com/install.sh | sh`
2. **Pull the Model:** `ollama run llama3.1`
3. **Clone our Repo:** `git clone https://github.com/hiteshvishwakarma/InboxEval.git`

At that point, the infrastructure is completely built, and I can trigger `mass_evolution_runner.py` inside a `tmux` session!
