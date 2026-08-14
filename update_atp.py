#!/usr/bin/env python3
"""Weekly ATP ranking update: overlay the newly-published rankings + race onto the
existing dataset, swap top-100 entrants/exits (full transform for entrants), bump the
ranking date. Keeps retained players' match/tournament data from the prior snapshot."""
import json, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
# all three overridable by atp_update.py via env; defaults are the last run's values
SCRATCH = os.environ.get("ATP_REFRESH_DIR", "/private/tmp/claude-501/-Users-carlodemarchis-Documents--cdm--carlo-FACTORY63-Claude-Code/6132c4a3-a142-471c-8e3b-545ddc53f416/scratchpad/atp")
ENTRANT_FILE = os.environ.get("ATP_ENTRANTS", "/Users/carlodemarchis/.claude/projects/-Users-carlodemarchis-Documents--cdm--carlo-FACTORY63-Claude-Code/6132c4a3-a142-471c-8e3b-545ddc53f416/tool-results/mcp-Claude_Browser-javascript_tool-1786690076408.txt")
NEW_DATE = os.environ.get("ATP_DATE", "2026-08-10")

def load_entrants():
    parts = json.load(open(ENTRANT_FILE))
    raw = "".join(p["text"] for p in parts)
    obj, _ = json.JSONDecoder().raw_decode(raw)   # tool result is double-encoded + trailing note
    if isinstance(obj, str):
        obj = json.loads(obj)
    return obj

def money(n):
    try: return "$" + "{:,}".format(int(round(float(n))))
    except Exception: return ""

def build_score(m):
    out = []
    for i in range(1, 6):
        p, o, tie = m.get(f"Set{i}Player"), m.get(f"Set{i}Opponent"), m.get(f"Set{i}Tie")
        if p is None and o is None:
            continue
        piece = f"{p}-{o}"
        if tie is not None:
            piece += f"({tie})"
        out.append(piece)
    return " ".join(out)

def transform_match(m):
    rnd = m.get("Round") or {}
    bye = bool(m.get("IsBye"))
    opp = ""
    if not bye:
        opp = f'{(m.get("OpponentFirstInitial") or "").strip()}. {(m.get("OpponentLastName") or "").strip()}'.strip()
    return {
        "round": rnd.get("ShortName"),
        "roundLong": rnd.get("LongName"),
        "wl": m.get("WinLoss"),
        "bye": bye,
        "opp": opp,
        "oppC": m.get("OpponentNatlId"),
        "oppR": m.get("OpponentRank") or None,
        "score": "" if bye else build_score(m),
        "stats": m.get("MatchStatsUrl"),
    }

def transform_tournament(t):
    return {
        "name": t.get("EventName"),
        "loc": t.get("Location"),
        "date": t.get("EventDate"),
        "type": t.get("EventType"),
        "surface": t.get("Surface"),
        "draw": t.get("SglDrawSize"),
        "seed": t.get("PlayerRank"),
        "points": t.get("Points") or 0,
        "result": (t.get("HiRound") or {}).get("ShortName", "-"),
        "resultLong": (t.get("HiRound") or {}).get("LongName", "-"),
        "won": t.get("Won") or 0,
        "lost": t.get("Lost") or 0,
        "title": bool(t.get("CountableTitle")),
        "url": t.get("TournamentUrl"),
        "matches": [transform_match(m) for m in (t.get("Matches") or [])],
        "prize": t.get("Prize") or 0,
        "cur": t.get("CurrSymbol") or "$",
    }

def transform_entrant(id_, blob, rankrow, racerow):
    h, a = blob["hero"], blob["act"]
    yr = next((x for x in (a.get("Activity") or []) if str(x.get("EventYear")) == "2026"), {})
    slug_m = re.search(r"/players/([^/]+)/", h.get("ScRelativeUrlPlayerProfile") or "")
    slug = slug_m.group(1) if slug_m else re.sub(r"[^a-z0-9]+", "-", f'{h.get("FirstName","")}-{h.get("LastName","")}'.lower()).strip("-")
    return {
        "rank": rankrow["rank"],
        "nextBest": "-",
        "id": id_,
        "slug": slug,
        "first": h.get("FirstName"),
        "last": h.get("LastName"),
        "country": h.get("Nationality"),
        "age": h.get("Age"),
        "birthDate": h.get("BirthDate"),
        "birthCity": h.get("BirthCity"),
        "residence": h.get("Residence"),
        "heightCm": h.get("HeightCm"),
        "heightFt": h.get("HeightFt"),
        "weightKg": h.get("WeightKg"),
        "weightLb": h.get("WeightLb"),
        "plays": h.get("PlayHand"),
        "backhand": h.get("BackHand"),
        "proYear": h.get("ProYear"),
        "coach": h.get("Coach"),
        "sglRank": rankrow["rank"],
        "hiRank": h.get("SglHiRank"),
        "hiRankDate": h.get("SglHiRankDate"),
        "rankMove": rankrow.get("move", 0),
        "ytdWon": yr.get("Won", a.get("Won", 0)),
        "ytdLost": yr.get("Lost", a.get("Lost", 0)),
        "ytdTitles": yr.get("Titles", a.get("Titles", 0)),
        "ytdPrize": money(yr.get("PrizeMoney", a.get("Prize", 0))),
        "carWon": a.get("WonTotal", 0),
        "carLost": a.get("LostTotal", 0),
        "carTitles": a.get("TitlesTotal", 0),
        "carPrize": money(a.get("PrizeMoneyTotal", 0)),
        "social": h.get("SocialLinks") or h.get("Social") or [],
        "tournaments": [transform_tournament(t) for t in (yr.get("Tournaments") or [])],
        "raceRank": racerow["raceRank"] if racerow else None,
        "racePoints": racerow["racePoints"] if racerow else None,
        "points": rankrow["pointsFmt"],
    }

def main():
    data = json.load(open(os.path.join(HERE, "data", "players.json"), encoding="utf-8"))
    new_rank = {p["id"]: p for p in json.load(open(f"{SCRATCH}/new_rankings.json"))}
    new_race = {p["id"]: p for p in json.load(open(f"{SCRATCH}/new_race.json"))}
    entrants_raw = load_entrants()

    keep = []
    for p in data["players"]:
        r = new_rank.get(p["id"])
        if not r:                       # dropped out of the top 100
            continue
        old_rank = p["rank"]            # move = positions gained vs last week (page no longer exposes it)
        p["rank"] = r["rank"]; p["sglRank"] = r["rank"]
        p["points"] = r["pointsFmt"]; p["rankMove"] = old_rank - r["rank"]
        rc = new_race.get(p["id"])
        if rc:
            p["raceRank"] = rc["raceRank"]; p["racePoints"] = rc["racePoints"]
        keep.append(p)

    existing_ids = {p["id"] for p in keep}
    for id_, r in new_rank.items():
        if id_ in existing_ids:
            continue
        blob = entrants_raw.get(id_)
        if not blob:
            print(f"  ! entrant {id_} has no fetched data — skipping"); continue
        keep.append(transform_entrant(id_, blob, r, new_race.get(id_)))

    keep.sort(key=lambda p: p["rank"])
    for i, p in enumerate(keep):
        if p["id"] in [e for e in new_rank if e not in existing_ids]:  # only reset entrants' nextBest
            p["nextBest"] = keep[i+1]["last"] if i + 1 < len(keep) else "-"

    data["players"] = keep
    data["ranking_date"] = NEW_DATE
    json.dump(data, open(os.path.join(HERE, "data", "players.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(f"✓ players.json updated: {len(keep)} players, ranking_date {NEW_DATE}")
    print("  top5:", [(p["rank"], p["last"], p["points"]) for p in keep[:5]])
    ents = [p for p in keep if p["id"] in new_rank and p["id"] not in existing_ids]
    print("  entrants added:", [(p["rank"], p["last"], len(p["tournaments"]), "T") for p in ents])

if __name__ == "__main__":
    main()
