#!/usr/bin/env python3
"""Overlay fresh 2026 tournaments + results (and the W-L/titles/prize they imply) onto
players.json, keeping the just-updated rankings, race, ranking_date and bios. Reads the
compact activity captured in-browser (window.__act) from a tool-results file."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ACT_FILE = "/Users/carlodemarchis/.claude/projects/-Users-carlodemarchis-Documents--cdm--carlo-FACTORY63-Claude-Code/6132c4a3-a142-471c-8e3b-545ddc53f416/tool-results/mcp-Claude_Browser-javascript_tool-1785764733254.txt"

def load_act():
    parts = json.load(open(ACT_FILE))
    obj, _ = json.JSONDecoder().raw_decode("".join(p["text"] for p in parts))
    return json.loads(obj) if isinstance(obj, str) else obj

def money(n):
    try: return "$" + "{:,}".format(int(round(float(n))))
    except Exception: return ""

def expand_match(m):
    return {"round": m.get("r"), "roundLong": m.get("rL"), "wl": m.get("wl"),
            "bye": bool(m.get("bye")), "opp": m.get("opp"), "oppC": m.get("oc"),
            "oppR": m.get("or"), "score": m.get("sc", ""), "stats": m.get("st")}

def expand_tournament(t):
    return {"name": t.get("name"), "loc": t.get("loc"), "date": t.get("date"),
            "type": t.get("type"), "surface": t.get("surf"), "draw": t.get("draw"),
            "seed": t.get("seed"), "points": t.get("pts", 0),
            "result": t.get("res", "-"), "resultLong": t.get("resL", "-"),
            "won": t.get("won", 0), "lost": t.get("lost", 0), "title": bool(t.get("title")),
            "url": t.get("url"), "matches": [expand_match(m) for m in (t.get("M") or [])],
            "prize": t.get("prize", 0), "cur": t.get("cur", "$")}

def main():
    data = json.load(open(os.path.join(HERE, "data", "players.json"), encoding="utf-8"))
    act = load_act()
    updated = skipped = 0
    for p in data["players"]:
        a = act.get(p["id"])
        if not a or a.get("err") or a.get("T") is None:
            skipped += 1                       # e.g. Rune (no 2026 activity) — keep existing
            continue
        p["tournaments"] = [expand_tournament(t) for t in a["T"]]
        if a.get("yw") is not None: p["ytdWon"] = a["yw"]
        if a.get("yl") is not None: p["ytdLost"] = a["yl"]
        if a.get("yt") is not None: p["ytdTitles"] = a["yt"]
        if a.get("yp") is not None: p["ytdPrize"] = money(a["yp"])
        if a.get("cw") is not None: p["carWon"] = a["cw"]
        if a.get("cl") is not None: p["carLost"] = a["cl"]
        if a.get("ct") is not None: p["carTitles"] = a["ct"]
        if a.get("cp") is not None: p["carPrize"] = money(a["cp"])
        updated += 1
    json.dump(data, open(os.path.join(HERE, "data", "players.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(f"✓ activity refreshed: {updated} updated, {skipped} kept as-is")
    # spot report: players whose newest tournament changed
    for pid in ["s0ag", "a0e2", "z355", "su55"]:
        p = next(x for x in data["players"] if x["id"] == pid)
        newest = p["tournaments"][0] if p["tournaments"] else {}
        print(f"  {p['last']:16} {p['ytdWon']}-{p['ytdLost']} | {len(p['tournaments'])} tournaments | latest: {newest.get('name')} ({newest.get('result')})")

if __name__ == "__main__":
    main()
