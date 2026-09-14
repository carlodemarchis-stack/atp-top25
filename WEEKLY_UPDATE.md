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
Scrape `table.desktop-table` on `…/rankings/singles?rankRange=0-100`. Per row: `id` (from the
player link), plus these `td` indices — **read the header row first, the layout moves**:

| td | column | use as |
|----|--------|--------|
| 0 | Rank | `rank` |
| 1 | Player | name |
| 2 | Age | — |
| 3 | Official Points | `pointsFmt` |
| 4 | +/- | `delta` → `ptsMove` (weekly points swing, e.g. `-1300`) |
| 5 | Tourn Played | — |
| 6 | Dropping | — |
| 7 | Next Best | — |

`cc` comes from the row's flag `use`. Confirm the `dateWeek-filter` select's newest option
equals the target Monday.

> ⚠️ **The table gained an `Age` column** at some point before 2026-09-14, shifting every
> later index right by one. The old instruction ("points = cell 2") silently yielded *ages*
> — Sinner 25, Djokovic 39 — which look plausible enough to ship. **Always dump the `thead`
> and one row before trusting the indices**, and sanity-check that #1 has four figures.

**b) Race** → `scratchpad/atp/new_race.json`
Scrape `…/rankings/singles-race-to-turin?rankRange=0-100`. Same Age-column shift applies:
`raceRank` = td 0, `racePoints` = **first token** of **td 4** (Live Points; td 2 is Age,
td 3 is Current Tournament).

**c) Entrants** → a tool-result file
Diff new vs current top-100 (`data/players.json`) for ids not already present. For each
entrant fetch `/en/-/www/players/hero/<id>` + `/en/-/www/activity/sgl/<id>/2026`, **plus
`/en/-/www/activity/sgl/<id>/all` and `/en/-/www/activity/dbl/<id>/all`** for the career
totals, and return `{id:{hero,act,all,allDbl}}`. (`update_atp.py` now hard-errors if `all`
is missing rather than silently writing career == YTD.) Also grab their gladiator PNG (`/-/media/alias/player-gladiator-headshot/<id>`,
base64 → `img/full/<id>.png`).

**d) Activity (all 100)** → a tool-result file
For every id in the new top 100, fetch `/en/-/www/activity/sgl/<id>/2026` and transform to
the compact blob (see `update_atp_activity.py` schema). **Name = `EventDisplayName`** (sponsor
name), NOT `EventName` (generic). Fetch in small batches to stay under the rate limit.

> ⚠️ **Career stats are NOT in the `/2026` response.** That endpoint is *year-scoped*: its
> `WonTotal` / `LostTotal` / `TitlesTotal` / `PrizeMoneyTotal` fields equal the season values,
> so reading them yields career == YTD (this shipped as a bug until 2026-09-06 — every ATP card
> showed its 2026 W-L/titles/prize as the career figures).
> For the **career** blob (`cw`/`cl`/`ct`/`cp`) fetch the `all` variant instead:
> * `/en/-/www/activity/sgl/<id>/all` → `Won`, `Lost`, `Titles` = career **singles** totals
> * career prize money as ATP displays it = **`sgl.Prize` + `dbl.Prize`**, i.e. also fetch
>   `/en/-/www/activity/dbl/<id>/all` and sum the two `Prize` fields ("Singles & Doubles
>   Combined" on the player page). Verified: Vukic `v832` → 60-93, $4,087,355 (site: $4,087,354).
>
> `tools/fetch_atp_career.js` holds the ready-made in-browser snippet.

## Step 2 — One command

```bash
python3 atp_update.py 2026-09-14 <entrants_file> <activity_file>
```

> Both files must **start with the JSON**. If the capture wrapped it in `|||S|||…|||E|||`
> or padded it with `X`s to force a tool-result file, re-emit it first as
> `[{"text": "<json>"}]` — `raw_decode` the tool-result text (it is a JSON-encoded string
> with a trailing tab-context note), strip the markers, then dump. See
> `scratchpad/atp/entrants_clean.json` / `activity_clean.json` from the 2026-09-14 run.

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
python3 tools/build_ranks.py      # RANK map in draws.html — the draw panel links by rank
git add data/players.json index.html wta.html draws.html img/full/*.png && git commit && git push
```

`build_ranks.py` is **not** optional since the draw's player panel became a link to that
player's card: a stale RANK map sends people to the wrong card (or drops the link for a
new entrant).

GitHub Pages redeploys in ~1–2 min. Nothing else to touch.

---

## Dropping in a player photo by hand

Five WTA players have no `full-body` cutout upstream (see `data/wta_images_kind.json`
for who, and the URL of the head-only shot where one exists). To supply one yourself:

* save it as **`img/wta/<playerId>.png`** — e.g. `img/wta/327845.png` for Snigur
* **transparent background**, roughly 640px wide, torso crop (head to waist), subject centred

`download_wta_images.py` will not overwrite it: it only writes the purple placeholder over
nothing or over another placeholder, and reports `+ N hand-added kept`. Players who *do*
have an upstream cutout are still refreshed each week, so replacing one of those by hand
will not stick.

ATP is the same idea — `img/full/<playerId>.png`, though there the gladiator cutouts are
379x603 and three current entrants only have a 300x300 circular headshot.
