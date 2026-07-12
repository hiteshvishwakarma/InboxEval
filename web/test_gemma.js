const { Groq } = require('groq-sdk');
const client = new Groq({apiKey: process.env.GROQ_API_KEY});

async function run() {
  const models = ['gemma2-9b-it', 'mixtral-8x7b-32768', 'llama3-8b-8192', 'llama3-70b-8192'];
  for (const model of models) {
    try {
      const res = await client.chat.completions.create({
        model: model,
        messages: [{ role: "user", content: "Hi" }]
      });
      console.log(`[PASS] ${model}`);
    } catch (e) {
      console.log(`[FAIL] ${model} - Error: ${e.message}`);
    }
  }
}
run();
