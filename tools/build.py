"""Build remake_map.json (and the HTML page) for the REmake level atlas.

Inputs: outlines.json and rooms_raw.json (parsed from Evil Resource's REmake map pages) plus the hand-written
progression logic below, checked against the GameFAQs guides in the survival-horror corpus.
"""
import datetime, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from geometry import door_point, label_point, pts, inside, area as poly_area

ROOT = Path(sys.argv[1])
OUT_JSON, OUT_HTML = Path(sys.argv[2]), Path(sys.argv[3])
PUBLIC = "--public" in sys.argv[4:]  # no pictures and no Evil Resource descriptions: safe for a public repo

AREAS = [  # id, label, colour, floors
    ("mansion", "Mansion", "#4a6fa5", ["mansion3f", "mansion2f", "mansion1f", "mansionb1"]),
    ("courtyard", "Courtyard", "#5f8f4e", ["courtyard1f"]),
    ("guardhouse", "Guardhouse", "#a5774a", ["residence1f", "aquaringb1", "aquaringb2"]),
    ("caves", "Caves", "#7a5a8c", ["courtyardb1", "courtyardb2"]),
    ("altar", "Altar", "#9a4f4f", ["altarb1", "altarb2"]),
    ("lab", "Laboratory", "#4f8f8a", ["laboratoryb1", "laboratoryb2", "laboratoryb3", "laboratoryb4", "heliport"]),
]
NAV = [  # floor tab groups, top floor first
    ("Mansion", ["mansion3f", "mansion2f", "mansion1f", "mansionb1"]),
    ("Courtyard", ["courtyard1f", "courtyardb1", "courtyardb2"]),
    ("Guardhouse", ["residence1f", "aquaringb1", "aquaringb2"]),
    ("Altar", ["altarb1", "altarb2"]),
    ("Lab", ["heliport", "laboratoryb1", "laboratoryb2", "laboratoryb3", "laboratoryb4"]),
]
SHORT = {"mansion3f": "3F", "mansion2f": "2F", "mansion1f": "1F", "mansionb1": "B1", "courtyard1f": "1F",
         "courtyardb1": "B1 caves", "courtyardb2": "B2 caves", "heliport": "Heliport", "residence1f": "1F",
         "aquaringb1": "Aqua B1", "aquaringb2": "Aqua B2", "altarb1": "B1", "altarb2": "B2", "laboratoryb1": "B1",
         "laboratoryb2": "B2", "laboratoryb3": "B3", "laboratoryb4": "B4"}
LEVEL = {"mansion3f": 3, "mansion2f": 2, "mansion1f": 1, "mansionb1": -1, "courtyard1f": 1, "courtyardb1": -1,
         "courtyardb2": -2, "heliport": 1, "residence1f": 1, "aquaringb1": -1, "aquaringb2": -2, "altarb1": -1, "altarb2": -2,
         "laboratoryb1": -1, "laboratoryb2": -2, "laboratoryb3": -3, "laboratoryb4": -4}
ATLAS_COLS = [["mansion3f", "mansion2f", "mansion1f", "mansionb1"],
              ["heliport", "courtyard1f", "courtyardb1", "courtyardb2"],
              ["residence1f", "aquaringb1", "aquaringb2", "altarb1", "altarb2"],
              ["laboratoryb1", "laboratoryb2", "laboratoryb3", "laboratoryb4"]]
START = {"jill": "main-hall", "chris": "main-hall"}
START_HAVE = {"jill": [], "chris": ["lighter"]}  # Chris starts with the Lighter

OLD = ["old-key-kitchen", "old-key-bathroom", "old-key-storeroom", "old-key-researchers", "old-key-bedroom"]
NOTE_REQ = {
    "": "",
    "Requires unlocking from the other side": "@other",
    "Requires the Armor Key": "armor-key",
    "Requires the Sword Key": "sword-key",
    "Requires the Helmet Key": "helmet-key",
    "Requires the Shield Key": "shield-key",
    "Requires the Lock Pick as Jill or an Old Key as Chris": " | ".join(["lockpick"] + OLD),
    "Requires two Stone & Metal Objects": "stone-metal-1 & stone-metal-2",
    "Requires the Stone & Metal Object": "stone-metal-1",
    "Requires the Key for the Power Area": "power-key",
    "Requires the Battery": "lift-powered",
    "Requires the Medal of Eagle and the Medal of Wolf": "medal-eagle & medal-wolf",
    "Requires the Key for Room 001": "key-001",
    "Requires the Key for Room 003": "key-003",
    "Requires the Gallery Key": "gallery-key",
    "Requires the Control Room Key": "control-key",
    "Requires the Closet Key": "closet-key",
    "Requires the Emblem Key": "emblem-key",
    "Impassable from this side": None,
}
# Direction-specific gates Evil Resource does not record (puzzles, events, missing links), from the guides.
# (from, to): requirement; None = no way through in that direction. A pair listed here replaces the page data.
GATES = {
    ("graveyard", "crypt"): "arrowhead",
    ("main-garden", "falls-area"): "lift-powered",
    ("falls-area", "main-garden"): "lift-powered",
    ("water-pool", "falls-area"): "pool-drained",
    ("falls-area", "water-pool"): "pool-drained",
    ("falls-area", "mining-area"): "waterfall-stopped",
    ("muddy-path", "small-headstone-area"): "weathervanes",
    ("cabin", "lisas-room"): "@other",
    ("central-corridor", "room-002"): "",
    ("room-002", "central-corridor"): "",
    ("entry-corridor", "central-corridor"): "crate-bridge | plant42-dead",
    ("central-corridor", "entry-corridor"): "crate-bridge | plant42-dead",
    ("entry-corridor", "room-001"): "key-001 & crate-bridge | key-001 & plant42-dead",
    ("room-002", "aqua-ring-entry"): "bookcases-002",
    ("aqua-ring-entry", "aqua-ring-walkway"): "aqua-crates",
    ("aqua-ring-walkway", "aqua-ring-entry"): "aqua-crates",
    ("control-room", "aqua-ring-storage"): "aqua-drained",
    ("aqua-ring-storage", "control-room"): "aqua-drained",
    ("gallery", "plant-42-room"): "@other",
    ("plant-42-room", "gallery"): "plant42-dead",
    ("room-003", "plant-42-room"): "red-book-shelf",
    ("gallery", "residence-medical-room"): "medical-code",
    ("kitchen", "elevator-corridor"): "kitchen-fuse",
    ("elevator-corridor", "kitchen"): "kitchen-fuse",
    ("kitchen", "concrete-passage-2"): "@other",
    ("sliding-trap-room", "secret-passage"): "crusher-statue",
    ("stairway-passage", "jessicas-tomb"): "",
    ("jessicas-tomb", "stairway-passage"): "",
    ("jessicas-tomb", "fountain"): "lisa-defeated",
    ("laboratory-stairway", "visual-data-room"): "lab-computer",
    ("pass-code-corridor", "x-ray-room-b"): "lab-computer",
    ("pass-code-corridor", "cell-entrance"): "prison-door",
    ("cell-entrance", "cell"): "tyrant-defeated",
    ("elevator-entry", "main-laboratory-entrance"): "lab-elevator",
    ("main-laboratory-entrance", "elevator-entry"): "lab-elevator",
    ("laboratory-entrance", "passage-to-heliport"): "tyrant-defeated",
    ("passage-to-heliport", "landing-point"): "fuse-unit",
    ("landing-point", "passage-to-heliport"): "fuse-unit",
    ("mining-area", "boulder-passage-1"): "hex-crank",
    ("straight-passage", "boulder-passage-2"): "hex-crank",
    ("generator-room", "garbage-compactor-room"): "cave-elevator",
    ("garbage-compactor-room", "generator-room"): "cave-elevator",
    ("winding-underground-passage", "lisas-room"): "flamethrower-hooks",
}
GATE_NOTES = {
    ("main-garden", "falls-area"): "Lift; dead until the Battery is fitted in the Falls Area",
    ("water-pool", "falls-area"): "Path across the reservoir floor, once it is drained with the Square Crank",
    ("falls-area", "mining-area"): "Behind the waterfall; refill the reservoir to stop it",
    ("muddy-path", "small-headstone-area"): "Gate opens when both weathervanes are set (red west, blue north)",
    ("cabin", "lisas-room"): "Trapdoor; opened from below",
    ("entry-corridor", "central-corridor"): "Plant 42's vines strike from holes in the floor; push the crate into a bridge (not needed once the plant is dead)",
    ("room-002", "aqua-ring-entry"): "Ladder hidden behind the two bookcases",
    ("aqua-ring-entry", "aqua-ring-walkway"): "Push three crates into the flooded corridor to float across",
    ("control-room", "aqua-ring-storage"): "Waterproof hatch; opens once the Aqua Ring is drained",
    ("room-003", "plant-42-room"): "Bookcase opens when the red books form the picture",
    ("gallery", "residence-medical-room"): "Keypad: lamp colours and pool-ball numbers from the Rec Room",
    ("kitchen", "elevator-corridor"): "Kitchen lift; the fuse is at the end of the flooded B1 passage",
    ("kitchen", "concrete-passage-2"): "Bolted; unlocked from the basement tunnel side (Muchitsujo's guide)",
    ("sliding-trap-room", "secret-passage"): "Hole behind the statue puzzle in the crushing-wall room",
    ("jessicas-tomb", "fountain"): "Lift up to the courtyard fountain after the fight with Lisa",
    ("laboratory-stairway", "visual-data-room"): "Electronic lock: JOHN / ADA / CELL at the lab computer",
    ("pass-code-corridor", "cell-entrance"): "Triple security door: an MO Disk read at each of the three terminals",
    ("cell-entrance", "cell"): "Opens with the self-destruct sequence (or the Master Key)",
    ("elevator-entry", "main-laboratory-entrance"): "Main elevator; powered from the Power Control Room",
    ("laboratory-entrance", "passage-to-heliport"): "Emergency exit; opens after the Tyrant",
    ("passage-to-heliport", "landing-point"): "Lift needs the Fuse Unit",
    ("mining-area", "boulder-passage-1"): "Turn the passage with the Hexagon Crank",
    ("straight-passage", "boulder-passage-2"): "Turn the passage with the Hexagon Crank (three times)",
    ("generator-room", "garbage-compactor-room"): "Mining lift; powered by the Cylinder Shaft",
    ("winding-underground-passage", "lisas-room"): "Hooks; weigh them down with the Broken Flamethrower",
    ("graveyard", "crypt"): "Grave opens with the Arrowhead",
}

G_KEYS, G_MAN, G_OUT, G_GH, G_LAB, G_EV, G_WPN = "keys", "mansion", "outside", "guardhouse", "lab", "events", "weapons"
TOKEN_GROUPS = [(G_KEYS, "Keys"), (G_MAN, "Mansion items"), (G_OUT, "Courtyard, caves and altar"), (G_GH, "Guardhouse"),
                (G_LAB, "Laboratory"), (G_WPN, "Weapons"), (G_EV, "Events and puzzles")]
B, J, C = ["jill", "chris"], ["jill"], ["chris"]
# id, name, room (None = combined anywhere), characters, requirement, group, kind, note
TOKENS = [
    ("lockpick", "Lock Pick", "main-hall", J, "", G_KEYS, "key", "Barry hands it over in the Main Hall"),
    ("old-key-storeroom", "Old Key (East Wing Storeroom)", "east-wing-storeroom", C, "", G_KEYS, "key", "Each Old Key opens one simple lock; this model lets any of them open any such door"),
    ("old-key-bathroom", "Old Key (Bathroom)", "bathroom", C, "", G_KEYS, "key", "In the bathtub once it is drained"),
    ("old-key-kitchen", "Old Key (Kitchen)", "kitchen", C, "", G_KEYS, "key", ""),
    ("old-key-researchers", "Old Key (Researcher's Bedroom)", "researchers-bedroom", C, "", G_KEYS, "key", "In the wardrobe"),
    ("old-key-bedroom", "Old Key (Bedroom)", "bedroom", C, "", G_KEYS, "key", ""),
    ("sword-key", "Sword Key", "crypt", B, "", G_KEYS, "key", "On the back of the Book of Curses"),
    ("armor-key", "Armor Key", "death-passage", B, "imitation-key", G_KEYS, "key", "Swap it for the Imitation of a key or the blade trap fires"),
    ("shield-key", "Shield Key", "dining-room", B, "gold-emblem", G_KEYS, "key", "Gold Emblem over the fireplace opens the clock; set it to six"),
    ("helmet-key", "Helmet Key", "plant-42-room", B, "plant42-dead", G_KEYS, "key", "In the fireplace once Plant 42 is dead"),
    ("emblem-key", "Emblem Key", "mirror-room", B, "red-gem", G_KEYS, "key", "Red Gemstone opens Jewelry Box 2; the Broach turns into the key"),
    ("key-001", "Key for Room 001", "room-002-bathroom", B, "", G_KEYS, "key", ""),
    ("key-003", "Key for Room 003", "gallery", B, "bees-smoked", G_KEYS, "key", "Under the hive; smoke the bees first"),
    ("control-key", "Control Room Key", "room-001-bathroom", B, "", G_KEYS, "key", "In the bathtub; drain it"),
    ("gallery-key", "Gallery Key", "aqua-ring-water-tank", B, "", G_KEYS, "key", "The shark knocks it into the water; electrify the pool"),
    ("power-key", "Key for the Power Area", "visual-data-room", B, "slide-filter", G_KEYS, "key", "Slide Filter in the projector shows the code 8462 for the hidden room"),
    ("closet-key", "Closet Key", None, B, "escape", G_KEYS, "key", "Reward for finishing the game; opens the costume closet"),
    ("lighter", "Lighter", "small-library", J, "", G_MAN, "item", "Chris starts with one"),
    ("arrowhead", "Golden Arrow / Arrowhead", "mirror-corridor", B, "", G_MAN, "item", "Examine the Golden Arrow to free the Arrowhead"),
    ("dog-whistle", "Dog Whistle", "small-library", B, "", G_MAN, "item", ""),
    ("imitation-key", "Imitation of a key", "outside-balcony", B, "dog-whistle", G_MAN, "item", "Blow the whistle, kill the two Cerberus; Collar > Coin > key"),
    ("herbicide", "Herbicide", "outside-boiler", B, "", G_MAN, "item", ""),
    ("mask-eyes", "Mask without eyes", "greenhouse", B, "herbicide", G_MAN, "item", "Herbicide in the pump, handle to red"),
    ("mask-mouth", "Mask without a mouth", "large-gallery", B, "", G_MAN, "item", "Painting puzzle"),
    ("mask-all", "Mask without eyes, nose, or mouth", "armor-room", B, "", G_MAN, "item", "Armour vents puzzle, then Jewelry Box 1"),
    ("mask-nose", "Mask without a nose", "attic", B, "", G_MAN, "item", "Yawn's first appearance"),
    ("serum", "Serum", "mansion-drug-room", B, "richard-found", G_MAN, "item", "Only on the shelf once Richard needs it"),
    ("music-mid", "Music, mid-pages", "small-dining-room", B, "lighter", G_MAN, "item", "Light the candle to see behind the cupboard"),
    ("missing-music", "Missing Music", "bar", B, "", G_MAN, "item", "Behind the bookshelf"),
    ("emblem", "Wooden Emblem", "dining-room", B, "", G_MAN, "item", "Above the fireplace"),
    ("gold-emblem", "Gold Emblem", "bar", B, "sonata & emblem", G_MAN, "item", "Swap in the Wooden Emblem or the wall closes"),
    ("wind-crest", "Wind Crest", "fish-tank-room", B, "", G_MAN, "item", "Bee specimen and lure puzzle"),
    ("broken-shotgun", "Broken Shotgun", "small-storeroom", B, "", G_MAN, "item", "Hang it on the hooks in place of the Shotgun"),
    ("stone-metal-1", "Stone & Metal Object", "crypt", B, "mask-eyes & mask-mouth & mask-nose & mask-all", G_MAN, "item", "Four death masks on the wall; the coffin falls"),
    ("red-gem", "Red Gemstone", "trophy-room", B, "", G_MAN, "item", "Lights off, dodge the eagle"),
    ("yellow-gem", "Yellow Gemstone", "trophy-room", B, "", G_MAN, "item", ""),
    ("metal-object", "Metal Object", "courtyard-study", B, "", G_MAN, "item", "Switch the lamp on first"),
    ("medal-eagle", "Medal of Eagle", "secret-passage", B, "", G_MAN, "item", "In Last Book Vol. 1"),
    ("medal-wolf", "Medal of Wolf", "library", B, "", G_MAN, "item", "In Last Book Vol. 2, after Yawn"),
    ("battery", "Battery", "materials-room", B, "", G_MAN, "item", ""),
    ("square-crank", "Square Crank", "cabin", B, "", G_OUT, "item", "Lisa Trevor's first appearance"),
    ("hex-crank", "Hexagon Crank", "enrico-room", B, "", G_OUT, "item", "On Enrico's body"),
    ("cylinder", "Cylinder", "underground-statue-room", B, "hex-crank", G_OUT, "item", "Statue puzzle"),
    ("broken-flamethrower", "Broken Flamethrower", "garbage-compactor-room", B, "crate-sent", G_OUT, "item", "Crush the crate"),
    ("stone-ring", "Stone Ring", "lisas-room", B, "", G_OUT, "item", "In Jewelry Box 3"),
    ("stone-metal-2", "Second Stone & Metal Object", None, B, "stone-ring & metal-object", G_OUT, "item", "Combine the Stone Ring and the Metal Object"),
    ("unprinted-book", "Unprinted Book", "rec-room", B, "", G_GH, "item", ""),
    ("insecticide", "Insecticide Spray", "gallery", B, "", G_GH, "item", ""),
    ("mo-tiger", "MO Disk (Tiger Statue)", "tiger-statue-room", B, "yellow-gem", G_LAB, "item", "Yellow Gemstone in the tiger's eye"),
    ("mo-stairway", "MO Disk (Lab Stairway)", "laboratory-stairway", B, "", G_LAB, "item", ""),
    ("mo-visual", "MO Disk (Visual Data Room)", "visual-data-room", B, "", G_LAB, "item", ""),
    ("slide-filter", "Slide Filter", "x-ray-room-b", B, "", G_LAB, "item", ""),
    ("capsule-empty", "Fuel Supply Capsule", "power-maze-a", B, "", G_LAB, "item", ""),
    ("capsule-full", "Fuel Supply Capsule (full)", "x-ray-room-b", B, "capsule-empty", G_LAB, "item", "Carry it back without taking a hit"),
    ("fuse-unit", "Fuse Unit", "passage-to-heliport", B, "", G_LAB, "item", ""),
    ("signal-rockets", "Signal Rockets", "landing-point", B, "", G_LAB, "item", ""),
    ("shotgun", "Shotgun", "living-room", B, "jill | broken-shotgun", G_WPN, "weapon", "Ceiling trap: Barry saves Jill; otherwise swap in the Broken Shotgun"),
    ("grenade-launcher", "Grenade Launcher", "outside-patio", J, "", G_WPN, "weapon", "Beside Forest's body"),
    ("magnum", "Magnum Revolver", "small-headstone-area", B, "wind-crest", G_WPN, "weapon", "Wind Crest gives the Sun, Moon and Star Crests; they open the left headstone"),
    ("assault-shotgun", "Assault Shotgun", "attic", J, "richard-saved", G_WPN, "weapon", "Richard drops it during the Yawn fight if you saved him"),
    ("assault-shotgun-c", "Assault Shotgun", "aqua-ring-water-tank", C, "richard-saved & aqua-drained", G_WPN, "weapon", "Richard's, after the sharks get him"),
    ("flamethrower", "Flamethrower", "boulder-passage-1", C, "", G_WPN, "weapon", ""),
    ("self-defense-gun", "Self Defense Gun", "room-001", B, "", G_WPN, "weapon", ""),
    ("richard-found", "Find Richard poisoned", "pillar-room", B, "", G_EV, "event", "Optional branch"),
    ("richard-saved", "Save Richard with the Serum", "pillar-room", B, "serum", G_EV, "event", "Optional; changes who helps with Yawn"),
    ("sonata", "Play the Moonlight Sonata", "bar", B, "music-mid & missing-music", G_EV, "event", "Chris has Rebecca play it, after she practises"),
    ("weathervanes", "Set the weathervanes", "muddy-path", B, "", G_EV, "event", "Red west, blue north"),
    ("pool-drained", "Drain the reservoir", "water-pool", B, "square-crank", G_EV, "event", ""),
    ("crate-bridge", "Crate bridge over the vine holes", "entry-corridor", B, "", G_EV, "event", ""),
    ("bookcases-002", "Move the bookcases in Room 002", "room-002", B, "", G_EV, "event", "Reveals the ladder to the Aqua Ring"),
    ("aqua-crates", "Float the crates across", "aqua-ring-entry", B, "", G_EV, "event", ""),
    ("aqua-drained", "Drain the Aqua Ring", "control-room", B, "", G_EV, "event", "Pressure shield puzzle, on a timer"),
    ("bees-smoked", "Smoke out the bees", "central-corridor", B, "insecticide", G_EV, "event", "Spray through the hole behind the Residence map"),
    ("medical-code", "Open the chemical room keypad", "gallery", B, "", G_EV, "event", "Optional: V-JOLT ingredients"),
    ("red-book-shelf", "Red book puzzle", "room-003", B, "unprinted-book", G_EV, "event", ""),
    ("plant42-dead", "Kill Plant 42", "plant-42-room", B, "", G_EV, "event", "Or V-JOLT the roots first"),
    ("crusher-statue", "Statue puzzle in the crushing room", "sliding-trap-room", B, "", G_EV, "event", ""),
    ("kitchen-fuse", "Fuse for the kitchen lift", "concrete-passage-2", B, "", G_EV, "event", ""),
    ("lift-powered", "Fit the Battery to the lift", "falls-area", B, "battery", G_EV, "event", ""),
    ("waterfall-stopped", "Refill the reservoir", "water-pool", B, "square-crank & lift-powered", G_EV, "event", "The waterfall stops and opens the way to the caves"),
    ("cave-elevator", "Power the mining lift", "generator-room", B, "cylinder", G_EV, "event", "Cylinder + Shaft, buttons IV II III I"),
    ("crate-sent", "Send the crate down", "underground-storage-room", B, "", G_EV, "event", ""),
    ("flamethrower-hooks", "Weigh down the hooks", "winding-underground-passage", B, "broken-flamethrower", G_EV, "event", ""),
    ("lisa-defeated", "Lisa Trevor at the altar", "jessicas-tomb", B, "", G_EV, "event", "Push the four stones"),
    ("cell-password", "Read the X-ray password", "x-ray-room-a", B, "", G_EV, "event", "CELL"),
    ("lab-computer", "Log in at the lab computer", "operating-room", B, "cell-password", G_EV, "event", "JOHN / ADA, then CELL"),
    ("mo-read-fuel", "MO Disk reader 1", "x-ray-room-b", B, "mo-tiger | mo-stairway | mo-visual", G_EV, "event", ""),
    ("mo-read-storage", "MO Disk reader 2", "morgue", B, "mo-tiger | mo-stairway | mo-visual", G_EV, "event", "Through the air ducts"),
    ("mo-read-power", "MO Disk reader 3", "power-maze-b", B, "mo-tiger | mo-stairway | mo-visual", G_EV, "event", ""),
    ("prison-door", "Open the prison door", "pass-code-corridor", B, "mo-read-fuel & mo-read-storage & mo-read-power & mo-tiger & mo-stairway & mo-visual", G_EV, "event", "All three disks read"),
    ("lab-elevator", "Power the main elevator", "power-control-room", B, "capsule-full", G_EV, "event", ""),
    ("tyrant-defeated", "Tyrant in the Main Laboratory", "main-laboratory", B, "", G_EV, "event", ""),
    ("partner-rescued", "Free your partner", "cell", B, "", G_EV, "event", "Best ending"),
    ("escape", "Signal Brad and escape", "landing-point", B, "signal-rockets & tyrant-defeated", G_EV, "event", "End of the game"),
]
COMMON_TAIL = ["weathervanes", "magnum", "square-crank", "pool-drained", "crate-bridge", "unprinted-book", "key-001",
               "control-key", "bookcases-002", "aqua-crates", "aqua-drained", "gallery-key", "insecticide", "bees-smoked",
               "key-003", "red-book-shelf", "plant42-dead", "helmet-key", "red-gem", "yellow-gem", "mo-tiger", "emblem-key",
               "metal-object", "crusher-statue", "medal-eagle", "kitchen-fuse", "battery", "medal-wolf", "lift-powered",
               "waterfall-stopped", "hex-crank", "flamethrower", "cylinder", "cave-elevator", "crate-sent", "broken-flamethrower",
               "flamethrower-hooks", "stone-ring", "stone-metal-2", "lisa-defeated", "mo-stairway", "cell-password",
               "lab-computer", "slide-filter", "mo-read-fuel", "mo-visual", "power-key", "mo-read-storage", "capsule-empty",
               "capsule-full", "mo-read-power", "lab-elevator", "prison-door", "tyrant-defeated", "partner-rescued",
               "fuse-unit", "signal-rockets", "escape"]
OBJECTIVES = {
    "jill": ["lockpick", "arrowhead", "grenade-launcher", "sword-key", "herbicide", "lighter", "dog-whistle", "imitation-key",
             "armor-key", "mask-eyes", "mask-mouth", "mask-all", "richard-found", "serum", "richard-saved", "music-mid",
             "emblem", "missing-music", "sonata", "gold-emblem", "shield-key", "mask-nose", "assault-shotgun", "wind-crest",
             "broken-shotgun", "shotgun", "stone-metal-1"] + COMMON_TAIL,
    "chris": ["arrowhead", "sword-key", "old-key-storeroom", "old-key-bathroom", "herbicide", "old-key-kitchen", "dog-whistle",
              "imitation-key", "armor-key", "mask-eyes", "mask-mouth", "mask-all", "old-key-researchers", "old-key-bedroom",
              "wind-crest", "richard-found", "serum", "richard-saved", "music-mid", "emblem", "missing-music", "sonata",
              "gold-emblem", "shield-key", "mask-nose", "broken-shotgun", "shotgun", "stone-metal-1"]
             + COMMON_TAIL[:12] + ["assault-shotgun-c"] + COMMON_TAIL[12:],
}
MODES = ["jill-ve", "chris-ve", "jill-easy", "chris-easy", "jill-normal", "chris-normal", "jill-hard", "chris-hard"]


def req(expr):
    if expr is None:
        return None
    alts = [a.strip() for a in expr.split("|")] if expr.strip() else [""]
    return [[t.strip() for t in a.split("&") if t.strip()] for a in alts]


def main():
    o = json.load(open(ROOT / "outlines.json"))
    raw = json.load(open(ROOT / "rooms_raw.json"))
    floors = {f["floor_id"]: f for f in o["floors"]}
    area_of = {fl: a[0] for a in AREAS for fl in a[3]}
    slug = lambda i: i.split("/")[1]

    rooms = {}
    for ol in o["outlines"]:
        s = slug(ol["id"])
        r = rooms.setdefault(s, {"id": s, "name": ol["name"], "area": area_of[ol["floor"]], "outlines": [], "pages": []})
        P = pts(ol["poly"])
        xs, ys = [p[0] for p in P], [p[1] for p in P]
        lp = label_point(ol["poly"])
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        fs = max(2.2, min(7.0, w * 0.92 / (len(ol["name"]) * 0.5), h * 0.42))
        r["outlines"].append({"floor": ol["floor"], "poly": ol["poly"], "lp": list(lp), "fs": round(fs, 2), "a": poly_area(ol["poly"])})
        r["pages"].append(ol["id"])
    for r in rooms.values():  # biggest piece first: it is the room's home floor
        r["outlines"].sort(key=lambda x: -x["a"])
        r["floor"] = r["outlines"][0]["floor"]

    # contents: merge the identical pages of multi-floor rooms
    for r in rooms.values():
        page = raw[r["pages"][0]]
        r["contents"] = [{"t": c["title"], "k": c["kind"], "d": c["desc"], "s": c["slug"], "c": item_cat(c["kind"], c["slug"]),
                          "m": sum(1 << MODES.index(m) for m in c["modes"] if m in MODES)} for c in page["contents"]]
        r["save"] = any(c["t"] == "Typewriter" for c in r["contents"])
        r["box"] = any(c["t"] == "Item Box" for c in r["contents"])

    # directed links from the pages, then the hand gates
    directed = {}
    for r in rooms.values():
        for pid in r["pages"]:
            for l in raw[pid]["links"]:
                b = slug(l["to"])
                if b == r["id"]:
                    continue
                if l["note"] not in NOTE_REQ:
                    raise SystemExit(f"unknown note {l['note']!r}")
                directed[(r["id"], b)] = NOTE_REQ[l["note"]]
    # Evil Resource notes a key on the side you first meet the door; the lock holds from both sides.
    for (a, b), v in list(directed.items()):
        if v and "@other" not in v and directed.get((b, a)) == "" and (b, a) not in GATES:
            directed[(b, a)] = v
    for k, v in GATES.items():
        assert k[0] in rooms and k[1] in rooms, k
        directed[k] = v
    pairs = sorted({tuple(sorted(k)) for k in directed})
    doors, oneway = [], []
    for a, b in pairs:
        ab, ba = directed.get((a, b), "MISSING"), directed.get((b, a), "MISSING")
        if ab == "MISSING" or ba == "MISSING":
            oneway.append((a, b, ab, ba))
        A, Bm = rooms[a], rooms[b]
        best = None
        for oa in A["outlines"]:
            for ob in Bm["outlines"]:
                if oa["floor"] == ob["floor"]:
                    p, shared = door_point(oa["poly"], ob["poly"])
                    cand = (shared, oa["floor"], p)
                    if best is None or (shared and not best[0]):
                        best = cand
        note = GATE_NOTES.get((a, b)) or GATE_NOTES.get((b, a)) or ""
        d = {"a": a, "b": b, "ab": req(None if ab == "MISSING" else ab), "ba": req(None if ba == "MISSING" else ba), "note": note}
        if best:
            d.update(fa=best[1], fb=best[1], pa=list(best[2]), pb=list(best[2]), wall=bool(best[0]))
        else:  # stairs, ladders, lifts: a tag in each room
            d.update(fa=A["floor"], fb=Bm["floor"], pa=None, pb=None)
        doors.append(d)
    sym = json.load(open(ROOT / "symbols.json"))
    place_doors(doors, rooms, sym)
    # tags for stairs, ladders and lifts that have no mark: on the room's stair hatching, else under its name
    count = {}
    for d in doors:
        for side, fk, pk, tk in ((d["a"], "fa", "pa", "ta"), (d["b"], "fb", "pb", "tb")):
            if d["fa"] == d["fb"] or d.get(tk):
                continue
            r = rooms[side]
            ol = next(x for x in r["outlines"] if x["floor"] == d[fk])
            free = [h for h in sym_hatch(sym, d[fk]) if inside(h, pts(ol["poly"])) and h not in count.get(("h", side), [])]
            if free and d[pk] is None:
                h = min(free, key=lambda q: (q[0] - ol["lp"][0]) ** 2 + (q[1] - ol["lp"][1]) ** 2)
                count.setdefault(("h", side), []).append(h)
                d[pk] = [round(h[0], 1), round(h[1], 1)]
                d[tk] = d[pk]
                continue
            if d[pk] is None:
                k = count.get((side, d[fk]), 0)
                count[(side, d[fk])] = k + 1
                d[pk] = [round(ol["lp"][0], 1), round(ol["lp"][1] + ol["fs"] * 0.9 + 4 + 8.5 * k, 1)]
            d[tk] = d[pk]
    # stairs inside one room that spans two floors (Main Hall, the stairways, the library): a link on each floor's piece
    for r in rooms.values():
        spot = {}
        for ol in r["outlines"] if len(r["outlines"]) > 1 else []:
            free = [h for h in sym_hatch(sym, ol["floor"]) if inside(h, pts(ol["poly"])) and h not in count.get(("h", r["id"]), [])]
            if free:
                h = min(free, key=lambda q: (q[0] - ol["lp"][0]) ** 2 + (q[1] - ol["lp"][1]) ** 2)
                count.setdefault(("h", r["id"]), []).append(h)
                spot[ol["floor"]] = [round(h[0], 1), round(h[1], 1)]
            else:
                k = count.get((r["id"], ol["floor"]), 0)
                count[(r["id"], ol["floor"])] = k + 1
                spot[ol["floor"]] = [round(ol["lp"][0], 1), round(ol["lp"][1] + ol["fs"] * 0.9 + 4 + 8.5 * k, 1)]
        r["stairs"] = [{"f": a, "p": spot[a], "to": b} for a in spot for b in spot if a != b]
    # floor badges (the page's stair links) kept off room names and off each other, inside their room
    names = {}
    for r in rooms.values():
        for ol in r["outlines"]:
            lw = len(r["name"]) * ol["fs"] * 0.56
            names.setdefault(ol["floor"], []).append((ol["lp"][0] - lw / 2, ol["lp"][1] - ol["fs"] * 0.75, ol["lp"][0] + lw / 2, ol["lp"][1] + ol["fs"] * 0.45))
    taken = {}
    def settle(room, f, to, p):
        poly = pts(next(x for x in rooms[room]["outlines"] if x["floor"] == f)["poly"])
        text = SHORT[to] if area_of[f] == area_of[to] else floors[to]["label"]
        w = 11.6 + (len(text) + 2) * 2.95  # same box as linkBox() in the page
        hit = lambda b: any(o[0] < b[2] and b[0] < o[2] and o[1] < b[3] and b[1] < o[3] for o in names[f] + taken.get(f, []))
        for dx, dy in ((0, 0), (0, 9), (0, -9), (0, 18), (0, -18), (w * 0.6, 0), (-w * 0.6, 0), (0, 27), (0, -27)):
            q = [round(p[0] + dx, 1), round(p[1] + dy, 1)]
            if inside(q, poly) and not hit((q[0] - w / 2 - 1, q[1] - 5, q[0] + w / 2 + 1, q[1] + 5)):
                break
        else:
            q = p
        taken.setdefault(f, []).append((q[0] - w / 2, q[1] - 4, q[0] + w / 2, q[1] + 4))
        return q
    for d in doors:
        if d["fa"] != d["fb"]:
            d["ta"], d["tb"] = settle(d["a"], d["fa"], d["fb"], d["ta"]), settle(d["b"], d["fb"], d["fa"], d["tb"])
    for r in rooms.values():
        for st in r["stairs"]:
            st["p"] = settle(r["id"], st["f"], st["to"], st["p"])
        for st in r["stairs"]:
            st["tp"] = next(x["p"] for x in r["stairs"] if x["f"] == st["to"])
    used = {(b["f"], tuple(b["r"])) for d in doors for b in d["bars"]}
    sealed = {fid: [m["rect"] for m in v["doors"] if (fid, tuple(m["rect"])) not in used] for fid, v in sym.items()}

    toks = []
    for tid, name, room, chars, rq, group, kind, note in TOKENS:
        assert room is None or room in rooms, (tid, room)
        toks.append({"id": tid, "name": name, "room": room, "chars": chars, "req": req(rq), "group": group, "kind": kind, "note": note,
                     "img": item_slug(name, room, kind, rooms)})
    ids = {t["id"] for t in toks} | {"jill", "chris", "@other"}
    for t in toks:
        for cl in t["req"]:
            for x in cl:
                assert x in ids, (t["id"], x)
    for d in doors:
        for r_ in (d["ab"], d["ba"]):
            for cl in r_ or []:
                for x in cl:
                    assert x in ids, (d["a"], d["b"], x)
    for ch, ob in OBJECTIVES.items():
        for x in ob:
            assert x in ids, (ch, x)

    # atlas offsets
    x = 0
    for col in ATLAS_COLS:
        y, wmax = 0, 0
        for fid in col:
            f = floors[fid]
            f["ax"], f["ay"] = x, y
            y += f["h"] + 46
            wmax = max(wmax, f["w"])
        x += wmax + 70
    fl_out = [{"id": fid, "label": f["label"], "short": SHORT[fid], "w": f["w"], "h": f["h"], "ax": f["ax"], "ay": f["ay"],
               "area": area_of[fid], "lvl": LEVEL[fid], "stripes": sym[fid]["stripes"], "raised": sym[fid]["raised"], "icons": sym[fid]["icons"],
               "sealed": sealed[fid]} for fid, f in floors.items()]

    data = {
        "built": datetime.date.today().isoformat(),
        "areas": [{"id": a, "label": l, "color": c} for a, l, c, _ in AREAS],
        "areaOrder": [{"label": l, "floors": f} for l, f in NAV],
        "floors": fl_out,
        "rooms": [{k: r[k] for k in ("id", "name", "area", "floor", "outlines", "contents", "save", "box", "stairs")} for r in rooms.values()],
        "doors": doors,
        "tokens": toks,
        "tokenGroups": [{"id": g, "label": l} for g, l in TOKEN_GROUPS],
        "start": START, "startHave": START_HAVE, "goal": {"jill": "escape", "chris": "escape"},
        "objectives": OBJECTIVES,
        "media": None,
        "public": PUBLIC,
    }
    media_file = next((p for p in (ROOT / "media", OUT_HTML.parent / "media", ROOT.parent / "media") if (p / "media.json").exists()), None)
    media = json.load(open(media_file / "media.json")) if media_file else None
    data["plan"] = media_plan(media)
    if not PUBLIC:
        data["media"] = media
    else:  # Evil Resource's wording stays out: the asset pack carries it
        for r in data["rooms"]:
            for c in r["contents"]:
                c.pop("d", None)
    for r in data["rooms"]:
        for ol in r["outlines"]:
            ol.pop("a")
    OUT_JSON.write_text(json.dumps(data, separators=(",", ":")))
    tpl = (ROOT / "app_template.html").read_text()
    page = tpl.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    if PUBLIC:  # a standalone page (the private copy is published as an artifact, which adds its own document skeleton)
        page = ('<!doctype html>\n<html lang="en" data-skin="remake"><head><meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                + page.replace("</style>", "[hidden] { display: none !important; }\n</style>\n</head><body>", 1)
                + "\n</body></html>\n")
    OUT_HTML.write_text(page)
    write_csvs(OUT_JSON.parent, data, rooms)
    print(f"{len(rooms)} rooms, {len(doors)} doors, {len(toks)} tokens; html {OUT_HTML.stat().st_size // 1024} KB")
    for a, b, ab, ba in oneway:
        print("one-way:", a, "->", b, ab, "|", b, "->", a, ba)


HEALTH = {"green-herb", "red-herb", "blue-herb", "mixed-herbs-gg", "mixed-herbs-gb", "first-aid-spray", "first-aid-box"}
AMMO = {"handgun-magazine", "shotgun-shells", "magnum-rounds", "grenade-shells", "acid-shells", "incendiary-shells"}
DEFENSE = {"dagger", "flash-grenade", "battery-pack", "self-defense-gun", "fuel-canteen", "kerosene"}
SAVE = {"ink-ribbon", "typewriter", "item-box"}


# The game's own inventory icon for each item (REmake HD itemicon.arc, "iNNNs"), matched by eye against Evil
# Resource's renders: a PS3 import uses these instead of the renders. Items not listed fall back to a drawn glyph.
ITEM_ICON = {
    "survival-knife": 1, "handgun": 3, "self-defense-gun": 4, "shotgun": 6, "grenade-launcher": 7, "rocket-launcher": 10,
    "magnum-revolver": 11, "flamethrower": 12, "assault-shotgun": 13, "barrys-44-magnum": 15, "grenade-shells": 16,
    "handgun-magazine": 17, "shotgun-shells": 18, "acid-shells": 19, "incendiary-shells": 20, "golden-arrow": 21,
    "book-of-curses-item": 22, "coin": 23, "collar": 24, "magnum-rounds": 25, "broach": 26, "fuel-canteen": 27,
    "arrowhead": 28, "imitation-of-a-key": 29, "gallery-key": 30, "fuel-supply-capsule": 31, "first-aid-spray": 33,
    "green-herb": 34, "red-herb": 35, "blue-herb": 36, "mixed-herbs-gg": 37, "mixed-herbs-gb": 41, "lock-pick": 43,
    "old-key": 44, "sword-key": 45, "armor-key": 46, "shield-key": 47, "helmet-key": 48, "key-for-room-001": 49,
    "key-for-room-003": 50, "medal-of-eagle": 51, "medal-of-wolf": 52, "stone-and-metal-object": 53,
    "key-for-the-power-area": 54, "master-key": 55, "star-crest": 56, "wind-crest": 57, "sun-crest": 58, "moon-crest": 59,
    "hexagon-crank": 60, "square-crank": 61, "emblem-key": 63, "stone-ring": 64, "metal-object": 65, "battery": 67,
    "ink-ribbon": 68, "emblem": 69, "gold-emblem": 70, "red-gemstone": 72, "blue-gemstone": 73, "yellow-gemstone": 74,
    "broken-shotgun": 75, "herbicide": 76, "lighter": 77, "serum": 78, "radio": 79, "empty-bottle": 80, "water": 81,
    "umb-no3": 82, "yellow-6": 84, "unprinted-book": 90, "last-book-vol-1": 91, "last-book-vol-2": 92, "mo-disk": 93,
    "dog-whistle": 96, "fuse-unit": 97, "fuel-supply-capsule-empty": 98, "jewelry-box-3": 99, "insecticide-spray": 100,
    "first-aid-box": 101, "jewelry-box-2": 102, "jewelry-box-1": 103, "kerosene": 106, "broken-flamethrower": 107,
    "wooden-mount": 108, "slide-filter": 109, "control-room-key": 110, "dagger": 112, "flash-grenade": 113,
    "bee-specimen": 115, "lure-without-a-hook": 116, "fishhook": 117, "x-ray-of-clark": 119, "x-ray-of-gail": 120,
    "battery-pack": 121, "shaft": 122, "cylinder": 123, "mask-without-eyes-nose-or-mouth": 125, "mask-without-a-nose": 126,
    "mask-without-eyes": 127, "mask-without-a-mouth": 128, "music-mid-pages": 129,
}


def media_plan(media):
    """What an import rebuilds from the player's own discs, without any pictures: the PS3 cameras of each room
    (code_camera, in order), the RE1 frames of each group, and the inventory icon of each item."""
    if not media:
        return None
    return {"remake": {k: v["labels"] for k, v in media["remake"].items() if v.get("src") == "ps3"},
            "re1": {k: {"labels": v["labels"], "parts": v["parts"]} for k, v in media["re1"].items()},
            "re1_only": media["re1_only"], "icons": ITEM_ICON}


def item_cat(kind, slug):
    """Map icon category of a room content entry (the border colour on the map)."""
    if kind == "enemies":
        return "enemy"
    if kind == "characters":
        return "person"
    if slug in SAVE:
        return "save"
    if slug in DEFENSE:
        return "defense"
    if kind == "weaponry":
        return "ammo" if slug in AMMO else "weapon"
    if kind == "items":
        if slug in HEALTH:
            return "health"
        return "key" if slug.endswith("-key") or slug.startswith("key-for") or slug in ("lock-pick", "imitation-of-a-key") else "quest"
    return "file"  # files, maps, the radio, the pass code terminal


def item_slug(name, room, kind, rooms):
    """Evil Resource picture for a key item: the content entry in its room whose title matches the name."""
    if kind == "event" or not room:
        return None
    n = name.lower().split(" (")[0].split(" / ")[0]
    for c in rooms[room]["contents"]:
        if c["k"] in ("items", "weaponry") and c["s"]:
            tl = c["t"].lower()
            if n in tl or tl in n or c["s"].replace("-", " ") in n:
                return c["s"]
    return None


def sym_hatch(sym, fid, gap=2):
    """Stair hatch regions on a floor: stripes merged when they lie within `gap` px; returns region centres."""
    st = sym[fid]["stripes"]
    parent = list(range(len(st)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, a in enumerate(st):
        for j in range(i):
            b = st[j]
            if a[0] - gap <= b[2] and b[0] - gap <= a[2] and a[1] - gap <= b[3] and b[1] - gap <= a[3]:
                parent[root(i)] = root(j)
    groups = {}
    for i, s in enumerate(st):
        groups.setdefault(root(i), []).append(s)
    out = []
    for g in groups.values():
        if len(g) < 3:
            continue
        x0, y0 = min(s[0] for s in g), min(s[1] for s in g)
        x1, y1 = max(s[2] for s in g), max(s[3] for s in g)
        out.append(((x0 + x1) / 2, (y0 + y1) / 2))
    return out


def place_doors(doors, rooms, sym):
    """Put each door on the door mark of the in-game map (Evil Resource's floor images) where one exists."""
    marks = [{"f": fid, "r": m["rect"], "h": m["horiz"], "s": m["rooms"], "used": False}
             for fid, v in sym.items() for m in v["doors"]]
    ctr = lambda m: [m["r"][0] + m["r"][2] / 2, m["r"][1] + m["r"][3] / 2]
    floors_of = lambda s: {o["floor"] for o in rooms[s]["outlines"]}
    for d in doors:
        d["bars"], d["ta"], d["tb"] = [], None, None
        same = [m for m in marks if not m["used"] and set(m["s"]) == {d["a"], d["b"]}]
        for m in same:
            m["used"] = True
            d["bars"].append({"f": m["f"], "r": m["r"]})
        if same:
            p = ctr(same[0])
            d.update(fa=same[0]["f"], fb=same[0]["f"], pa=p, pb=p, kind="door")

    def cands(s, other):
        return [m for m in marks if not m["used"] and s in m["s"] and (None in m["s"] or m["s"][0] == m["s"][1])
                and m["f"] not in floors_of(other)]
    # a door between rooms that share a wall on one floor stays on that wall: the one-sided marks below are for stairs
    todo = [d for d in doors if not d["bars"] and not d.get("wall")]
    for d in doors:
        if not d["bars"] and d.get("wall"):
            d["kind"] = "opening"
        d.pop("wall", None)
    todo.sort(key=lambda d: (not (cands(d["a"], d["b"]) and cands(d["b"], d["a"])), len(cands(d["a"], d["b"])) + len(cands(d["b"], d["a"]))))
    for d in todo:
        ca, cb = cands(d["a"], d["b"]), cands(d["b"], d["a"])
        pa = pb = None
        if ca and cb:
            pa, pb = min(((x, y) for x in ca for y in cb), key=lambda q: (q[0]["h"] != q[1]["h"], q[0]["s"][0] != q[0]["s"][1]))
        elif ca or cb:
            c = ca or cb
            pick = min(c, key=lambda m: m["s"][0] != m["s"][1])
            if ca:
                pa = pick
            else:
                pb = pick
        for m, fk, pk in ((pa, "fa", "pa"), (pb, "fb", "pb")):
            if m:
                m["used"] = True
                d["bars"].append({"f": m["f"], "r": m["r"]})
                d[fk], d[pk] = m["f"], ctr(m)
        # the other side of a one-sided mark: if both rooms share that floor keep the wall point, else a tag later
        if (pa and not pb) and d["fb"] != d["fa"]:
            d["pb"] = None
        if (pb and not pa) and d["fa"] != d["fb"]:
            d["pa"] = None
        if d["bars"]:
            d["kind"] = "door"
        else:
            d["kind"] = "opening" if d["fa"] == d["fb"] else "link"
        if d["fa"] != d["fb"]:  # floor tags sit just inside the room from the door mark
            for m, s, fk, tk in ((pa, d["a"], "fa", "ta"), (pb, d["b"], "fb", "tb")):
                if m:
                    ol = next(x for x in rooms[s]["outlines"] if x["floor"] == d[fk])
                    c = ctr(m)
                    if m["h"]:
                        c[1] += 8 if ol["lp"][1] > c[1] else -8
                    else:
                        c[0] += 14 if ol["lp"][0] > c[0] else -14
                    d[tk] = [round(c[0], 1), round(c[1], 1)]


def write_csvs(folder, data, rooms):
    """Plain tables of the same data, for reading without the page."""
    import csv
    fl = {f["id"]: f["label"] for f in data["floors"]}
    rt = lambda r: "" if r is None else " | ".join(" & ".join(cl) for cl in r)
    deg = {}
    for d in data["doors"]:
        deg[d["a"]] = deg.get(d["a"], 0) + 1
        deg[d["b"]] = deg.get(d["b"], 0) + 1
    with open(folder / "rooms.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "area", "floors", "doors", "save_room", "item_box"])
        for r in data["rooms"]:
            w.writerow([r["id"], r["name"], r["area"], " + ".join(fl[o["floor"]] for o in r["outlines"]), deg.get(r["id"], 0),
                        "yes" if r["save"] else "", "yes" if r["box"] else ""])
    with open(folder / "doors.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["room_a", "room_b", "a_to_b_needs", "b_to_a_needs", "floor_a", "floor_b", "source", "note"])
        for d in data["doors"]:
            src = "guide gate" if (d["a"], d["b"]) in GATES or (d["b"], d["a"]) in GATES else "evil resource"
            w.writerow([d["a"], d["b"], rt(d["ab"]) if d["ab"] is not None else "(no way through)",
                        rt(d["ba"]) if d["ba"] is not None else "(no way through)", fl[d["fa"]], fl[d["fb"]], src, d["note"]])
    with open(folder / "items.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "kind", "group", "room", "characters", "needs", "note"])
        for t in data["tokens"]:
            w.writerow([t["id"], t["name"], t["kind"], t["group"], t["room"] or "(combine)", "+".join(t["chars"]), rt(t["req"]), t["note"]])


if __name__ == "__main__":
    main()
