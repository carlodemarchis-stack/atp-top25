#!/usr/bin/env python3
"""Download WTA torso cutouts -> img/wta/{id}.png (from data/wta_images.json).
Players without a cutout get a neutral purple bust placeholder so the card still renders."""
import json, os, urllib.request
from PIL import Image, ImageDraw, ImageFilter
import io

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "img", "wta")
os.makedirs(OUT, exist_ok=True)
imgs = json.load(open(os.path.join(HERE, "data", "wta_images.json")))
HDRS = {"User-Agent": "Mozilla/5.0"}

def placeholder():
    """soft neutral bust silhouette on transparent bg"""
    W = H = 600
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = (150, 120, 190, 235)               # muted WTA violet
    d.ellipse([W*0.34, H*0.12, W*0.66, H*0.44], fill=c)          # head
    d.pieslice([W*0.14, H*0.50, W*0.86, H*1.30], 180, 360, fill=c)  # shoulders/torso
    return im.filter(ImageFilter.GaussianBlur(1))

ph = placeholder()
_buf = io.BytesIO(); ph.save(_buf, format="PNG")
PH_BYTES = _buf.getvalue()          # every generated placeholder is byte-identical

def is_placeholder(path):
    """True if the file on disk is one we generated (so it is safe to overwrite)."""
    try:
        with open(path, "rb") as fh:
            return fh.read() == PH_BYTES
    except OSError:
        return False

ok = miss = kept = 0
for pid, url in imgs.items():
    dest = os.path.join(OUT, f"{pid}.png")
    if url:
        try:
            u = url.split("?")[0] + "?width=640"
            req = urllib.request.Request(u, headers=HDRS)
            data = urllib.request.urlopen(req, timeout=40).read()
            im = Image.open(io.BytesIO(data)).convert("RGBA")
            im.save(dest)
            ok += 1
            continue
        except Exception as e:
            print(f"  ! {pid}: {e}")
    # No cutout upstream. Never clobber a hand-sourced image dropped in here by
    # someone — only (re)write the placeholder over nothing, or over another placeholder.
    if os.path.exists(dest) and not is_placeholder(dest):
        kept += 1
        continue
    ph.save(dest)
    miss += 1
msg = f"✓ {ok} cutouts + {miss} placeholders"
if kept:
    msg += f" + {kept} hand-added kept"
print(f"{msg} -> {OUT}")
