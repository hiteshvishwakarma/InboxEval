import json
import os

trace_file = "data/traces/trace_1783.jsonl"
output_artifact = "/Users/hiteshvishwakarma/.gemini/antigravity-cli/brain/d0f7f1dd-b711-408e-8797-ee0e26e16a07/engine_visualizer.md"

def generate_markdown():
    if not os.path.exists(trace_file):
        print(f"Error: {trace_file} not found.")
        return

    lines = []
    with open(trace_file, 'r') as f:
        for line in f:
            lines.append(json.loads(line))

    md = ["# ⚙️ Evolutionary Engine Teardown: Live Execution Trace (Email 1783)"]
    md.append("This visualizer acts as an X-Ray of the pipeline, showing the exact data payloads moving through the FSM (Finite State Machine).")
    
    md.append("## Engine State Diagram")
    md.append("```mermaid")
    md.append("stateDiagram-v2")
    md.append("    direction TB")
    md.append("    [*] --> Ingest")
    md.append("    Ingest --> PersonaExtract")
    md.append("    PersonaExtract --> Vectorization")
    md.append("    Vectorization --> PersonaSynthesis")
    md.append("    PersonaSynthesis --> GenesisMutation")
    md.append("    GenesisMutation --> Evaluate")
    md.append("    Evaluate --> KDARanking")
    md.append("    KDARanking --> ConvergenceCheck")
    md.append("    ConvergenceCheck --> FeedbackLoop : Evolution Continues")
    md.append("    FeedbackLoop --> Crossover")
    md.append("    Crossover --> Elitism")
    md.append("    Elitism --> Evaluate")
    md.append("    ConvergenceCheck --> [*] : Early Stop / Converged")
    md.append("```\n")

    md.append("---\n")

    for step_data in lines:
        step_name = step_data.get("step")
        gen = step_data.get("generation")
        inputs = step_data.get("inputs", {})
        outputs = step_data.get("outputs", {})

        gen_label = f" (Generation {gen})" if gen >= 0 else ""
        md.append(f"## 🧩 {step_name}{gen_label}")
        
        # Determine FSM transition
        md.append("```mermaid")
        md.append("graph LR")
        md.append(f"    Inputs[{list(inputs.keys())}] --> Engine[fa:fa-cogs {step_name}]")
        md.append(f"    Engine --> Outputs[{list(outputs.keys()) if isinstance(outputs, dict) else 'List of Objects'}]")
        md.append("```")

        md.append("### 📥 Input Payloads to Engine:")
        md.append("```json")
        md.append(json.dumps(inputs, indent=2)[:1000] + ("\n... [truncated for readability]" if len(json.dumps(inputs)) > 1000 else ""))
        md.append("```")

        md.append("### 📤 Output Payloads from Engine:")
        md.append("```json")
        out_str = json.dumps(outputs, indent=2)
        md.append(out_str[:1500] + ("\n... [truncated for readability]" if len(out_str) > 1500 else ""))
        md.append("```")
        md.append("---\n")

    with open(output_artifact, 'w') as f:
        f.write("\n".join(md))
        
    print(f"Artifact successfully generated at {output_artifact}")

if __name__ == "__main__":
    generate_markdown()
