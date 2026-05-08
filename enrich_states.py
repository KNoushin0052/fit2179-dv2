"""
FIT2179 DV2 — AI-Powered Player State Enrichment
==================================================
This script uses the Anthropic API to automatically look up
the home state for each unknown MPL Malaysia player.

Run this on YOUR LAPTOP after scraper.py has finished.

Requirements:
    pip install anthropic pandas requests

Usage:
    python enrich_states.py
"""

import anthropic
import pandas as pd
import time
import json
import re
import requests
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────

DELAY = 1.5   # seconds between API calls

VALID_STATES = [
    "Johor", "Kedah", "Kelantan", "Melaka", "Negeri Sembilan",
    "Pahang", "Perak", "Perlis", "Pulau Pinang", "Sabah",
    "Sarawak", "Selangor", "Terengganu", "Kuala Lumpur",
    "Putrajaya", "Labuan", "Unknown"
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Helper: scrape player page for raw text ───────────────────────────────────

def get_player_page_text(player_ign):
    """Fetch the raw text from a player's Liquipedia page."""
    url = f"https://liquipedia.net/mobilelegends/{player_ign}"
    try:
        time.sleep(2)
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            # Get all text, focus on the main content area
            main = soup.find("div", class_="mw-parser-output")
            if main:
                return main.get_text(separator=" ", strip=True)[:3000]
        return ""
    except Exception:
        return ""


# ── Helper: ask Claude about a player ────────────────────────────────────────

def ask_claude_for_state(client, player_ign, real_name, page_text):
    """
    Ask Claude what Malaysian state this MPL player is from.
    Returns the state name string.
    """
    # Build context from page text if available
    context_block = ""
    if page_text:
        context_block = f"""
Here is the text from the player's Liquipedia page:
---
{page_text[:2000]}
---
"""

    prompt = f"""You are a knowledgeable Malaysian esports expert.

I need to find the home state (negeri) in Malaysia for this MPL Malaysia player:
- IGN (in-game name): {player_ign}
- Real name: {real_name if real_name != "Unknown" else "not known"}
{context_block}

Based on your knowledge of Malaysian MPL players, what Malaysian state is this player from?

You MUST respond with ONLY a JSON object in this exact format:
{{"state": "StateName", "confidence": "high/medium/low", "reason": "brief reason"}}

The state MUST be one of these exact values:
Johor, Kedah, Kelantan, Melaka, Negeri Sembilan, Pahang, Perak, Perlis, 
Pulau Pinang, Sabah, Sarawak, Selangor, Terengganu, Kuala Lumpur, Unknown

Use "Kuala Lumpur" for players from KL specifically.
Use "Selangor" for players from Shah Alam, Petaling Jaya, Subang, Klang, etc.
Use "Unknown" ONLY if you genuinely have no information about this player.

Respond with JSON only. No other text."""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text.strip()

        # Clean up response — sometimes model adds markdown
        response_text = re.sub(r"```json|```", "", response_text).strip()

        result = json.loads(response_text)
        state = result.get("state", "Unknown")
        confidence = result.get("confidence", "low")
        reason = result.get("reason", "")

        # Validate the state is in our allowed list
        if state not in VALID_STATES:
            # Try to fuzzy-match
            for valid in VALID_STATES:
                if valid.lower() in state.lower() or state.lower() in valid.lower():
                    state = valid
                    break
            else:
                state = "Unknown"

        return state, confidence, reason

    except (json.JSONDecodeError, Exception) as e:
        print(f"    ⚠️  API error for {player_ign}: {e}")
        return "Unknown", "low", "api_error"


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("FIT2179 DV2 — AI Player State Enrichment")
    print("=" * 60)

    # Load the raw dataset from scraper
    try:
        df = pd.read_csv("mpl_players_raw.csv")
        print(f"✅ Loaded mpl_players_raw.csv — {len(df)} rows")
    except FileNotFoundError:
        print("❌ mpl_players_raw.csv not found. Run scraper.py first.")
        exit(1)

    # Find unique players with Unknown state
    unknown_mask = df["home_state"] == "Unknown"
    unknown_players = df[unknown_mask].drop_duplicates("player_ign")[
        ["player_ign", "real_name", "liquipedia_url"]
    ].copy()

    print(f"🔍 Found {len(unknown_players)} unique players needing state lookup")
    print(f"   (Already known: {df[~unknown_mask]['player_ign'].nunique()} players)")

    if len(unknown_players) == 0:
        print("✅ All states already known! Nothing to enrich.")
        exit(0)

    # Init Anthropic client — API key auto-read from ANTHROPIC_API_KEY env var
    client = anthropic.Anthropic()

    print(f"\n🤖 Starting AI enrichment...")
    print(f"   Estimated time: ~{len(unknown_players) * 5 // 60} mins {len(unknown_players) * 5 % 60} secs\n")

    # Build lookup results
    lookup = {}  # player_ign → (state, confidence, reason)

    for i, row in unknown_players.iterrows():
        ign = row["player_ign"]
        real_name = row["real_name"]
        print(f"  [{list(unknown_players.index).index(i)+1}/{len(unknown_players)}] {ign} ({real_name})")

        # Step 1: Try to get page text for more context
        print(f"    → Fetching Liquipedia page...")
        page_text = get_player_page_text(ign)

        # Step 2: Ask Claude
        print(f"    → Asking AI...")
        state, confidence, reason = ask_claude_for_state(client, ign, real_name, page_text)

        lookup[ign] = (state, confidence, reason)

        icon = "✅" if state != "Unknown" else "❓"
        conf_icon = "🟢" if confidence == "high" else ("🟡" if confidence == "medium" else "🔴")
        print(f"    {icon} {conf_icon} {state} — {reason}")

        # Save progress every 10 players
        if (list(unknown_players.index).index(i) + 1) % 10 == 0:
            # Apply what we have so far
            df_temp = df.copy()
            for p_ign, (p_state, _, _) in lookup.items():
                df_temp.loc[df_temp["player_ign"] == p_ign, "home_state"] = p_state
            df_temp.to_csv("mpl_players_final.csv", index=False)
            print(f"\n  💾 Progress saved ({len(lookup)} players enriched so far)\n")

        time.sleep(DELAY)

    # Apply all results to the dataframe
    print("\n📊 Applying enrichment results...")
    df_enriched = df.copy()
    df_enriched["ai_confidence"] = "original"
    df_enriched["ai_reason"] = ""

    for ign, (state, confidence, reason) in lookup.items():
        mask = df_enriched["player_ign"] == ign
        df_enriched.loc[mask, "home_state"] = state
        df_enriched.loc[mask, "ai_confidence"] = confidence
        df_enriched.loc[mask, "ai_reason"] = reason

    # Save final output
    df_enriched.to_csv("mpl_players_final.csv", index=False)

    # Print summary
    total = len(df_enriched)
    known = len(df_enriched[df_enriched["home_state"] != "Unknown"])
    still_unknown = total - known
    unique_known = df_enriched[df_enriched["home_state"] != "Unknown"]["player_ign"].nunique()

    print("\n" + "=" * 60)
    print("✅ ENRICHMENT COMPLETE!")
    print(f"   Total rows:           {total}")
    print(f"   States now known:     {known} rows ({known/total*100:.0f}%)")
    print(f"   Unique players known: {unique_known}")
    print(f"   Still unknown:        {still_unknown}")
    print(f"\n📄 Final file: mpl_players_final.csv")

    # Print state distribution
    print("\n🗺️  Unique players by state:")
    state_dist = (
        df_enriched[df_enriched["home_state"] != "Unknown"]
        .drop_duplicates("player_ign")
        .groupby("home_state")
        .size()
        .sort_values(ascending=False)
    )
    national_avg = state_dist.mean()
    for state, count in state_dist.items():
        bar = "█" * count
        flag = " ← inequality visible here" if count >= 10 else ""
        print(f"   {state:<22} {bar} ({count}){flag}")

    print(f"\n   National avg: {national_avg:.1f} players per state")

    # Alert about confidence
    low_conf = [(ign, s) for ign, (s, c, _) in lookup.items() if c == "low" and s != "Unknown"]
    if low_conf:
        print(f"\n⚠️  {len(low_conf)} players have LOW confidence — consider verifying:")
        for ign, state in low_conf:
            print(f"   {ign} → {state}")

    print("\n🎉 You're ready to build Vega-Lite charts!")
    print("   Next: download broadband data from data.gov.my")