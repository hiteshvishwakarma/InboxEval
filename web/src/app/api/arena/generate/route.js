import { NextResponse } from 'next/server';
import { Groq } from 'groq-sdk';

export const dynamic = 'force-dynamic';

const client = new Groq({ apiKey: process.env.GROQ_API_KEY });

export async function POST(req) {
  try {
    const { prompt, available_models } = await req.json();

    if (!available_models || available_models.length < 2) {
      return NextResponse.json({ error: "Not enough models available for Arena" }, { status: 400 });
    }

    // Pick 2 random unique models
    const shuffled = [...available_models].sort(() => 0.5 - Math.random());
    const modelA = shuffled[0];
    const modelB = shuffled[1];

    const generateEmail = async (modelId) => {
      try {
        const response = await client.chat.completions.create({
          model: modelId,
          messages: [{ role: "user", content: prompt }],
          temperature: 0.7, // Higher temp for more natural/variable writing in the arena
          max_tokens: 1000
        });
        return response.choices[0].message.content;
      } catch (e) {
        console.error(`Error generating for ${modelId}:`, e);
        return "ERROR: Model failed to generate response.";
      }
    };

    const [textA, textB] = await Promise.all([
      generateEmail(modelA),
      generateEmail(modelB)
    ]);

    return NextResponse.json({
      modelA,
      modelB,
      textA,
      textB
    });

  } catch (error) {
    console.error("Arena Generate Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
