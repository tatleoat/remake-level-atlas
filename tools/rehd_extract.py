"""Extract every background camera from the Resident Evil HD (PS3) package: PKG -> SFH/ARC -> TEX -> WebP.

Usage: rehd_extract.py PKG OUT_DIR   -> OUT_DIR/<room code>_<camera>[_<layer>].webp (1280x960) and index.tsv
"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ps3pkg, rehd

pkg = ps3pkg.Pkg(sys.argv[1])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
idx = open(out / "index.tsv", "w")
pat = re.compile(r"arc/scr/st0\d/(r[0-9a-f]{3})/(r[0-9a-f]{3})(\d\d)\.arc$")
n = 0
for name, do, ds, flags in pkg.entries():
    m = pat.search(name)
    if not m or flags & 0xFF == 0x04:
        continue
    raw = pkg.dec(do, ds)
    try:
        for k, (tname, im, info) in enumerate(rehd.backgrounds(raw)):
            fn = f"{m.group(2)}_{m.group(3)}" + (f"_{k}" if k else "") + ".webp"
            im.save(out / fn, "WEBP", quality=90, method=4)
            idx.write(f"{fn}\t{m.group(1)}\t{int(m.group(3))}\t{k}\t{tname}\t{info[0]}x{info[1]}\tfmt{info[2]}\n")
            n += 1
    except Exception as e:
        idx.write(f"ERROR\t{m.group(1)}\t{m.group(3)}\t\t{name}\t{e}\n")
    idx.flush()
print("done", n, "images")
