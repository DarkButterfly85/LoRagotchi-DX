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


# ---- 7. the waiting hint (screen off) -------------------------------------------------------------
wt = re.findall(r'^WAIT (\d)$', run_harness('\n'.join(['REQ 1000', 'WAIT 2000', 'WAIT 4500', 'F 4600', 'rect 1 1 2 2', 'E', 'WAIT 4700',
                                                         'REQ 9000', 'WAIT 9500', 'WAIT 12500']) + '\n'), re.M)
check(wt == ['0', '1', '0', '0', '1'], 'waiting hint (asked, no frame for 3 s; frame drawn; asked again): %s' % wt)
print('"screen is off" is detected: asked for >3 s and no frame drawn')

# ---- 8. the serial commands, from the real MyMesh.cpp ------------------------------------------------
mm = (CR / 'MyMesh.cpp').read_text()
a = mm.index('#ifdef LORAGOTCHI_NOVA_LINK\n// ---- LORAGOTCHI NOVA serial link')
endmark = '#endif  // LORAGOTCHI_NOVA_LINK'
b = mm.index(endmark, a) + len(endmark)
(work / 'nova_block.inc').write_text(mm[a:b] + '\n')
check('checkNovaSerial();' in mm[mm.index('void MyMesh::loop()'):], 'loop() must call checkNovaSerial()')
loop = mm[mm.index('void MyMesh::loop()'):]
check(loop.index('if (_cli_rescue)') < loop.index('checkNovaSerial();') and loop.index('} else {') < loop.index('checkNovaSerial();'),
      'checkNovaSerial() must sit in the branch that is not CLI Rescue')
sexe = work / 'serial_harness'
cc = subprocess.run(['g++', '-std=c++17', '-O1', '-Wall', '-Wextra', '-Wno-unused-parameter', '-Wno-delete-non-virtual-dtor', '-Werror',
                     '-I', str(work), '-I', str(HERE), '-I', str(ROOT / 'src'), '-I', str(CR), '-I', str(CR / 'ui-new'),
                     str(HERE / 'serial_harness.cpp'), '-o', str(sexe)], capture_output=True, text=True, timeout=180)
check(cc.returncode == 0, 'serial harness did not compile:\n' + cc.stdout + cc.stderr)


def run_serial(script):
    p = subprocess.run([str(sexe)], input='\n'.join(script) + '\n', capture_output=True, text=True, timeout=60)
    check(p.returncode == 0, 'serial harness crashed: ' + p.stderr)
    return [l.split(' ', 3) for l in p.stdout.splitlines() if l.startswith('OUT ')]   # ['OUT', bytes, writes, text]


def outs(rows):
    return [(r[3] if len(r) > 3 else '').replace('\\n', '\n').replace('\\r', '\r') for r in rows]


def dispatch(line):                    # the dashboard's onLine(), conditions copied from its source
    line = line.strip()
    if line[:1] == '{' and line.find('"mesh"') == 1: return 'mesh'
    if line[:1] == '{' and line.find('"pet"') == 1: return 'pet'
    if line[:1] == '{' and line.find('"nova"') > 0: return 'frame'          # would be read as radio telemetry
    if line[:1] == '#':
        return 'nosupport' if re.match(r'^nova \[status\|profile', line[1:].strip()) else 'log'
    return 'ignored'


s1 = ['SUP 1', 'T 100', 'RX nova hello\\r\\n', 'T 110', 'RX nova mesh\\n', 'T 120', 'RX nova petname Fluffy\\n', 'T 130',
      'RX nova profile away\\n', 'T 140', 'RX hello\\nls\\nnext\\nnovapet\\n', 'T 150', 'RX nova   he', 'T 160', 'RX llo\\n', 'T 170',
      'RX nova pets\\n', 'T 180', 'RXLONG 200', 'T 190']
o = outs(run_serial(s1))
check(o[0] == '', 'nothing may be sent before a command')
check(o[1] == '{"lg":{"hello":1,"pet":1,"mesh":0}}\n', 'nova hello reply: %r' % o[1])
check(o[2] == '{"lg":{"mesh":0}}\n', 'nova mesh reply: %r' % o[2])
check(o[3].startswith('# petname: ') and o[3].count('\n') == 1, 'nova petname reply: %r' % o[3])
check(o[4].startswith('# nova: not supported') and o[4].count('\n') == 1, 'unknown nova command reply: %r' % o[4])
check(o[5] == '', 'lines that are not "nova ..." must be ignored: %r' % o[5])
check(o[6] == '' and o[7] == '{"lg":{"hello":1,"pet":1,"mesh":0}}\n', 'a command split over two reads, extra spaces: %r %r' % (o[6], o[7]))
check(o[8].startswith('# nova: not supported'), '"nova pets" is not "nova pet": %r' % o[8])
check(o[9] == '', 'a 200 character line must be dropped whole: %r' % o[9])
d = [dispatch(x) for x in (o[1], o[2], o[3], o[4], o[8])]
check(d == ['ignored', 'ignored', 'log', 'log', 'log'], 'the dashboard must ignore the JSON replies and log the # lines: %s' % d)
print('commands: hello, mesh, petname, unknown, partial/long/non-nova lines behave; the dashboard ignores the JSON, logs the # lines')

# "nova petname": the real handler from MyMesh.cpp -> the real LoRaFishIdentity.h -> the real SafeSave, on a fake flash
def run_id(script):
    p = subprocess.run([str(sexe)], input='\n'.join(script) + '\n', capture_output=True, text=True, timeout=60)
    check(p.returncode == 0, 'serial harness crashed: ' + p.stderr)
    rows = []
    for l in p.stdout.splitlines():
        if l.startswith('OUT '):
            r = l.split(' ', 3); rows.append(('OUT', (r[3] if len(r) > 3 else '').replace('\\n', '\n')))
        elif l.startswith('ID '):
            rows.append(('ID', dict(re.findall(r'(\w+)=(\[[^\]]*\]|\S+)', l))))
    return rows


pn = ['SETTER 1', 'LIVE 0 1 2 3', 'ID',
      'RX nova petname Fluffy\\n', 'T 10', 'ID',                       # created: name set, species and colours from the live pet
      'RX nova petname 0123456789ABCDEFG\\n', 'T 20', 'ID',           # 17 characters: refused, file unchanged
      'RX nova petname caf\u00e9\\n', 'T 30', 'ID',                   # not ASCII: refused
      'RX nova petname   Mr Bubbles  \\n', 'T 40', 'ID',             # spaces trimmed, inner space kept
      'RX nova petname 0123456789ABCDEF\\n', 'T 50', 'ID',           # exactly 16: fine
      'RX nova petname -\\n', 'T 60', 'ID',                          # dash clears (the dashboard's way)
      'RX nova petname\\n', 'T 70', 'ID',                            # no name: usage, nothing written
      'FAIL 1', 'RX nova petname Nope\\n', 'T 80', 'FAIL 0', 'ID',    # flash write fails: reported, file unchanged
      'SETTER 0', 'RX nova petname Y\\n', 'T 90']                    # no pet screen in this build
rows = run_id(pn)
texts = [v for k, v in rows if k == 'OUT']
ids = [v for k, v in rows if k == 'ID']
check(len(ids) == 9 and len(texts) == 9, 'petname script produced %d ID rows, %d replies' % (len(ids), len(texts)))
check(ids[0]['files'] == '-' and ids[0]['src'] == '0', 'before any name there is no file at all: %s' % ids[0])
check(texts[0].startswith('# petname: saved "Fluffy" in /lorafish.id') and texts[0].count('\n') == 1, 'petname reply: %r' % texts[0])
files = sorted(ids[1]['files'].split(','))
check(files == ['/lorafish.id'], 'only /lorafish.id may be written (no pet record, no settings): %s' % files)
check(ids[1]['name'] == '[Fluffy]' and ids[1]['sp'] == '0' and ids[1]['genes'] == '1,2,3', 'name saved with the live species and colours: %s' % ids[1])
check(texts[1].startswith('# petname: too long') and ids[2] == ids[1], 'a 17 character name is refused and changes nothing: %r %s' % (texts[1], ids[2]))
check(texts[2].startswith('# petname: plain keyboard') and ids[3] == ids[1], 'a non-ASCII name is refused: %r' % texts[2])
check(ids[4]['name'] == '[Mr Bubbles]' and texts[3].startswith('# petname: saved "Mr Bubbles"'), 'trimmed name: %s %r' % (ids[4], texts[3]))
check(ids[5]['name'] == '[0123456789ABCDEF]', '16 characters are accepted: %s' % ids[5])
check(ids[6]['name'] == '[]' and ids[6]['sp'] == '0' and texts[5].startswith('# petname: name cleared'), 'dash clears the name, keeps species/colours: %s %r' % (ids[6], texts[5]))
check(texts[6].startswith('# petname: usage') and ids[7] == ids[6], 'no name: usage line only: %r' % texts[6])
check(texts[7].startswith('# petname: could not save') and ids[8] == ids[6], 'a failed write is reported and changes nothing: %r' % texts[7])
check(texts[8].startswith('# petname: this build has no pet name'), 'no pet screen: %r' % texts[8])
for t in texts: check(dispatch(t) == 'log' and t.count('\n') == 1, 'petname replies are single # lines: %r' % t)
print('petname: writes only /lorafish.id, 16 ok / 17 refused / non-ASCII refused, dash clears, failures and no-pet builds answer in one # line')

s2 = ['SUP 0', 'RX nova hello\\n', 'T 10', 'RX nova pet\\n', 'T 20', 'RX nova pet\\n', 'T 3020', 'RX nova pet\\n', 'T 31000']
o = outs(run_serial(s2))
check(o[0] == '{"lg":{"hello":1,"pet":0,"mesh":0}}\n', 'hello on a screen that cannot be copied: %r' % o[0])
check(o[1].startswith('# nova pet: this radio has no 128x64') and o[2] == '' and o[3].startswith('# nova pet:'), 'unsupported screen: one note, then quiet for 30 s: %r' % o)
check(dispatch(o[1]) == 'log', 'the dashboard must log the unsupported note (not mistake it for "no pet support")')
print('screen that cannot be copied: hello says pet 0; "nova pet" explains itself once every 30 s')

# end to end: nova pet, the screen draws, the lines go out 96 bytes per 10 ms, the dashboard decodes them
sc1, sc2 = Model(), Model()
DENSE = bytes([0x55, 0x00] * 8) * 64         # every other byte set: the longest kind of picture to code
sc1.xbm(0, 0, 128, 64, DENSE); sc1.fill(10, 20, 6, 4)
sc2.fill(40, 30, 6, 4); sc2.box(0, 0, 128, 64); sc2.fill(60, 5, 8, 3)
s3 = ['SUP 1', 'RX nova pet\\n', 'T 1000']
s3 += ['F 1000', 'xbm 0 0 128 64 ' + DENSE.hex(), 'rect 10 20 6 4', 'E']
for t in range(1000, 1290, 10): s3.append('T %d' % t)
s3 += ['F 1300', 'rect 40 30 6 4', 'box 0 0 128 64', 'rect 60 5 8 3', 'E']
for t in range(1300, 1600, 10): s3.append('T %d' % t)
rows = run_serial(s3)
o = outs(rows)
check(o[0] == '', 'nova pet must not answer with text')
sizes = [int(r[1]) for r in rows]
check(max(sizes) <= 96, 'at most 96 bytes may go out per loop pass, saw %d' % max(sizes))
stream = ''.join(o)
lines = stream.splitlines(keepends=True)
check(len(lines) == 2 and all(l.endswith('\n') for l in lines), 'expected two complete lines, got %d' % len(lines))
check([dispatch(l) for l in lines] == ['pet', 'pet'], 'the dashboard must take both lines as pet pictures')
ks = [json.loads(l)['pet']['k'] for l in lines]
check(ks == [1, 0], 'key picture then a delta, got %s' % ks)
res = dashboard_decode(lines)
check(all(r[0] for r in res) and res[0][2] == sc1.frame_bytes() and res[1][2] == sc2.frame_bytes(),
      'dashboard did not decode the lines that went over the fake serial port to the pictures drawn')
sent_at = [i for i, s in enumerate(sizes) if s]
check(len(sent_at) >= 20, 'a whole picture should need many small writes (%d)' % len(sent_at))
print('end to end: "nova pet" -> screen draws -> %d small writes -> 2 lines -> dashboard shows both pictures' % len(sent_at))

# a lapsed stream drops its unsent bytes; nothing leaks out later
s4 = ['SUP 1', 'RX nova pet\\n', 'T 1000', 'F 1000', 'xbm 0 0 128 64 ' + DENSE.hex(), 'E', 'T 1010', 'T 1020', 'T 6000', 'T 6010', 'T 6020']
rows = run_serial(s4)
o = outs(rows)
check(len(o[1]) == 96 and len(o[2]) == 96 and o[3] == '' and o[4] == '' and o[5] == '', 'a line half sent when the window lapses must be dropped, not finished: %s' % [len(x) for x in o])
# screen asleep: one hint, once per 30 s; the page keeps asking every 3 s
s5 = ['SUP 1', 'RX nova pet\\n', 'T 1000', 'T 2000', 'RX nova pet\\n', 'T 3000', 'T 4100', 'RX nova pet\\n', 'T 6000', 'T 6100']
o = outs(run_serial(s5))
hints = [x for x in o if x]
check(len(hints) == 1 and hints[0].startswith('# nova pet: waiting for the radio') and dispatch(hints[0]) == 'log', 'screen-off hint: %s' % hints)
# a long line, then a good command: the stream still starts
s6 = ['SUP 1', 'RXLONG 200', 'T 1000', 'F 1010', 'rect 1 1 3 3', 'E', 'T 1020', 'RX nova pet\\n', 'T 1030', 'F 1040', 'rect 1 1 3 3', 'E', 'T 1050', 'T 1060']
o = outs(run_serial(s6))
check(o[0] == '' and o[1] == '' and o[2] == '' and any(x for x in o[3:]), 'a 200 character line must not start the stream, a later good command must: %s' % [len(x) for x in o])
print('lapse, screen-off hint and long-line recovery behave')

# the source: no other reader of Serial may be in the same build
ui = (CR / 'ui-new/UITask.cpp').read_text()
check('#if defined(LORAFISH_SERIAL_TEST)' in ui and '!defined(LORAFISH_SERIAL_TEST)' in hdr, 'LORAFISH_SERIAL_TEST builds read USB serial themselves: the link must be left out of them')
check('!defined(ENABLE_USB_INTERFACE)' in hdr, 'the link must be left out of builds that carry the phone protocol on USB')
check(ui.count('NovaPetTee tee(') == 1 and 'NovaPetLink::supported() ? NovaPetLink::link() : NULL' in ui, 'UITask must only use the tee when the link is asked')
print('wiring checks ok')

shutil.rmtree(work, ignore_errors=True)
print('OK (decoder: %s)' % ('node, ' + BLOCK.name if NODE else 'python port: node not found'))
