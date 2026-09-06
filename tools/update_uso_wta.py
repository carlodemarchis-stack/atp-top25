#!/usr/bin/env python3
"""Live-refresh the WTA US Open tree inside draws.html (self-contained; run from anywhere).
/draw positions + /matches results propagated up the bracket. No-ops after the tournament
(2026-09-06 US Eastern) and when nothing changed. Prints CHANGED / UNCHANGED / SKIPPED."""
import json, math, os, sys, datetime, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
F = os.path.normpath(os.path.join(HERE, "..", "draws.html"))
HDRS = {"accept": "application/json", "account": "wta"}
def get(u): return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=HDRS), timeout=60))

# stop after the tournament ends: 2026-09-06 ET ≈ up to 2026-09-07 05:00 UTC
if datetime.datetime.utcnow() > datetime.datetime(2026, 9, 7, 5, 0, 0):
    print("SKIPPED — past 2026-09-06 (US Open over)"); sys.exit(0)

def analyze(m):
    scA, scB, sA, sB = [], [], 0, 0
    for i in (1,2,3,4,5):
        a=str(m.get(f"ScoreSet{i}A","")).strip(); b=str(m.get(f"ScoreSet{i}B","")).strip()
        if a=="" or b=="": continue
        try: ai,bi=int(a),int(b)
        except ValueError: continue
        tb=str(m.get(f"ScoreTbSet{i}","")).strip(); ta,tbk=a,b
        if tb:
            if ai<bi: ta=a+tb
            elif bi<ai: tbk=b+tb
        scA.append(ta); scB.append(tbk)
        if ai>bi: sA+=1
        elif bi>ai: sB+=1
    if sA!=sB: w='A' if sA>sB else 'B'
    else:
        wf=str(m.get("Winner","")).strip(); w=('A' if int(wf)%2==0 else 'B') if wf.isdigit() else 'A'
    return scA, scB, w

def draw_positions(gid, year):
    d=get(f"https://api.wtatennis.com/tennis/tournaments/{gid}/{year}/draw")
    di=d["drawInfo"][0]; di=json.loads(di) if isinstance(di,str) else di
    ev=[e for e in di["Draws"]["Events"]["Event"] if isinstance(e,dict)]
    sing=[e for e in ev if "Women Singles" in (e.get("DrawTypeTitle") or "")][0]
    lines=sorted([L for L in (sing.get("Draw") or {}).get("DrawLine") or [] if isinstance(L,dict)], key=lambda L:L.get("Pos",0))
    countries={}; qn=[0]; out=[]
    for L in lines:
        pl=(L.get("Players") or {}).get("Player"); disp=(L.get("DisplayLine") or "").strip()
        if isinstance(pl,dict) and pl.get("id"):
            pid=str(pl["id"])
            nm=(lambda a:f"{a[1].strip()} {a[0].strip()}")(disp.split(",",1)) if "," in disp else (pl.get("FirstName","") or disp)
            if pl.get("Country"): countries[pid]=pl["Country"]
            seed=L.get("Seed"); seed=str(seed) if str(seed or "").strip() else None
            out.append({"n":nm,"id":pid,"s":seed})
        else:
            qn[0]+=1; out.append({"n":"Qualifier","id":f"wq{qn[0]}","s":None})
    return out, countries

def matches_index(gid, year):
    ms=[x for x in get(f"https://api.wtatennis.com/tennis/tournaments/{gid}/{year}/matches")["matches"]
        if x.get("DrawLevelType")=="M" and x.get("DrawMatchType")=="S"]
    idx={}
    for m in ms:
        idA,idB=str(m.get("PlayerIDA","")),str(m.get("PlayerIDB",""))
        if not idA or not idB: continue
        scA,scB,w=analyze(m)
        idx[frozenset([idA,idB])]={"played":m.get("MatchState")=="F","winId":idA if w=="A" else idB,"sc":{idA:scA,idB:scB}}
    return idx

def build_live(gid, year):
    pos,countries=draw_positions(gid,year); midx=matches_index(gid,year)
    N=len(pos); maxR=int(round(math.log2(N)))-1
    def player(d): return {"n":d["n"],"id":d["id"],"s":d.get("s"),"w":False,"sc":[]}
    def apply_result(node):
        ps=[x for x in node["p"] if x.get("id")]
        if len(ps)!=2: return
        rec=midx.get(frozenset([ps[0]["id"],ps[1]["id"]]))
        if rec and rec["played"]:
            for x in node["p"]:
                if x.get("id"): x["w"]=(x["id"]==rec["winId"]); x["sc"]=rec["sc"].get(x["id"],[])
    def winner_of(node):
        for x in node.get("p",[]):
            if x.get("w") and x.get("id"): return x
        return None
    def build(lo,size,r):
        if r==0:
            node={"r":0,"dur":"","p":[player(pos[lo]),player(pos[lo+1])]}; apply_result(node); return node
        half=size//2; left=build(lo,half,r-1); right=build(lo+half,half,r-1)
        lw,rw=winner_of(left),winner_of(right)
        node={"r":r,"dur":"","p":[player(lw) if lw else {"tbd":True}, player(rw) if rw else {"tbd":True}],"c":[left,right]}
        if lw and rw: apply_result(node)
        return node
    return build(0,N,maxR), countries

tree, countries = build_live(905, 2026)
h = open(F, encoding="utf-8").read()
i = h.index("const WTA_TREES = ")+len("const WTA_TREES = ")
trees, end = json.JSONDecoder().raw_decode(h, i); assert h[end]==";"
before = json.dumps(trees.get("USO"), sort_keys=True)
trees["USO"] = tree
if json.dumps(trees["USO"], sort_keys=True) == before:
    print("UNCHANGED — no new WTA results"); sys.exit(0)
h2 = h[:i] + json.dumps(trees, ensure_ascii=False, separators=(",",":")) + h[end:]
h2 = h2.replace('Object.assign(IOC,{AND:', 'Object.assign(CC, '+json.dumps(countries, separators=(",",":"))+');\nObject.assign(IOC,{AND:', 1)
open(F, "w", encoding="utf-8").write(h2)
def decided(n, a=[0]):
    if any(p.get("w") for p in n.get("p",[])): a[0]+=1
    for c in n.get("c",[]): decided(c,a)
    return a[0]
print(f"CHANGED — WTA US Open now has {decided(tree)} decided matches")
