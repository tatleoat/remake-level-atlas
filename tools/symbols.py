"""Vectorise the map symbols in Evil Resource's floor images: door bars, stair hatching, raised areas.

Writes symbols.json: per floor, door rectangles with the two rooms each one sits between, stair stripes as
line segments, and raised areas (dark green) as rectangles. Coordinates match the room outlines.
"""
import json, sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from geometry import inside, pts, area

ROOT = Path(sys.argv[1])
DOOR = {(204, 153, 0), (204, 153, 51)}
STAIR = {(0, 0, 0)}
RAISED = {(0, 51, 0)}


def components(px, w, h, colours):
    seen, out = set(), []
    for y in range(h):
        for x in range(w):
            if (x, y) in seen or px[x, y] not in colours:
                continue
            stack, comp = [(x, y)], []
            seen.add((x, y))
            while stack:
                cx, cy = stack.pop()
                comp.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and px[nx, ny] in colours:
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            out.append(comp)
    return out


def bbox(c):
    xs, ys = [p[0] for p in c], [p[1] for p in c]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def rects_of(comp):
    """Cover a component with rectangles: horizontal runs per row, merged down while identical."""
    rows = {}
    for x, y in comp:
        rows.setdefault(y, []).append(x)
    runs = []
    for y in sorted(rows):
        xs = sorted(rows[y])
        s = p = xs[0]
        for x in xs[1:] + [None]:
            if x is not None and x == p + 1:
                p = x
                continue
            runs.append([s, y, p + 1, y + 1])
            if x is not None:
                s = p = x
    merged = []
    for r in runs:
        for m in merged:
            if m[0] == r[0] and m[2] == r[2] and m[3] == r[1]:
                m[3] = r[3]
                break
        else:
            merged.append(r)
    return merged


def main():
    o = json.load(open(ROOT / "outlines.json"))
    out = {}
    for f in o["floors"]:
        fid = f["floor_id"]
        im = Image.open(ROOT / "web" / "gifs" / f"{fid}.gif").convert("RGB")
        w, h = im.size
        px = im.load()
        ols = [(x["id"].split("/")[1], pts(x["poly"]), area(x["poly"])) for x in o["outlines"] if x["floor"] == fid]

        def room_at(x, y):
            hits = [(a, s) for s, P, a in ols if inside((x, y), P)]
            return min(hits)[1] if hits else None

        doors = []
        for c in components(px, w, h, DOOR):
            x0, y0, x1, y1 = bbox(c)
            horiz = (x1 - x0) >= (y1 - y0)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            sides = []
            for sign in (-1, 1):
                hit = None
                for d in (2, 3, 4, 6, 8, 11):
                    p = (cx, (y0 - d if sign < 0 else y1 + d)) if horiz else ((x0 - d if sign < 0 else x1 + d), cy)
                    hit = room_at(*p)
                    if hit:
                        break
                sides.append(hit)
            doors.append({"rect": [x0, y0, x1 - x0, y1 - y0], "horiz": horiz, "rooms": sides})
        stripes, icons = [], []
        for c in components(px, w, h, STAIR):
            x0, y0, x1, y1 = bbox(c)
            if (x1 - x0 == 1 or y1 - y0 == 1) and len(c) == (x1 - x0) * (y1 - y0) and max(x1 - x0, y1 - y0) >= 3:
                stripes.append([x0, y0, x1, y1])
            else:
                icons.extend(rects_of(c))
        raised = []
        for c in components(px, w, h, RAISED):
            raised.extend(rects_of(c))
        out[fid] = {"doors": doors, "stripes": stripes, "icons": icons, "raised": raised}
        print(f"{fid}: {len(doors)} door marks, {len(stripes)} stair stripes, {len(raised)} raised rects")
    json.dump(out, open(ROOT / "symbols.json", "w"))


if __name__ == "__main__":
    main()
