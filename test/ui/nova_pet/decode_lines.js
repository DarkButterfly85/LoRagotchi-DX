// Test helper. Not firmware. usage: node decode_lines.js <file with the dashboard PET block>
// Reads the radio's lines on stdin. For each pet line prints {"applied":bool,"seq":n,"fb":"hex of 1024 bytes"}.
const fs = require("fs");
const vm = require("vm");
const src = fs.readFileSync(process.argv[2], "utf8");
const ctx = vm.createContext({ atob: (s) => Buffer.from(s, "base64").toString("binary"), Uint8Array });
vm.runInContext(src + "\nthis.PET = PET;", ctx);
const PET = ctx.PET;
const lines = fs.readFileSync(0, "utf8").split("\n");
for (const line of lines) {
  if (!line) continue;
  let o; try { o = JSON.parse(line); } catch (e) { console.log(JSON.stringify({ applied: false, parse: false })); continue; }
  const ok = PET.apply(o.pet);
  console.log(JSON.stringify({ applied: !!ok, seq: PET.seq, fb: Buffer.from(PET.fb).toString("hex") }));
}
