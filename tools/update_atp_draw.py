#!/usr/bin/env python3
"""Build an ATP draw tree from an atptour.com draws-page scrape and splice it into draws.html.

  python3 tools/update_atp_draw.py TREE_SHANGHAI <scrape tool-result file>

The scrape is the in-browser snippet that returns  |||S|||<rounds json>|||E|||…  where
rounds[ri] is the list of draw items for that round, and each item is two cells:
  null           — slot not filled yet
  {"bye": true}  — the bye opposite a seed (96-draws show as 128 with 32 of these)
  {i,n,s,c,w,sc} — a player: id, name, seed, IOC country, won?, set tokens

Byes become a one-player leaf {"r":0, "bye":true, "p":[seed]} — the shape every existing
96-draw tree (Montreal, Cincinnati) already uses. Round ri item j is fed by round ri-1
items 2j and 2j+1. Where the site has not filled a cell yet, the child's winner moves up.
Countries are merged into the page's existing Object.assign(CC, {...}) rather than adding
another one.
"""
import json, re, sys, os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(HERE, "draws.html")

def load_rounds(path):
    # A single javascript_tool result is one part; a browser_batch result has one part per
    # action (navigate, wait, …), so look for the part that carries the scrape.
    for part in json.load(open(path)):
        t = part.get("text", "")
        k = t.find('"|||S|||')
        if k < 0:
            continue
        s, _ = json.JSONDecoder().raw_decode(t, k)   # the JS return value, JSON-encoded
        return json.loads(s.split("|||S|||", 1)[1].split("|||E|||", 1)[0])
    sys.exit(f"! no |||S||| scrape found in {path}")

def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    const, src = sys.argv[1], sys.argv[2]
    rounds = load_rounds(src)
    sizes = [len(r) for r in rounds]
    n = len(rounds)
    assert sizes == [2 ** (n - 1 - i) for i in range(n)], f"not a full bracket: {sizes}"

    countries = {}
    def player(x, won=None):
        if x.get("c"):
            countries[x["i"]] = x["c"]
        return {"n": x["n"], "id": x["i"], "s": x.get("s"),
                "w": bool(x.get("w")) if won is None else won, "sc": x.get("sc") or []}

    def winner_of(node):
        return next((p for p in node.get("p", []) if p.get("w") and p.get("id")), None)

    def build(ri, j):
        item = rounds[ri][j]
        if ri == 0:
            cells = [c for c in item if c]
            real = [c for c in cells if not c.get("bye")]
            if any(c.get("bye") for c in cells):
                assert len(real) == 1, f"bye slot without exactly one player: {item}"
                return {"r": 0, "dur": "", "bye": True, "p": [player(real[0], won=True) | {"sc": []}]}
            return {"r": 0, "dur": "", "p": [player(c) if c else {"tbd": True} for c in item]}
        left, right = build(ri - 1, 2 * j), build(ri - 1, 2 * j + 1)
        p = []
        for k, child in enumerate((left, right)):
            cell = item[k] if k < len(item) else None
            if cell and cell.get("i"):
                p.append(player(cell))
            else:
                w = winner_of(child)
                p.append({"n": w["n"], "id": w["id"], "s": w.get("s"), "w": False, "sc": []} if w else {"tbd": True})
        return {"r": ri, "dur": "", "p": p, "c": [left, right]}

    tree = build(n - 1, 0)

    def count(node):
        return (0 if node.get("bye") else int(any(x.get("w") for x in node.get("p", [])))) + \
               sum(count(c) for c in node.get("c", []))
    champ = next((x["n"] for x in tree["p"] if x.get("w")), None)
    print(f"{const}: {n} rounds {sizes} | decided {count(tree)} (byes excluded) | champion {champ}")

    h = open(PAGE).read()
    blob = json.dumps(tree, ensure_ascii=False, separators=(",", ":"))
    key = f"const {const} = "
    if key in h:                                      # replace an existing tree
        i = h.index(key) + len(key)
        _, end = json.JSONDecoder().raw_decode(h, i)
        assert h[end] == ";"
        h = h[:i] + blob + h[end:]
        print("  replaced existing", const)
    else:                                             # new event: insert after the last ATP tree
        last = list(re.finditer(r"^const TREE_[A-Z0-9_]+ = .*$", h, re.M))[-1]
        h = h[:last.end()] + f"\n{key}{blob};" + h[last.end():]
        print("  inserted new", const)

    ck = "Object.assign(CC, "
    i = h.index(ck) + len(ck)
    cc, end = json.JSONDecoder().raw_decode(h, i)
    added = {k: v for k, v in countries.items() if k not in cc}
    cc.update(countries)
    h = h[:i] + json.dumps(cc, separators=(",", ":")) + h[end:]
    print(f"  countries: {len(countries)} in draw, {len(added)} new to CC")
    open(PAGE, "w").write(h)

if __name__ == "__main__":
    main()
