#!/usr/bin/env python3
"""One-command ATP weekly update — runs the whole Python side in order.

Run it AFTER the browser fetch step (see WEEKLY_UPDATE.md), which produces:
  scratchpad/atp/new_rankings.json   (rank/points per id — written by the rankings scrape)
  scratchpad/atp/new_race.json       (raceRank/racePoints per id — race scrape)
  <entrants tool-result file>        (hero+activity for NEW top-100 entrants)
  <activity tool-result file>        (compact 2026 activity for all 100)

Usage:
  python3 atp_update.py <YYYY-MM-DD> <entrants_file> <activity_file>

It then: overlays rankings+race+entrants, overlays tournaments/results, rebuilds the
season-calendar final four, and re-renders index.html + wta.html. Verify, then push.
"""
import os, sys, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

def step(script, env=None):
    print(f"\n─────── {script} ───────", flush=True)
    e = dict(os.environ); e.update(env or {})
    subprocess.run([sys.executable, os.path.join(HERE, script)], env=e, check=True)

def main():
    if len(sys.argv) < 4:
        print(__doc__); sys.exit(1)
    date, entrants, activity = sys.argv[1], sys.argv[2], sys.argv[3]
    for f in (entrants, activity,
              os.path.join(os.environ.get("ATP_REFRESH_DIR",
                  "/private/tmp/claude-501/-Users-carlodemarchis-Documents--cdm--carlo-FACTORY63-Claude-Code/6132c4a3-a142-471c-8e3b-545ddc53f416/scratchpad/atp"),
                  "new_rankings.json")):
        if not os.path.exists(f):
            print(f"! missing input: {f}"); sys.exit(1)
    env = {"ATP_DATE": date, "ATP_ENTRANTS": entrants, "ATP_ACTIVITY": activity}
    step("update_atp.py", env)           # rankings + race + entrants/exits + ranking date
    step("update_atp_activity.py", env)  # tournaments + results + ytd/career stats (all 100)
    step("build_atp_calendar.py")        # season-calendar final four from the refreshed matches
    step("render.py")                    # rebuild index.html (ATP) + wta.html (WTA)
    print(f"\n✓ ATP updated to {date}. Verify locally, then: "
          f"git add data/players.json index.html && git commit && git push")

if __name__ == "__main__":
    main()
