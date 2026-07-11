import { NextResponse } from 'next/server';
import { Groq } from 'groq-sdk';
import { v4 as uuidv4 } from 'uuid';
import fs from 'fs';
import path from 'path';

const client = new Groq({ apiKey: process.env.GROQ_API_KEY });

const PARAMETERS = `1. instruction_adherence\n2. factual_accuracy\n3. professionalism\n4. tone_appropriateness\n5. human_likeness\n6. persona_adherence\n7. spam_safety\n8. deliverability\n9. formatting\n10. structure\n11. conciseness\n12. intent_clarity`;

export async function POST(req) {
  try {
    const { emailText } = await req.json();
    if (!emailText) return NextResponse.json({ error: "Email text is required" }, { status: 400 });

    // Multi-Agent Debate Protocol
    // Agent 1: The Harsh Critic
    const harshPromise = client.chat.completions.create({
      model: "qwen/qwen3-32b",
      messages: [
        { role: "system", content: `You are an extremely harsh AI critic. Evaluate this email on the following 12 parameters:\n${PARAMETERS}\nFocus entirely on flaws, robotic language, and structural errors. Output a 3-sentence critique.` },
        { role: "user", content: emailText }
      ]
    });

    // Agent 2: The Constructive Advocate
    const advocatePromise = client.chat.completions.create({
      model: "llama-3.1-8b-instant",
      messages: [
        { role: "system", content: `You are a constructive AI advocate. Evaluate this email on the following 12 parameters:\n${PARAMETERS}\nFocus on the strengths, intent clarity, and effective communication. Output a 3-sentence defense.` },
        { role: "user", content: emailText }
      ]
    });

    const [harshRes, advoRes] = await Promise.all([harshPromise, advocatePromise]);
    const harshCritique = harshRes.choices[0].message.content;
    const advocateDefense = advoRes.choices[0].message.content;

    // Agent 3: The Moderator (Final Scoring)
    const moderatorPrompt = `
You are the Executive Moderator. 
Read the Email, the Harsh Critique, and the Constructive Defense.
Synthesize the debate and issue the final, unbiased scores for all 12 parameters (1-10).

Email:
${emailText}

Harsh Critique:
${harshCritique}

Constructive Defense:
${advocateDefense}

Return ONLY a valid JSON object:
{
  "scorecard": {
    "instruction_adherence": 8,
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
    "intent_clarity": 10
  },
  "overall_score": 8.5,
  "reasoning": "Synthesized 2-sentence reasoning."
}
`;

    const finalCompletion = await client.chat.completions.create({
      model: "qwen/qwen3-32b",
      messages: [{ role: "user", content: moderatorPrompt }],
      response_format: { type: "json_object" },
      temperature: 0.1,
    });

    const result = JSON.parse(finalCompletion.choices[0].message.content);
    
    // Add Metadata & UUID for Shareable Evidence
    const evalId = uuidv4().slice(0,8); // Short ID for permalink
    const fullRecord = {
      id: evalId,
      timestamp: new Date().toISOString(),
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
