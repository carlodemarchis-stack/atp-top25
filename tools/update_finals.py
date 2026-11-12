#!/usr/bin/env python3
"""Year-end Finals (round robin) -> `const FINALS = {...};` in draws.html.

usage: python3 tools/update_finals.py            # from the atp-cards folder

WTA  — fetched from api.wtatennis.com (tournament 808): groups, alternates, results, live score, knockout.
ATP  — groups below + seeds from data/players.json (Race order of the eight who play); results come from
       data/atp_finals_results.json when it exists (atptour is behind Cloudflare: read the results page
       in the browser and write them there). Format, winner's score first:
         {"rr": [{"a": "z355", "b": "s0s1", "day": 1, "w": "a", "score": "6-4 7-6(3)", "dur": "1:32"}],
          "ko": [{"round": 2, "a": "z355", "b": "c0e9", "w": "a", "score": "6-3 6-4"},   # semi-finals
                 {"round": 1, "a": "...", "b": "...", "w": "b", "score": "..."}],         # final
          "days": {"z355-s0s1": 1}}                                                        # order of play, optional
       day 1 = Sun 15 Nov … day 6 = Fri 20 (round robin), 7 = SF (Sat 21), 8 = Final (Sun 22).
"""
import datetime as dt, itertools, json, os, re, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAWS = os.path.join(ROOT, "draws.html")
NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

# ---------------------------------------------------------------- WTA
def wta_get(path):
    req = urllib.request.Request("https://api.wtatennis.com/tennis/tournaments/" + path,
                                 headers={"account": "wta", "accept": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))

def build_wta(gid=808, year=2026, start=dt.date(2026, 11, 8), utc=-8):
    draw = json.loads(wta_get(f"{gid}/{year}/draw")["drawInfo"][0])
    mjs = wta_get(f"{gid}/{year}/matches")["matches"]
    ev = next(e for e in draw["Draws"]["Events"]["Event"] if e["EventTypeCode"] == "LS")
    day0 = start - dt.timedelta(days=1)               # dSeq 1 = first day
    live = {m["MatchID"]: m for m in mjs if m["DrawMatchType"] == "S"}
    players, groups = {}, []
    for g in ev["RoundRobinGroups"]["Group"]:
        groups.append({"name": g["Name"], "ids": [], "out": []})
    gi = {g["name"]: i for i, g in enumerate(groups)}

    def addp(p, seed, etype=""):
        pid = str(p["id"])
        players.setdefault(pid, {"id": pid, "first": p["FirstName"], "last": p["SurName"],
                                 "cc": p["Country"], "seed": int(seed or 0), "alt": etype == "ALT"})
        return pid

    def score(lm):                                   # winner's score first, sets space-separated
        return lm["ResultString"].rsplit(" ", 1)[-1].replace(",", " ")

    drawn = {}
    for dl in ev["Draw"]["DrawLine"]:
        drawn.setdefault(dl["GroupName"], []).append(addp(dl["Players"]["Player"], dl["Seed"]))

    matches, ko = [], []
    for rnd in ev["Results"]["Round"]:
        for m in (rnd["Match"] if isinstance(rnd["Match"], list) else [rnd["Match"]]):
            pts = m["Players"]["PT"] if isinstance(m["Players"], dict) else []
            pts = pts if isinstance(pts, list) else [pts]
            lm = live.get(m["Id"], {})
            rec = {"id": m["Id"], "day": int(m.get("dSeq") or 0) or None, "state": lm.get("MatchState") or m["mState"]}
            if m.get("RRGroup"):
                a, b = (addp(p["Player"], p.get("seed"), p.get("eType", "")) for p in pts)
                g = groups[gi[m["RRGroup"]]]
                g["ids"] += [x for x in (a, b) if x not in g["ids"]]
                rec.update(g=gi[m["RRGroup"]], a=a, b=b)
                if rec["state"] == "F" and lm:
                    rec.update(w="a" if lm["Winner"] == "2" else "b", score=score(lm),
                               ts=lm["MatchTimeStamp"], dur=lm.get("MatchTimeTotal", ""))
                    # dSeq is an order-of-play number, not always the day: use the local date it was played
                    t = dt.datetime.strptime(lm["MatchTimeStamp"][:19], "%Y-%m-%dT%H:%M:%S") + dt.timedelta(hours=utc)
                    rec["day"] = (t.date() - day0).days
                elif lm and rec["state"] not in ("F", "U", "N", ""):     # on court / suspended: player A's side first
                    rec["live"] = (lm.get("ScoreString") or "0-0").replace(",", " ")
                matches.append(rec)
            else:
                rec.update(round=rnd["roundId"], day=8 if rnd["roundId"] == 1 else 7)
                if lm.get("MatchState") == "F":
                    rec.update(a=str(lm["PlayerIDA"]), b=str(lm["PlayerIDB"]),
                               w="a" if lm["Winner"] == "2" else "b", score=score(lm))
                ko.append(rec)

    # seats follow the draw order; a drawn player with no match withdrew and the alternate takes the seat
    for g in groups:
        order = drawn.get(g["name"], [])
        seats = [p for p in order if p in g["ids"]]
        g["out"] = [p for p in order if p not in g["ids"]]
        seats += [x for x in g["ids"] if x not in seats]
        for o in g["out"]:
            alt = next((x for x in seats if players[x]["alt"]), None)
            if alt:
                seats.remove(alt); seats.insert(order.index(o), alt)
        g["ids"] = seats
    return {"tour": "wta", "short": "WTA Finals", "name": "WTA Finals", "loc": "Indian Wells", "flag": "🇺🇸",
            "dates": "8–15 Nov", "start": str(start), "utc": utc, "trophy": "Billie Jean King Trophy", "asof": NOW,
            "players": players, "groups": groups, "matches": matches, "ko": ko}

# ---------------------------------------------------------------- ATP
ATP_GROUPS = [("John McEnroe Group", ["z355", "s0s1", "f0f1", "j0dz"]),     # announced 12 Nov 2026
              ("Ivan Lendl Group",   ["a0e2", "mm58", "c0e9", "td51"])]
IOC = {"Germany": "GER", "Spain": "ESP", "United States": "USA", "Russia": "RUS", "Italy": "ITA", "France": "FRA",
       "Great Britain": "GBR", "Australia": "AUS", "Canada": "CAN", "Norway": "NOR", "Denmark": "DEN", "Serbia": "SRB",
       "Czechia": "CZE", "Poland": "POL", "Greece": "GRE", "Belgium": "BEL", "Argentina": "ARG", "Brazil": "BRA"}

def build_atp():
    ps = {p["id"]: p for p in json.load(open(os.path.join(ROOT, "data", "players.json")))["players"]}
    field = sorted((i for _, ids in ATP_GROUPS for i in ids), key=lambda i: ps[i]["raceRank"])
    players = {i: {"id": i, "first": ps[i]["first"], "last": ps[i]["last"], "cc": IOC.get(ps[i]["country"], ""),
                   "seed": field.index(i) + 1, "alt": False} for i in field}
    res_path = os.path.join(ROOT, "data", "atp_finals_results.json")
    res = json.load(open(res_path)) if os.path.exists(res_path) else {}
    played = {frozenset((r["a"], r["b"])): r for r in res.get("rr", [])}
    days = {frozenset(k.split("-")): v for k, v in res.get("days", {}).items()}
    missing = [p for p in ps.values() if p["raceRank"] and p["raceRank"] <= 8 and p["id"] not in players]
    groups, matches = [], []
    for gi, (name, ids) in enumerate(ATP_GROUPS):
        g = {"name": name, "ids": ids, "out": []}
        if gi == 0 and missing:
            late = max(field, key=lambda i: ps[i]["raceRank"])
            g["note"] = " · ".join(f'{m["last"]} (Race No. {m["raceRank"]}) not in the field' for m in missing) + \
                        f' · {ps[late]["last"]} (No. {ps[late]["raceRank"]}) in'
        groups.append(g)
        for n, (a, b) in enumerate(itertools.combinations(ids, 2)):
            k = frozenset((a, b)); r = played.get(k)
            rec = {"id": f"RR{gi + 1}{n + 1}", "day": (r or {}).get("day") or days.get(k), "state": "F" if r else "N",
                   "g": gi, "a": a, "b": b}
            if r:                                        # keep our a/b orientation, map the winner onto it
                rec.update(w="a" if r[r["w"]] == a else "b", score=r["score"], dur=r.get("dur", ""))
            matches.append(rec)
    ko = [{"id": "SF1", "day": 7, "round": 2}, {"id": "SF2", "day": 7, "round": 2}, {"id": "F", "day": 8, "round": 1}]
    for r in res.get("ko", []):
        slot = next(k for k in ko if k["round"] == r["round"] and "w" not in k)
        slot.update(a=r["a"], b=r["b"], w=r["w"], score=r["score"])
    return {"tour": "atp", "short": "ATP Finals", "name": "Nitto ATP Finals", "loc": "Turin", "flag": "🇮🇹",
            "dates": "15–22 Nov", "start": "2026-11-15", "utc": 1, "trophy": "", "asof": NOW,
            "players": players, "groups": groups, "matches": matches, "ko": ko}

# ---------------------------------------------------------------- splice
def main():
    data = {"atp": build_atp(), "wta": build_wta()}
    line = "const FINALS = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";"
    s = open(DRAWS, encoding="utf-8").read()
    if re.search(r"^const FINALS = .*;$", s, flags=re.M):
        s = re.sub(r"^const FINALS = .*;$", lambda _: line, s, count=1, flags=re.M)
    else:
        s = s.replace("\nconst CX = ", "\n" + line + "\nconst CX = ", 1)
    open(DRAWS, "w", encoding="utf-8").write(s)
    for t, d in data.items():
        done = sum(1 for m in d["matches"] if m.get("w"))
        livem = [f'{d["players"][m["a"]]["last"]}-{d["players"][m["b"]]["last"]} {m["live"]}' for m in d["matches"] if m.get("live")]
        print(f'{t}: {done}/{len(d["matches"])} RR played, KO {sum(1 for k in d["ko"] if k.get("w"))}/3'
              + (f', live: {"; ".join(livem)}' if livem else ""))

if __name__ == "__main__":
    main()
