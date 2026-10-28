"""Parse Evil Resource REmake room pages into rooms.json: links (with lock notes) and contents per game mode."""
import base64, html, json, re, sys
from pathlib import Path

ROOT = Path(sys.argv[1])
MODES = {"gm24": "jill-ve", "gm25": "chris-ve", "gm26": "jill-easy", "gm27": "chris-easy",
         "gm13": "jill-normal", "gm12": "chris-normal", "gm28": "jill-hard", "gm29": "chris-hard"}


def text(s):
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def links_in(s):
    return [(m[1], text(m[2])) for m in re.finditer(r'<a href="/resident-evil-remake/([^"#]+)"[^>]*>(.*?)</a>', s, re.S)]


outlines = json.load(open(ROOT / "outlines.json"))
out = {}
for o in outlines["outlines"]:
    f = ROOT / "web" / "rooms" / (o["id"].replace("/", "__") + ".html")
    if not f.exists():
        print("missing", f.name)
        continue
    t = f.read_text(encoding="utf-8")
    room = {"id": o["id"], "name": o["name"], "floor": o["floor"], "links": [], "contents": []}
    lk = re.search(r"linked to the following locations:</p>\s*<ul>(.*?)</ul>", t, re.S)
    if lk:
        for li in re.finditer(r"<li>(.*?)</li>", lk[1], re.S):
            a = re.search(r'<a href="/resident-evil-remake/maps/[a-z-]+/([a-z0-9-]+/[a-z0-9-]+)">(.*?)</a>', li[1])
            note = re.search(r'<span class="note">(.*?)</span>', li[1], re.S)
            room["links"].append({"to": a[1], "to_name": text(a[2]),
                                  "note": text(note[1]).strip("() ") if note else "",
                                  "note_links": links_in(note[1]) if note else []})
    loc = re.search(r'<th id="attribute_\d+">Location</th>\s*<td[^>]*>(.*?)&nbsp;', t, re.S)
    room["location"] = text(loc[1]) if loc else ""
    seen = {}
    for li in re.finditer(r'<li data-gamemode="(gm\d+)">(.*?)</li>\s*(?=<li data-gamemode|</ul>)', t, re.S):
        body = li[2]
        title = text(re.search(r"<h4[^>]*>(.*?)</h4>", body, re.S)[1])
        desc_m = re.search(r'<div class="text">(.*?)</div>', body, re.S)
        desc = text(desc_m[1]) if desc_m else ""
        detail = re.search(r'<a href="/resident-evil-remake/([a-z-]+)/([^"]+)" class="btn[^"]*icon-link"', body)
        mapref = re.search(r'#\?([A-Za-z0-9+/=]+)"', body)
        ent = ""
        if mapref:
            raw = mapref[1] + "=" * (-len(mapref[1]) % 4)
            q = base64.b64decode(raw).decode()
            em = re.match(r"0=(e\d+)gm\d+", q)
            ent = em[1] if em else q
        key = (ent or title, desc)
        if key not in seen:
            seen[key] = {"entity": ent, "title": title, "desc": desc,
                         "kind": detail[1] if detail else "", "slug": detail[2] if detail else "",
                         "desc_links": links_in(desc_m[1]) if desc_m else [], "modes": []}
            room["contents"].append(seen[key])
        seen[key]["modes"].append(MODES.get(li[1], li[1]))
    out[o["id"]] = room
json.dump(out, open(ROOT / "rooms_raw.json", "w"), indent=1)
print(len(out), "rooms;", sum(len(r["links"]) for r in out.values()), "links;",
      sum(len(r["contents"]) for r in out.values()), "content entries")
