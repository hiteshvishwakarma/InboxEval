# Llama 3.3 Calibration Report

This report summarizes the average discrepancies (Deltas) between **your manual human scores** and **the AI Judge's scores** across all 30 emails (10 Human Baselines, 10 Hallucination Edge Cases, and 10 Spam Edge Cases) in the Golden Dataset.

### How to Read Deltas
*   **Negative Delta (`-`)**: The AI is too **harsh** (it scored the parameter lower than you did).
*   **Positive Delta (`+`)**: The AI is too **lenient** (it scored the parameter higher than you did).
*   **Zero Delta (`0`)**: The AI perfectly matches your human intuition.

---

### Key Biases Identified

#### 1. The AI is Too Harsh On:
| Parameter | Avg Delta | Analysis |
| :--- | :--- | :--- |
| **Human Likeness** | `-1.20` | The AI struggles to recognize human nuance. It heavily penalizes brief, terse, or informal emails because it expects "human" to mean "conversational" and "chatty". |
| **Professionalism** | `-1.10` | The AI expects highly formal, corporate language. It penalizes emails to dogs or friends for being "unprofessional", failing to recognize casual contexts. |
| **Intent Clarity** | `-1.00` | The AI expects intent to be explicitly spelled out (e.g., "The purpose of this email is..."). It struggles to infer intent from natural human subtext. |
| **Structure** | `-0.53` | The AI expects traditional email structure (greeting, body, sign-off). It penalizes list-based or concise formats. |
| **Tone Appropriateness** | `-0.43` | The AI has slight trouble matching tone to the `target_persona`, skewing slightly too strict. |

#### 2. The AI is Too Lenient On:
| Parameter | Avg Delta | Analysis |
| :--- | :--- | :--- |
| **Deliverability** | `+0.80` | The AI is too forgiving of Spam edge cases, assuming they will reach the inbox when they likely wouldn't. |
| **Formatting** | `+0.67` | The AI likes its own generated text blocks and scores them high, even if a human would find the formatting clunky. |
| **Instruction Adherence**| `+0.57` | The AI is slightly too forgiving of hallucinations, sometimes believing the hallucinated text was part of the original prompt's instructions. |
| **Persona Adherence** | `+0.37` | The AI tends to assume the generated email matches the persona a bit too easily. |

#### 3. Highly Calibrated (Near Perfect Match):
| Parameter | Avg Delta | Analysis |
| :--- | :--- | :--- |
| **Spam Safety** | `-0.10` | The AI's spam detection algorithm perfectly aligns with your manual scores. |
| **Conciseness** | `-0.10` | The AI accurately judges the length and brevity of the emails. |
| **Factual Accuracy** | `-0.13` | The AI is excellent at detecting facts against the provided `context`. |

---

### Next Steps for Phase 2

To fix these biases and achieve a perfect World-Class Evaluation Framework, we need to **Prompt Engineer the Judge**. 

Right now, our `dynamic_evals.py` has a very basic instruction:
> *"Grade this email strictly based on our 12 parameters..."*

To fix the `-1.20` bias on `human_likeness`, we would update the prompt to say:
> *"For Human Likeness: Remember that humans are often terse, informal, or use lists. Do not penalize an email for lacking conversational filler if the Target Persona is analytical."*

By feeding these delta insights back into the judge's prompt, we mathematically align the AI with your brain.
