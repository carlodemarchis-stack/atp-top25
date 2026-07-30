# ATP Top 100 — Player Film (snapshot prototype)

Ranking-ordered player film, styled after the WC "player film". One full-screen card per player:
**left** column = every tournament played in 2026; **right** column = a smaller full-body cutout on
top with the identity block below it (flag + rank tag, big number + name, pills, vitals line, and a
summary stat bar: Points / Win-Loss / Titles / Prize).

Bottom **control bar** drives it horizontally: restart · prev · play/pause (autoplay) · next ·
`n / 10 · TOP 10` · fullscreen. Also ← → arrows, spacebar (play), swipe. Tournament rows
auto-compact per card so even the busiest players (17 events) fit above the control bar.

Each tournament row is **clickable** → opens a modal with the full match-by-match breakdown
(round, opponent + rank + flag, W/L, set scores with tiebreaks) — mirrors the ATP player-activity
page. Modal has ‹ › carousel arrows + `n / total` pager to page through the player's tournaments
(also ← →). Won tournaments are gold-highlighted (🏆 Winner + championship-final row). Close with
×, overlay click, or Esc.

Left column has a **Tournaments / Opponents / Rivals** toggle. Opponents = season head-to-head,
derived from the match data: rivals (2+ meetings) as rows (flag · name · rank · per-match win/loss
dots · W–L), then all single-meeting opponents condensed into a wrapped run of `Name ●` (green/red
dot). Sorted most-faced first. **Rivals** = the other Top-10 in ranking order, same row visual,
showing the current player's H2H vs each; not-yet-played rivals are greyed "— not played".

Final card **"The Field"** = a points bar chart of the Top 10; each bar's height scales to ranking
points, topped with the player's round headshot (leader in gold). It's the 11th card in the film.

Open `index.html` directly in a browser — self-contained (data inlined, images local under `img/`).
`server.py` serves the folder for local preview (`python3 server.py` → localhost:8777).

## Data snapshot
- **Ranking date:** 2026-07-27 · **captured:** 2026-07-29 · **scope:** Top 100 singles (102 cards: 100 player cards + "The Field" top-10 points chart + "Prize Money" top-25 chart; Rivals tab only on the top 10)
- `data/players.json` — assembled records
- `img/full/{id}.png` — 379×603 transparent full-body "gladiator" cutouts
- `img/face/{id}.png` — 300×300 round headshots
- Rebuild the page after editing data: `python3 -c "import json;open('index.html','w').write(open('template.html').read().replace('/*__DATA__*/',json.dumps(json.load(open('data/players.json')),ensure_ascii=False)))"`

## Where the data comes from (atptour.com)
ATP has **no public API**; data is Vue-hydrated from internal JSON endpoints. Cloudflare blocks
plain server fetches (403) — a real/headless browser passes the JS challenge, then these endpoints
return clean JSON (`x-requested-with: XMLHttpRequest` header):

| Endpoint | Gives |
|---|---|
| `/en/-/www/players/hero/{id}` | bio + YTD/career stats, gladiator img url, social |
| `/en/-/www/activity/sgl/{id}/{year}` | every tournament: name, location, surface, category, seed, points, result (HiRound), W-L |
| rankings page HTML | rank, points, move, next-best + player id (from `/players/{slug}/{id}/overview`) |
| `/en/rankings/singles-race-to-turin` HTML | Race-to-Turin rank per id (shown as a top-right tag, green if top-8 qualifying) |

Images (keyed purely by 4-char player id):
- round: `/-/media/alias/player-headshot/{id}`
- full body: `/-/media/alias/player-gladiator-headshot/{id}`

## Refresh path (unattended)
Curl/WebFetch get 403. To auto-refresh headless, use **Apify** (Crawlee + PlaywrightCrawler +
residential proxy) to clear Cloudflare once, grab the `cf_clearance` cookie, then reuse it to fetch
the JSON endpoints for N players. ATP's wall is a JS challenge (passable), not an interactive CAPTCHA.

## Player ids (top 10, 2026-07-27)
s0ag Sinner · z355 Zverev · a0e2 Alcaraz · ag37 Auger-Aliassime · d643 Djokovic ·
dh58 de Minaur · mm58 Medvedev · s0s1 Shelton · c0e9 Cobolli · fb98 Fritz
