#!/usr/bin/env python3
"""WTA data pipeline — fetches the WTA top-100 singles from api.wtatennis.com +
profile HTML (all plain-curl, no Cloudflare) and emits data/wta_players.json in the
exact schema the shared template.html consumes (twin of the ATP players.json)."""
import time
import urllib.request, urllib.error, json, re, html, os, sys, unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed

AT = "2026-08-24"                          # ranking issue date (matches ATP snapshot); bump each Monday to refresh
API = "https://api.wtatennis.com/tennis"
HDRS = {"account": "wta", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
OUT = os.path.join(os.path.dirname(__file__), "data", "wta_players.json")

def _get(url, as_json=True, tries=6):
    last = None
    for i in range(tries):
        try:
            time.sleep(0.4)                       # gentle throttle so ~200 reqs don't trip the rate limit
            req = urllib.request.Request(url, headers=HDRS)
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
            return json.loads(data) if as_json else data.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = e
            time.sleep(10 * (i + 1) if e.code == 429 else 1.5)   # back off hard on 429
        except Exception as e:
            last = e
            time.sleep(1.5)
    raise last

# ---- 3-letter code -> full country name (must match template FLAG keys) ----
CC = {
 "BLR":"Belarus","RUS":"Russia","KAZ":"Kazakhstan","USA":"United States","POL":"Poland",
 "ITA":"Italy","CZE":"Czechia","CHN":"China","GRE":"Greece","UKR":"Ukraine","ESP":"Spain",
 "FRA":"France","GER":"Germany","TUN":"Tunisia","CAN":"Canada","LAT":"Latvia","BRA":"Brazil",
 "ROU":"Romania","COL":"Colombia","CRO":"Croatia","SUI":"Switzerland","GBR":"Great Britain",
 "AUS":"Australia","JPN":"Japan","SRB":"Serbia","SVK":"Slovak Republic","DEN":"Denmark",
 "NED":"Netherlands","BEL":"Belgium","EST":"Estonia","MEX":"Mexico","SLO":"Slovenia",
 "HUN":"Hungary","ARG":"Argentina","AUT":"Austria","POR":"Portugal","SWE":"Sweden",
 "NOR":"Norway","FIN":"Finland","BUL":"Bulgaria","LTU":"Lithuania","GEO":"Georgia",
 "IND":"India","THA":"Thailand","EGY":"Egypt","PUR":"Puerto Rico","SVN":"Slovenia","UZB":"Uzbekistan",
 "TPE":"Chinese Taipei","HKG":"Hong Kong","INA":"Indonesia","PHI":"Philippines","RSA":"South Africa",
 "MDA":"Moldova","LUX":"Luxembourg","URU":"Uruguay","PAR":"Paraguay","BOL":"Bolivia",
 "SGP":"Singapore","TUR":"Turkey","ISR":"Israel","NZL":"New Zealand","IRL":"Ireland",
}

def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s

_ACRONYMS = {"Wta":"WTA","Atp":"ATP","Bnp":"BNP","Bnl":"BNL","Us":"US","Hsbc":"HSBC",
             "Dc":"DC","Wm":"WM","Jsm":"JSM"}
def fix_name(s):
    """undo str.title() damage on tennis acronyms (Wta -> WTA, Bnp -> BNP, Us Open -> US Open)"""
    return re.sub(r"[A-Za-z]+", lambda m: _ACRONYMS.get(m.group(0), m.group(0)), s)

def fmt_name(first, last):
    """opponent display key must equal template's `${first[0]}. ${last}`"""
    fi = (first or "").strip()
    return (fi[0] + ". " if fi else "") + (last or "").strip()

# WTA round_name -> template round token.  Q = QuarterFinal, S = SemiFinal here.
ROUND = {"F":"F","S":"SF","Q":"QF","R16":"R16","R32":"R32","R64":"R64","R128":"R128",
         "R256":"R128","RR":"RR","BR":"RR"}
def norm_round(r):
    r = (r or "").upper()
    if re.match(r"^Q[0-9]", r):      # real qualifying (Q1/Q2/Q3)
        return r
    return ROUND.get(r, r)

# WTA level -> template type code
LEVEL = {"Grand Slam":"GS","WTA 1000":"1000","WTA 500":"500","WTA 250":"250",
         "WTA Finals":"WF","United Cup":"UC","Billie Jean King Cup":"BJK","BJK Cup":"BJK"}
KEEP = set(LEVEL)                    # only main-tour events become cards' tournaments

def parse_profile(id_, full_name):
    """returns dict: bio + official ytd/career stats + torso image url + slug"""
    txt = None
    # the slug URL serves the full profile (data-player-stats blob + bio); id-only does not
    for url in (f"https://www.wtatennis.com/players/{id_}/{slugify(full_name)}",
                f"https://www.wtatennis.com/players/{id_}/{slugify(full_name)}/overview"):
        try:
            txt = _get(url, as_json=False)
            if 'data-player-stats' in txt:
                break
        except Exception:
            pass
    if not txt:
        return {}
    out = {}
    m = re.search(r'data-player-stats="([^"]+)"', txt)
    if m:
        try: out["stats"] = json.loads(html.unescape(m.group(1)))
        except Exception: out["stats"] = None
    # schema.org additionalProperty name/value pairs
    pairs = {n: v for n, v in re.findall(r'"name":\s*"([^"]+)",\s*"value":\s*"([^"]*)"', txt)}
    # HEIGHT — prefer the page's own foot/inch string; else derive it from the metric value
    mft = re.search(r'(\d)\'\s*(\d{1,2})"?\s*\(([12]\.\d{2})\s*m\)', txt)
    if mft:
        out["height"] = f"{mft.group(1)}'{mft.group(2)}\" ({mft.group(3)}m)"
    else:
        mh = re.search(r'([12]\.\d{2})\s*m\)', txt) or re.search(r'>\s*([12]\.\d{2})\s*m\b', txt)
        if mh:
            m = float(mh.group(1)); tot_in = round(m / 0.0254)
            out["height"] = f"{tot_in//12}'{tot_in%12}\" ({m:.2f}m)"
        else:
            out["height"] = ""
    out["plays"] = pairs.get("Plays", "")
    mc = re.search(r'Coached by ([^<\n,]+)', txt)
    out["coach"] = mc.group(1).strip() if mc else ""
    ma = re.search(r'"addressLocality":\s*"([^"]+)"', txt)
    out["birthCity"] = ma.group(1).strip() if ma else ""
    # torso / hero cutout image
    mi = re.search(r'https://photoresources\.wtatennis\.com/[^"\']*?(?:Torso|Headshot|Hero|Full)[^"\']*?_?%s[^"\']*\.png[^"\']*' % id_, txt)
    if not mi:
        mi = re.search(r'https://photoresources\.wtatennis\.com/photo-resources/[^"\']*%s[^"\']*\.png[^"\']*' % id_, txt)
    out["img"] = mi.group(0) if mi else ""
    return out

def build_tournaments(matches):
    """group a player's 2026 singles matches into tournament objects"""
    order, groups = [], {}
    for m in matches:
        if m.get("s_d_flag") != "S":
            continue
        t = m.get("tournament") or {}
        lvl = LEVEL.get(t.get("tournamentGroup", {}).get("level") or t.get("level"))
        if lvl is None:                       # skip ITF / WTA 125 etc (like ATP: main tour only)
            continue
        key = (t.get("tournamentGroup", {}).get("id"), t.get("year"))
        if key not in groups:
            order.append(key)
            surf = (t.get("surface") or "").lower()
            groups[key] = {
                "gid": t.get("tournamentGroup", {}).get("id"),
                "name": fix_name(re.sub(r"\s*[-–].*$", "", (t.get("title") or t.get("tournamentGroup", {}).get("name") or "").title()).strip()
                        or (t.get("tournamentGroup", {}).get("name") or "").title()),
                "loc": {"EventCity": (t.get("city") or "").title(),
                        "EventCountry": CC.get(t.get("country"), (t.get("country") or "").title()),
                        "EventLocation": (t.get("city") or "").title()},
                "type": lvl,
                "surface": "hard" if "hard" in surf else "clay" if "clay" in surf else "grass" if "grass" in surf else surf,
                "draw": t.get("singlesDrawSize"),
                "points": m.get("points_champ_1") or m.get("points_1") or 0,
                "prize": 0, "cur": "$",
                "start": t.get("startDate"), "_matches": [],
            }
        groups[key]["prize"] = max(groups[key]["prize"], m.get("PrizeWon") or 0)
        g = groups[key]
        won = (m.get("winner") == 1)
        rnd = norm_round(m.get("round_name"))
        op = m.get("opponent") or {}
        is_bye = not (op.get("lastName") or op.get("id"))       # no real opponent = bye
        reason = (m.get("reason_code") or "").upper()
        walkover = reason in ("WO", "W/O", "DEF")
        score = re.sub(r"\s+", " ", (m.get("scores") or "").strip())
        g["_matches"].append({
            "round": rnd,
            "wl": "W" if won else "L",
            "bye": is_bye,
            "walkover": walkover,
            "opp": fmt_name(op.get("firstName"), op.get("lastName")),
            "oppC": op.get("countryCode"),
            "oppR": (m.get("rank_2") or None),
            "oppSeed": m.get("seed_2"),
            "score": "" if (walkover or is_bye) else score,
            "_rlevel": {"F":7,"SF":6,"QF":5,"R16":4,"R32":3,"R64":2,"R128":1,"RR":5}.get(rnd, 0),
        })
    out = []
    for key in order:
        g = groups[key]
        ms = g.pop("_matches")
        ms.sort(key=lambda x: x.pop("_rlevel"))     # shallow -> deep for display order
        # tournament result: champion if won the final, else round of the loss
        result = "-"
        won_final = any(x["round"] == "F" and x["wl"] == "W" for x in ms)
        if won_final:
            result = "W"
        else:
            losses = [x for x in ms if x["wl"] == "L"]
            deep = max(ms, key=lambda x: {"F":7,"SF":6,"QF":5,"R16":4,"R32":3,"R64":2,"R128":1,"RR":5}.get(x["round"],0)) if ms else None
            loss = losses[-1] if losses else None
            result = (loss or deep or {}).get("round", "-")
        g["result"] = result
        g["title"] = won_final
        g["won"] = sum(1 for x in ms if x["wl"] == "W" and not x["bye"])
        g["lost"] = sum(1 for x in ms if x["wl"] == "L" and not x["bye"])
        g["matches"] = ms[::-1]      # display final-first (F→…→R128), matching the ATP modal
        out.append(g)
    out.sort(key=lambda g: g.get("start") or "", reverse=True)   # latest tournament first, like ATP
    return out

def wl_split(s):
    m = re.match(r"\s*(\d+)\s*/\s*(\d+)", s or "")
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

def build_player(row, race):
    p = row["player"]
    id_ = p["id"]
    prof = parse_profile(id_, p.get("fullName",""))
    st = prof.get("stats") or {}
    ytd = (st.get("ytd") or {}).get("singles") or {}
    car = (st.get("career") or {}).get("singles") or {}
    yw, yl = wl_split(ytd.get("winLoss"))
    cw, cl = wl_split(car.get("winLoss"))
    matches = _get(f"{API}/players/{id_}/matches?year=2026&pageSize=300").get("matches", [])
    tournaments = build_tournaments(matches)
    ytd_titles = ytd.get("titles", sum(1 for t in tournaments if t.get("title")))
    # birth year -> age
    dob = p.get("dateOfBirth") or ""
    age = 2026 - int(dob[:4]) if dob[:4].isdigit() else None
    hi = car.get("rank")
    country = CC.get(p.get("countryCode"), (p.get("countryCode") or "").title())
    race2026 = sum((t.get("points") or 0) for t in tournaments)   # WTA Race = 2026 points earned
    def money(v):
        try: return "${:,}".format(int(v))
        except Exception: return ""
    obj = {
        "rank": row["ranking"],
        "id": str(id_),
        "slug": slugify(p.get("fullName","")),
        "first": p.get("firstName",""),
        "last": p.get("lastName",""),
        "country": country,
        "cc": p.get("countryCode"),
        "age": age,
        "birthDate": dob,
        "birthCity": prof.get("birthCity",""),
        "heightFt": prof.get("height",""),
        "plays": {"Description": prof.get("plays","")},
        "coach": prof.get("coach",""),
        "hiRank": hi,
        "hiRankDate": car.get("highRankDate",""),
        "points": "{:,}".format(row["points"]),
        "ytdWon": yw, "ytdLost": yl,
        "ytdTitles": ytd_titles,
        "ytdPrize": money((st.get("ytd") or {}).get("prizeMoney")),
        "carWon": cw, "carLost": cl,
        "carTitles": car.get("titles", 0),
        "carPrize": money((st.get("career") or {}).get("prizeMoney")),
        "raceRank": None,                    # assigned in main() by 2026-points order
        "racePoints": "{:,}".format(race2026),
        "_raceSum": race2026,
        "tournaments": tournaments,
        "_img": prof.get("img",""),
    }
    return obj

def fetch_ranked(rank_type):
    rows = []
    for page in range(0, 6):
        part = _get(f"{API}/players/ranked?page={page}&pageSize=50&type={rank_type}&sort=asc&metric=SINGLES&at={AT}")
        rows += part
        if len(part) < 50:
            break
    return rows

def main():
    print("· rankings …", flush=True)
    ranked = fetch_ranked("rankSingles")[:100]
    print(f"  {len(ranked)} ranked", flush=True)

    players = [None] * len(ranked)
    with ThreadPoolExecutor(max_workers=2) as ex:   # gentle: avoid api.wtatennis.com 429 rate-limit
        futs = {ex.submit(build_player, row, None): i for i, row in enumerate(ranked)}
        done = 0
        for f in as_completed(futs):
            i = futs[f]
            try:
                players[i] = f.result()
            except Exception as e:
                players[i] = {"rank": ranked[i]["ranking"], "id": str(ranked[i]["player"]["id"]),
                              "first": ranked[i]["player"].get("firstName",""), "last": ranked[i]["player"].get("lastName",""),
                              "_error": str(e), "tournaments": []}
                print(f"  ! {ranked[i]['player'].get('lastName')} : {e}", flush=True)
            done += 1
            if done % 10 == 0:
                print(f"  {done}/{len(ranked)}", flush=True)

    players.sort(key=lambda x: x["rank"])
    for i, p in enumerate(players):
        p["nextBest"] = players[i+1]["last"] if i+1 < len(players) else ""
    # WTA Race to the WTA Finals: rank everyone by 2026 points earned
    for i, p in enumerate(sorted(players, key=lambda x: -x.get("_raceSum", 0))):
        p["raceRank"] = i + 1
    for p in players:
        p.pop("_raceSum", None)

    # image url manifest (downloaded separately)
    imgs = {p["id"]: p.pop("_img","") for p in players}
    data = {"tour": "wta", "ranking_date": AT, "players": players}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(os.path.dirname(OUT), "wta_images.json"), "w") as fh:
        json.dump(imgs, fh)

    # diagnostics
    miss_flag = sorted({p["country"] for p in players if p.get("country") and p["country"] not in FLAG_KEYS})
    miss_img = [p["id"] for p in players if not imgs.get(p["id"])]
    miss_bio = [(p["rank"], p["last"]) for p in players if not p.get("heightFt")]
    print(f"✓ wrote {OUT}  ({os.path.getsize(OUT)//1024} KB, {len(players)} players)")
    print(f"  countries not in FLAG map: {miss_flag}")
    print(f"  players without image: {len(miss_img)} {miss_img[:12]}")
    print(f"  players without bio height: {len(miss_bio)} {miss_bio[:12]}")

# template FLAG keys (to flag any country needing a map addition)
FLAG_KEYS = {"Italy","Germany","Spain","Canada","Serbia","Australia","Russia","United States",
 "Great Britain","France","Kazakhstan","Czechia","Norway","Monaco","Argentina","Greece","Denmark",
 "Netherlands","Chile","Bulgaria","Poland","Switzerland","Austria","Hungary","Finland","Portugal",
 "Belgium","Croatia","Japan","China","Brazil","Bahrain","Dominican Republic","Ecuador","Hong Kong",
 "Mexico","Morocco","New Zealand","Paraguay","Qatar","Romania","Rwanda","Slovak Republic","South Korea",
 "Sweden","United Arab Emirates","Peru","Bolivia","Georgia","Estonia","Jordan","Lebanon","Luxembourg",
 "Jamaica","North Macedonia","Slovenia","Latvia","Lithuania","Ukraine","Moldova","Uruguay","India",
 "South Africa","Bosnia and Herzegovina","Belarus","Chinese Taipei","Tunisia"}

if __name__ == "__main__":
    main()
