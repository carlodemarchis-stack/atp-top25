#!/usr/bin/env python3
"""Apply finished US Open singles results from the tournament's own draw feed.

usopen.org/.../draws/MS.json and WS.json carry every match with scores, ids and status.
It is hours ahead of the ATP draw page during play, so this is what keeps the fan current;
the ATP scrape stays useful as a cross-check.
"""
import json, re, urllib.request

F  = "montreal_bracket.html"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/127.0 Safari/537.36"}
URL = "https://www.usopen.org/en_US/scores/feeds/2026/draws/%s.json"
pid = lambda x: re.sub(r"^(atp|wta)", "", (x or "").strip().lower())

def cells(sets):
    """set tokens for both players; the tie-break loser carries the superscript"""
    a, b = [], []
    for s in sets:
        ga, gb = str(s[0].get("scoreDisplay") or ""), str(s[1].get("scoreDisplay") or "")
        ta, tb = s[0].get("tiebreak"), s[1].get("tiebreak")
        if ta is not None and tb is not None:
            if   int(ta) < int(tb): ga += str(ta)
            elif int(tb) < int(ta): gb += str(tb)
        a.append(ga); b.append(gb)
    return a, b

def results(code):
    feed = json.load(urllib.request.urlopen(urllib.request.Request(URL % code, headers=UA), timeout=60))
    out = {}
    for m in feed["matches"]:
        if m.get("status") not in ("Completed", "Retired"): continue
        ia, ib = pid(m["team1"]["idA"]), pid(m["team2"]["idA"])
        if not ia or not ib: continue
        sa, sb = cells(m["scores"]["sets"])
        win = ia if str(m.get("winner")) == "1" else ib
        out[frozenset([ia, ib])] = {"win": win, "sc": {ia: sa, ib: sb}, "dur": m.get("duration") or ""}
    return out

def apply(tree, res):
    added = [0]
    def walk(n):
        for c in n.get("c", []): walk(c)                      # children first, so winners can move up
        for k, c in enumerate(n.get("c", [])):                # fill a TBD slot from the child's winner
            w = next((p for p in c.get("p", []) if p.get("w")), None)
            if w and k < len(n.get("p", [])) and not n["p"][k].get("id"):
                n["p"][k] = {"n": w["n"], "id": w["id"], "s": w.get("s"), "w": False, "sc": []}
        ids = [p["id"] for p in n.get("p", []) if p.get("id")]
        if len(ids) == 2 and not any(p.get("w") for p in n["p"]):
            r = res.get(frozenset(ids))
            if r:
                for p in n["p"]:
                    p["w"] = (p["id"] == r["win"]); p["sc"] = r["sc"].get(p["id"], [])
                if r["dur"]: n["dur"] = r["dur"]
                n.pop("up", None); n.pop("live", None)
                added[0] += 1
    walk(tree)
    return added[0]

h = open(F).read()
def splice(key, code, pick=None):
    global h
    i = h.index(key)+len(key)
    obj, end = json.JSONDecoder().raw_decode(h, i); assert h[end] == ";"
    tree = obj[pick] if pick else obj
    n = apply(tree, results(code))
    h = h[:i] + json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + h[end:]
    return n

print("ATP results applied:", splice("const TREE_USO = ", "MS"))
print("WTA results applied:", splice("const WTA_TREES = ", "WS", "USO"))
open(F, "w").write(h); print("bytes", len(h))
