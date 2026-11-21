#!/usr/bin/env python3
"""Instagram-story PNGs (1080×1920) of the Finals card, one per tour.

usage: python3 tools/story.py [--base http://localhost:8777] [--tours atp,wta] [--day N] [--out DIR]

Opens draws.html?story&noumami#<tour>/finals in headless Chrome at 540×960 with a 2× device scale
and saves the frame. The page must be served (images are relative): run the local preview server,
or pass --base https://tennis.aguywithascarf.com to shoot the live site. Files are named
story-<tour>-<YYYY-MM-DD>-<HHMM>.png in --out (default ~/Downloads/dataviz social).

Chrome quirk on this Mac: --headless=new writes the screenshot and then never exits, so each
shot runs in the background and is killed once the file has appeared (see social-share notes).
"""
import argparse, datetime as dt, os, subprocess, tempfile, time

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def shoot(url, out, wait=14):
    prof = tempfile.mkdtemp(prefix="story-")
    if os.path.exists(out):
        os.remove(out)
    p = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                          f"--user-data-dir={prof}", "--window-size=540,960", "--force-device-scale-factor=2",
                          "--virtual-time-budget=6000",
                          "--host-resolver-rules=MAP static.cloudflareinsights.com 127.0.0.1, MAP m.aguywithascarf.com 127.0.0.1",
                          f"--screenshot={out}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while time.time() - t0 < wait and not (os.path.exists(out) and os.path.getsize(out) > 0):
        time.sleep(0.5)
    time.sleep(1.0)                      # let the file finish writing
    p.kill()
    subprocess.run(["pkill", "-f", f"user-data-dir={prof}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return os.path.exists(out) and os.path.getsize(out) > 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://tennis.aguywithascarf.com")      # --base http://localhost:8777 for a local build
    ap.add_argument("--tours", default="atp,wta")
    ap.add_argument("--day", type=int, default=0, help="tournament day 1-8 (default: today)")
    ap.add_argument("--out", default=os.path.expanduser("~/Downloads/dataviz social"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    for tour in [t.strip() for t in a.tours.split(",") if t.strip()]:
        url = f"{a.base.rstrip('/')}/draws.html?story&noumami#{tour}/finals" + (f"?d={a.day}" if a.day else "")
        out = os.path.join(a.out, f"story-{tour}-{stamp}.png")
        ok = shoot(url, out)
        size = ""
        if ok:
            try:
                from PIL import Image
                size = "%dx%d" % Image.open(out).size
            except Exception:
                pass
        print(("✓ " if ok else "✗ ") + out, size)

if __name__ == "__main__":
    main()
