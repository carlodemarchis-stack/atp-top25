#!/usr/bin/env python3
"""Build a RANK map {playerId: currentRank} from the top-100 data files (ATP + WTA)
and splice `const RANK = {...};` into montreal_bracket.html (insert or replace)."""
import json
REPO = "/Users/carlodemarchis/Documents/_cdm/_carlo/FACTORY63/Claude Code/atp-cards"
F = "montreal_bracket.html"

RANK = {}
for fn in ("data/players.json", "data/wta_players.json"):
    for p in json.load(open(f"{REPO}/{fn}"))["players"]:
        if p.get("id") and p.get("rank"): RANK[str(p["id"])] = p["rank"]
print("RANK entries:", len(RANK))

h = open(F).read()
block = "const RANK = " + json.dumps(RANK, separators=(",", ":")) + ";"
key = "const RANK = "
if key in h:
    i = h.index(key)
    _, end = json.JSONDecoder().raw_decode(h, i + len(key))
    semi = h.index(";", end - 1)
    h = h[:i] + block + h[semi + 1:]
    print("replaced existing RANK")
else:
    anchor = "Object.assign(IOC,{AND:"
    k = h.index(";", h.index(anchor)) + 1
    h = h[:k] + "\n" + block + h[k:]
    print("inserted RANK after IOC additions")
open(F, "w").write(h)
print("bytes", len(h))
