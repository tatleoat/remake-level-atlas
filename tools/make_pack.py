"""Zip a private build's pictures and Evil Resource's room descriptions into an asset pack for a public copy of the page.

Usage: make_pack.py PRIVATE_DIR OUT.zip   (PRIVATE_DIR holds media/ and the private remake_map.json)
The page's Assets dialog imports it; keep the zip private, it holds Capcom's art and Evil Resource's text.
"""
import json, sys, zipfile
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
data = json.load(open(src / "remake_map.json"))
texts = {r["id"]: [c.get("d", "") for c in r["contents"]] for r in data["rooms"]}
n = 0
with zipfile.ZipFile(out, "w") as z:
    for f in sorted((src / "media").rglob("*")):
        if f.is_file():  # pictures are already compressed: stored; json deflated
            z.write(f, f.relative_to(src).as_posix(), compress_type=zipfile.ZIP_DEFLATED if f.suffix == ".json" else zipfile.ZIP_STORED)
            n += 1
    z.writestr("texts.json", json.dumps(texts, separators=(",", ":")), compress_type=zipfile.ZIP_DEFLATED)
print(f"{out}: {n} files + texts.json, {out.stat().st_size // 2**20} MB")
