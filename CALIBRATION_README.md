# Calibration & Golden Dataset Manual Review Guide

This document outlines the step-by-step process for manually calibrating the Golden Dataset using our granular, 12-parameter matrix.

## The Standardized Grading Scale (1-10)
Every single parameter is graded on a scale of 1 to 10. 
- **10 is always the BEST/MOST OPTIMAL score.**
- **1 is always the WORST/MOST HARMFUL score.**

Use the milestone rubrics below. If an email falls between two milestones (e.g., better than a 5, but not quite a 7), assign it an even number (6).

### 🧠 The Dynamic Persona-Driven Baseline
**Crucial Grading Note:** The 1-10 scale is an absolute measurement scale. A "10" means *robotic, mathematical perfection* (e.g., flawless formatting, extreme conciseness). 
However, **a universal "human average" does not exist.** The ideal target score is highly subjective and depends entirely on the specific *Persona* and context requested in the prompt. 
For example, a senior corporate lawyer in New York will have a vastly different baseline for "Professionalism" and "Formatting" compared to a 22-year-old freelance graphic designer in Brazil. 
When you manually grade the dataset, you are establishing the baseline for that **specific demographic and context**. If a prompt asks for a casual marketing email, the target benchmark for Professionalism might legitimately be a 5. You are the arbiter of what the baseline should be for the specific persona in each prompt. Later, our AI Engine will be calibrated to hit these dynamic, persona-driven targets rather than striving for a universal, synthetic "10".

---

## The 12 Core Evaluation Parameters (Milestone Rubrics)

### 1. Instruction Adherence
*Did it follow all explicit and implicit constraints?*
- **10**: Followed every instruction perfectly without missing a single detail.
- **7**: Followed all major instructions, but missed a minor formatting or implicit constraint.
- **5**: Followed about half the instructions; missed key requirements.
- **3**: Barely addressed the prompt, went off on a tangent.
- **1**: Completely ignored the core prompt.

### 2. Factual Accuracy (Anti-Hallucination)
*Did it invent fake details not present in the context?*
- **10**: Zero hallucinations; strictly adhered to provided facts.
- **7**: Mostly factual, but added minor harmless filler details.
- **5**: Added a specific detail (like a fake date or name) that wasn't requested.
- **3**: Heavily hallucinated multiple core facts.
- **1**: The entire email is based on fabricated information.

### 3. Professionalism
*Is the language suitable for a workplace environment?*
- **10**: Highly professional, respectful, and polished.
- **7**: Professional, but slightly casual.
- **5**: Too casual for a formal email (e.g., using slang like "gonna", "tbh").
- **3**: Disrespectful or highly unprofessional.
- **1**: Contains profanity or severely inappropriate language.

### 4. Tone Appropriateness
*Did it match the requested emotion (e.g., urgent, empathetic, stern)?*
- **10**: Perfectly nailed the exact requested emotion.
- **7**: Captured the general mood, but could be stronger.
- **5**: Neutral tone; failed to express the requested emotion.
- **3**: Expressed the opposite of the requested tone (e.g., happy instead of serious).
- **1**: Tone is wildly inappropriate for the scenario (e.g., mocking a customer complaint).

### 5. Human Likeness
*Does it sound like a real person wrote it, avoiding obvious AI tells?*
- **10**: Completely indistinguishable from a human. Uses natural layman terms and phrasing.
- **7**: Sounds human, but slightly rigid.
- **5**: Sounds like a template. Uses some AI jargon ("I hope this email finds you well").
- **3**: Obvious AI generation ("As an AI language model...", highly robotic vocabulary).
- **1**: Completely synthetic and robotic; no human would ever write this way.

### 6. Persona Adherence
*Did it match the demographic, role, company, or region requested?*
- **10**: Perfect stylistic match. Uses correct regional dialect, industry jargon, and role perspective.
- **7**: Adopted the persona generally, but missed subtle stylistic nuances.
- **5**: Mentioned the persona (e.g., "I am a manager") but didn't write like one.
- **3**: Completely missed the persona; sounded generic.
- **1**: Broke character entirely.

### 7. Spam Safety
*Does it use spam trigger words that would alert filters?*
- **10**: Completely safe. Natural language.
- **7**: Mostly safe, but uses a few salesy words (e.g., "discount").
- **5**: Borderline. Uses words like "urgent" or "act now".
- **3**: High risk. Uses all caps, excessive exclamation points, or "FREE".
- **1**: Blatant spam ("CLICK HERE FOR FREE MONEY!!!").

### 8. Deliverability
*Technical safety (links, HTML).*
- **10**: Clean text or safe, verified links.
- **7**: Contains links, but they look normal.
- **5**: Contains too many links or slight formatting issues.
- **3**: Contains sketchy or hidden links.
- **1**: Contains known malicious patterns or broken HTML that will bounce.

### 9. Formatting
*Visual presentation (paragraphs, bullet points).*
- **10**: Visually beautiful. Great use of whitespace, paragraphs, and bullet points.
- **7**: Good formatting, easy to read.
- **5**: A bit dense. Could use more line breaks.
- **3**: Very hard to read. Poor line breaks.
- **1**: A single, massive block of unreadable text.

### 10. Structure
*Logical flow.*
- **10**: Perfect flow (Greeting -> Context -> Call to Action -> Sign-off).
- **7**: Good flow, but maybe the Call to Action is slightly buried.
- **5**: Missing a standard structural element (e.g., no greeting or no sign-off).
- **3**: Highly disjointed; thoughts jump around randomly.
- **1**: Complete structural chaos.

### 11. Conciseness
*Respecting the reader's time.*
- **10**: Perfectly succinct. Not a single wasted word.
- **7**: Mostly concise, slightly wordy in one paragraph.
- **5**: A bit long-winded; could be cut down by 30%.
- **3**: Highly repetitive and overly verbose.
- **1**: Rambles endlessly; buries the point in paragraphs of fluff.

### 12. Intent Clarity
*How obvious is the purpose of the email?*
- **10**: The recipient instantly knows exactly what they need to do after reading the first sentence.
- **7**: The goal is clear, but takes a few sentences to get to.
- **5**: The reader has to hunt for the action item.
- **3**: Very confusing; the reader might not know what to reply with.
- **1**: Completely incoherent intent.

---

## Step-by-Step Calibration Workflow
1. Open `data/golden_dataset.json`.
2. Read the `context` and `prompt`.
3. For each generated email, use the 1-10 milestone rubrics above to fill in the `expected_scores` JSON object.
