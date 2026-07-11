import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

const ELO_K = 32;

function calculateElo(ratingA, ratingB, scoreA) {
  const expectedA = 1 / (1 + Math.pow(10, (ratingB - ratingA) / 400));
  const newRatingA = ratingA + ELO_K * (scoreA - expectedA);
  const newRatingB = ratingB + ELO_K * ((1 - scoreA) - (1 - expectedA));
  return [newRatingA, newRatingB];
}

export async function POST(req) {
  try {
    const { modelA, modelB, winner, timeToVoteMs, approxTokens } = await req.json();

    // 1. Read Velocity Filter (Telemetry & Calibration)
    // Assume average human reading speed is ~250 words/min = ~4 words/sec = ~5 tokens/sec
    // But humans skim. Let's set a strict minimum: 1.5 seconds flat, OR less than 50ms per token.
    let isSpam = false;
    let feedbackMsg = "Vote recorded successfully.";

    if (timeToVoteMs < 1500) {
      isSpam = true;
      feedbackMsg = "Vote ignored: Time-to-Vote velocity filter triggered (Impossible read speed detected).";
    }

    const dataPath = path.join(process.cwd(), '../data/arena_elo.json');
    let eloData = {};
    if (fs.existsSync(dataPath)) {
      eloData = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
    }

    if (!eloData[modelA]) eloData[modelA] = { elo: 1000, matches: 0 };
    if (!eloData[modelB]) eloData[modelB] = { elo: 1000, matches: 0 };

    if (!isSpam) {
      let scoreA = 0.5; // Tie
      if (winner === 'A') scoreA = 1;
      else if (winner === 'B') scoreA = 0;

      const [newA, newB] = calculateElo(eloData[modelA].elo, eloData[modelB].elo, scoreA);

      eloData[modelA].elo = newA;
      eloData[modelA].matches += 1;
      
      eloData[modelB].elo = newB;
      eloData[modelB].matches += 1;

      fs.writeFileSync(dataPath, JSON.stringify(eloData, null, 2));
    }

    return NextResponse.json({
      success: true,
      isSpam,
      feedback: feedbackMsg,
      newEloA: eloData[modelA]?.elo,
      newEloB: eloData[modelB]?.elo
    });

  } catch (error) {
    console.error("Arena Vote Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
