import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const dataPath = path.join(process.cwd(), '../data/leaderboard_results.json');
    if (!fs.existsSync(dataPath)) {
      return NextResponse.json([]);
    }
    
    const fileContents = fs.readFileSync(dataPath, 'utf8');
    const rawData = JSON.parse(fileContents);
    
    const leaderboard = [];
    
    for (const [model, prompts] of Object.entries(rawData)) {
      let count = 0;
      let totalScore = 0;
      let paramScores = {};
      
      prompts.forEach(p => {
        const scores = Object.entries(p.scorecard).filter(([k, v]) => typeof v === 'number');
        if (scores.length > 0) {
          let promptTotal = 0;
          scores.forEach(([key, val]) => {
            promptTotal += val;
            paramScores[key] = (paramScores[key] || 0) + val;
          });
          totalScore += promptTotal / scores.length;
          count++;
        }
      });
      
      const finalScore = count > 0 ? (totalScore / count) : 0;
      
      // Compute averages for each parameter
      const averagedParams = {};
      if (count > 0) {
        Object.entries(paramScores).forEach(([key, total]) => {
          averagedParams[key] = total / count;
        });
      }
      
      // Determine size heuristically based on the name
      let parameters = "Unknown";
      if (model.toLowerCase().includes("8b")) parameters = "8B";
      if (model.toLowerCase().includes("17b")) parameters = "17B";
      if (model.toLowerCase().includes("27b")) parameters = "27B";
      if (model.toLowerCase().includes("32b")) parameters = "32B";
      if (model.toLowerCase().includes("70b")) parameters = "70B";
      if (model.toLowerCase().includes("120b")) parameters = "120B";
      
      leaderboard.push({
        model,
        score: finalScore,
        parameters,
        type: "Open Source",
        paramScores: averagedParams
      });
    }
    
    // Sort descending by score
    leaderboard.sort((a, b) => b.score - a.score);
    
    // Add rank
    leaderboard.forEach((item, index) => {
      item.rank = index + 1;
    });

    return NextResponse.json(leaderboard);
  } catch (error) {
    console.error(error);
    return NextResponse.json({ error: "Failed to load leaderboard data." }, { status: 500 });
  }
}
