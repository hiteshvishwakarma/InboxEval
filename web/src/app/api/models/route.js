import { NextResponse } from 'next/server';
import { Groq } from 'groq-sdk';

const client = new Groq({ apiKey: process.env.GROQ_API_KEY });

export async function GET() {
  try {
    const modelsResponse = await client.models.list();
    // Filter out audio models and guard models
    const textModels = modelsResponse.data
      .map(m => m.id)
      .filter(id => !id.includes('whisper') && !id.includes('guard') && !id.includes('compound') && !id.includes('orpheus'));
      
    return NextResponse.json(textModels);
  } catch (error) {
    console.error("Models Error:", error);
    return NextResponse.json({ error: "Failed to fetch models" }, { status: 500 });
  }
}
