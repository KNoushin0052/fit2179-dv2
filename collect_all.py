"""
FIT2179 DV2 — Automated Data Collection (Fixed & Reliable)
============================================================
Collects ALL data needed for your visualisation automatically.

What this collects:
  1. MPL Malaysia season prize tables (Liquipedia)     → mpl_teams.csv
  2. M-Series World Championship results (Liquipedia)  → mpl_worlds.csv
  3. Broadband penetration by state (data.gov.my API)  → broadband_by_state.csv
  4. Derives summary files                             → mpl_state_summary.csv
                                                       → mpl_season_meta.csv

Requirements:
    pip install requests beautifulsoup4 pandas

Run on YOUR LAPTOP:
    python collect_all.py
"""

import requests
import time
import re
import pandas as pd
from bs4 import BeautifulSoup

# ── Config ─────────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
BASE  = "https://liquipedia.net"
DELAY = 3.0   # seconds — be polite

# Seasons to collect
SEASONS = {
    11: (2023, "S1"), 12: (2023, "S2"),
    13: (2024, "S1"), 14: (2024, "S2"),
    15: (2025, "S1"), 16: (2025, "S2"),
}

# Known team headquarters — verified from Liquipedia team pages
# Used to add team_state column
TEAM_STATE = {
    "srg":             "Selangor",
    "selangor":        "Selangor",
    "todak":           "Johor",
    "cg esports":      "Selangor",
    "homeBois":        "Selangor",
    "homebois":        "Selangor",
    "aero":            "Selangor",
    "monster":         "Kuala Lumpur",
    "team vamos":      "Selangor",
    "untitled":        "Kuala Lumpur",
    "team rey":        "Selangor",
    "kelantan":        "Kelantan",
    "penang":          "Pulau Pinang",
    "sabah":           "Sabah",
    "sarawak":         "Sarawak",
    "johor":           "Johor",
    "kedah":           "Kedah",
    "geek fam":        "Kuala Lumpur",
    "team smg":        "Selangor",
    "7th heaven":      "Selangor",
    "axis":            "Selangor",
    "ampverse":        "Kuala Lumpur",
}

M_WORLDS = [
    ("M1", 2021), ("M2", 2022), ("M3", 2022),
    ("M4", 2023), ("M5", 2023), ("M6", 2024), ("M7", 2025),
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def fetch(url):
    time.sleep(DELAY)
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"    ⚠️  Could not fetch {url}: {e}")
        return None


def match_state(team_name):
    """Map a team name to its headquarters state."""
    name_lower = team_name.lower()
    for keyword, state in TEAM_STATE.items():
        if keyword in name_lower:
            return state
    return "Unknown"


def clean_prize(text):
    """Extract integer prize from text like '$31,900' or 'USD 31,900'."""
    m = re.search(r'[\$\s]*([\d,]+)', text.replace(",", ""))
    return int(m.group(1)) if m else 0


# ── Part 1: Liquipedia — Prize Tables ──────────────────────────────────────────

def scrape_prize_table(season_num, year, split):
    """
    Scrape the prize pool table from an MPL Malaysia season page.
    Key fix vs previous version: only reads tables with ≤ 12 rows
    that contain a '$' sign — this targets prize tables only.
    """
    url = f"{BASE}/mobilelegends/MPL/Malaysia/Season_{season_num}"
    print(f"  Season {season_num} ({year} {split}): {url}")
    soup = fetch(url)
    if not soup:
        return []

    rows = []

    # Step 1: Find prize pool total from infobox
    prize_pool = 0
    infobox = soup.find("div", class_=re.compile("infobox"))
    if infobox:
        for text in infobox.stripped_strings:
            m = re.search(r'[\$]([\d,]+)', text)
            if m:
                prize_pool = int(m.group(1).replace(",", ""))
                break

    # Step 2: Find the prize pool TABLE specifically
    # Strategy: look for tables where:
    #   - Has <= 12 data rows (a prize table won't have 137 rows)
    #   - Contains '$' somewhere in the table
    #   - Has a column with placement numbers (1, 2, 3...)
    prize_table = None
    for table in soup.find_all("table"):
        data_rows = table.find_all("tr")[1:]  # skip header
        if len(data_rows) > 12 or len(data_rows) < 2:
            continue
        table_text = table.get_text()
        if "$" not in table_text and "USD" not in table_text:
            continue
        # Must have a placement number (1st place)
        if not re.search(r'\b1\b', table_text):
            continue
        prize_table = table
        break  # take the first match

    if not prize_table:
        print(f"    ⚠️  No prize table found for Season {season_num}")
        return []

    # Step 3: Extract rows from the prize table
    for tr in prize_table.find_all("tr"):
        tds = tr.find_all(["td", "th"])
        if len(tds) < 2:
            continue

        row_text = tr.get_text(separator="|")
        cells = [td.get_text(strip=True) for td in tds]

        # Skip header rows
        if any(h in cells[0].lower() for h in ["place", "team", "prize"]):
            continue

        # Extract placement — first cell with a digit
        placement = None
        for cell in cells:
            m = re.search(r'^(\d+)', cell.strip())
            if m:
                placement = int(m.group(1))
                break
        if placement is None or placement > 12:
            continue

        # Extract team name — find the <a> tag link in any cell
        team_name = ""
        for td in tds:
            a = td.find("a")
            if a:
                t = a.get_text(strip=True)
                # Skip short strings and known non-team links
                if len(t) > 2 and not re.match(r'^\d+', t):
                    team_name = t
                    break
        if not team_name:
            # Fallback: use last cell text
            team_name = cells[-1][:40]

        # Extract prize — find $ amount in any cell
        prize = 0
        for cell in cells:
            m = re.search(r'\$([\d,]+)', cell)
            if m:
                prize = int(m.group(1).replace(",", ""))
                break

        team_state = match_state(team_name)

        rows.append({
            "season":           season_num,
            "year":             year,
            "split":            split,
            "prize_pool_usd":   prize_pool,
            "team":             team_name,
            "team_state":       team_state,
            "placement":        placement,
            "prize_won_usd":    prize,
            "qualified_worlds": placement <= 2,
        })

    # Deduplicate by placement (keep first occurrence per placement)
    seen = set()
    deduped = []
    for r in sorted(rows, key=lambda x: x["placement"]):
        if r["placement"] not in seen:
            seen.add(r["placement"])
            deduped.append(r)

    print(f"    ✅ {len(deduped)} teams found | Prize pool: ${prize_pool:,}")
    return deduped


# ── Part 2: Liquipedia — M-Series Worlds ──────────────────────────────────────

def scrape_worlds(code, year):
    """Scrape Malaysia's placement at one M-Series World Championship."""
    url = f"{BASE}/mobilelegends/{code}_World_Championship"
    print(f"  {code} ({year}): {url}")
    soup = fetch(url)
    if not soup:
        return None

    # Find total teams from infobox
    total_teams = 16
    infobox = soup.find("div", class_=re.compile("infobox"))
    if infobox:
        m = re.search(r'(\d+)\s*[Tt]eams?', infobox.get_text())
        if m:
            total_teams = int(m.group(1))

    # Malaysian teams to look for
    my_keywords = ["todak", "srg", "smg", "geek fam", "homeBois",
                   "homebois", "aero", "cg esports", "monster"]

    # Find final standings table (usually the first table with 1st place)
    for table in soup.find_all("table"):
        table_text = table.get_text().lower()
        if not any(k in table_text for k in my_keywords):
            continue
        for tr in table.find_all("tr"):
            row_text = tr.get_text(separator="|").lower()
            for kw in my_keywords:
                if kw in row_text:
                    # Found a Malaysian team row — get placement
                    cells = [td.get_text(strip=True) for td in tr.find_all(["td","th"])]
                    place_m = re.search(r'\b(\d+)\b', cells[0]) if cells else None
                    placement = int(place_m.group(1)) if place_m else 0
                    # Get team name from link
                    team_link = tr.find("a")
                    team_name = team_link.get_text(strip=True) if team_link else kw.title()
                    if 0 < placement <= total_teams:
                        print(f"    ✅ {team_name} placed #{placement} of {total_teams}")
                        return {
                            "tournament":          f"{code} World Championship",
                            "year":                year,
                            "malaysia_team":        team_name,
                            "malaysia_placement":   placement,
                            "total_teams":          total_teams,
                        }

    print(f"    ⚠️  Malaysia placement not found for {code}")
    return {"tournament": f"{code} World Championship", "year": year,
            "malaysia_team": "Not found", "malaysia_placement": 0, "total_teams": total_teams}


# ── Part 3: data.gov.my API — Broadband by State ──────────────────────────────

def fetch_broadband_api():
    """
    Fetch broadband penetration data from data.gov.my official API.
    Tries multiple known dataset IDs — uses whichever works.
    No scraping needed, this is a clean government API.
    """
    # These are the dataset IDs to try, in order of preference
    # Find the correct one at: data.gov.my/data-catalogue
    # (search "broadband" and check the "Sample OpenAPI query" at bottom of page)
    CANDIDATE_IDS = [
        "fixed_bband_postpaid",
        "fixed_bband_state",
        "internet_penetration_state",
        "bband_state",
        "mcmc_bband_state",
        "fixed_broadband_state",
    ]

    base_api = "https://api.data.gov.my/data-catalogue"

    for dataset_id in CANDIDATE_IDS:
        try:
            url = f"{base_api}?id={dataset_id}&limit=5"
            print(f"    Trying dataset ID: {dataset_id}")
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data and len(data) > 0:
                    print(f"    ✅ Found dataset: {dataset_id}")
                    print(f"       Sample columns: {list(data[0].keys())}")
                    # Fetch all records
                    r_full = requests.get(f"{base_api}?id={dataset_id}&limit=10000", timeout=30)
                    return dataset_id, r_full.json()
        except Exception as e:
            print(f"       Error: {e}")
        time.sleep(0.5)

    return None, None


def process_broadband(dataset_id, raw_data):
    """
    Normalise the broadband API response into a clean DataFrame.
    Column names vary by dataset — this handles the common patterns.
    """
    df = pd.DataFrame(raw_data)
    print(f"    Raw columns: {list(df.columns)}")
    print(f"    Raw shape: {df.shape}")

    # Normalise column names to lowercase
    df.columns = [c.lower().strip() for c in df.columns]

    # Find state column
    state_col = next((c for c in df.columns
                      if any(k in c for k in ["state", "negeri", "region"])), None)
    # Find year/date column
    date_col  = next((c for c in df.columns
                      if any(k in c for k in ["date", "year", "quarter", "tahun"])), None)
    # Find fixed broadband column
    fixed_col = next((c for c in df.columns
                      if any(k in c for k in ["fixed", "tetap", "premises", "pct", "rate",
                                               "penetration", "peratusan"])), None)
    # Find mobile broadband column
    mobile_col = next((c for c in df.columns
                       if any(k in c for k in ["mobile", "mudah", "cellular"])), None)

    print(f"    Mapped: state={state_col}, date={date_col}, fixed={fixed_col}, mobile={mobile_col}")

    if not state_col or not fixed_col:
        print("    ❌ Could not identify required columns. See raw columns above.")
        return None

    rename_map = {state_col: "state", fixed_col: "fixed_bb_pct"}
    if date_col:  rename_map[date_col]  = "date"
    if mobile_col: rename_map[mobile_col] = "mobile_bb_pct"
    df = df.rename(columns=rename_map)

    # Extract year from date column
    if "date" in df.columns:
        df["year"] = pd.to_datetime(df["date"], errors="coerce").dt.year

    # Add broadband tier
    df["broadband_tier"] = pd.cut(
        pd.to_numeric(df["fixed_bb_pct"], errors="coerce"),
        bins=[0, 35, 65, 200],
        labels=["Low", "Medium", "High"]
    )

    keep = ["state", "year", "fixed_bb_pct"]
    if "mobile_bb_pct" in df.columns: keep.append("mobile_bb_pct")
    keep.append("broadband_tier")
    df = df[[c for c in keep if c in df.columns]].dropna(subset=["state","fixed_bb_pct"])

    return df


# ── Part 4: Derive Summary Files ──────────────────────────────────────────────

def derive_summaries(df_teams, df_bb):
    """Generate mpl_season_meta.csv and mpl_state_summary.csv."""

    # Season meta
    df_meta = (
        df_teams.groupby(["season","year","split"], as_index=False)
        .agg(prize_pool_usd=("prize_pool_usd","first"), teams_count=("team","count"))
        .sort_values("season")
    )

    # State summary — all states
    df_state = (
        df_teams.groupby("team_state", as_index=False)
        .agg(
            teams_total       = ("team",          "nunique"),
            total_prize_usd   = ("prize_won_usd",  "sum"),
            championships     = ("placement",      lambda x: (x==1).sum()),
            top2_finishes     = ("placement",      lambda x: (x<=2).sum()),
            avg_placement     = ("placement",      "mean"),
            seasons_present   = ("season",         "nunique"),
        )
        .rename(columns={"team_state":"state"})
    )

    # Join broadband (latest year) — ensure ALL states appear
    if df_bb is not None and "year" in df_bb.columns:
        latest = df_bb["year"].max()
        bb_snap = df_bb[df_bb["year"]==latest].copy()
        # Merge: right join keeps all states in broadband data
        df_full = bb_snap.merge(df_state, on="state", how="left")
        df_full["teams_total"]     = df_full["teams_total"].fillna(0).astype(int)
        df_full["total_prize_usd"] = df_full["total_prize_usd"].fillna(0)
        df_full["championships"]   = df_full["championships"].fillna(0).astype(int)
        df_full["top2_finishes"]   = df_full["top2_finishes"].fillna(0).astype(int)
        df_full["seasons_present"] = df_full["seasons_present"].fillna(0).astype(int)
        df_full["avg_placement"]   = df_full["avg_placement"].fillna(0)
    else:
        df_full = df_state

    return df_meta, df_full


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("FIT2179 DV2 — Automated Data Collection")
    print("Collecting from: Liquipedia + data.gov.my API")
    print("=" * 65)

    # ── 1. MPL Season Prize Tables ──────────────────────────────────────────
    print("\n📋 PART 1: MPL Season Prize Tables")
    print("-" * 40)
    all_teams = []
    for s, (y, split) in SEASONS.items():
        rows = scrape_prize_table(s, y, split)
        all_teams.extend(rows)
        pd.DataFrame(all_teams).to_csv("mpl_teams.csv", index=False)  # save after each

    df_teams = pd.DataFrame(all_teams)
    df_teams.to_csv("mpl_teams.csv", index=False)
    print(f"\n✅ mpl_teams.csv saved — {len(df_teams)} rows")
    print(df_teams[["season","team","team_state","placement","prize_won_usd"]].to_string(index=False))

    # ── 2. M-Series Worlds ──────────────────────────────────────────────────
    print("\n\n🏆 PART 2: M-Series World Championships")
    print("-" * 40)
    worlds_rows = []
    for code, year in M_WORLDS:
        result = scrape_worlds(code, year)
        if result:
            worlds_rows.append(result)

    df_worlds = pd.DataFrame(worlds_rows)
    df_worlds.to_csv("mpl_worlds.csv", index=False)
    print(f"\n✅ mpl_worlds.csv saved — {len(df_worlds)} rows")
    print(df_worlds.to_string(index=False))

    # ── 3. Broadband by State ───────────────────────────────────────────────
    print("\n\n📡 PART 3: Broadband Penetration (data.gov.my API)")
    print("-" * 40)
    dataset_id, raw = fetch_broadband_api()

    df_bb = None
    if raw:
        df_bb = process_broadband(dataset_id, raw)
        if df_bb is not None:
            df_bb.to_csv("broadband_by_state.csv", index=False)
            print(f"\n✅ broadband_by_state.csv saved — {len(df_bb)} rows")
        else:
            print("\n⚠️  Broadband data found but column mapping failed.")
            print("    See instructions below to download manually.")
    else:
        print("\n⚠️  Could not auto-fetch broadband data from API.")
        print("    Manual download (5 mins):")
        print("    1. Go to: https://data.gov.my/data-catalogue")
        print("    2. Search: 'broadband' or 'internet penetration'")
        print("    3. Open the state-level dataset")
        print("    4. Click Download → CSV")
        print("    5. Rename to broadband_by_state.csv")

    # ── 4. Derive Summaries ─────────────────────────────────────────────────
    print("\n\n📊 PART 4: Deriving Summary Files")
    print("-" * 40)
    df_meta, df_summary = derive_summaries(df_teams, df_bb)
    df_meta.to_csv("mpl_season_meta.csv", index=False)
    df_summary.to_csv("mpl_state_summary.csv", index=False)
    print(f"✅ mpl_season_meta.csv — {len(df_meta)} rows")
    print(f"✅ mpl_state_summary.csv — {len(df_summary)} rows")

    # ── Final Summary ───────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("✅ COLLECTION COMPLETE")
    print("=" * 65)
    print("\n📁 Files ready for Vega-Lite:")
    print("   mpl_teams.csv           → bar, bump, lollipop charts")
    print("   mpl_worlds.csv          → line, slope charts")
    print("   mpl_season_meta.csv     → prize trend line chart")
    print("   broadband_by_state.csv  → broadband choropleth + heatmap")
    print("   mpl_state_summary.csv   → scatter plot + state choropleth")

    # ── Inequality Snapshot ─────────────────────────────────────────────────
    print("\n📊 INEQUALITY SNAPSHOT:")
    print(f"{'State':<22} {'Teams':>6}  {'Prize Won':>12}  {'Champ':>5}")
    print("-" * 55)
    for _, r in df_summary.sort_values("total_prize_usd", ascending=False).iterrows():
        if r.get("state") == "Unknown":
            continue
        bar  = "█" * int(r.get("teams_total", 0))
        champ = "👑" * int(r.get("championships", 0))
        print(f"  {r['state']:<20} {int(r.get('teams_total',0)):>6}  "
              f"${r.get('total_prize_usd',0):>11,.0f}  {champ}")

    zero = df_summary[df_summary.get("teams_total",0) == 0]["state"].tolist() \
           if "teams_total" in df_summary.columns else []
    if zero:
        print(f"\n⚠️  States with ZERO MPL representation: {len(zero)}")
        for s in zero:
            print(f"   • {s}")