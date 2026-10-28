// Node check of the page's importers on real files: node tools/test_import.js PAGE.html RE1.bin PS3.pkg OUTDIR
// Writes raw RGB dumps next to Python's decodes so tools can compare them.
const fs = require("fs");
const html = fs.readFileSync(process.argv[2], "utf8");
const code = html.slice(html.indexOf("/* ---------- importers ---------- */"), html.indexOf("/* ---------- end importers ---------- */"));
const fileReader = path => { const fd = fs.openSync(path, "r"), size = fs.fstatSync(fd).size;
  return {size, read: async (o, n) => { n = Math.max(0, Math.min(n, size - o)); const b = Buffer.alloc(n); fs.readSync(fd, b, 0, n, o); return new Uint8Array(b.buffer, b.byteOffset, n); }}; };
const out = process.argv[5];
const run = new Function("fileReader", "out", "fs", code + `
return (async () => {
  let t = Date.now();
  const re1 = fileReader(${JSON.stringify(process.argv[3])});
  const disc = await openDisc(re1.read, re1.size);
  const bss = disc.files.filter(f => /ROOM\\w+\\.BSS$/i.test(f.path));
  console.log("RE1:", disc.files.length, "files,", bss.length, "BSS, e.g.", bss[0].path, "list ms", Date.now() - t);
  t = Date.now(); let frames = 0;
  for (const f of bss.slice(0, 3)) { const d = await disc.readFile(f.lba, f.size);
    for (let k = 0; k * 32768 < d.length; k++) { const blk = d.subarray(k * 32768, (k + 1) * 32768); if (!MDEC.isFrame(blk)) continue;
      const px = MDEC.frame(blk); frames++; const name = f.path.split("/").pop().replace(/\\.BSS$/i, "") + "_" + k;
      const rgb = Buffer.alloc(320 * 240 * 3); for (let i = 0; i < 320 * 240; i++) { rgb[3 * i] = px[4 * i]; rgb[3 * i + 1] = px[4 * i + 1]; rgb[3 * i + 2] = px[4 * i + 2]; }
      fs.writeFileSync(out + "/" + name + ".rgb", rgb); } }
  console.log("RE1 frames decoded:", frames, "ms", Date.now() - t);
  t = Date.now();
  const pkgf = fileReader(${JSON.stringify(process.argv[4])});
  const pkg = await openPkg(pkgf.read);
  console.log("PKG entries:", pkg.entries.length, "ms", Date.now() - t);
  for (const want of ["arc/scr/st01/r106/r10600.arc", "arc/scr/st04/r40d/r40d08.arc"]) {
    t = Date.now(); const e = pkg.entries.find(x => x.name.endsWith(want));
    const bg = await arcBackground(pkg.reader(e), e.size);
    const rgb = Buffer.alloc(bg.w * bg.h * 3); for (let i = 0; i < bg.w * bg.h; i++) { rgb[3 * i] = bg.px[4 * i]; rgb[3 * i + 1] = bg.px[4 * i + 1]; rgb[3 * i + 2] = bg.px[4 * i + 2]; }
    fs.writeFileSync(out + "/" + want.split("/").pop() + ".rgb", rgb); console.log("bg", want, bg.w + "x" + bg.h, "arc MB", (e.size / 1e6).toFixed(1), "ms", Date.now() - t);
  }
  const ie = pkg.entries.find(x => x.name.endsWith("e_rom/subscr/itemicon.arc")); const view = arcView(pkg.reader(ie), ie.size);
  const list = await arcList(view); const icon = list.find(x => x.name.endsWith("i034s_ID")); const ic = decodeBC(await arcRead(view, icon));
  fs.writeFileSync(out + "/i034s.rgba", Buffer.from(ic.px.buffer)); console.log("icon", icon.name, ic.w + "x" + ic.h, list.length, "entries");
})();`);
run(fileReader, out, fs).catch(e => { console.error("FAIL", e); process.exit(1); });
