#!/usr/bin/env python3
"""Set node.up (date · time · court) on the ATP TREE_USO's upcoming (pending) matches
from the scraped daily-schedule (atp_sched.json). Same node.up the tooltip already shows for WTA."""
import json
F = "montreal_bracket.html"
s = json.load(open("atp_sched.json"))
pair = {}
for m in s["matches"]:
    a, b = m["ids"]
    pair[frozenset([a, b])] = f'{s["date"]} · {m["time"]} · {m["court"]}'

h = open(F).read()
key = "const TREE_USO = "; i = h.index(key) + len(key)
tree, end = json.JSONDecoder().raw_decode(h, i); assert h[end] == ";"
n_set = [0]
def walk(n):
    reals = [p for p in n.get("p", []) if p.get("id")]
    haswin = any(p.get("w") for p in n.get("p", []))
    if len(reals) == 2 and not haswin:
        up = pair.get(frozenset([reals[0]["id"], reals[1]["id"]]))
        if up: n["up"] = up; n_set[0] += 1
    for c in n.get("c", []): walk(c)
walk(tree)
h = h[:i] + json.dumps(tree, ensure_ascii=False, separators=(",", ":")) + h[end:]
open(F, "w").write(h)
print("ATP upcoming matches tagged with schedule:", n_set[0])
