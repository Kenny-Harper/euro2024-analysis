# Euro 2024: What Separated the Best Teams?

An analysis of all 51 matches of UEFA Euro 2024 using StatsBomb open event data. It looks at whether controlling territory, pressing and finishing explain how far each team went.

**Live dashboard:** [View the interactive dashboard](https://public.tableau.com/app/profile/kenny.harper/viz/Euro2024-WhatSeparatedtheBestTeams/Dashboard1)

**Tools:** Python (pandas), Tableau Public

## Key findings
1. **Territory drives chance quality.** Field tilt (share of final-third passes) had a 0.86 correlation with xG difference per match across the 24 teams. Pressing intensity (PPDA) had a -0.73 correlation: teams that pressed harder created more than they conceded.
2. **Spain won by doing both.** Spain led the tournament for high turnovers (16.6 per match) and scored 15 goals from 10.6 xG, finishing 4.4 goals above expectation.
3. **Finishing cost Portugal and France.** Portugal had the best xG difference per match (+1.00) and France reached the semi-finals, but both scored about 4 goals fewer than their chances were worth.
4. **England reached the final on fine margins.** Their xG difference was only +0.07 per match, and they needed penalties to beat Switzerland.

> Caveat: 24 teams and up to 7 matches each is a small sample, and correlation does not prove causation. These findings describe this tournament; they are not general rules.

## Data
| File | One row per | Key fields |
|---|---|---|
| `data/matches.csv` | match | stage, teams, score |
| `data/team_matches.csv` | team per match | xG for/against, possession, field tilt, PPDA, high turnovers |
| `data/team_summary.csv` | team | tournament totals and averages, furthest stage |
| `data/shots.csv` | shot | location (x, y), xG, outcome, player |

### Metric definitions
- **xG (expected goals):** StatsBomb's estimate of the chance a shot is scored. Penalty shoot-outs are excluded.
- **Field tilt:** a team's passes in the attacking third as a share of both teams' attacking-third passes.
- **PPDA (passes per defensive action):** opponent passes in their own 60% of the pitch divided by our tackles, interceptions and fouls there. Lower means a more intense press.
- **High turnovers:** ball recoveries and interceptions within 40m of the opponent's goal.
- **Possession:** share of total passes in the match.
- Goals come from the final score, so they include own goals; `shots.csv` does not.

## How to reproduce
```bash
pip install pandas matplotlib
# download competitions/matches/events for competition 55, season 282 from the StatsBomb repo into raw/
python scripts/build_dataset.py raw data
python scripts/make_pitch.py data/pitch_background.png
```

## Data source
Data provided by [StatsBomb](https://github.com/statsbomb/open-data) open data.
