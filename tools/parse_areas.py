"""Parse Evil Resource's REmake area map pages: one row per room outline (floor, id, name, polygon)."""
import html, json, re, sys
from pathlib import Path

web = Path(sys.argv[1])
rooms = []
floors = {}
for f in sorted(web.glob("area_*.html")):
    t = f.read_text(encoding="utf-8")
    for img in re.finditer(r'<img src="(/maps/(remake_[a-z0-9]+)/map\.gif)[^"]*" usemap="#\2_map" alt="Image of ([^"]+)" width="(\d+)" height="(\d+)"', t):
        floors[img[2]] = {"floor_id": img[2].removeprefix("remake_"), "label": img[3], "w": int(img[4]), "h": int(img[5]),
                          "area_page": f.stem.removeprefix("area_"), "gif": img[1]}
    for m in re.finditer(r'<map id="(remake_[a-z0-9]+)_map"(.*?)</map>', t, re.S):
        for a in re.finditer(r'<area ([^>]*)>', m[2]):
            at = dict(re.findall(r'([a-z-]+)="([^"]*)"', a[1]))
            c = [int(v) for v in at["coords"].split(",")]
            if at["shape"] == "rect":
                x0, y0, x1, y1 = c
                c = [x0, y0, x1, y0, x1, y1, x0, y1]
            rooms.append({"floor": m[1].removeprefix("remake_"), "id": at["data-id"], "name": html.unescape(at["data-name"]),
                          "loc": at["data-location"], "poly": c})
json.dump({"floors": list(floors.values()), "outlines": rooms}, open(sys.argv[2], "w"), indent=1)
ids = {r["id"] for r in rooms}
print(len(rooms), "outlines,", len(ids), "rooms,", len(floors), "floors")
multi = {}
for r in rooms:
    multi.setdefault(r["id"], set()).add(r["floor"])
print("on several floors:", {k: sorted(v) for k, v in multi.items() if len(v) > 1})
