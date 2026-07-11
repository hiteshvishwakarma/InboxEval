import { NextResponse } from 'next/server';
import { Groq } from 'groq-sdk';

const client = new Groq({
  apiKey: process.env.GROQ_API_KEY,
});

const EVALUATOR_PROMPT = `
You are an elite, world-class AI Email Evaluator.
Your job is to strictly evaluate the following email on 12 industry-standard parameters.
Score each parameter from 1 to 10 (10 being perfect). Be extremely critical.

Parameters:
1. instruction_adherence
2. factual_accuracy
3. professionalism
4. tone_appropriateness
5. human_likeness
6. persona_adherence
7. spam_safety
8. deliverability
9. formatting
10. structure
11. conciseness
12. intent_clarity

Return ONLY a valid JSON object in this exact schema:
{
  "scorecard": {
    "instruction_adherence": 10,
    "factual_accuracy": 9,
    ...
  },
  "overall_score": 9.5,
  "reasoning": "A brief, highly critical 2-sentence explanation of the score."
}
`;

export async function POST(req) {
  try {
    const { emailText } = await req.json();

    if (!emailText) {
      return NextResponse.json({ error: "Email text is required" }, { status: 400 });
    }

    const completion = await client.chat.completions.create({
      model: "qwen/qwen3-32b",
      messages: [
        { role: "system", content: EVALUATOR_PROMPT },
        { role: "user", content: `Evaluate this email:\n\n${emailText}` }
      ],
      response_format: { type: "json_object" },
      temperature: 0.1,
    });

    const result = JSON.parse(completion.choices[0].message.content);

    return NextResponse.json(result);
  } catch (error) {
    console.error("Evaluation Error:", error);
    return NextResponse.json({ error: "Failed to evaluate email" }, { status: 500 });
  }
}
