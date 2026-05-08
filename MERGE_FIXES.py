"""
FIT2179 DV2 — Merge Manual Fixes Back into Main Dataset
=========================================================
Run this AFTER:
  1. scraper.py has finished
  2. You've filled in home_state in mpl_players_unknown.csv

Usage:
    python merge_fixes.py
"""

import pandas as pd

# Load main dataset
df_main = pd.read_csv("mpl_players_raw.csv")

# Load the manually fixed unknowns
df_fixes = pd.read_csv("mpl_players_unknown.csv")

if "home_state" not in df_fixes.columns:
    print("⚠️  Warning: The 'home_state' column is missing from 'mpl_players_unknown.csv'.")
    print("    No manual fixes will be applied. To apply fixes, add the 'home_state' column to the CSV.")
    fixes_lookup = {}
else:
    # Build a lookup dict: player_ign → home_state
    fixes_lookup = df_fixes.set_index("player_ign")["home_state"].to_dict()

# Apply fixes to main dataset
def apply_fix(row):
    if row["home_state"] == "Unknown" and row["player_ign"] in fixes_lookup:
        state = fixes_lookup[row["player_ign"]]
        if pd.notna(state) and state.strip() != "":
            return state
    return row["home_state"]

df_main["home_state"] = df_main.apply(apply_fix, axis=1)

# Save final clean dataset
df_main.to_csv("mpl_players_final.csv", index=False)

# Print summary
total = len(df_main)
known = len(df_main[df_main["home_state"] != "Unknown"])
still_unknown = total - known

print("✅ Merge complete!")
print(f"   Total rows:          {total}")
print(f"   State known:         {known} ({known/total*100:.0f}%)")
print(f"   Still unknown:       {still_unknown}")
print(f"\n📄 Final file: mpl_players_final.csv")

# Preview state distribution
print("\n🗺️  Players by state:")
state_counts = df_main[df_main["home_state"] != "Unknown"].groupby("home_state")["player_ign"].nunique().sort_values(ascending=False)
for state, count in state_counts.items():
    bar = "█" * count
    print(f"   {state:<20} {bar} ({count})")