"""
Euro 2024: turn StatsBomb open event data into tidy, Tableau-ready CSV files.

Data: StatsBomb Open Data (https://github.com/statsbomb/open-data)
Usage: python build_dataset.py <raw_folder> <output_folder>

Outputs
  matches.csv      one row per match
  team_matches.csv one row per team per match (xG, pressing, territory, ...)
  team_summary.csv one row per team for the whole tournament
  shots.csv        one row per shot (for shot maps)

Notes on StatsBomb coordinates: the pitch is 120 x 80, and every event's
location is recorded from the acting team's point of view, attacking left to
right. So x = 120 is always the goal that team is attacking.
"""
import json
import sys
from pathlib import Path

import pandas as pd

RAW = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

STAGE_ORDER = {"Group Stage": 1, "Round of 16": 2, "Quarter-finals": 3, "Semi-finals": 4, "Final": 5}
DEF_ACTIONS = {"Interception", "Foul Committed"}  # plus tackles, handled below
FINAL_THIRD_X = 80   # x >= 80 is the attacking third
PPDA_LINE = 48       # pressing zone: opponent's 60% of the pitch (x >= 48 for the presser)

# ---------- 1. Matches ----------
matches_raw = json.loads((RAW / "matches.json").read_text())
match_rows = []
for m in matches_raw:
    match_rows.append({
        "match_id": m["match_id"],
        "date": m["match_date"],
        "stage": m["competition_stage"]["name"],
        "stage_order": STAGE_ORDER.get(m["competition_stage"]["name"], 0),
        "home_team": m["home_team"]["home_team_name"],
        "away_team": m["away_team"]["away_team_name"],
        "home_score": m["home_score"],
        "away_score": m["away_score"],
    })
matches = pd.DataFrame(match_rows).sort_values("date")

# ---------- 2. Events -> per team per match ----------
team_rows, shot_rows = [], []

for _, m in matches.iterrows():
    events = json.loads((RAW / "events" / f"{m.match_id}.json").read_text())
    events = [e for e in events if e["period"] <= 4]  # drop penalty shoot-outs (period 5)
    teams = [m.home_team, m.away_team]

    stats = {t: {"xg": 0.0, "np_xg": 0.0, "shots": 0, "shots_on_target": 0, "passes": 0,
                 "final_third_passes": 0, "own_half_passes": 0, "def_actions_high": 0,
                 "pressures": 0, "high_turnovers": 0} for t in teams}

    for e in events:
        team = e["team"]["name"]
        if team not in stats:
            continue
        s = stats[team]
        etype = e["type"]["name"]
        x = e.get("location", [None])[0]

        if etype == "Shot":
            shot = e["shot"]
            xg = shot.get("statsbomb_xg", 0.0)
            is_pen = shot["type"]["name"] == "Penalty"
            outcome = shot["outcome"]["name"]
            s["xg"] += xg
            s["np_xg"] += 0 if is_pen else xg
            s["shots"] += 1
            s["shots_on_target"] += outcome in ("Goal", "Saved", "Saved To Post")
            shot_rows.append({
                "match_id": m.match_id, "stage": m.stage, "team": team,
                "opponent": teams[1] if team == teams[0] else teams[0],
                "player": e["player"]["name"], "minute": e["minute"],
                "x": e["location"][0], "y": e["location"][1],
                "xg": round(xg, 4), "outcome": outcome, "is_goal": int(outcome == "Goal"),
                "shot_type": shot["type"]["name"], "body_part": shot["body_part"]["name"],
            })

        elif etype == "Pass":
            s["passes"] += 1
            if x is not None and x >= FINAL_THIRD_X:
                s["final_third_passes"] += 1
            if x is not None and x < 120 - PPDA_LINE:   # pass inside own 60%: counts for opponent's PPDA
                s["own_half_passes"] += 1

        elif etype == "Pressure":
            s["pressures"] += 1

        # Defensive actions high up the pitch (used for PPDA)
        is_tackle = etype == "Duel" and e.get("duel", {}).get("type", {}).get("name") == "Tackle"
        if (is_tackle or etype in DEF_ACTIONS) and x is not None and x >= PPDA_LINE:
            s["def_actions_high"] += 1

        # High turnovers: winning the ball within 40m of the opponent's goal
        if etype in ("Ball Recovery", "Interception") and x is not None and x >= FINAL_THIRD_X:
            recovered = not e.get("ball_recovery", {}).get("recovery_failure", False)
            if recovered:
                s["high_turnovers"] += 1

    scores = {m.home_team: m.home_score, m.away_team: m.away_score}
    for t in teams:
        o = teams[1] if t == teams[0] else teams[0]
        st, so = stats[t], stats[o]
        gf, ga = scores[t], scores[o]
        team_rows.append({
            "match_id": m.match_id, "date": m.date, "stage": m.stage, "stage_order": m.stage_order,
            "team": t, "opponent": o, "venue": "Home" if t == m.home_team else "Away",
            "goals_for": gf, "goals_against": ga,
            "result": "W" if gf > ga else "L" if gf < ga else "D",
            "xg_for": round(st["xg"], 3), "xg_against": round(so["xg"], 3),
            "np_xg_for": round(st["np_xg"], 3),
            "shots": st["shots"], "shots_on_target": st["shots_on_target"],
            "possession_pct": round(100 * st["passes"] / (st["passes"] + so["passes"]), 1),
            "field_tilt_pct": round(100 * st["final_third_passes"] /
                                    max(st["final_third_passes"] + so["final_third_passes"], 1), 1),
            # PPDA = opponent passes in their own 60% / our defensive actions there. Lower = more intense press.
            "ppda": round(so["own_half_passes"] / max(st["def_actions_high"], 1), 2),
            "pressures": st["pressures"], "high_turnovers": st["high_turnovers"],
        })

team_matches = pd.DataFrame(team_rows)

# Knockout draws were settled by extra time or penalties; record who actually went through.
winners = {}
for _, m in matches.iterrows():
    if m.stage != "Group Stage":
        if m.home_score != m.away_score:
            winners[m.match_id] = m.home_team if m.home_score > m.away_score else m.away_team
team_matches["went_through"] = team_matches.apply(
    lambda r: "" if r.stage == "Group Stage" else
    ("Yes" if winners.get(r.match_id) == r.team else "No" if r.match_id in winners else "Penalties"), axis=1)

# ---------- 3. Tournament summary per team ----------
g = team_matches.groupby("team")
summary = pd.DataFrame({
    "matches": g.size(),
    "wins": g.apply(lambda d: (d.result == "W").sum()),
    "draws": g.apply(lambda d: (d.result == "D").sum()),
    "losses": g.apply(lambda d: (d.result == "L").sum()),
    "furthest_stage_order": g.stage_order.max(),
    "goals_for": g.goals_for.sum(), "goals_against": g.goals_against.sum(),
    "xg_for": g.xg_for.sum().round(2), "xg_against": g.xg_against.sum().round(2),
    "xg_per_match": g.xg_for.mean().round(2), "xga_per_match": g.xg_against.mean().round(2),
    "possession_pct": g.possession_pct.mean().round(1),
    "field_tilt_pct": g.field_tilt_pct.mean().round(1),
    "ppda": g.ppda.mean().round(2),
    "high_turnovers_per_match": g.high_turnovers.mean().round(1),
    "pressures_per_match": g.pressures.mean().round(0),
}).reset_index()
stage_names = {v: k for k, v in STAGE_ORDER.items()}
summary["furthest_stage"] = summary.furthest_stage_order.map(stage_names)
final = matches[matches.stage == "Final"].iloc[0]
champion = final.home_team if final.home_score > final.away_score else final.away_team
summary.loc[summary.team == champion, "furthest_stage"] = "Winner"
summary.loc[summary.team == champion, "furthest_stage_order"] = 6
summary["xg_difference"] = (summary.xg_for - summary.xg_against).round(2)
summary["goals_minus_xg"] = (summary.goals_for - summary.xg_for).round(2)

# ---------- 4. Save ----------
matches.to_csv(OUT / "matches.csv", index=False)
team_matches.to_csv(OUT / "team_matches.csv", index=False)
summary.sort_values("furthest_stage_order", ascending=False).to_csv(OUT / "team_summary.csv", index=False)
pd.DataFrame(shot_rows).to_csv(OUT / "shots.csv", index=False)
print(f"{len(matches)} matches, {len(team_matches)} team-matches, {len(summary)} teams, {len(shot_rows)} shots")
