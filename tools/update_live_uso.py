#!/usr/bin/env python3
"""Mark the US Open singles matches being played right now, from the tournament's own live feed.

usopen.org publishes the real-time score; the ATP site's LiveMatches feed can lag by an hour or
more, so this is the source for anything in progress. Run it AFTER update_uso_{atp,wta}_live.py,
which re-splice the trees and would drop the flag.
"""
import json, re, urllib.request

F   = "montreal_bracket.html"
URL = "https://www.usopen.org/en_US/scores/feeds/2026/matches/live/scores.json"
UA  = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/127.0 Safari/537.36"}

pid = lambda x: re.sub(r"^(atp|wta)", "", (x or "").strip().lower())   # "atpz355" -> "z355"

def tokens(sets):
    """per-set cells for both players; the last set is the one in play, so it never gets a
    tie-break superscript. Elsewhere the superscript marks the LOSER of the breaker."""
    a, b = [], []
    for i, s in enumerate(sets):
        ga, gb = str(s[0].get("score") or ""), str(s[1].get("score") or "")
        ta, tb = s[0].get("tiebreak"), s[1].get("tiebreak")
        if i < len(sets)-1 and ta is not None and tb is not None:
            if   int(ta) < int(tb): ga += str(ta)
            elif int(tb) < int(ta): gb += str(tb)
        a.append(ga); b.append(gb)
    return a, b

live = {}          # frozenset(ids) -> record
feed = json.load(urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=60))
for m in feed.get("matches", []):
    ev = m.get("eventName") or ""
    if ev not in ("Men's Singles", "Women's Singles"): continue
    if m.get("status") != "In Progress": continue
    ia, ib = pid(m["team1"]["idA"]), pid(m["team2"]["idA"])
    sets = m["scores"]["sets"]
    sa, sb = tokens(sets)
    g = [str(x) for x in (m["scores"].get("gameScore") or ["", ""])]
    last = sets[-1] if sets else None
    tb = bool(last and last[0].get("tiebreak") is not None and last[1].get("tiebreak") is not None)
    live[frozenset([ia, ib])] = {"tour": "atp" if ev.startswith("Men") else "wta", "ids": [ia, ib],
        "sc": {ia: sa, ib: sb}, "g": g, "tb": tb, "srv": m.get("server"), "dur": m.get("duration") or "",
        "who": m["team1"]["displayNameA"] + " v " + m["team2"]["displayNameA"]}

h = open(F).read()
hits, cleared = [], [0]
def apply(tree, tour):
    def walk(n):
        if n.pop("live", None) is not None: cleared[0] += 1      # yesterday's live match is over
        ids = [p["id"] for p in n.get("p", []) if p.get("id")]
        if len(ids) == 2:
            rec = live.get(frozenset(ids))
            if rec and rec["tour"] == tour and not any(p.get("w") for p in n["p"]):
                for p in n["p"]:
                    p["sc"] = rec["sc"].get(p["id"], [])
                srv = None                                   # "A"/"B" is the feed's own player order
                if rec["srv"] in ("A", "B"):
                    sid = rec["ids"][0 if rec["srv"] == "A" else 1]
                    srv = next((k for k, p in enumerate(n["p"]) if p.get("id") == sid), None)
                n["live"] = {"g": rec["g"], "tb": rec["tb"], "dur": rec["dur"], "srv": srv}
                hits.append(rec["who"] + "  " + " ".join(f"{a}-{b}" for a, b in
                            zip(rec["sc"][ids[0]], rec["sc"][ids[1]])) +
                            ("  [tb " if rec["tb"] else "  [game ") + "-".join(rec["g"]) + "]")
        for c in n.get("c", []): walk(c)
    walk(tree)

key = "const TREE_USO = "; i = h.index(key)+len(key)
A, end = json.JSONDecoder().raw_decode(h, i); assert h[end] == ";"
apply(A, "atp")
h = h[:i] + json.dumps(A, ensure_ascii=False, separators=(",", ":")) + h[end:]

key = "const WTA_TREES = "; i = h.index(key)+len(key)
W, end = json.JSONDecoder().raw_decode(h, i); assert h[end] == ";"
apply(W["USO"], "wta")
h = h[:i] + json.dumps(W, ensure_ascii=False, separators=(",", ":")) + h[end:]

open(F, "w").write(h)
print("live singles matches:", len(hits), "| stale flags cleared:", cleared[0])
for x in hits: print("  ", x)
