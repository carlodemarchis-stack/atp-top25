#!/usr/bin/env python3
"""Build a WTA draw tree from api.wtatennis.com and splice it into draws.html as WTA_TREES[KEY].

  python3 tools/update_wta_draw.py BEIJING 1020

Generalises update_uso_wta_live.py (which was hard-wired to the US Open, id 905):
  * any event — pass the WTA_TREES key and the tournament-group id
    (ids: GET /tennis/tournaments?from=…&to=…, field tournamentGroup.id)
  * byes — 96-draws come back as 128 lines with 32 "Bye" rows; those become the one-player
    {"bye": true} leaf the Canada / Cincinnati trees already use
  * singles found by title ("Women's Singles", not "…Quali" or "…Doubles"); the US Open
    feed says "Women Singles", Beijing says "Women's Singles"
Results come from /matches (winner by set count, as before), winners propagate up, and
scheduled-but-unplayed matches get node.up = "Sat 10 Oct · 1:00 PM · Diamond Court".
"""
import json, math, os, sys, datetime, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(HERE, "draws.html")
HDRS = {"accept": "application/json", "account": "wta"}
API = "https://api.wtatennis.com/tennis/tournaments"

def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=HDRS), timeout=60))

def analyze(m):
    scA, scB, sA, sB = [], [], 0, 0
    for i in (1, 2, 3, 4, 5):
        a = str(m.get(f"ScoreSet{i}A", "")).strip(); b = str(m.get(f"ScoreSet{i}B", "")).strip()
        if a == "" or b == "": continue
        try: ai, bi = int(a), int(b)
        except ValueError: continue
        tb = str(m.get(f"ScoreTbSet{i}", "")).strip(); ta, tbk = a, b
        if tb:                                   # superscript goes on the tie-break loser
            if ai < bi: ta = a + tb
            elif bi < ai: tbk = b + tb
        scA.append(ta); scB.append(tbk)
        if ai > bi: sA += 1
        elif bi > ai: sB += 1
    if sA != sB: w = "A" if sA > sB else "B"
    else:
        wf = str(m.get("Winner", "")).strip()
        w = ("A" if int(wf) % 2 == 0 else "B") if wf.isdigit() else "A"
    return scA, scB, w

def draw_positions(gid, year):
    d = get(f"{API}/{gid}/{year}/draw")
    di = d["drawInfo"][0]; di = json.loads(di) if isinstance(di, str) else di
    ev = di["Draws"]["Events"]["Event"]; ev = ev if isinstance(ev, list) else [ev]
    ev = [e for e in ev if isinstance(e, dict)]
    def is_main_singles(e):
        t = (e.get("DrawTypeTitle") or "").lower()
        return "singles" in t and "quali" not in t and "doubles" not in t
    sing = [e for e in ev if is_main_singles(e)]
    assert len(sing) == 1, [e.get("DrawTypeTitle") for e in ev]
    lines = sorted([L for L in (sing[0].get("Draw") or {}).get("DrawLine") or [] if isinstance(L, dict)],
                   key=lambda L: L.get("Pos", 0))
    countries, out, qn = {}, [], 0
    for L in lines:
        pl = (L.get("Players") or {}).get("Player"); disp = (L.get("DisplayLine") or "").strip()
        if isinstance(pl, dict) and pl.get("id"):
            pid = str(pl["id"])
            nm = (lambda a: f"{a[1].strip()} {a[0].strip()}")(disp.split(",", 1)) if "," in disp else (disp or pl.get("FirstName", ""))
            if pl.get("Country"): countries[pid] = pl["Country"]
            seed = L.get("Seed"); seed = str(seed) if str(seed or "").strip() else None
            out.append({"n": nm, "id": pid, "s": seed})
        elif disp.lower() == "bye":
            out.append({"bye": True})
        else:                                     # qualifier slot not filled yet
            qn += 1; out.append({"n": "Qualifier", "id": f"wq{qn}", "s": None})
    return out, countries

def matches_index(gid, year):
    ms = [x for x in get(f"{API}/{gid}/{year}/matches")["matches"]
          if x.get("DrawLevelType") == "M" and x.get("DrawMatchType") == "S"]
    idx = {}
    for m in ms:
        a, b = str(m.get("PlayerIDA", "")), str(m.get("PlayerIDB", ""))
        if not a or not b: continue
        scA, scB, w = analyze(m)
        sched = None
        if m.get("MatchState") in ("U", "P") and not m.get("Unscheduled"):
            nb = (m.get("NotBefore") or "").strip(); ts = m.get("MatchTimeStamp") or ""
            if nb and ts: sched = {"ts": ts, "nb": nb, "court": (m.get("CourtName") or "").strip()}
        idx[frozenset([a, b])] = {"played": m.get("MatchState") == "F",
                                  "winId": a if w == "A" else b, "sc": {a: scA, b: scB}, "sched": sched}
    return idx

def fmt_sched(s):
    date = ""
    try:
        dt = datetime.datetime.fromisoformat(s["ts"].replace("Z", "+00:00"))
        date = f"{dt.strftime('%a')} {dt.day} {dt.strftime('%b')}"
    except Exception: pass
    court = s["court"] if s["court"] and s["court"] != "Unknown Court" else ""
    return " · ".join(p for p in (date, s["nb"], court) if p)

def build(gid, year):
    pos, countries = draw_positions(gid, year)
    midx = matches_index(gid, year)
    N = len(pos); maxR = int(round(math.log2(N))) - 1
    def player(d): return {"n": d["n"], "id": d["id"], "s": d.get("s"), "w": False, "sc": []}
    def apply(node):
        ids = [x["id"] for x in node["p"] if x.get("id")]
        if len(ids) != 2: return
        rec = midx.get(frozenset(ids))
        if not rec: return
        if rec["played"]:
            for x in node["p"]:
                x["w"] = (x["id"] == rec["winId"]); x["sc"] = rec["sc"].get(x["id"], [])
        elif rec.get("sched"):
            node["up"] = fmt_sched(rec["sched"])
    def winner_of(node):
        return next((x for x in node.get("p", []) if x.get("w") and x.get("id")), None)
    def rec(lo, size, r):
        if r == 0:
            a, b = pos[lo], pos[lo + 1]
            if a.get("bye") or b.get("bye"):
                seed = b if a.get("bye") else a
                return {"r": 0, "dur": "", "bye": True, "p": [player(seed) | {"w": True}]}
            node = {"r": 0, "dur": "", "p": [player(a), player(b)]}
            apply(node); return node
        half = size // 2
        left, right = rec(lo, half, r - 1), rec(lo + half, half, r - 1)
        lw, rw = winner_of(left), winner_of(right)
        node = {"r": r, "dur": "", "p": [player(lw) if lw else {"tbd": True},
                                          player(rw) if rw else {"tbd": True}], "c": [left, right]}
        if lw and rw: apply(node)
        return node
    return rec(0, N, maxR), countries

def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    key, gid = sys.argv[1], int(sys.argv[2])
    tree, countries = build(gid, 2026)
    def count(n):
        return (0 if n.get("bye") else int(any(x.get("w") for x in n.get("p", [])))) + \
               sum(count(c) for c in n.get("c", []))
    champ = next((x["n"] for x in tree["p"] if x.get("w")), None)
    print(f"WTA_TREES.{key} (id {gid}): decided {count(tree)} (byes excluded) | champion {champ} | countries {len(countries)}")

    h = open(PAGE).read()
    k = "const WTA_TREES = "; i = h.index(k) + len(k)
    trees, end = json.JSONDecoder().raw_decode(h, i); assert h[end] == ";"
    print("  replaced" if key in trees else "  inserted", key)
    trees[key] = tree
    h = h[:i] + json.dumps(trees, ensure_ascii=False, separators=(",", ":")) + h[end:]
    ck = "Object.assign(CC, "; j = h.index(ck) + len(ck)
    cc, e2 = json.JSONDecoder().raw_decode(h, j)
    cc.update(countries)
    h = h[:j] + json.dumps(cc, separators=(",", ":")) + h[e2:]
    open(PAGE, "w").write(h)

if __name__ == "__main__":
    main()
