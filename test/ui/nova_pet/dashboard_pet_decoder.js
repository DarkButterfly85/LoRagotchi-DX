/* Test fixture. Not firmware.
 * The pet-picture decoder of the Nova dashboard, copied unchanged from the LODESTAR ORION overlay
 * dashboard (DrToxic/lodestar-orion-overlay @ ab2b93d, dashboard/index.html, between the PET-BEGIN
 * and PET-END markers). LODESTAR ORION / NOVA: Aries Thorne, Todd Steinhauer, FEAR REACTIVE, used with
 * the authors' permission (see docs/CREDITS.md). check_nova_pet_frame.py runs it with node.
 * To test against a newer dashboard instead, set NOVA_DASHBOARD_HTML to its index.html: the test then
 * cuts the block between the same markers out of that file.
 */
/*PET-BEGIN*/
const PET = {
  ask: false, probe: 0, seen: 0, seq: -1, fb: new Uint8Array(1024), meta: null, last: 0, grid: false, lastSeq: 0,
  decode(b64) {                       // base64 -> run-length bytes -> 1024 delta bytes
    const bin = atob(b64), out = new Uint8Array(1024); let o = 0;
    for (let i = 0; i < bin.length && o < 1024;) {
      const c = bin.charCodeAt(i++);
      if (c) out[o++] = c; else { const run = bin.charCodeAt(i++) | 0; o += run; }
    }
    return out;
  },
  // returns true when a picture was updated
  apply(p) {
    if (!p || typeof p.d !== "string") return false;
    if (p.k) {
      this.fb = this.decode(p.d); this.seq = p.s;
      if (p.n) this.meta = { n: p.n, u: p.u || "", x: p.x, m: p.m, c: p.c, i: p.i };
    } else {
      if (this.seq < 0 || p.s !== this.seq + 1) { this.seq = -1; return false; }    // missed one: wait for the next key frame
      const d = this.decode(p.d); for (let i = 0; i < 1024; i++) this.fb[i] ^= d[i];
      this.seq = p.s;
    }
    return true;
  },
  reset() { this.seq = -1; this.seen = 0; this.meta = null; this.fb = new Uint8Array(1024); this.asks = 0; this.nosupport = false; },
};
/*PET-END*/
