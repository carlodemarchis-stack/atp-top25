#!/usr/bin/env python3
"""Refresh the ATP season calendar's final four (champion / runner-up / semi-finalists)
in-place on data/players.json, reconstructed from the top-100 players' own match records.
Events are matched to player tournaments by the tournament id embedded in the match url
(/en/tournaments/<slug>/<ID>/overview  <->  calendar event 'id'). No network needed —
run it after the weekly activity refresh; the schedule metadata already lives in the
calendar array, we only rewrite winner/runner/sf for events that now have a final."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "players.json")

def tid(url):
    m = re.search(r"/tournaments/[^/]+/(\d+)", url or "")
    return m.group(1) if m else None

def reconstruct(players):
    # name -> IOC (every finalist appears as someone's opponent) and name -> current rank
    name2ioc, name2rank = {}, {}
    for p in players:
        name2rank[f"{(p.get('first') or ' ')[0]}. {p['last']}"] = p["rank"]
        for t in p.get("tournaments", []):
            for m in t.get("matches", []):
                if m.get("opp") and m.get("oppC"):
                    name2ioc.setdefault(m["opp"], m["oppC"])

    def entry(name, ioc, fallback_rank):
        return {"name": name, "ioc": ioc, "rank": name2rank.get(name, fallback_rank)}

    fin, semis = {}, {}
    for p in players:
        me_name = f"{(p.get('first') or ' ')[0]}. {p['last']}"
        me = entry(me_name, name2ioc.get(me_name, ""), p["rank"])
        for t in p.get("tournaments", []):
            tt = tid(t.get("url"))
            if not tt:
                continue
            for m in t.get("matches", []):
                if m.get("bye"):
                    continue
                opp = entry(m.get("opp"), m.get("oppC"), m.get("oppR"))
                if m["round"] == "F":
                    fin[tt] = ({"winner": me, "runner": opp} if m["wl"] == "W"
                               else {"winner": opp, "runner": me})
                elif m["round"] == "SF":
                    loser = me if m["wl"] == "L" else opp
                    if loser["name"]:
                        semis.setdefault(tt, {})[loser["name"]] = loser
    out = {}
    for tt, f in fin.items():
        sfs = [v for k, v in semis.get(tt, {}).items()
               if k not in (f["winner"]["name"], f["runner"]["name"])][:2]
        out[tt] = {**f, "sf": sfs}
    return out

def main():
    data = json.load(open(DATA, encoding="utf-8"))
    ff = reconstruct(data["players"])
    updated = 0
    for e in data.get("calendar", []):
        r = ff.get(str(e.get("id")))
        if r:                                   # played (has a final) → refresh; else leave as upcoming
            e["winner"], e["runner"], e["sf"] = r["winner"], r["runner"], r.get("sf", [])
            updated += 1
    json.dump(data, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"✓ ATP calendar refreshed: {updated}/{len(data.get('calendar', []))} events have a final four")
    # spot-check the newest completed Masters
    for e in data.get("calendar", []):
        if str(e.get("id")) == "421":           # Canada / Toronto
            w = e.get("winner", {})
            print(f"  Toronto winner: {w.get('name')} ({w.get('ioc')})  runner: {e.get('runner',{}).get('name')}")

if __name__ == "__main__":
    main()
