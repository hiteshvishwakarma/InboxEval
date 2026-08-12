import json
import os

trace_file = "data/traces/trace_1783.jsonl"
output_html = "docs/evolution_graphs.html"

def generate_graphs():
    if not os.path.exists(trace_file):
        print(f"Error: {trace_file} not found.")
        return

    # Extract data
    targets = {}
    generations = []
    overall_deltas = []
    tone_scores = []
    conciseness_scores = []
    accuracy_scores = []
    
    with open(trace_file, 'r') as f:
        for line in f:
            data = json.loads(line)
            step = data.get("step")
            
            # Get DPBC targets
            if step == "Step03_Vectorization":
                targets = data.get("outputs", {})
                
            # Get Champion stats per generation
            if step == "Step07_KDARanking":
                gen = data.get("generation")
                kda = data.get("outputs", {})
                winner_id = kda.get("overall_winner_mutation_id")
                
                # Find the winning evaluation
                for eval_obj in kda.get("evaluations", []):
                    if eval_obj.get("mutation_id") == winner_id:
                        generations.append(f"Gen {gen}")
                        overall_deltas.append(eval_obj.get("overall_delta"))
                        tone_scores.append(eval_obj.get("tone_score"))
                        conciseness_scores.append(eval_obj.get("conciseness_score"))
                        accuracy_scores.append(eval_obj.get("accuracy_score"))
                        break

    # HTML Template with Chart.js
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Evolutionary Engine Graphs</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: 'Inter', sans-serif; background-color: #0d1117; color: #c9d1d9; text-align: center; padding: 20px; }}
            .chart-container {{ width: 80%; margin: 40px auto; background: #161b22; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
            h1 {{ color: #58a6ff; }}
            h2 {{ color: #8b949e; }}
        </style>
    </head>
    <body>
        <h1>🧬 Evolutionary Trajectory (Email 1783)</h1>
        
        <div class="chart-container">
            <h2>Graph 1: Elo Error Delta over Generations (Lower is Better)</h2>
            <canvas id="deltaChart"></canvas>
        </div>

        <div class="chart-container">
            <h2>Graph 2: Parameter Convergence vs Seed Targets</h2>
            <canvas id="paramChart"></canvas>
        </div>

        <script>
            // Data Injection
            const labels = {json.dumps(generations)};
            const deltas = {json.dumps(overall_deltas)};
            
            const tone_scores = {json.dumps(tone_scores)};
            const tone_target = Array(labels.length).fill({targets.get('tone_target', 8.5)});
            
            const conciseness_scores = {json.dumps(conciseness_scores)};
            const conciseness_target = Array(labels.length).fill({targets.get('conciseness_target', 9.0)});
            
            const accuracy_scores = {json.dumps(accuracy_scores)};
            const accuracy_target = Array(labels.length).fill({targets.get('accuracy_target', 9.5)});

            // Graph 1: Overall Delta
            new Chart(document.getElementById('deltaChart'), {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [{{
                        label: 'Overall Error Delta (Elo)',
                        data: deltas,
                        borderColor: '#ff7b72',
                        backgroundColor: 'rgba(255, 123, 114, 0.2)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.3
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{ y: {{ beginAtZero: true, grid: {{ color: '#30363d' }} }}, x: {{ grid: {{ color: '#30363d' }} }} }},
                    plugins: {{ legend: {{ labels: {{ color: '#c9d1d9' }} }} }}
                }}
            }});

            // Graph 2: Parameter Convergence
            new Chart(document.getElementById('paramChart'), {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [
                        {{ label: 'Tone Score', data: tone_scores, borderColor: '#79c0ff', borderWidth: 2, tension: 0.1 }},
                        {{ label: 'Target Tone', data: tone_target, borderColor: '#79c0ff', borderDash: [5, 5], borderWidth: 1 }},
                        
                        {{ label: 'Conciseness Score', data: conciseness_scores, borderColor: '#d2a8ff', borderWidth: 2, tension: 0.1 }},
                        {{ label: 'Target Conciseness', data: conciseness_target, borderColor: '#d2a8ff', borderDash: [5, 5], borderWidth: 1 }},
                        
                        {{ label: 'Accuracy Score', data: accuracy_scores, borderColor: '#a5d6ff', borderWidth: 2, tension: 0.1 }},
                        {{ label: 'Target Accuracy', data: accuracy_target, borderColor: '#a5d6ff', borderDash: [5, 5], borderWidth: 1 }}
                    ]
                }},
                options: {{
                    responsive: true,
                    scales: {{ y: {{ beginAtZero: true, max: 10, grid: {{ color: '#30363d' }} }}, x: {{ grid: {{ color: '#30363d' }} }} }},
                    plugins: {{ legend: {{ labels: {{ color: '#c9d1d9' }} }} }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    with open(output_html, 'w') as f:
        f.write(html_content)
        
    print(f"Graphs successfully generated at {output_html}")

if __name__ == "__main__":
    generate_graphs()
