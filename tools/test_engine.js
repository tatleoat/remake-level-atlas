// Load the page's logic (everything before the colour section) and check progression for both characters.
const fs = require("fs");
const html = fs.readFileSync(process.argv[2], "utf8");
const s = html.slice(html.indexOf("<script>") + 8);
const logic = s.slice(0, s.indexOf("/* ---------- colour ---------- */"));
const run = new Function(logic + `
for (const c of ["jill", "chris"]) {
  const sp = spheres(c);
  const never = D.rooms.filter(r => !sp.roomS.has(r.id)).map(r => r.id);
  console.log(c, "layers", sp.layers.length, "escape@", sp.tokS.get("escape"), "unreached rooms", never.join(",") || "none");
  const missTok = D.tokens.filter(t => t.chars.includes(c) && !sp.tokS.has(t.id)).map(t => t.id);
  console.log("  tokens never obtainable:", missTok.join(",") || "none");
  const r = planRoute(c, D.objectives[c]);
  const bl = r.legs.filter(l => l.blocked);
  console.log("  guide route: legs", r.legs.length, "doors", r.legs.reduce((a, l) => a + l.path.length, 0), "blocked", bl.map(l => l.tok + " (" + l.missing + ")").join("; ") || "none");
  const g = greedyOrder(c); const rg = planRoute(c, g);
  console.log("  greedy: objectives", g.length, "doors", rg.legs.reduce((a, l) => a + l.path.length, 0), "blocked", rg.legs.filter(l => l.blocked).length, "ends with", g.slice(-3).join(","));
  console.log("  needs(escape):", (needs("escape", c) || []).length, "tokens");
}
console.log("chokepoints", METRIC.art.size, "top hubs", [...METRIC.bc.entries()].sort((a,b)=>b[1]-a[1]).slice(0,6).map(([k,v])=>k+" "+(v*100).toFixed(1)).join(", "));
console.log("save rooms", [...SAVE].join(","));
const unreachSave = D.rooms.filter(r => !METRIC.save.has(r.id)).map(r=>r.id); console.log("no path to save:", unreachSave.join(",")||"none");
`);
run();
