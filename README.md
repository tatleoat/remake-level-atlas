# REmake Level Atlas

An interactive map and progression model of *Resident Evil* (2002, the GameCube "REmake"). The page covers:
- all 122 rooms and 134 doors, with every lock
- what each character needs to reach each room
- every route from one objective to the next, with the alternative ways
- a room-by-room route player that runs the game state as you step through it
- background pictures from the REmake and the 1996 original, side by side

It has three looks: **REmake (2002)** (the default), **Resident Evil 2 (1998)** and **Atlas** (plain dark map).

It is one static page (`index.html`) with no server and no build step needed to use it.

## No game art in this repository

The backgrounds and item pictures are Capcom's, so this repository ships none of them. The page rebuilds them **in your
browser from your own copies of the games** through the **Assets** button. They are stored in the browser's IndexedDB
and never uploaded anywhere.

| Import | What you pick | What it gives | Time |
|---|---|---|---|
| Resident Evil (PlayStation, 1996) | the disc image as `.bin` (MODE2/2352) or `.iso` | 655 RE1 backgrounds in 108 rooms | ~10 s |
| Resident Evil HD Remaster (PlayStation 3) | the game's `.pkg`, or its installed `USRDIR` / `nativePS3` folder | 1,641 REmake backgrounds at 1280×960 in 120 rooms, and the game's own inventory icons for 102 items | ~1.5 min |
| Asset pack | a `.zip` made with `tools/make_pack.py` from a private build | everything, plus Evil Resource's room descriptions | seconds |

Notes:
- **Converting a `.chd`:** `chdman extractcd -i game.chd -o game.cue -ob game.bin`. The RE1 import was tested with *Resident Evil (USA)*.
- **PS3 package:** it is decrypted in the browser with the published PS3 package key, the same one RPCS3's installer uses. Only the parts of each archive that hold a background are read.
- **Other releases:** the PC, PS4 and Xbox releases of the HD Remaster use different archive formats and are not supported.
- **Not on any disc:**
  - Two REmake rooms (the Crypt and the West Wing Outer Stairway) are drawn in real-time 3D in the HD Remaster, so they have no pre-rendered background.
  - Files, maps and enemies have no inventory icon. Without a picture, the map draws each item as a small line glyph of its type.
- **Asset pack contents:** the pack carries the GameCube shots of the two 3D rooms, Evil Resource's item renders and descriptions, and every background. Keep it private.

## What the page does

- **Explore:** walk door to door, pick up items, or tick any key or event to test a what-if. Rooms recolour by what is
  reachable. Room cards show the doors and locks, the contents per character and difficulty, the smallest set of items
  that opens the room, and alternative routes.
- **Route:** both characters' item routes, in walkthrough order or "nearest-next" (only what the ending needs).
  - **Ways:** pick a leg to see each way of walking it with what you hold at that point, and choose one.
  - **Route player:** steps room by room (buttons, slider, arrow keys, Play). It runs the simulation as it goes: where you stand, what you carry, which doors are open. The camera follows you between floors.
- **Locks / Analysis:** every lock and how much it holds back, progression layers, chokepoints, hub scores, distance to
  a save room, enemies per room.
- **Gallery:** every room's backgrounds, REmake beside RE1.
- **Map:**
  - Door marks come from the in-game map.
  - Stair badges jump to the connected floor.
  - Item icons are framed by type: keys, puzzle items, healing, weapons, ammo and so on.

## The looks

- **Resident Evil 2 (1998):** colours taken from the game's own status-screen textures on the Leon disc
  (`COMMON/DATA/ST0.TIM`, `SELECT_W.TIM`, `CONFIG.TIM`). Brushed gunmetal plates, green ECG/LCD readouts, navy
  fields, a blue map on a black grid, pale serif capitals.
- **REmake (2002):** colours taken from the HD Remaster's status, file and map screens (`id/e_rom/subscr/*.arc`).
  Those textures store brightness in alpha and chroma in red and blue (YCbCr in DXT5 blocks). The palette:
  - green-black gunmetal
  - olive-tan file paper
  - bone text and amber labels
  - copper wall lines on a khaki map
  - a blood-red route
  - type after the game's menus: Archivo Narrow for commands and room names (the game's Equip/Use/Combine buttons
    are a condensed grotesque), IM Fell English for headings (old print, like the files), Special Elite typewriter
    for numbers and tags; all free Google Fonts
  - film grain and a vignette

## Layout

| Path | What it is |
|---|---|
| `index.html` | The page: `src/app_template.html` with `data/remake_map.json` inside |
| `src/app_template.html` | Page source: styles, map, logic engine, importers, Assets dialog |
| `data/remake_map.json` | The public model: floors, room outlines, doors and locks, items and events, objectives, the import plan (which camera or frame belongs to which room). No pictures, no Evil Resource text |
| `data/rooms.csv`, `doors.csv`, `items.csv` | The same model as plain tables |
| `tools/` | The build pipeline, the extraction tools for private builds, and the tests |

After editing the page source:

```sh
python3 tools/render_page.py src/app_template.html data/remake_map.json index.html
node tools/test_engine.js index.html          # both characters can still finish; no blocked leg
node tools/test_import.js index.html RE1.bin "Resident Evil HD.pkg" /tmp/out   # importers on real files
```

Rebuilding the model itself needs Evil Resource's map pages, which you fetch yourself:
1. `tools/fetch.sh` and `tools/parse_areas.py` / `tools/parse_rooms.py` read the map pages.
2. `tools/symbols.py` reads door marks, stairs and raised floors from the floor images.
3. `tools/build.py ROOT OUT.json OUT.html --public` writes the public model.

A private build without `--public` embeds the pictures that `tools/media.py` packs from your own extractions:
- `tools/rehd_extract.py` with `tools/ps3pkg.py` for the PS3 copy
- `tools/iso9660.py` with `tools/bsdecode.py` for the PS1 disc

`tools/make_pack.py` turns a private build into an asset pack.

## Credits

- **Map data:** room outlines, door links and room contents come from [Evil Resource](https://www.evilresource.com/resident-evil-remake/maps), traced from the game's map screen. Their descriptions are not in this repository.
- **Item and event logic:** checked against the GameFAQs guides by CyricZ (item guide) and Albert VVesker (puzzle guide), and several walkthroughs.
- **PS3 archive layout:** the SFH wrapper layout comes from kapdap's re-cvx-tools.
- **RE1 rooms:** mapped to REmake rooms with help from BioRand's door graph.
- **Game:** all game art and names are Capcom's.
