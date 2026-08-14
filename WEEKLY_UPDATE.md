# Weekly ATP update

ATP rankings publish every **Monday**. atptour.com sits behind Cloudflare, so the *fetch*
step must run in a real browser (curl gets a 403) — that part is driven by Claude. Once the
four fetch files exist, **one command** does everything else.

> WTA is separate and much simpler — plain `python3 build_wta.py && build_wta_calendar.py &&
> render.py` (bump `AT` to the Monday date first; it's a public API, no browser).

---

## Step 1 — Browser fetch (on `https://www.atptour.com`, Cloudflare-cleared)

Run these in the browser console / `javascript_tool`. Save the outputs as noted.

**a) Rankings** → `scratchpad/atp/new_rankings.json`
Scrape `…/rankings/singles?rankRange=0-100`. Per row: `id` (from the player link), `rank`
(cell 0), `pointsFmt` (cell 2 — **not** cell 3, that's "points dropping"), `cc` (flag `use`).
Confirm the newest date option equals the target Monday.

**b) Race** → `scratchpad/atp/new_race.json`
Scrape `…/rankings/singles-race-to-turin?rankRange=0-100`. `raceRank` (cell 0), `racePoints`
= **first token** of cell 2 (e.g. `"6,560 +10"` → 6560).

**c) Entrants** → a tool-result file
Diff new vs current top-100 (`data/players.json`) for ids not already present. For each
entrant fetch `/en/-/www/players/hero/<id>` + `/en/-/www/activity/sgl/<id>/2026`, return
`{id:{hero,act}}`. Also grab their gladiator PNG (`/-/media/alias/player-gladiator-headshot/<id>`,
base64 → `img/full/<id>.png`).

**d) Activity (all 100)** → a tool-result file
For every id in the new top 100, fetch `/en/-/www/activity/sgl/<id>/2026` and transform to
the compact blob (see `update_atp_activity.py` schema). **Name = `EventDisplayName`** (sponsor
name), NOT `EventName` (generic). Fetch in small batches to stay under the rate limit.

## Step 2 — One command

```bash
python3 atp_update.py 2026-08-17 <entrants_tool_result.txt> <activity_tool_result.txt>
```

This runs, in order:
1. `update_atp.py` — overlay rankings + race, swap entrants/exits, set the ranking date.
   Move is computed as *previous rank − new rank* (the page no longer prints it).
2. `update_atp_activity.py` — refresh every player's tournaments/results + YTD/career stats.
3. `build_atp_calendar.py` — rebuild each event's champion/runner-up/semi-finalists from the
   refreshed matches (in-progress events stay "upcoming"). No network.
4. `render.py` — rebuild `index.html` + `wta.html`.

The prize-money card needs nothing — it live-sorts by `ytdPrize` at render time.

## Step 3 — Verify & ship

Spot-check locally (points for a shuffled top-10 player, an entrant card + photo, a completed
event's calendar winner, Cincinnati/whatever is in progress showing "upcoming"), then:

```bash
git add data/players.json index.html img/full/*.png && git commit && git push
```

GitHub Pages redeploys in ~1–2 min. Nothing else to touch.
