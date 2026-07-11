import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function POST(req) {
  try {
    const body = await req.json();
    const { email_text, prompt, available_models } = body;

    if (!email_text) {
      return NextResponse.json({ error: "Email text is required" }, { status: 400 });
    }

    if (!available_models || available_models.length === 0) {
      return NextResponse.json({ error: "No active models available for routing" }, { status: 400 });
    }

    const textLength = email_text.length + (prompt ? prompt.length : 0);
    const combinedText = (email_text + " " + (prompt || "")).toLowerCase();

    // Heuristic 1: Detect high-complexity domains
    const highComplexityKeywords = ["legal", "contract", "financial", "compliance", "policy", "lawyer", "law", "sue", "penalty", "gdpr", "audit", "investigation"];
    const hasHighComplexity = highComplexityKeywords.some(keyword => combinedText.includes(keyword));

    // Determine target size requirement based on heuristics
    let targetSize = "medium";
    let reasoning = "";

    if (hasHighComplexity || textLength > 2000) {
      targetSize = "large";
      reasoning = hasHighComplexity 
        ? "High contextual complexity detected (Corporate/Legal/Financial semantics). Routing to a Heavyweight reasoning model."
        : "Massive context payload detected. Routing to a Heavyweight model with a larger context window.";
    } else if (textLength < 300) {
      targetSize = "small";
      reasoning = "Short, casual communication detected. Routing to a high-speed Lightweight model for maximum efficiency.";
    } else {
      targetSize = "medium";
      reasoning = "Standard enterprise communication detected. Routing to a balanced Midweight model.";
    }

    // Parse models and categorize them by parameter size
    const categorizedModels = { large: [], medium: [], small: [] };
    
    available_models.forEach(model => {
      const match = model.match(/(\d+(?:\.\d+)?)b/i);
      const size = match ? parseFloat(match[1]) : 0;
      
      if (size >= 70) categorizedModels.large.push(model);
      else if (size >= 20) categorizedModels.medium.push(model);
      else categorizedModels.small.push(model);
    });

    // Fallback logic if the target category is empty
    let selectedModel = null;
    if (targetSize === "large" && categorizedModels.large.length > 0) {
      selectedModel = categorizedModels.large[0];
    } else if ((targetSize === "medium" || targetSize === "large") && categorizedModels.medium.length > 0) {
      selectedModel = categorizedModels.medium[0];
      if (targetSize === "large") reasoning += " (Fallback: Heavyweight unavailable, using Midweight)";
    } else if (categorizedModels.small.length > 0) {
      selectedModel = categorizedModels.small[0];
    } else {
      selectedModel = available_models[0]; // Absolute fallback
    }

    return NextResponse.json({
      selected_model: selectedModel,
      reasoning: reasoning
    });

  } catch (error) {
    console.error("Routing Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
