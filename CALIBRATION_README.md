# Calibration & Golden Dataset Manual Review Guide

This document outlines the step-by-step process for manually calibrating the Golden Dataset. 

Since you (the human expert) are establishing the ground truth, we are not just grading emails as "Good" or "Bad". We are evaluating them across a strict, multi-dimensional matrix. The more precise your manual scores are, the more precise the AI Evaluator Engine will become when we calibrate it against your scores.

## The 6 Core Evaluation Parameters

When you open `data/golden_dataset.json`, you must review every email variation (the baseline, the hallucination, the spam) against these 6 parameters:

1. **Instruction Adherence (Score 1-10):**
   - *10*: Followed every single instruction perfectly (explicit and implicit).
   - *1*: Completely ignored the prompt.
2. **Hallucination Level (Score 1-10):**
   - *10*: Highly hallucinated (invented fake meetings, names, or prices not in the context).
   - *1*: Zero hallucinations; strictly adhered to provided facts.
3. **Tone Professionalism (Score 1-10):**
   - *10*: Perfectly polite, professional, and empathetic.
   - *1*: Rude, aggressive, or completely inappropriate.
4. **Deliverability & Spam Risk (Low / Medium / High):**
   - *High*: Contains obvious spam triggers ("CLICK HERE", "FREE MONEY", all caps).
   - *Low*: Natural, human-like language that will pass spam filters.
5. **Formatting & Structure (Score 1-10):**
   - *10*: Perfect email structure (Greeting -> Context -> Call to Action -> Sign-off).
   - *1*: A giant, unreadable block of text.
6. **Conciseness (Score 1-10):**
   - *10*: Gets straight to the point without fluff.
   - *1*: Rambles endlessly before making a point.

---

## Step-by-Step Calibration Workflow

### Step 1: Open the Dataset
Navigate to `data/golden_dataset.json` in your IDE.

### Step 2: Read the Context & Prompt
For every entry, read the `context` and the `prompt`. You MUST understand what the AI was instructed to do before you can grade it.

### Step 3: Grade the Variations
For each email variation inside the `edge_cases` object, you will see the generated email text. Add or update the expected scores based on the 6 parameters above. 

*Example of a fully calibrated edge case:*
```json
"spam_and_toxicity": {
    "email_text": "URGENT!!! SEND ME THE REPORT NOW OR YOU ARE FIRED!!!",
    "expected_scores": {
        "instruction_adherence": 2,
        "hallucination": 1,
        "tone_professionalism": 1,
        "spam_risk": "High",
        "formatting": 2,
        "conciseness": 8
    }
}
```

### Step 4: Lock the Dataset
Once you have reviewed and filled in these granular scores for the dataset, the Golden Dataset is officially "Locked". 

### Step 5: Engine Calibration (The Next Phase)
In the next step, we will run our `engine.py` against these emails. If our AI Engine gives an email a "Tone: 8", but your Golden Dataset says "Tone: 1", we know our Engine's prompt is flawed, and we will tweak the Engine until its scores match your Golden scores perfectly.
