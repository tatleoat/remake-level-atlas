"""Pack backgrounds and item pictures for the atlas: one sheet per room per game, one sheet for items.

REmake backgrounds: Resident Evil HD Remaster (PS3), one 1280x960 base map per camera, extracted by rehd_extract.py
into ps3/bg/. Room codes are assigned through the wiki's article usage for the GameCube images (CODE_ROOM, PAGE_ROOM),
RE1's numbering where the REmake kept it, and a look at the pictures (PS3_CODE_ROOM); codes the wiki split between
two rooms are resolved per camera by matching each PS3 camera to the most similar wiki image of that code. RE1 backgrounds: decoded from the PS1 disc's ROOM*.BSS
(320x240), assigned by room number, BioRand's door graph and a look at the pictures. Items: Evil Resource.
Writes media/remake/<room>.webp, media/re1/<room-or-code>.webp, media/items.webp, media/item_icons.webp (map icons) and media.json.
With a third argument --items it rebuilds only items.webp, item_icons.webp and their media.json entries.
"""
import json, re, sys
from pathlib import Path
from PIL import Image

ROOT = Path(sys.argv[1])
OUT = Path(sys.argv[2])

PAGE_ROOM = {  # wiki article -> room id (only where a room code is split between articles)
    "Spencer Mansion/Tea room": "tea-room", "Spencer Mansion/F-shaped corridor": "northern-corridor",
    "Spencer Mansion/Mansion bathroom": "bathroom", "Spencer Mansion/North-east corridor": "winding-corridor",
    "Large Art Room": "large-art-room", "Costume room": "mirror-room",
    "Dormitory/Room 003": "room-003", "Dormitory/Room 001": "room-001",
    "Dormitory/Room 002 bathroom": "room-002-bathroom", "Dormitory/Room 003 bathroom": "room-003-bathroom",
    "Arklay Laboratory/Morgue": "morgue", "Operating room": "surgeons-room",
    "Spencer Mansion/West staircase": "west-wing-inner-stairway", "2F west staircase": "west-wing-inner-stairway",
}
CODE_ROOM = {  # REmake room code -> room id
    "r100": "mansion-drug-room", "r101": "west-wing-inner-stairway", "r102": "small-storeroom", "r103": "tea-room",
    "r105": "dining-room", "r107": "art-room", "r108": "l-corridor", "r109": "bathroom", "r10a": "dark-corridor",
    "r10b": "graveyard", "r10e": "researchers-bedroom", "r10f": "bar", "r111": "large-art-room",
    "r112": "west-wing-outer-stairway", "r114": "outside-boiler", "r116": "living-room", "r117": "large-gallery",
    "r118": "east-wing-storeroom", "r11a": "roofed-passage", "r11b": "garden-shed", "r202": "dining-room-2f",
    "r203": "outside-balcony", "r204": "c-corridor", "r205": "armor-room", "r206": "small-library", "r208": "deer-room",
    "r209": "bedroom", "r20a": "fish-tank-room", "r20b": "resting-room", "r20c": "sliding-trap-room",
    "r20d": "pillar-room", "r20e": "attic-entry", "r20f": "small-dining-room", "r210": "attic", "r212": "outside-patio",
    "r213": "elevator-corridor", "r214": "mirror-corridor", "r215": "trophy-room", "r216": "library",
    "r217": "death-passage", "r219": "materials-room", "r21a": "concrete-passage-1", "r21b": "concrete-passage-2",
    "r21c": "kitchen", "r300": "main-garden", "r302": "falls-area", "r303": "landing-point", "r304": "zigzag-path",
    "r305": "fountain", "r306": "underground-statue-room", "r30c": "underground-storage-room", "r30d": "straight-passage",
    "r311": "muddy-path", "r312": "small-headstone-area", "r313": "forest-pathway", "r314": "cabin",
    "r31a": "stairway-passage", "r401": "room-001", "r402": "room-001-bathroom", "r403": "residence-storeroom",
    "r404": "rec-room", "r405": "central-corridor", "r406": "room-002", "r407": "room-002-bathroom", "r408": "gallery",
    "r409": "residence-medical-room", "r40c": "plant-42-room", "r40d": "aqua-ring-entry", "r500": "laboratory-entrance",
    "r501": "passage-to-heliport", "r502": "item-box-room", "r503": "laboratory-stairway", "r504": "visual-data-room",
    "r505": "o-room", "r506": "operating-room", "r507": "morgue", "r508": "pass-code-corridor", "r509": "x-ray-room-a",
    "r50a": "x-ray-room-b", "r50b": "cell-entrance", "r50c": "elevator-entry", "r50d": "elevator-entry",
    "r50e": "laboratory-lounge-room", "r50f": "power-maze-a", "r510": "power-maze-b", "r511": "power-control-room",
    "r512": "cell", "r513": "main-laboratory", "r514": "main-laboratory-entrance", "r515": "main-laboratory-entrance",
}
# RE1 room code -> (REmake room id or None, RE1 name, how sure). None = no counterpart in the REmake.
RE1 = {
    "100": ("mansion-drug-room", "Storeroom (save room)", "sure"), "101": ("west-wing-inner-stairway", "West staircase", "sure"),
    "102": ("small-storeroom", "Closet", "sure"), "103": ("northern-corridor", "F-shaped corridor", "sure"),
    "104": ("tea-room", "Corridor where Kenneth is found (the REmake's Tea Room stands here)", "likely"),
    "105": ("dining-room", "Dining room", "sure"), "106": ("main-hall", "Main hall", "sure"),
    "107": ("art-room", "Statue room", "sure"), "108": ("l-corridor", "L-shaped corridor", "sure"),
    "109": ("winding-corridor", "North-east corridor", "sure"), "10A": ("dark-corridor", "Corridor to the back entrance", "sure"),
    "10B": ("east-wing-stairway", "East staircase", "sure"), "10C": ("greenhouse", "Greenhouse", "sure"),
    "10D": ("tiger-statue-room", "Tiger statue room", "sure"), "10E": ("researchers-bedroom", "Keeper's bedroom", "sure"),
    "10F": ("bar", "Piano bar", "sure"), "110": ("tea-room", "Stairwell to the kitchen", "likely"),
    "111": ("large-art-room", "Globe room", "likely"), "112": ("mirror-room", "Room beyond the globe room", "likely"),
    "113": ("bathroom", "Bathroom", "sure"), "114": ("outside-boiler", "Boiler yard", "sure"),
    "115": ("marble-room", "Trap room", "likely"), "116": ("living-room", "Living room", "sure"),
    "117": ("large-gallery", "Gallery", "sure"), "118": ("east-wing-storeroom", "East storeroom (save room)", "sure"),
    "119": ("courtyard-study", "Study", "likely"), "11A": ("roofed-passage", "Passage to the shed", "sure"),
    "11B": ("garden-shed", "Shed", "sure"), "11C": ("hidden-wardrobe", "Closet", "likely"),
    "200": (None, "Kitchen lift", "sure"), "201": ("west-wing-inner-stairway", "West staircase 2F", "sure"),
    "202": ("dining-room-2f", "Dining room balcony", "sure"), "203": ("main-hall", "Main hall 2F", "sure"),
    "204": ("c-corridor", "U-shaped corridor", "sure"), "205": ("armor-room", "Armour room", "sure"),
    "206": ("small-library", "Reading room", "sure"), "207": ("east-wing-stairway", "East staircase 2F", "sure"),
    "208": ("deer-room", "Stuffed deer room", "sure"), "209": ("bedroom", "Bedroom", "sure"),
    "20A": ("fish-tank-room", "Researcher's room", "sure"), "20B": ("resting-room", "Lounge", "sure"),
    "20C": ("sliding-trap-room", "Lesson room", "likely"), "20D": ("pillar-room", "Pillar corridor", "sure"),
    "20E": ("attic-entry", "Attic landing", "sure"), "20F": ("small-dining-room", "Small dining room", "sure"),
    "210": ("attic", "Attic", "sure"), "211": (None, "Corridor to the balcony", "likely"),
    "212": ("outside-patio", "Balcony", "likely"), "213": ("elevator-corridor", "Corridor by the lift", "sure"),
    "214": ("mirror-corridor", "West corridor", "likely"), "215": ("trophy-room", "Trophy room", "sure"),
    "216": ("library", "Library", "likely"), "217": ("library", "Library (stacks)", "likely"),
    "218": (None, "Small study", "unsure"), "219": ("materials-room", "Storage closet", "sure"),
    "21A": ("concrete-passage-1", "Underground passage 1", "sure"), "21B": ("concrete-passage-2", "Underground passage 2", "sure"),
    "21C": ("kitchen", "Kitchen", "sure"),
    "300": ("main-garden", "Courtyard", "likely"), "301": ("water-pool", "Reservoir", "sure"),
    "302": ("falls-area", "Waterfall courtyard", "likely"), "303": ("landing-point", "Heliport lift", "likely"),
    "304": ("zigzag-path", "Path to the guardhouse", "sure"), "305": ("fountain", "Fountain garden", "likely"),
    "306": (None, "Caves (306)", "unsure"), "307": (None, "Behind the waterfall (307)", "unsure"),
    "308": (None, "Caves (308)", "unsure"), "309": (None, "Caves (309)", "unsure"), "30A": (None, "Caves (30A)", "unsure"),
    "30B": (None, "Caves (30B)", "unsure"), "30C": (None, "Caves (30C)", "unsure"), "30D": (None, "Caves (30D)", "unsure"),
    "30E": (None, "Caves break room (30E)", "unsure"), "30F": (None, "Caves (30F)", "unsure"),
    "310": ("fountain", "Stairs down through the fountain", "likely"), "311": (None, "Courtyard (311)", "unsure"),
    "400": ("entry-corridor", "Entrance hallway", "sure"), "401": ("room-001", "Room 001", "likely"),
    "402": ("room-001-bathroom", "Room 001 bathroom", "likely"), "403": ("residence-storeroom", "Break room", "sure"),
    "404": ("rec-room", "Recreation room", "sure"), "405": ("central-corridor", "Corridor", "sure"),
    "406": ("room-002", "Room 002", "sure"), "407": ("room-002-bathroom", "Room 002 bathroom", "sure"),
    "408": ("gallery", "Gallery", "sure"), "409": ("residence-medical-room", "Pharmacy", "sure"),
    "40A": ("room-003", "Room 003", "sure"), "40B": ("room-003-bathroom", "Room 003 bathroom", "sure"),
    "40C": ("plant-42-room", "Plant 42's room", "sure"), "40D": ("aqua-ring-entry", "Passage to the large tank", "sure"),
    "40E": ("aqua-ring-walkway", "Aqua Ring corridor", "likely"), "40F": ("guard-room", "Aqua Ring room (40F)", "unsure"),
    "410": ("aqua-ring-storage", "Storage", "unsure"), "411": ("control-room", "Control room", "likely"),
    "500": ("laboratory-entrance", "Laboratory entrance", "sure"), "501": ("passage-to-heliport", "Way to the heliport", "sure"),
    "502": ("item-box-room", "Preparation room", "sure"), "503": ("laboratory-stairway", "B2 stair hall", "sure"),
    "504": ("visual-data-room", "Visual data room", "sure"), "505": ("o-room", "Central cloister", "sure"),
    "506": ("operating-room", "Laboratory", "sure"), "507": ("morgue", "Morgue", "sure"),
    "508": ("pass-code-corridor", "B3 west corridor", "sure"), "509": ("x-ray-room-a", "X-ray room", "sure"),
    "50A": ("x-ray-room-b", "Researcher's private room", "sure"), "50B": ("cell-entrance", "Detention passage", "sure"),
    "50C": ("elevator-entry", "T-shaped corridor", "sure"), "50D": ("passage-to-heliport", "Lift to the heliport", "likely"),
    "50E": ("laboratory-lounge-room", "Lounge", "sure"), "50F": ("power-maze-a", "Power room passage A", "sure"),
    "510": ("power-maze-b", "Power room passage B", "sure"), "511": ("power-control-room", "Power room", "sure"),
    "512": ("cell", "Detention chamber", "sure"), "513": ("main-laboratory", "Tyrant's laboratory", "sure"),
    "514": ("main-laboratory-entrance", "B4 corridor", "sure"), "515": ("main-laboratory-entrance", "Main lift", "likely"),
}
RE1_AREA = {"1": "mansion", "2": "mansion", "3": "courtyard", "4": "guardhouse", "5": "lab"}
STREAKED = {"200", "306", "307", "30B", "30F", "50D", "515"}


PER = 8  # full-size cameras per sheet (2 x 4 at 1280x960): small enough for a browser to decode comfortably
PS3_CODE_ROOM = {  # codes the wiki has no images for; numbering follows RE1 where the REmake kept the room
    "r106": "main-hall", "r10c": "greenhouse", "r10d": "tiger-statue-room", "r115": "marble-room",
    "r119": "courtyard-study", "r11c": "hidden-wardrobe", "r207": "east-wing-stairway", "r301": "water-pool",
    "r400": "entry-corridor", "r40a": "room-003", "r40b": "room-003-bathroom",
    # identified by eye from the PS3 pictures (caves follow the route order of the codes)
    "r307": "mining-area", "r308": "forked-passage", "r309": "generator-room", "r30a": "enrico-room",
    "r30b": "boulder-passage-1", "r30c": "spider-room", "r30f": "boulder-passage-2", "r315": "jessicas-tomb",
    "r316": "garbage-compactor-room", "r317": "winding-underground-passage", "r318": "underground-storage-room",
    "r319": "lisas-room", "r40e": "aqua-ring-walkway", "r40f": "guard-room", "r410": "aqua-ring-storage",
    "r411": "control-room", "r412": "aqua-ring-water-tank",
}
SPLIT = {"r103", "r109", "r111", "r507"}
CAMERA_SPLIT = {  # cameras of one code that show a neighbouring room (checked by eye)
    "r20c": [(0, 2, "secret-passage")],     # Trevor's tomb under the crushing room
    "r40d": [(8, 11, "aqua-ring-exit")],    # the V-shaped hall with the ladder
}
GC_ONLY = [  # rooms the HD Remaster draws in real-time 3D: the wiki's GameCube shots stand in
    ("r112", lambda n: True, "west-wing-outer-stairway"),
    ("r10b", lambda n: n >= 184 and n != 305, "crypt"),
]  # one code, two rooms on the wiki: resolve per camera
ONLY = {"r401": "room-001", "r407": "room-002-bathroom"}  # the wiki reused these for Room 003, which has its own codes


def _vec(im):
    px = list(im.convert("L").resize((32, 24), Image.BILINEAR).getdata())
    m = sum(px) / len(px)
    v = [p - m for p in px]
    n = sum(x * x for x in v) ** 0.5 or 1
    return [x / n for x in v]


def remake_cameras():
    """room id -> [(code, camera, file)] for the PS3 base maps (first texture of each camera)."""
    use = json.load(open(ROOT / "wiki" / "fileusage.json"))
    pat = re.compile(r"^R([1-7][0-9a-fA-F]{2})_(\d{5})\.")
    wiki = {}
    for f in (ROOT / "wiki" / "bg").iterdir():
        m = pat.match(f.name)
        code = "r" + m.group(1).lower()
        if code in SPLIT:
            rooms = [PAGE_ROOM[p] for p in use.get("File:" + f.name.replace("_", " "), []) if p in PAGE_ROOM]
            if rooms:
                wiki.setdefault(code, []).append((_vec(Image.open(f)), rooms[0]))
    by_room = {}
    for line in open(ROOT / "ps3" / "bg" / "index.tsv"):
        fn, code, cam, layer = line.split("\t")[:4]
        if fn == "ERROR" or layer != "0":
            continue
        f = ROOT / "ps3" / "bg" / fn
        if code in SPLIT:
            v = _vec(Image.open(f))
            room = max(wiki[code], key=lambda w: sum(a * b for a, b in zip(v, w[0])))[1]
        else:
            room = ONLY.get(code) or PS3_CODE_ROOM.get(code) or CODE_ROOM.get(code)
            room = next((r for a, b, r in CAMERA_SPLIT.get(code, []) if a <= int(cam) <= b), room)
        if room:
            by_room.setdefault(room, []).append((code, int(cam), f))
    return by_room


def gc_fallback(by_room):
    """Add the wiki's GameCube images for rooms the PS3 package has no pre-rendered backgrounds for."""
    pat = re.compile(r"^R([1-7][0-9a-fA-F]{2})_(\d{5})\.")
    for f in sorted((ROOT / "wiki" / "bg").iterdir()):
        m = pat.match(f.name)
        code, num = "r" + m.group(1).lower(), int(m.group(2))
        for c, keep, room in GC_ONLY:
            if c == code and keep(num) and (room not in by_room or by_room[room][0][0] == "gc"):
                by_room.setdefault(room, []).append(("gc", num, f))
    return by_room


def sheet(images, cell, cols, path, quality=82):
    rows = (len(images) + cols - 1) // cols
    s = Image.new("RGB", (cell[0] * cols, cell[1] * rows), (0, 0, 0))
    for i, im in enumerate(images):
        s.paste(im.convert("RGB").resize(cell, Image.LANCZOS), ((i % cols) * cell[0], (i // cols) * cell[1]))
    path.parent.mkdir(parents=True, exist_ok=True)
    s.save(path, "WEBP", quality=quality, method=5)
    return rows


ICON, ICON_COLS = 80, 16


def item_files():
    items = {}
    for f in sorted((ROOT / "web" / "items" / "thumbs").glob("*.png")):
        full = ROOT / "web" / "items" / "full" / f.name
        items[f.stem] = full if full.exists() and full.stat().st_size else f
    return items, sorted(items)


def icon_sheet(items, names):
    """Map icons: each item picture cropped to the object (the renders sit on black), padded square, 80x80, same order as items.webp."""
    s = Image.new("RGB", (ICON * ICON_COLS, ICON * ((len(names) + ICON_COLS - 1) // ICON_COLS)), (0, 0, 0))
    for i, n in enumerate(names):
        im = Image.open(items[n]).convert("RGB")
        box = im.convert("L").point(lambda v: 255 if v > 24 else 0).getbbox() or (0, 0, *im.size)
        im = im.crop(box)
        side = int(max(im.size) * 1.08) + 2
        sq = Image.new("RGB", (side, side), (0, 0, 0))
        sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
        s.paste(sq.resize((ICON, ICON), Image.LANCZOS), ((i % ICON_COLS) * ICON, (i // ICON_COLS) * ICON))
    s.save(OUT / "item_icons.webp", "WEBP", quality=86, method=5)
    return {"file": "media/item_icons.webp", "cols": ICON_COLS, "size": ICON, "w": s.width, "h": s.height}


def main():
    if sys.argv[3:] == ["--items"]:  # rebuild only the item sheets, keep the backgrounds in media.json
        media = json.load(open(OUT / "media.json"))
        items, names = item_files()
        rows = sheet([Image.open(items[n]) for n in names], (225, 180), 12, OUT / "items.webp")
        media["items"] = {"file": "media/items.webp", "cols": 12, "rows": rows, "w": 225, "h": 180, "index": {n: i for i, n in enumerate(names)}}
        media["icons"] = icon_sheet(items, names)
        json.dump(media, open(OUT / "media.json", "w"), separators=(",", ":"))
        print(len(names), "item pictures;", media["icons"])
        return
    media = {"remake": {}, "re1": {}, "re1_only": [], "items": {}}
    for room, cams in gc_fallback(remake_cameras()).items():
        if cams and cams[0][0] == "gc":  # GameCube images from the wiki, only where the PS3 package has none
            files = [f for _, _, f in cams]
            d = OUT / "remake" / room
            rows = sheet([Image.open(f) for f in files], (512, 448), 4, d / "gc.webp")
            media["remake"][room] = {"n": len(files), "src": "gc", "labels": [f.stem for f in files],
                                     "thumb": {"file": f"media/remake/{room}/gc.webp", "cols": 4, "rows": rows, "w": 512, "h": 448},
                                     "full": {"files": [f"media/remake/{room}/gc.webp"], "per": len(files), "cols": 4, "w": 512, "h": 448}}
            continue
        cams.sort()
        d = OUT / "remake" / room
        full = []
        for s in range(0, len(cams), PER):
            part = cams[s:s + PER]
            sheet([Image.open(f) for _, _, f in part], (1280, 960), 2, d / f"full_{s // PER}.webp", quality=80)
            full.append(f"media/remake/{room}/full_{s // PER}.webp")
        rows = sheet([Image.open(f) for _, _, f in cams], (192, 144), 6, d / "thumbs.webp", quality=80)
        media["remake"][room] = {"n": len(cams), "src": "ps3", "labels": [f"{c}_{n:02d}" for c, n, _ in cams],
                                 "thumb": {"file": f"media/remake/{room}/thumbs.webp", "cols": 6, "rows": rows, "w": 192, "h": 144},
                                 "full": {"files": full, "per": PER, "cols": 2, "w": 1280, "h": 960}}
    groups = {}
    for f in sorted((ROOT / "re1" / "bg").glob("ROOM*.png"), key=lambda p: (p.stem.split("_")[0], int(p.stem.split("_")[1]))):
        code = f.stem.split("_")[0][4:]
        groups.setdefault(code, []).append(f)
    for code, files in groups.items():
        room, name, sure = RE1[code]
        key = room or f"re1-{code.lower()}"
        entry = media["re1"].setdefault(key, {"n": 0, "cols": 4, "w": 320, "h": 240, "labels": [], "parts": [], "_files": []})
        entry["parts"].append({"code": code, "name": name, "sure": sure, "n": len(files), "motion": code in STREAKED})
        entry["_files"] += files
        entry["labels"] += [f"ROOM{code}_{i}" for i in range(len(files))]
        entry["n"] += len(files)
        if room is None:
            media["re1_only"].append({"key": key, "code": code, "name": name, "area": RE1_AREA[code[0]], "sure": sure})
    for key, e in media["re1"].items():
        rows = sheet([Image.open(f) for f in e.pop("_files")], (320, 240), 4, OUT / "re1" / f"{key}.webp")
        f = f"media/re1/{key}.webp"
        e["thumb"] = {"file": f, "cols": 4, "rows": rows, "w": 320, "h": 240}
        e["full"] = {"files": [f], "per": e["n"], "cols": 4, "w": 320, "h": 240}
        for k in ("cols", "w", "h"):
            e.pop(k)
    # items: one sheet of 225x180 cells (full renders where fetched, thumbnails otherwise)
    items, names = item_files()
    rows = sheet([Image.open(items[n]) for n in names], (225, 180), 12, OUT / "items.webp")
    media["items"] = {"file": "media/items.webp", "cols": 12, "rows": rows, "w": 225, "h": 180, "index": {n: i for i, n in enumerate(names)}}
    media["icons"] = icon_sheet(items, names)
    json.dump(media, open(OUT / "media.json", "w"), separators=(",", ":"))
    print(len(media["remake"]), "rooms with REmake backgrounds,", sum(e["n"] for e in media["remake"].values()), "images;",
          len(media["re1"]), "RE1 groups,", sum(e["n"] for e in media["re1"].values()), "images;", len(names), "item pictures")


if __name__ == "__main__":
    main()
