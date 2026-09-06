#!/usr/bin/env python3
"""Live-refresh the ATP US Open tree (TREE_USO) from the scraped draw page (all rounds, with results)."""
import json, glob, os

F = "montreal_bracket.html"
# newest atp draws dump
# session-specific by nature; override with USO_RESDIR when the session id changes
RESDIR = os.environ.get("USO_RESDIR",
    "/Users/carlodemarchis/.claude/projects/-Users-carlodemarchis-Documents--cdm--carlo-FACTORY63-Claude-Code/6132c4a3-a142-471c-8e3b-545ddc53f416/tool-results")
res = max(glob.glob(os.path.join(RESDIR, "mcp-Claude_Browser-javascript_tool-*.txt")), key=os.path.getmtime)
raw = json.load(open(res))
text = raw[0]["text"] if isinstance(raw, list) else raw["text"]
payload = text.split("|||S|||",1)[1].split("|||E|||",1)[0].replace('\\"', '"')
rounds = json.loads(payload)     # rounds[ri] = items; item = [stats0, stats1]; stats = null | {i,n,s,c,w,sc}
print("rounds:", [len(r) for r in rounds])
assert [len(r) for r in rounds] == [64,32,16,8,4,2,1], [len(r) for r in rounds]

countries = {}
def player(x):
    if x.get("c"): countries[x["i"]] = x["c"]
    return {"n": x["n"], "id": x["i"], "s": x.get("s"), "w": bool(x.get("w")), "sc": x.get("sc") or []}
def winner_of(node):
    for p in node.get("p", []):
        if p.get("w") and p.get("id"): return p
    return None
def build(ri, j):
    item = rounds[ri][j]
    if ri == 0:
        return {"r":0,"dur":"","p":[player(item[0]), player(item[1])]}
    left, right = build(ri-1, 2*j), build(ri-1, 2*j+1)
    slots = [left, right]
    p = []
    for k in (0,1):
        cell = item[k] if k < len(item) else None
        if cell and cell.get("i"):
            p.append(player(cell))                      # the site already names this player (with result if any)
        else:
            w = winner_of(slots[k]); p.append({"n":w["n"],"id":w["id"],"s":w.get("s"),"w":False,"sc":[]} if w else {"tbd":True})
    return {"r":ri,"dur":"","p":p,"c":[left,right]}

tree = build(6, 0)
def count(n, a=[0]):
    if any(p.get("w") for p in n.get("p",[])): a[0]+=1
    for c in n.get("c",[]): count(c,a)
    return a[0]
champ = next((p["n"] for p in tree["p"] if p.get("w")), None)
print("ATP US Open live — decided matches:", count(tree), "| champion:", champ, "| countries:", len(countries))

h = open(F).read()
key = "const TREE_USO = "; i = h.index(key)+len(key)
_, end = json.JSONDecoder().raw_decode(h, i); assert h[end]==";"
h = h[:i] + json.dumps(tree, ensure_ascii=False, separators=(",",":")) + h[end:]
h = h.replace('Object.assign(IOC,{AND:', 'Object.assign(CC, '+json.dumps(countries, separators=(",",":"))+');\nObject.assign(IOC,{AND:', 1)
open(F, "w").write(h); print("spliced TREE_USO | bytes", len(h))
