#!/usr/bin/env python3
"""Build season.html — the animated "player 2026 film" (globe + match-by-match).

Reads data/players.json (+ data/rank_history_<id>.json) and inlines one player's
ATP-tour season into season_template.html.  Team events (United Cup, Davis Cup,
Laver Cup) and byes are left out.

  python3 build_season.py                 # Zverev
  python3 build_season.py --player z355
"""
import argparse, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ATP_TYPES = ("GS", "1000", "500", "250", "WC")

# venue coordinates (lat, lon) for every ATP-tour city in the data
CITY = {
    "'s-Hertogenbosch": (51.69, 5.30), "Acapulco": (16.85, -99.82), "Adelaide": (-34.93, 138.60),
    "Almaty": (43.24, 76.89), "Auckland": (-36.85, 174.76), "Barcelona": (41.39, 2.17),
    "Basel": (47.56, 7.59), "Bastad": (56.43, 12.85), "Beijing": (39.90, 116.40),
    "Brisbane": (-27.47, 153.03), "Brussels": (50.85, 4.35), "Bucharest": (44.43, 26.10),
    "Buenos Aires": (-34.60, -58.38), "Chengdu": (30.57, 104.07), "Cincinnati": (39.10, -84.51),
    "Dallas": (32.78, -96.80), "Delray Beach": (26.46, -80.07), "Doha": (25.29, 51.53),
    "Dubai": (25.20, 55.27), "Eastbourne": (50.77, 0.28), "Estoril": (38.71, -9.40),
    "Geneva": (46.20, 6.14), "Gstaad": (46.48, 7.29), "Halle": (52.06, 8.36),
    "Hamburg": (53.55, 9.99), "Hangzhou": (30.27, 120.16), "Hong Kong": (22.32, 114.17),
    "Houston": (29.76, -95.37), "Indian Wells": (33.72, -116.31), "Kitzbuhel": (47.45, 12.39),
    "London": (51.43, -0.21), "Los Cabos": (22.89, -109.91), "Lyon": (45.76, 4.84),
    "Madrid": (40.42, -3.70), "Mallorca": (39.70, 3.03), "Marrakech": (31.63, -8.01),
    "Melbourne": (-37.82, 144.98), "Miami": (25.76, -80.19), "Monte-Carlo": (43.75, 7.44),
    "Montpellier": (43.61, 3.88), "Montreal": (45.50, -73.57), "Munich": (48.14, 11.58),
    "New York": (40.75, -73.85), "Paris": (48.85, 2.25), "Rio de Janeiro": (-22.91, -43.17),
    "Rome": (41.93, 12.46), "Rotterdam": (51.92, 4.48), "Santiago": (-33.45, -70.67),
    "Shanghai": (31.23, 121.47), "Stockholm": (59.33, 18.07), "Stuttgart": (48.78, 9.18),
    "Tokyo": (35.68, 139.69), "Turin": (45.07, 7.69), "Umag": (45.43, 13.52),
    "Vienna": (48.21, 16.37), "Washington": (38.91, -77.04), "Winston-Salem": (36.10, -80.24),
}
# event prize money is in local currency; fixed approximate rates to show one running US$ total
TO_USD = {"$": 1.0, "€": 1.10, "£": 1.30, "A$": 0.66}
IOC2 = {
    "ARG": "AR", "AUS": "AU", "AUT": "AT", "BEL": "BE", "BIH": "BA", "BOL": "BO", "BRA": "BR", "BUL": "BG",
    "CAN": "CA", "CHI": "CL", "CHN": "CN", "COL": "CO", "CRO": "HR", "CZE": "CZ", "DEN": "DK", "ECU": "EC",
    "ESP": "ES", "EST": "EE", "FIN": "FI", "FRA": "FR", "GBR": "GB", "GEO": "GE", "GER": "DE", "GRE": "GR",
    "HKG": "HK", "HUN": "HU", "IND": "IN", "ITA": "IT", "JPN": "JP", "KAZ": "KZ", "KOR": "KR", "LTU": "LT",
    "MDA": "MD", "MON": "MC", "NED": "NL", "NOR": "NO", "NZL": "NZ", "PAR": "PY", "PER": "PE", "POL": "PL",
    "POR": "PT", "QAT": "QA", "ROU": "RO", "RSA": "ZA", "SRB": "RS", "SLO": "SI", "SUI": "CH", "SVK": "SK",
    "SWE": "SE", "TPE": "TW", "TUN": "TN", "UKR": "UA", "URU": "UY", "USA": "US", "UZB": "UZ", "LBN": "LB",
}
NEUTRAL = {"RUS", "BLR"}
COUNTRY2 = {"Germany": "DE", "Spain": "ES", "Italy": "IT", "France": "FR", "United States": "US", "Serbia": "RS",
            "Australia": "AU", "Canada": "CA", "Great Britain": "GB", "Czechia": "CZ", "Norway": "NO",
            "Denmark": "DK", "Greece": "GR", "Poland": "PL", "Belgium": "BE", "Argentina": "AR", "Brazil": "BR",
            "Netherlands": "NL", "Switzerland": "CH", "Chile": "CL", "Portugal": "PT", "Kazakhstan": "KZ"}
# opponents outside the top-100 dataset: ATP id (photo in img/full/<id>.png, gladiator cutout
# fetched from atptour.com) + full name, from the player's /activity JSON (OpponentId/FirstName)
OPP_EXTRA = {
    "G. Diallo": ("d0f6", "Gabriel Diallo"), "A. Muller": ("mp20", "Alexandre Muller"),
    "C. Moutet": ("mw02", "Corentin Moutet"), "M. Damm": ("d0dt", "Martin Damm"),
    "C. Garin": ("gd64", "Cristian Garin"), "J. de Jong": ("d0c1", "Jesper de Jong"),
    "V. Royer": ("r0eb", "Valentin Royer"), "L. Sonego": ("su87", "Lorenzo Sonego"),
    "J. Shang": ("s0re", "Juncheng Shang"), "Y. Wu": ("wb32", "Yibing Wu"),
}
SURF = {"Hard": "hard", "Clay": "clay", "Grass": "grass"}
CAT = {"GS": "Grand Slam", "1000": "Masters 1000", "500": "ATP 500", "250": "ATP 250", "WC": "ATP Finals"}


def parse_score(s):
    """'6-7(10) 6-1' (player first) -> [[6,7,10],[6,1,None]]"""
    out = []
    for part in s.split():
        m = re.fullmatch(r"(\d+)-(\d+)(?:\((\d+)\))?", part)
        if m:
            out.append([int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else None])
    return out


def fmt_score(sets):
    return " ".join(f"{x}-{y}" + (f"({tb})" if tb is not None else "") for x, y, tb in sets)


def opp_entry(o, rnd, rnd_long, won, sets, has_full):
    return {"round": rnd, "roundLong": rnd_long, "wl": "W" if won else "L",
            "opp": f"{o['first']} {o['last']}", "oppShort": o["last"], "oppC": "", "oppR": o["rank"],
            "oppFlag": COUNTRY2.get(o["country"], ""), "oppImg": o["id"] if o["id"] in has_full else None,
            "score": fmt_score(sets), "sets": sets}


def finals_matches(pid, players, has_full):
    """ATP Finals matches come from data/atp_finals_results.json (kept by the Finals updater;
    read-only here). Scores there are winner-first; flip them to the player's view."""
    path = os.path.join(HERE, "data/atp_finals_results.json")
    if not os.path.exists(path):
        return [], None
    fr, byid = json.load(open(path)), {x["id"]: x for x in players}
    out = []
    for stage, rows in (("RR", fr.get("rr", [])), ("KO", fr.get("ko", []))):
        for m in rows:
            if pid not in (m.get("a"), m.get("b")) or not m.get("w") or not m.get("score"):
                continue
            me_a = m["a"] == pid
            o = byid.get(m["b"] if me_a else m["a"])
            won = (m["w"] == "a") == me_a
            sets = parse_score(m["score"])
            if not won:
                sets = [[y, x, tb] for x, y, tb in sets]
            rnd = "RR" if stage == "RR" else m.get("round", "SF")
            if o:
                out.append(opp_entry(o, rnd, "Round Robin" if rnd == "RR" else rnd, won, sets, has_full))
    played = {(m["a"], m["b"]) for m in fr.get("rr", []) if m.get("w")}
    nxt = None
    for key, v in sorted(fr.get("days", {}).items(), key=lambda kv: kv[1]["day"]):
        a_, b_ = key.split("-")
        if pid in (a_, b_) and (a_, b_) not in played:
            o = byid.get(b_ if a_ == pid else a_)
            if o:
                nxt = {"opp": f"{o['first']} {o['last']}", "day": v["day"], "time": v.get("time")}
            break
    return out, {"next": nxt}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--player", default="z355")
    a = ap.parse_args()

    d = json.load(open(os.path.join(HERE, "data/players.json")))
    players = d["players"]
    p = next(x for x in players if x["id"] == a.player)
    by_abbr = {f"{x['first'][0]}. {x['last']}": x for x in players}
    cal = {c["id"]: c for c in d["calendar"]}
    has_full = set(f[:-4] for f in os.listdir(os.path.join(HERE, "img/full")))
    rh_path = os.path.join(HERE, f"data/rank_history_{a.player}.json")
    rh = json.load(open(rh_path)) if os.path.exists(rh_path) else {}
    ranks, career_high = rh.get("weeks", []), rh.get("careerHigh")

    events = []
    for t in sorted(p["tournaments"], key=lambda t: t["date"]):
        if t["type"] not in ATP_TYPES:
            continue
        city = t["loc"].get("EventCity")
        tid = t["url"].split("/")[-2] if t.get("url") else ""
        c = cal.get(tid, {})
        matches = []
        for m in reversed(t["matches"]):  # data is latest-round-first
            if m.get("bye") or not m.get("opp"):
                continue
            o = by_abbr.get(m["opp"])
            sets = parse_score(m["score"])
            oid = o["id"] if o and o["id"] in has_full else None
            xid, xname = OPP_EXTRA.get(m["opp"], (None, None))
            if not oid and xid in has_full:
                oid = xid
            matches.append({
                "round": m["round"], "roundLong": m["roundLong"], "wl": m["wl"],
                "opp": f"{o['first']} {o['last']}" if o else (xname or m["opp"]),
                "oppShort": m["opp"].split(". ", 1)[-1],
                "oppC": m["oppC"] or "", "oppR": m["oppR"],
                "oppFlag": "" if (m["oppC"] or "") in NEUTRAL else IOC2.get(m["oppC"] or "", ""),
                "oppImg": oid,
                "score": m["score"], "sets": sets,
            })
        live = None
        if t["type"] == "WC":
            matches, live = finals_matches(a.player, players, has_full)
        lat, lon = CITY.get(city, (0, 0))
        events.append({
            "live": live,
            "name": t["name"], "city": city, "country": t["loc"].get("EventCountry"),
            "lat": lat, "lon": lon, "type": t["type"], "cat": CAT[t["type"]],
            "surface": SURF.get(t["surface"], "hard"), "surfaceName": t["surface"],
            "start": c.get("start", t["date"][:10]), "end": c.get("end", t["date"][:10]),
            "draw": t["draw"], "seed": t["seed"], "points": t["points"],
            "result": t["result"], "resultLong": t["resultLong"], "title": t["title"],
            "prizeUSD": round((t.get("prize") or 0) * TO_USD.get(t.get("cur", "$"), 1)),
            "prize": t.get("prize") or 0, "cur": t.get("cur", "$"),
            "matches": matches,
        })

    data = {
        "player": {"id": p["id"], "first": p["first"], "last": p["last"], "country": p["country"],
                   "flag": COUNTRY2.get(p["country"], "")},
        "rankingDate": d.get("ranking_date"), "ranks": ranks, "careerHigh": career_high, "events": events,
    }
    tpl = open(os.path.join(HERE, "season_template.html"), encoding="utf-8").read()
    html = tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    open(os.path.join(HERE, "season.html"), "w", encoding="utf-8").write(html)
    nm = sum(len(e["matches"]) for e in events)
    print(f"season.html: {p['first']} {p['last']} · {len(events)} ATP events · {nm} matches · "
          f"prize ≈ ${sum(e['prizeUSD'] for e in events):,} (ytd {p['ytdPrize']})")


if __name__ == "__main__":
    main()
