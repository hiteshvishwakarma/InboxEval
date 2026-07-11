import { NextResponse } from 'next/server';
import { Groq } from 'groq-sdk';
import { v4 as uuidv4 } from 'uuid';
import fs from 'fs';
import path from 'path';

const client = new Groq({ apiKey: process.env.GROQ_API_KEY });

const FULL_PARAMETERS = `1. instruction_adherence\n2. factual_accuracy\n3. professionalism\n4. tone_appropriateness\n5. human_likeness\n6. persona_adherence\n7. spam_safety\n8. deliverability\n9. formatting\n10. structure\n11. conciseness\n12. intent_clarity`;

const STATIC_PARAMETERS = `1. professionalism\n2. tone_appropriateness\n3. human_likeness\n4. spam_safety\n5. deliverability\n6. formatting\n7. structure\n8. conciseness\n9. clarity`;

export async function POST(req) {
  try {
    let { promptText, emailText, judgeModel } = await req.json();
    if (!emailText) return NextResponse.json({ error: "Email text is required" }, { status: 400 });
    const selectedJudge = judgeModel || "qwen/qwen3-32b";

    const isBlindMode = !promptText || promptText.trim() === "";
    const activeParams = isBlindMode ? STATIC_PARAMETERS : FULL_PARAMETERS;

    // Dynamic Back-Translation (Reverse Engineering) if prompt is missing
    if (!promptText || promptText.trim() === "") {
      const backTranslation = await client.chat.completions.create({
        model: "llama-3.1-8b-instant",
        temperature: 0,
        messages: [
          { role: "system", content: "You are an expert reverse-engineer. Read the email and deduce the exact prompt/instructions that would have generated it. Output ONLY the prompt." },
          { role: "user", content: emailText }
        ]
      });
      promptText = backTranslation.choices[0].message.content;
    }

    // Multi-Agent Debate Protocol
    // Agent 1: The Harsh Critic
    const harshPromise = client.chat.completions.create({
      model: "qwen/qwen3-32b",
      temperature: 0,
      messages: [
        { role: "system", content: `You are an extremely harsh AI critic. Evaluate this email on the following parameters:\n${activeParams}\nFocus entirely on flaws, robotic language, and structural errors. Output a 3-sentence critique.` },
        { role: "user", content: isBlindMode ? `Generated Email:\n${emailText}` : `Original Prompt Given to AI:\n${promptText}\n\nGenerated Email:\n${emailText}` }
      ]
    });

    // Agent 2: The Constructive Advocate
    const advocatePromise = client.chat.completions.create({
      model: "llama-3.1-8b-instant",
      temperature: 0,
      messages: [
        { role: "system", content: `You are a constructive AI advocate. Evaluate this email on the following parameters:\n${activeParams}\nFocus on strengths and effective communication. Output a 3-sentence defense.` },
        { role: "user", content: isBlindMode ? `Generated Email:\n${emailText}` : `Original Prompt Given to AI:\n${promptText}\n\nGenerated Email:\n${emailText}` }
      ]
    });

    const [harshRes, advoRes] = await Promise.all([harshPromise, advocatePromise]);
    const harshCritique = harshRes.choices[0].message.content;
    const advocateDefense = advoRes.choices[0].message.content;

// Agent 3: The Moderator (Final Scoring)
    const moderatorPrompt = `
You are the Executive Moderator. 
Read the ${isBlindMode ? "Generated Email" : "Original Prompt, the Generated Email"}, the Harsh Critique, and the Constructive Defense.
Synthesize the debate and issue the final, unbiased scores for all parameters (1-10).

${isBlindMode ? "" : `Original Prompt:\n${promptText}\n\n`}Generated Email:
${emailText}

Harsh Critique:
${harshCritique}

Constructive Defense:
${advocateDefense}

Return ONLY a valid JSON object:
{
  "scorecard": {
    ${isBlindMode ? `"professionalism": 10,
    "tone_appropriateness": 8,
    "human_likeness": 7,
    "spam_safety": 10,
    "deliverability": 10,
    "formatting": 9,
    "structure": 8,
    "conciseness": 7,
    "clarity": 10` : `"instruction_adherence": 8,
    "factual_accuracy": 9,
    "professionalism": 10,
    "tone_appropriateness": 8,
    "human_likeness": 7,
    "persona_adherence": 9,
    "spam_safety": 10,
    "deliverability": 10,
    "formatting": 9,
    "structure": 8,
    "conciseness": 7,
    "intent_clarity": 10`}
  },
  "overall_score": 8.5,
  "reasoning": "Synthesized 2-sentence reasoning."
}
`;

    const finalCompletion = await client.chat.completions.create({
      model: selectedJudge,
      messages: [{ role: "user", content: moderatorPrompt }],
      response_format: { type: "json_object" },
      temperature: 0,
    });

    const result = JSON.parse(finalCompletion.choices[0].message.content);
    
    // Add Metadata & UUID for Shareable Evidence
    const evalId = uuidv4().slice(0,8); // Short ID for permalink
    const fullRecord = {
      id: evalId,
      timestamp: new Date().toISOString(),
      prompt_text: promptText,
      email_text: emailText,
      debate: {
        critic: harshCritique,
        advocate: advocateDefense
      },
      ...result
    };

    // Save to Disk
    const savePath = path.join(process.cwd(), '../data/evals', `${evalId}.json`);
    fs.writeFileSync(savePath, JSON.stringify(fullRecord, null, 2));

    return NextResponse.json({ id: evalId, debate: fullRecord.debate, ...result });
  } catch (error) {
    console.error("Evaluation Error:", error);
    return NextResponse.json({ error: "Failed to evaluate email" }, { status: 500 });
  }
}
