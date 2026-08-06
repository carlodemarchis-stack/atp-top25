#!/usr/bin/env python3
"""Build both pages from the one shared template.
  index.html  <- data/players.json      (ATP, tour defaults, output unchanged)
  wta.html    <- data/wta_players.json   (WTA: purple theme + swapped copy)"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))

WTA_REPLACEMENTS = [
    ("<title>ATP Top 100 — Player Film</title>", "<title>WTA Top 100 — Player Film</title>"),
    ('content="ATP Top 100 — Player Film"', 'content="WTA Top 100 — Player Film"'),   # og:title + twitter:title
    ('<link rel="canonical" href="https://tennis.aguywithascarf.com/">',
     '<link rel="canonical" href="https://tennis.aguywithascarf.com/wta.html">'),
    ('<meta property="og:url" content="https://tennis.aguywithascarf.com/">',
     '<meta property="og:url" content="https://tennis.aguywithascarf.com/wta.html">'),
    ("og-atp.png", "og-wta.png"),                                   # og:image + twitter:image
    ("Jannik Sinner — ATP Top 100 Player Film", "Aryna Sabalenka — WTA Top 100 Player Film"),  # og:image:alt
    ("fill='%23c9e548'", "fill='%23b57bff'"),                       # favicon ball: green -> WTA violet
    ("<body>", '<body class="wta">'),
    ('<div class="brand"><b>ATP</b> · TOP 100 · SINGLES</div>',
     '<div class="brand"><b>WTA</b> · TOP 100 · SINGLES</div>'),
    ('<div class="csub">ATP Top 100 · Player Film</div>',
     '<div class="csub">WTA Top 100 · Player Film</div>'),
    ("Data &amp; Images — atptour.com", "Data &amp; Images — wtatennis.com"),
    ('the official ATP site, <a href="https://www.atptour.com" target="_blank" rel="noopener noreferrer">atptour.com</a>',
     'the official WTA site, <a href="https://www.wtatennis.com" target="_blank" rel="noopener noreferrer">wtatennis.com</a>'),
    ("the PIF ATP Rankings and Race to Turin", "the WTA Rankings and the Race to the WTA Finals"),
    ("property of the ATP and its partners", "property of the WTA and its partners"),
    ("move through a season of ATP data", "move through a season of WTA data"),
    ("Everything shown is the property of the ATP", "Everything shown is the property of the WTA"),
]

def build(data_file, out_file, wta=False):
    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    data = json.load(open(os.path.join(HERE, "data", data_file), encoding="utf-8"))
    html = tpl.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    if wta:
        for a, b in WTA_REPLACEMENTS:
            if a not in html:
                print("  ! replacement not found:", a[:48])
            html = html.replace(a, b)
    open(os.path.join(HERE, out_file), "w", encoding="utf-8").write(html)
    print(f"✓ {out_file}  ({len(html)//1024} KB)")

if __name__ == "__main__":
    build("players.json", "index.html", wta=False)
    build("wta_players.json", "wta.html", wta=True)
