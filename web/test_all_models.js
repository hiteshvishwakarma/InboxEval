const { Groq } = require('groq-sdk');
const client = new Groq({apiKey: process.env.GROQ_API_KEY});

async function run() {
  const modelsResponse = await client.models.list();
  const textModels = modelsResponse.data
    .map(m => m.id)
    .filter(id => !id.includes('whisper') && !id.includes('guard') && !id.includes('compound') && !id.includes('orpheus'));
  
  console.log(`Testing ${textModels.length} models...`);
  
  for (const model of textModels) {
    try {
      const res = await client.chat.completions.create({
        model: model,
        messages: [{ role: "user", content: "You are an evaluator. Output ONLY a valid JSON object in a markdown block with a key 'score' set to 10. Example:\n```json\n{\"score\": 10}\n```" }],
        temperature: 0
      });
      const content = res.choices[0].message.content;
      const match = content.match(/\`\`\`json\s*(\{[\s\S]*?\})\s*\`\`\`/);
      const jsonStr = match ? match[1] : content;
      JSON.parse(jsonStr.trim());
      console.log(`[PASS] ${model}`);
    } catch (e) {
      console.log(`[FAIL] ${model} - Error: ${e.message}`);
    }
  }
}
run();
