#!/usr/bin/env python3
"""Build the 2026 WTA season calendar and merge it into data/wta_players.json.
Schedule comes from the tournaments API; the final-four (champion / runner-up /
semi-finalists) is reconstructed from the top-100 players' own match records
(matched by tournamentGroup id), exactly like the ATP calendar."""
import json, os, re, urllib.request
from build_wta import CC, fix_name          # reuse the 3-letter -> country-name map + acronym fixup

HERE = os.path.dirname(os.path.abspath(__file__))
HDRS = {"account": "wta", "User-Agent": "Mozilla/5.0"}
DATA = os.path.join(HERE, "data", "wta_players.json")

LEVEL_CAT = {"Grand Slam": "GS", "WTA 1000": "1000", "WTA 500": "500",
             "WTA 250": "250", "Finals": "WTA Finals", "WTA Finals": "WTA Finals"}
CC2 = dict(CC); CC2.update({"SIN": "Singapore", "KOR": "South Korea", "GREAT BRITAIN": "Great Britain"})

def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=HDRS), timeout=40))

def country_name(code):
    if not code: return ""
    code = code.strip()
    if len(code) == 3: return CC2.get(code, code.title())
    return CC2.get(code.upper(), code.title())

def surf(s):
    s = (s or "").lower()
    return "hard" if "hard" in s else "clay" if "clay" in s else "grass" if "grass" in s else "hard"

def fetch_schedule():
    out = {}
    for page in range(0, 12):
        d = get(f"https://api.wtatennis.com/tennis/tournaments?from=2026-01-01&to=2026-12-31&page={page}&pageSize=100")
        for t in d["content"]:
            lvl = t["tournamentGroup"].get("level") or t.get("level")
            if lvl not in LEVEL_CAT:
                continue
            name = (t["tournamentGroup"].get("name") or "").upper()
            if "UNITED CUP" in name:                      # mixed-team event: no individual final four
                continue
            gid = t["tournamentGroup"]["id"]
            out[(gid, t.get("startDate"))] = {
                "gid": gid,
                "cat": LEVEL_CAT[lvl],
                "name": fix_name((t.get("title") or t["tournamentGroup"]["name"]).split(" - ")[0].strip().title() or t["tournamentGroup"]["name"].title()),
                "city": (t.get("city") or "").title(),
                "country": country_name(t.get("country")),
                "surface": surf(t.get("surface")),
                "start": t.get("startDate"), "end": t.get("endDate"),
            }
        if len(d["content"]) < 100:
            break
    return list(out.values())

def reconstruct_final_four(players):
    """gid -> {winner, runner, sf[]}, each player = {name:'F. Last', ioc:'XXX'}"""
    fin, semis = {}, {}
    for p in players:
        me = {"name": f"{(p.get('first') or ' ')[0]}. {p['last']}", "ioc": p.get("cc")}
        for t in p.get("tournaments", []):
            gid = t.get("gid")
            if gid is None:
                continue
            for m in t.get("matches", []):
                if m.get("bye"):
                    continue
                opp = {"name": m.get("opp"), "ioc": m.get("oppC")}
                if m["round"] == "F":
                    fin[gid] = ({"winner": me, "runner": opp} if m["wl"] == "W"
                                else {"winner": opp, "runner": me})
                elif m["round"] == "SF":
                    loser = me if m["wl"] == "L" else opp     # the SF loser is a semi-finalist
                    semis.setdefault(gid, {})
                    if loser["name"]:
                        semis[gid][loser["name"]] = loser
    out = {}
    for gid, f in fin.items():
        sfs = [v for k, v in semis.get(gid, {}).items()
               if k not in (f["winner"]["name"], f["runner"]["name"])][:2]
        out[gid] = {**f, "sf": sfs}
    return out

def main():
    data = json.load(open(DATA, encoding="utf-8"))
    sched = fetch_schedule()
    ff = reconstruct_final_four(data["players"])
    n_played = 0
    for e in sched:
        r = ff.get(e["gid"])
        if r:
            e["winner"], e["runner"], e["sf"] = r["winner"], r["runner"], r.get("sf", [])
            n_played += 1
        if e["cat"] == "WTA Finals":
            e["name"] = "WTA Finals"                 # city shown separately; avoid redundant "… Indian Wells"
        e.pop("gid", None)
    sched.sort(key=lambda e: e["start"])
    data["calendar"] = sched
    json.dump(data, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    from collections import Counter
    cats = Counter(e["cat"] for e in sched)
    print(f"✓ calendar merged: {len(sched)} events ({dict(cats)}); {n_played} with results")
    miss = [(e["name"], e["start"]) for e in sched if e["start"] < "2026-07-27" and "winner" not in e]
    print(f"  played-but-no-final-four: {len(miss)} {miss[:8]}")

if __name__ == "__main__":
    main()
