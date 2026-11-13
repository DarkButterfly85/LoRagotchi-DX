#!/usr/bin/env python3
"""Nova data streams: the mesh line, the status frame and the battery reply, from the real MyMesh.cpp serial block.

python3 test/ui/check_nova_streams.py     (Python 3, g++, node optional; no firmware build, no board, no hardware)

  a. wiring (source): logRx/logTx feed the hub, the delivery hooks, novaRefreshEnv runs before checkNovaSerial, hello says mesh 1 only
     where the feeds exist, every use of NovaStreams in MyMesh.cpp sits inside LORAGOTCHI_NOVA_LINK (other builds are unchanged)
  b. behaviour: the production block (cut out of MyMesh.cpp, as check_nova_pet_frame.py does) is compiled against a fake serial port and
     fed packets, a battery reading and messages. What goes out is checked as the dashboard's line router and decoder read it,
     how often, at which pace (never more than 96 bytes per pass at the default speed), and that no line is ever mixed with another
  c. with the Nova dashboard page at hand (NOVA_DASHBOARD_HTML, or /tmp/nova-name-fix/docs/index.html) the page's own onMeshLine
     is run under node on the radio's mesh line
"""
from pathlib import Path
import json, os, re, shutil, subprocess, sys, tempfile

ROOT = Path(__file__).resolve().parents[2]
CR = ROOT / 'examples/companion_radio'
HERE = ROOT / 'test/ui/nova_pet'


def check(cond, msg):
    if not cond:
        print('FAIL:', msg)
        sys.exit(1)


mm = (CR / 'MyMesh.cpp').read_text()
mh = (CR / 'MyMesh.h').read_text()

# ---- a. wiring ---------------------------------------------------------------------------------------------------
a = mm.index('#ifdef LORAGOTCHI_NOVA_LINK\n// ---- LORAGOTCHI NOVA serial link')
endmark = '#endif  // LORAGOTCHI_NOVA_LINK'
b = mm.index(endmark, a) + len(endmark)
blk = mm[a:b]
check('void logRx(mesh::Packet* pkt, int len, float score) override;' in mh and 'void logTx(mesh::Packet* pkt, int len) override;' in mh,
      'MyMesh.h must override the Dispatcher hooks logRx and logTx')
check('void novaRefreshEnv();' in mh, 'MyMesh.h declares novaRefreshEnv')
feeds = mm[mm.index('void MyMesh::logRx(mesh::Packet* pkt, int len, float score) {'):]
check(re.search(r'logRx\(mesh::Packet\* pkt, int len, float score\) \{\s*NovaStreams::hub\(\)\.onRx\(millis\(\), _radio->getLastRSSI\(\), pkt->getSNR\(\), pkt->getPayloadType\(\), pkt->getRouteType\(\), pkt->getPathHashCount\(\),\s*pkt->getPathHashSize\(\), pkt->path, pkt->payload, pkt->payload_len, len\);', feeds),
      'logRx must hand the hub the packet as received: rssi, snr, type, route, hop count, hash size, path, payload, length')
check(re.search(r'logTx\(mesh::Packet\* pkt, int len\) \{\s*NovaStreams::hub\(\)\.onTx\(millis\(\), pkt->getPayloadType\(\), pkt->getRouteType\(\), len\);', feeds), 'logTx must hand the hub the packet sent')
check('void MyMesh::logRx(mesh::Packet*, int, float) {}' in feeds and 'void MyMesh::logTx(mesh::Packet*, int) {}' in feeds, 'builds without the link keep empty hooks (behaviour unchanged)')
check('hub.nf = (int)_radio->getNoiseFloor();' in mm and 'hub.sf = _prefs.sf; hub.bw = _prefs.bw; hub.cr = _prefs.cr;' in mm, 'radio settings come from the radio and the prefs')
check('hub.bat.sample(now, board.getBattMilliVolts(), board.isExternalPowered());' in mm and 'hub.bat.pctOf = LoRaFishBattery::percent;' in mm, 'battery: the same reading and the same curve as the status screen')
check('sensors.getLocationProvider()' in mm and 'hub.gps.update(' in mm, 'GPS position comes from the location provider when there is one')
check('NovaStreams::hub().dl.onSent(millis(), recipient->name, expected_ack, est_timeout' in mm and 'NovaStreams::hub().dl.onAck(millis(), novaAck);' in mm,
      'messages sent from the phone app: recorded when sent, delivered on their ack')
loop = mm[mm.index('void MyMesh::loop()'):]
check(loop.index('novaRefreshEnv();') < loop.index('checkNovaSerial();'), 'the feeds are refreshed before the serial block runs')
check('caps.mesh = 1;' in blk, 'hello lists mesh 1 in this build')
check('hub.askMesh(now);' in blk and 'hub.askStatus(now, NovaStreams::STATUS_GAP_MS);' in blk, 'nova mesh queues the mesh line and the status frame (5 s)')
check('p.cmd == NovaCli::Cmd::Status' in blk and 'p.cmd == NovaCli::Cmd::Battery' in blk, 'nova status and nova battery are answered')
check('Serial.write(' in blk and blk.count('hub.out.consumed(Serial.write(hub.out.data(), n));') == 1, 'the queue is written through one place, at the link pace')
# every use of NovaStreams sits inside a LORAGOTCHI_NOVA_LINK region
stack = []
for no, l in enumerate(mm.splitlines(), 1):
    s = l.strip()
    if s.startswith('#if'): stack.append(s)
    elif s.startswith('#endif'): stack.pop()
    elif s.startswith('#else') and stack: stack[-1] = '#ifnot ' + stack[-1]
    if ('NovaStreams::' in l or 'NovaStreams.h' in l) and not s.startswith('//'):
        check(any(x == '#ifdef LORAGOTCHI_NOVA_LINK' for x in stack), 'MyMesh.cpp line %d uses NovaStreams outside LORAGOTCHI_NOVA_LINK: %s' % (no, s))
print('wiring: rx/tx hooks, radio/battery/gps feeds, message hooks, loop order, hello mesh 1; all inside LORAGOTCHI_NOVA_LINK')

# ---- b. behaviour ------------------------------------------------------------------------------------------------
work = Path(tempfile.mkdtemp(prefix='nova-streams-'))
(work / 'nova_block.inc').write_text(blk + '\n')
exe = work / 'serial_harness'
cc = subprocess.run(['g++', '-std=c++17', '-O1', '-Wall', '-Wextra', '-Wno-unused-parameter', '-Wno-delete-non-virtual-dtor', '-Werror',
                     '-I', str(work), '-I', str(HERE), '-I', str(ROOT / 'src'), '-I', str(CR), '-I', str(CR / 'ui-new'),
                     str(HERE / 'serial_harness.cpp'), '-o', str(exe)], capture_output=True, text=True, timeout=240)
check(cc.returncode == 0, 'serial harness did not compile:\n' + cc.stdout + cc.stderr)


def run(script):
    p = subprocess.run([str(exe)], input='\n'.join(script) + '\n', capture_output=True, text=True, timeout=60)
    check(p.returncode == 0, 'serial harness crashed: ' + p.stderr)
    rows = []
    for l in p.stdout.splitlines():
        if l.startswith('OUT '):
            r = l.split(' ', 3)
            rows.append((int(r[1]), (r[3] if len(r) > 3 else '').replace('\\n', '\n').replace('\\r', '\r')))
    return rows


def ticks(t0, n=14):                  # the radio loop at 10 ms steps (the link's pace)
    return ['T %d' % (t0 + 10 * i) for i in range(n)]


def text(rows):
    return ''.join(t for _, t in rows)


def lines_of(s):
    out = s.splitlines(keepends=True)
    check(all(l.endswith('\n') for l in out), 'a line was cut: %r' % s[-120:])
    return out


def dispatch(line):                   # the dashboard's onLine() router, conditions copied from its source
    line = line.strip()
    if line[:1] == '{' and line.find('"mesh"') == 1: return 'mesh'
    if line[:1] == '{' and line.find('"pet"') == 1: return 'pet'
    if line[:1] == '{' and line.find('"contacts"') == 1: return 'contacts'
    if line[:1] == '{' and (line.find('"nova_ok"') == 1 or line.find('"nova_error"') == 1): return 'reply'
    if line.startswith('{"ed":') and line.find('"nova":{') > 0: return 'hello'
    if line[:1] == '{' and line.find('"nova"') > 0: return 'frame'
    return 'ignored'


# the first request: a mesh line (empty heartbeat, then the packets heard) and a status frame, in that order, at the link's pace
base = ['SUP 1', 'SETTER 1', 'RADIO -111 10 250.0 5', 'BAT 3900 0', 'HEARD 102 6.5', 'HEARD 102 7.0', 'HEARD 33 -14', 'SENT Alice 1 4000']
rows = run(base + ['T 1000', 'RX nova mesh\\n'] + ticks(1010, 20))
check(text(rows[:1]) == '', 'nothing goes out before the dashboard asks')
check(max(n for n, _ in rows) <= 96, 'at most 96 bytes a pass at the default speed, saw %d' % max(n for n, _ in rows))
ls = lines_of(text(rows))
check([dispatch(l) for l in ls] == ['mesh', 'frame'], 'one mesh line then one status frame: %s' % [dispatch(l) for l in ls])
mesh, frame = json.loads(ls[0])['mesh'], json.loads(ls[1])
check(list(mesh) == ['nf', 'sf', 'bw', 'cr', 'rx', 'tx', 'ty', 'p'], 'mesh keys in the order the decoder reads: %s' % list(mesh))
check(mesh['nf'] == -111 and mesh['sf'] == 10 and mesh['bw'] == 250.0 and mesh['cr'] == 5 and mesh['rx'] == 3 and mesh['tx'] == 0 and len(mesh['ty']) == 16 and mesh['ty'][2] == 3,
      'radio settings and counters: %s' % mesh)
check(len(mesh['p']) == 3 and all(len(p) == 10 for p in mesh['p']) and mesh['p'][0][8] == '66' and mesh['p'][2][8] == '21', 'three records of ten fields, last hop as id: %s' % mesh['p'])
check('ed' not in frame and ls[1].find('"nova"') == 1, 'the frame has no "ed" (that would be read as a hello) and "nova" comes first')
check(frame['bat']['mv'] == 3900 and frame['bat']['pct'] == 66 and frame['bat']['chg'] == 0 and frame['bat']['hist'] == [3900], 'battery tile: %s' % frame['bat'])
check([l['id'] for l in frame['links']] == ['66', '21'] and frame['links'][0]['best'] == 1 and frame['links'][1]['best'] == 0 and frame['best'] == 0x66,
      'repeaters best first, one best: %s' % frame['links'])
check(all(set(l) == {'id', 'name', 'best', 'sc', 'rel', 'lq', 'snr', 'rssi', 'age', 'hit', 'n'} for l in frame['links']), 'every key renderLinks reads is there')
check(frame['gps'] == {'fix': 0}, 'no GPS fix: the speed tile says so, nothing invented')
check(frame['dl'] == {'sent': 1, 'rep': 0, 'ok': 0, 'fail': 0, 'list': [{'who': 'Alice', 'st': 'sent', 'via': -1, 'rtt': 0, 'age': 1, 'flood': 0, 'link': 1, 'chan': 0}]}, 'messages sent: %s' % frame['dl'])
check(frame['diag']['rx'] == 3 and frame['diag']['tx'] == 0, 'diag counters')
print('first request: mesh line + status frame, in order, <=96 bytes a pass, routed as mesh / frame, every key the page reads')

# pacing and rate: asks every 3 s like the page does
sched = []
script = list(base)
for t in (1000, 4000, 6500, 11500, 11600, 12000):
    script += ['RX nova mesh\\n'] + ticks(t)
rows = run(script)
per = [lines_of(text(rows[i * 14:(i + 1) * 14])) for i in range(6)]
kinds = [[dispatch(l) for l in p] for p in per]
check(kinds == [['mesh', 'frame'], [], ['frame'], ['mesh', 'frame'], [], []], 'what each ask is answered with (asks at 1.0 4.0 6.5 11.5 11.6 12.0 s): %s' % kinds)
print('rate: mesh line at most 1 a second (an empty beat every 10 s), status frame at most every 5 s, nothing for a repeated ask: %s' % kinds)

# new packets are streamed once
rows = run(base + ['RX nova mesh\\n'] + ticks(1000, 14) + ['HEARD 55 3.0', 'RX nova mesh\\n'] + ticks(2500, 14))
second = lines_of(text(rows[14:]))
check([dispatch(l) for l in second] == ['mesh'], 'a later ask: the mesh line with only the new packet: %s' % [dispatch(l) for l in second])
check(len(json.loads(second[0])['mesh']['p']) == 1 and json.loads(second[0])['mesh']['p'][0][8] == '37', 'only the new packet')

# a reply never lands in the middle of a line; contacts wait until a line is complete
tab = ['CLR', 'CONTACT 1 16 4669736820f09f909f']
rows = run(base + tab + ['T 1000', 'RX nova mesh\\n', 'T 1010', 'RX nova hello\\n', 'RX nova contacts\\n', 'RX nova battery\\n'] + ticks(1020, 30))
ls = lines_of(text(rows))
kinds = [dispatch(l) for l in ls]
check(kinds[:2] == ['mesh', 'frame'] and sorted(kinds[2:]) == ['contacts', 'hello', 'reply'], 'order: mesh, frame, then the replies, each whole: %s' % kinds)
check(all(json.loads(l) is not None for l in ls), 'every line is valid JSON')
check(max(n for n, _ in rows) <= 96, 'pace held with queued replies')

# pictures and streams never mix: both orders
pic = ['F 1002', 'xbm 0 0 128 64 ' + (bytes([0x55, 0x00] * 8) * 64).hex(), 'E']
for order in ('pet first', 'mesh first'):
    if order == 'pet first':
        script = base + ['T 900', 'RX nova pet\\n', 'T 1000'] + pic + ['T 1005', 'RX nova mesh\\n'] + ticks(1010, 120)
    else:
        script = base + ['T 900', 'RX nova mesh\\n', 'T 1000', 'RX nova pet\\n', 'T 1001'] + pic + ticks(1010, 120)
    rows = run(script)
    ls = lines_of(text(rows))
    kinds = sorted(dispatch(l) for l in ls)
    check(kinds == ['frame', 'mesh', 'pet'], '%s: a picture, a mesh line and a frame, each whole: %s' % (order, kinds))
    for l in ls: json.loads(l)
    check(max(n for n, _ in rows) <= 96, '%s: pace held' % order)
print('queued replies, contacts and pictures wait for a line to finish: no two lines ever mix')

# nova battery / nova status
rows = run(['SUP 1', 'BAT 3900 0', 'RX nova battery\\n', 'T 10'])
check(text(rows) == '{"nova_ok":"battery","mv":3900,"pct":66,"chg":0}\n' and dispatch(text(rows)) == 'reply', 'nova battery reply: %r' % text(rows))
rows = run(['SUP 1', 'RX nova battery\\n', 'T 10'])
check(text(rows) == '{"nova_error":"battery_no_reading"}\n', 'no reading yet: an error line, not a made-up number: %r' % text(rows))
rows = run(base + ['RX nova status\\n'] + ticks(1000, 8) + ['RX nova status\\n'] + ticks(1500, 8) + ['RX nova status\\n'] + ticks(2100, 8))
per = [lines_of(text(rows[i * 8:(i + 1) * 8])) for i in range(3)]
check([[dispatch(l) for l in p] for p in per] == [['frame'], [], ['frame']], 'nova status: a frame, nothing within a second, a frame again after it')
print('nova battery: one reply (or an honest error); nova status: a frame at most once a second')

# messages sent: delivered on the ack, failed after the estimated time and the 3 s of grace
rows = run(base + ['ACK 1', 'T 1000', 'RX nova status\\n'] + ticks(1010, 8) + ['SENT Bob 2 1000', 'T 6000', 'T 9000', 'RX nova status\\n'] + ticks(9100, 8))
f1 = json.loads(lines_of(text(rows[1:9]))[0])['dl']
f2 = json.loads(lines_of(text(rows[11:]))[0])['dl']
check(f1['ok'] == 1 and f1['list'][0]['st'] == 'delivered', 'ack: delivered: %s' % f1)
check(f2['sent'] == 2 and f2['fail'] == 1 and [x['who'] + ':' + x['st'] for x in f2['list']] == ['Bob:failed', 'Alice:delivered'], 'no ack in time: failed: %s' % f2)
print('messages sent: delivered on the ack, failed without one, newest first')

# battery history: one point per 150 s; the page's chart reads hist in mV, oldest first
rows = run(['SUP 1', 'BAT 4000 0', 'T 100', 'BAT 3995 0', 'T 60000', 'T 160000', 'BAT 3990 0', 'RX nova mesh\\n'] + ticks(160010, 14))
fr = [json.loads(l) for l in lines_of(text(rows)) if dispatch(l) == 'frame'][0]
check(fr['bat']['hist'] == [4000, 3990] and fr['bat']['mv'] == 3990, 'history: %s' % fr['bat'])
print('battery: history one point per 150 s, current reading always the latest')

# ---- c. the dashboard's own decoder ---------------------------------------------------------------------------
html = os.environ.get('NOVA_DASHBOARD_HTML') or ('/tmp/nova-name-fix/docs/index.html' if Path('/tmp/nova-name-fix/docs/index.html').exists() else '')
if html and shutil.which('node'):
    src = Path(html).read_text()
    m = re.search(r'^function onMeshLine\(line\) \{.*?^\}', src, re.S | re.M)
    check(m is not None, 'onMeshLine not found in the dashboard page')
    js = r'''
const N = (v) => (typeof v === "number" && isFinite(v) ? v : (+v || 0));
const $ = () => ({ hidden: true });
const PC = { dx: true }; const pcCap = () => true;
const MESH = { recs: [], nf: [], cfg: {}, dirty: false };
''' + m.group(0) + r'''
const fs = require("fs");
for (const l of fs.readFileSync(0, "utf8").split("\n")) if (l) onMeshLine(l);
console.log(JSON.stringify({ recs: MESH.recs, cfg: MESH.cfg, rx: MESH.rxTotal, tx: MESH.txTotal, nf: MESH.nf.length, ty: MESH.ty.length }));
'''
    rows = run(base + ['RX nova mesh\\n'] + ticks(1000, 20))
    meshline = [l for l in lines_of(text(rows)) if dispatch(l) == 'mesh'][0]
    p = subprocess.run(['node', '-e', js], input=meshline, capture_output=True, text=True, timeout=60)
    check(p.returncode == 0, 'node failed: ' + p.stderr)
    r = json.loads(p.stdout)
    check(r['cfg'] == {'sf': 10, 'bw': 250, 'cr': 5} and r['rx'] == 3 and r['tx'] == 0 and r['ty'] == 16 and len(r['recs']) == 3, 'the page read the mesh line: %s' % r)
    check([x['id'] for x in r['recs']] == ['66', '66', '21'] and all(x['tx'] is False and x['type'] == 2 and x['hops'] == 1 for x in r['recs']), 'records as the page decodes them: %s' % r['recs'])
    print('the dashboard page\'s own onMeshLine decodes the radio\'s mesh line (records, settings, counters)')
else:
    print('(dashboard page or node not available: the decoder run was skipped)')

shutil.rmtree(work, ignore_errors=True)
print('check_nova_streams: all checks passed')
