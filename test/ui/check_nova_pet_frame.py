#!/usr/bin/env python3
"""Nova pet picture: the radio's encoder against the Nova dashboard's own decoder.

python3 test/ui/check_nova_pet_frame.py     (Python 3, g++ and node; no firmware build, no hardware)

What it does
  1. Compiles test/ui/nova_pet/harness.cpp with g++. The harness runs the real NovaPetLink.h (encoder,
     drawing canvas, stream rules) and NovaPetTee.h (the screen copy) from examples/companion_radio.
  2. Draws known scenes through the tee. The expected pixels are worked out here, in Python, from the
     contract (128x64, 16 bytes a row, top bit = leftmost pixel) and from a hand-written 'A' and 'g'.
  3. Feeds the radio's lines to the dashboard's own JavaScript (test/ui/nova_pet/dashboard_pet_decoder.js,
     the PET block of the dashboard page) under node and compares every pixel. Any change of bit order,
     row order, size, run-length or base64 makes this fail.
  4. Compares the C++ encoder with a Python reference encoder on random and worst-case pictures.
  5. Checks the stream rules (when a key picture or a delta goes out), the line size bound, and that the
     tee passes every call to the real screen unchanged.
Set NOVA_DASHBOARD_HTML=/path/to/index.html to decode with a newer dashboard (the block between the
/*PET-BEGIN*/ and /*PET-END*/ markers is cut out of that page).
"""
from pathlib import Path
import base64
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CR = ROOT / 'examples/companion_radio'
HERE = ROOT / 'test/ui/nova_pet'
W, H, ROW, BYTES = 128, 64, 16, 1024
MAX_LINE = 2112


def check(cond, msg):
    if not cond:
        print('FAIL:', msg)
        sys.exit(1)


# ---- build the harness --------------------------------------------------------------------------
work = Path(tempfile.mkdtemp(prefix='nova_pet_'))
exe = work / 'harness'
cc = subprocess.run(['g++', '-std=c++17', '-O1', '-Wall', '-Wextra', '-Wno-unused-parameter', '-Wno-delete-non-virtual-dtor', '-Werror', '-I', str(ROOT / 'src'), '-I', str(CR),
                     '-I', str(CR / 'ui-new'), str(HERE / 'harness.cpp'), '-o', str(exe)],
                    capture_output=True, text=True, timeout=180)
check(cc.returncode == 0, 'harness did not compile:\n' + cc.stdout + cc.stderr)


def run_harness(script):
    p = subprocess.run([str(exe)], input=script, capture_output=True, text=True, timeout=60)
    check(p.returncode == 0, 'harness crashed: ' + p.stderr)
    return p.stdout


# ---- the dashboard's decoder (node), with a Python port as the fallback when node is missing -------
def dashboard_block():
    html = os.environ.get('NOVA_DASHBOARD_HTML')
    if html:
        text = Path(html).read_text(encoding='utf-8', errors='replace')
        a, b = text.index('/*PET-BEGIN*/'), text.index('/*PET-END*/') + len('/*PET-END*/')
        out = work / 'dashboard_block.js'
        out.write_text(text[a:b])
        return out
    return HERE / 'dashboard_pet_decoder.js'


NODE = shutil.which('node')
BLOCK = dashboard_block()


class PyDecoder:                      # a line-by-line port of PET.decode / PET.apply (fallback only)
    def __init__(self):
        self.seq, self.fb = -1, bytearray(1024)

    def decode(self, b64):
        raw = base64.b64decode(b64)
        out, o, i = bytearray(1024), 0, 0
        while i < len(raw) and o < 1024:
            c = raw[i]; i += 1
            if c:
                out[o] = c; o += 1
            else:
                run = raw[i] if i < len(raw) else 0; i += 1; o += run
        return out

    def apply(self, p):
        if not p or not isinstance(p.get('d'), str):
            return False
        if p.get('k'):
            self.fb = self.decode(p['d']); self.seq = p['s']
        else:
            if self.seq < 0 or p['s'] != self.seq + 1:
                self.seq = -1
                return False
            d = self.decode(p['d'])
            for i in range(1024):
                self.fb[i] ^= d[i]
            self.seq = p['s']
        return True


def dashboard_decode(lines):
    """Run radio lines through the dashboard decoder. Returns [(applied, seq, framebuffer bytes)]."""
    if NODE:
        p = subprocess.run([NODE, str(HERE / 'decode_lines.js'), str(BLOCK)], input=''.join(lines),
                           capture_output=True, text=True, timeout=60)
        check(p.returncode == 0, 'node failed: ' + p.stderr)
        res = []
        for row in p.stdout.splitlines():
            o = json.loads(row)
            res.append((o['applied'], o.get('seq'), bytes.fromhex(o['fb']) if 'fb' in o else None))
        return res
    dec, res = PyDecoder(), []
    for ln in lines:
        ok = dec.apply(json.loads(ln)['pet'])
        res.append((ok, dec.seq, bytes(dec.fb)))
    return res


# ---- the expected picture, worked out independently --------------------------------------------
class Model:
    def __init__(self):
        self.g = [[False] * W for _ in range(H)]
        self.on = True

    def pix(self, x, y):
        if 0 <= x < W and 0 <= y < H:
            self.g[y][x] = self.on

    def fill(self, x, y, w, h):
        for j in range(y, y + h):
            for i in range(x, x + w):
                self.pix(i, j)

    def box(self, x, y, w, h):
        self.fill(x, y, w, 1); self.fill(x, y + h - 1, w, 1); self.fill(x, y, 1, h); self.fill(x + w - 1, y, 1, h)

    def xbm(self, x, y, w, h, data):
        stride = (w + 7) // 8
        for j in range(h):
            for i in range(w):
                if data[j * stride + i // 8] & (0x80 >> (i % 8)):
                    self.pix(x + i, y + j)

    # glyph columns of the 5x7 font, bit 0 = top row, written out by hand (bit 7 is the descender row)
    GLYPH = {'A': [0x7C, 0x12, 0x11, 0x12, 0x7C], 'g': [0x18, 0xA4, 0xA4, 0x9C, 0x78]}

    def text(self, x, y, size, s):
        for ch in s:
            for col, bits in enumerate(self.GLYPH[ch]):
                for row in range(8):
                    if bits >> row & 1:
                        self.fill(x + col * size, y + row * size, size, size)
            x += 6 * size

    def frame_bytes(self):          # the contract: 16 bytes a row, top row first, leftmost pixel = top bit
        out = bytearray(BYTES)
        for y in range(H):
            for x in range(W):
                if self.g[y][x]:
                    out[y * ROW + x // 8] |= 0x80 >> (x % 8)
        return bytes(out)


def pixels_of(fb, msb_first=True):  # how the dashboard's petDraw() reads the picture
    s = set()
    for y in range(H):
        for b in range(ROW):
            v = fb[y * ROW + b]
            for k in range(8):
                if v & ((0x80 >> k) if msb_first else (1 << k)):
                    s.add((b * 8 + k, y))
    return s


def model_pixels(m):
    return {(x, y) for y in range(H) for x in range(W) if m.g[y][x]}


# ---- 1. the glyph table is the 5x7 font, 95 glyphs ----------------------------------------------
hdr = (CR / 'NovaPetLink.h').read_text()
table = re.search(r'static const uint8_t t\[\] = \{(.*?)\};', hdr, re.S).group(1)
vals = [int(v, 16) for v in re.findall(r'0x[0-9A-Fa-f]{2}', table)]
check(len(vals) == 95 * 5, 'font table must hold 95 glyphs of 5 bytes, has %d' % len(vals))
for ch, cols in Model.GLYPH.items():
    check(vals[(ord(ch) - 32) * 5:(ord(ch) - 32) * 5 + 5] == cols, "font glyph '%s' differs from the 5x7 font" % ch)
check(vals[0:5] == [0] * 5, 'space must be blank')

# ---- 2. a known scene, drawn through the tee, decoded by the dashboard ----------------------------
XBM = [0x80, 0x40, 0xFF, 0xC0, 0x01, 0x00]          # 10 x 3
m = Model()
script = ['REQ 1000', 'F 1000']
ops = [('rect', (10, 5, 3, 2)), ('box', (20, 10, 8, 6)), ('xbm', (40, 20, 10, 3, XBM)),
       ('cursor', (60, 30)), ('print', 'Ag'), ('size', (2,)), ('cursor', (4, 40)), ('print', 'A'),
       ('rect', (-5, -5, 10, 10)), ('rect', (120, 60, 20, 20)), ('color', (0,)), ('rect', (11, 5, 1, 1)),
       ('color', (1,)), ('rect', (0, 63, 128, 1))]
for name, a in ops:
    if name == 'rect': script.append('rect %d %d %d %d' % a); m.fill(*a)
    elif name == 'box': script.append('box %d %d %d %d' % a); m.box(*a)
    elif name == 'xbm': script.append('xbm %d %d %d %d %s' % (a[0], a[1], a[2], a[3], bytes(a[4]).hex())); m.xbm(*a)
    elif name == 'cursor': script.append('cursor %d %d' % a); cur = a
    elif name == 'print': script.append('print ' + a); m.text(cur[0], cur[1], sz if 'sz' in dir() else 1, a)
    elif name == 'size': script.append('size %d' % a); sz = a[0]
    elif name == 'color': script.append('color %d' % a); m.on = bool(a[0])
script += ['DUMP', 'E']
out = run_harness('\n'.join(script) + '\n').splitlines()
lines = [l[5:] + '\n' for l in out if l.startswith('LINE ')]
check(len(lines) == 1, 'expected one key line, got %d' % len(lines))
obj = json.loads(lines[0])
check(list(obj.keys()) == ['pet'] and list(obj['pet'].keys()) == ['s', 'k', 'd'], 'line must be {"pet":{"s","k","d"}}: ' + lines[0][:60])
check(obj['pet']['s'] == 1 and obj['pet']['k'] == 1, 'first line must be key picture number 1')
expected = m.frame_bytes()
dump = bytes.fromhex([l for l in out if re.fullmatch(r'[0-9a-f]{2048}', l)][0])
check(dump == expected, 'canvas bytes differ from the independent model (layout or drawing)')
res = dashboard_decode(lines)
check(res[0][0] and res[0][2] == expected, 'dashboard decoder disagrees with the expected picture')
check(pixels_of(res[0][2]) == model_pixels(m), 'pixels as the dashboard draws them differ from the model')
# the descender row of 'g' (bit 7) must be there: it sits 7 rows below the text top
check({(67, 37), (68, 37), (69, 37)} <= pixels_of(res[0][2]), "descender row of 'g' is missing")   # 'g' is the 2nd character at x=66, bit 7 = row 7
check(pixels_of(res[0][2]) != pixels_of(res[0][2], msb_first=False), 'negative control: LSB-first reading must differ')
dec_b64_len = len(obj['pet']['d'])
check(dec_b64_len % 4 == 0 and re.fullmatch(r'[A-Za-z0-9+/]+={0,2}', obj['pet']['d']), 'd must be padded standard base64')
print('scene through the tee decodes to the expected %d pixels in the dashboard decoder' % len(model_pixels(m)))

# ---- 3. the encoder against a Python reference, random and worst-case pictures -----------------------
def ref_line(fb, prev, seq):
    data = fb if prev is None else bytes(a ^ b for a, b in zip(fb, prev))
    out, i = bytearray(), 0
    while i < len(data):
        if data[i]:
            out.append(data[i]); i += 1
        else:
            j = i
            while j < len(data) and data[j] == 0 and j - i < 255:
                j += 1
            out += bytes([0, j - i]); i = j
    return '{"pet":{"s":%d,"k":%d,"d":"%s"}}\n' % (seq, 0 if prev is not None else 1, base64.b64encode(bytes(out)).decode())


rng = random.Random(20261111)
frames = [bytes(BYTES), bytes([0xFF] * BYTES), bytes([0x80] + [0] * 1023), bytes([0] * 1023 + [1]),
          bytes([(0x55 if i % 2 == 0 else 0) for i in range(BYTES)]),               # worst case for the coding
          bytes([(1 if i % 2 == 0 else 0) for i in range(BYTES)]),
          bytes(rng.getrandbits(8) for _ in range(BYTES)),
          bytes(rng.choice([0, 0, 0, 0, 0, 0xA5]) for _ in range(BYTES)),
          bytes([0] * 300 + [7] + [0] * 700 + [9] + [0] * 22)]                       # runs longer than 255
enc_script, expect = [], []
for n, f in enumerate(frames):
    enc_script.append('ENC %d %s' % (n + 1, f.hex())); expect.append(ref_line(f, None, n + 1))
for n in range(1, len(frames)):
    enc_script.append('ENC %d %s %s' % (100 + n, frames[n].hex(), frames[n - 1].hex()))
    expect.append(ref_line(frames[n], frames[n - 1], 100 + n))
enc_script.append('ENC 4294967295 %s' % frames[4].hex()); expect.append(ref_line(frames[4], None, 4294967295))   # biggest sequence number
enc_script.append('ENCSMALL')
out = run_harness('\n'.join(enc_script) + '\n').splitlines()
got = [l for l in out if l.startswith('ENC ') and not l.startswith('ENCSMALL')]
check(len(got) == len(expect), 'encoder reply count')
longest = 0
for g, e in zip(got, expect):
    n, line = g.split(' ', 2)[1], g.split(' ', 2)[2]
    check(int(n) == len(e) and line + '\n' == e, 'C++ encoder differs from the reference:\n %s\n %s' % (line[:90], e[:90]))
    longest = max(longest, len(e))
check(longest < MAX_LINE, 'a line (%d) does not fit MAX_LINE %d' % (longest, MAX_LINE))
check(len(json.loads(expect[4])['pet']['d']) == 2048, 'worst-case picture should code to 1536 bytes = 2048 base64 characters')
check('ENCSMALL 0' in out, 'a buffer smaller than MAX_LINE must be refused')
print('encoder matches the reference on %d pictures; longest line %d of %d' % (len(expect), longest, MAX_LINE - 1))
# the dashboard decodes the keys and the deltas back to the original pictures
key_lines = [e for e in expect[:len(frames)]]
for f, kl in zip(frames, key_lines):
    r = dashboard_decode([kl])[0]
    check(r[0] and r[2] == f, 'dashboard decoded a key picture wrongly')
for n in range(1, len(frames)):
    r = dashboard_decode([ref_line(frames[n - 1], None, 7), ref_line(frames[n], frames[n - 1], 8)])
    check(r[1][0] and r[1][2] == frames[n], 'dashboard decoded a delta picture wrongly (frame %d)' % n)
# the C++ lines themselves, not only the reference lines, through the dashboard
cpp_lines = [l.split(' ', 2)[2] + '\n' for l in got[:len(frames)]]
for f, cl in zip(frames, cpp_lines):
    r = dashboard_decode([cl])[0]
    check(r[0] and r[2] == f, 'dashboard decoded a C++ key line wrongly')
print('dashboard decoder reads the C++ lines back to the original pictures')

# ---- 4. a moving picture: key, deltas, quiet, repeat key, dropped line ------------------------------
def scene(x):
    mm = Model(); mm.fill(x, 20, 6, 4); mm.box(0, 0, 128, 64); mm.fill(60, 30, 3, 3)
    return mm


def frame_ops(t, x, req=None):
    s = []
    if req is not None: s.append('REQ %d' % req)
    s += ['F %d' % t, 'rect %d 20 6 4' % x, 'box 0 0 128 64', 'rect 60 30 3 3', 'E']
    return s


seq_script, plan = [], []
seq_script += frame_ops(1000, 10, req=1000); plan.append(('key', 1, 10))          # first picture: key
seq_script += frame_ops(1100, 12);           plan.append(('none', None, None))     # under 250 ms later: wait
seq_script += frame_ops(1300, 14);           plan.append(('delta', 2, 14))         # moved: delta
seq_script += frame_ops(1600, 14);           plan.append(('none', None, None))     # did not move: nothing sent
seq_script += frame_ops(2000, 20, req=2000); plan.append(('delta', 3, 20))         # a keep-alive renews the window
for i in range(40):                                                               # 40 deltas, then a key
    t = 2300 + i * 300
    if i % 10 == 0: seq_script.append('REQ %d' % t)
    seq_script += frame_ops(t, 30 + i); plan.append(('delta' if i < 36 else ('key' if i == 36 else 'delta'), None, 30 + i))
out = run_harness('\n'.join(seq_script) + '\n').splitlines()
chunks, cur = [], []
for l in out:
    if l.startswith('LINE '): cur.append(l[5:])
    elif l.startswith('ACTIVE'): chunks.append(cur); cur = []
check(len(chunks) == len(plan), 'frame count %d vs plan %d' % (len(chunks), len(plan)))
kinds = []
for ch in chunks:
    if not ch: kinds.append('none'); continue
    o = json.loads(ch[0])['pet']; kinds.append('key' if o['k'] else 'delta')
check(kinds[:5] == ['key', 'none', 'delta', 'none', 'delta'], 'stream rules, first frames: %s' % kinds[:5])
check(kinds[5:].count('key') >= 1, 'a whole picture must follow within 40 changed pictures (got %s)' % kinds[5:])
sent = [(i, l + '\n') for i, ch in enumerate(chunks) for l in ch]
seqs = [json.loads(l)['pet']['s'] for _, l in sent]
check(seqs == list(range(1, len(seqs) + 1)), 'line numbers must count up by one: %s' % seqs[:8])
res = dashboard_decode([l for _, l in sent])
check(all(r[0] for r in res), 'dashboard rejected a line of the stream')
# the last decoded picture equals the last frame drawn (x = 30 + 39)
check(res[-1][2] == scene(30 + 39).frame_bytes(), 'stream did not end on the last picture drawn')
# a dropped line: the dashboard must wait for the next key picture, then recover
drop = [l for _, l in sent]
res2 = dashboard_decode(drop[:3] + drop[4:])
check(res2[3][0] is False, 'dashboard must ignore a delta after a missed line')
ks = [i for i, l in enumerate(drop[4:]) if json.loads(l)['pet']['k']]
check(ks, 'no key picture after the dropped line')
check(res2[3 + 1 + ks[0]][0] and res2[3 + 1 + ks[0]][2] is not None, 'dashboard did not recover on the next key picture')
print('stream: %s ...; %d lines, numbers 1..%d, dashboard rejects after a gap and recovers on a key' % (kinds[:5], len(sent), len(sent)))

# ---- 5. stream asks: nothing without a request, a key picture again after a pause --------------------
quiet = run_harness('\n'.join(['F 100', 'rect 1 1 4 4', 'E']) + '\n')
check('LINE' not in quiet, 'nothing may be sent before "nova pet"')
lapse = ['REQ 1000'] + frame_ops(1000, 10) + frame_ops(1500, 11) + frame_ops(9000, 12)        # 9000: window (4 s) is over
lapse += ['REQ 9100'] + frame_ops(9200, 13)
out = run_harness('\n'.join(lapse) + '\n').splitlines()
ch, cur = [], []
for l in out:
    if l.startswith('LINE '): cur.append(l[5:])
    elif l.startswith('ACTIVE'): ch.append(cur); cur = []
check(len(ch[0]) == 1 and len(ch[1]) == 1 and not ch[2], 'a lapsed window must stop the stream: %s' % [len(c) for c in ch])
last = json.loads(ch[3][0])['pet']
check(last['k'] == 1, 'a stream that lapsed and was asked again must start with a key picture')
print('no line without a request; stops when the window lapses; restarts with a key picture')

# ---- 6. the tee changes nothing on the real screen ------------------------------------------------------
pt = [l for l in run_harness('\n'.join(['REQ 1', 'F 1', 'color 1', 'size 2', 'cursor 3 4', 'print Ag', 'center 64 40 Ag', 'rect 1 2 3 4',
                                         'box 5 6 7 8', 'xbm 1 1 10 3 8040ffc00100', 'color 0', 'rect 0 0 2 2', 'clear', 'E']) + '\n').splitlines()
      if l.startswith('PASSTHROUGH')][0]
check(pt.startswith('PASSTHROUGH same'), 'the real screen got different calls with the tee in front: ' + pt)
print('tee passes every call to the real screen unchanged (' + pt + ')')

shutil.rmtree(work, ignore_errors=True)
print('OK (decoder: %s)' % ('node, ' + BLOCK.name if NODE else 'python port: node not found'))
