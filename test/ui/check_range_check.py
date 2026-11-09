#!/usr/bin/env python3
"""Range Check: one press asks nearby repeaters, the page says GOOD / OK / WEAK / NONE.

python3 test/ui/check_range_check.py (Python 3 and g++). No radio, no screen, no
flash. Three parts:
  1. LoRaFishRangeCheck.h on its own: grading, the listening window, the
     cooldown, tags, clock wrap-around.
  2. The real UITask.cpp functions (select handler, probe sender, reply hook,
     Range Check page) against a mock mesh: the probe is the stock zero-hop
     discover control packet; no reply -> NONE, weak -> WEAK, good -> GOOD, a late
     reply is ignored; text stays inside the screen at three colour sizes.
  3. Monochrome / e-ink: the select does nothing, nothing is sent, and the real
     RF Monitor page draws exactly what it drew before this change.
"""
from pathlib import Path
import re, subprocess, tempfile

root = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------- part 1
unit = r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include "examples/companion_radio/ui-new/LoRaFishRangeCheck.h"
using namespace LoRaFishRangeCheck;
static int q(double db) { return (int)(db * 4); }
int main() {
  // Grading: the weaker of RSSI and the two SNRs decides.
  assert(grade(-80, q(8), q(9)) == Verdict::Good);
  assert(grade(-100, q(4), q(4)) == Verdict::Good);       // edge is inclusive
  assert(grade(-101, q(8), q(8)) == Verdict::Ok);         // quiet signal
  assert(grade(-80, q(3.75), q(8)) == Verdict::Ok);       // our side hears them poorly
  assert(grade(-80, q(8), q(3.75)) == Verdict::Ok);       // they hear us poorly
  assert(grade(-112, q(-3), q(-3)) == Verdict::Ok);
  assert(grade(-113, q(8), q(8)) == Verdict::Weak);
  assert(grade(-80, q(-3.25), q(8)) == Verdict::Weak);
  assert(grade(-120, q(-12), q(-12)) == Verdict::Weak);   // heard at all, so never NONE
  assert(!strcmp(word(Verdict::None), "NONE") && !strcmp(word(Verdict::Weak), "WEAK"));
  assert(!strcmp(word(Verdict::Ok), "OK") && !strcmp(word(Verdict::Good), "GOOD"));

  // Idle until the first probe.
  Session s;
  assert(s.state(1000) == State::Idle && s.canStart(0) && s.replies() == 0);
  assert(!s.onReply(1000, 7, -80, 40, 40));               // no probe sent: ignored

  // No reply -> listening, then NONE.
  s.start(5000, 0xABCD);
  assert(s.state(5000) == State::Listening && s.secondsLeft(5000) == 10);
  assert(s.state(14999) == State::Listening && s.secondsLeft(14999) == 1);
  assert(s.state(15000) == State::Done && s.verdict() == Verdict::None && s.replies() == 0);

  // Weak reply -> WEAK.
  s.start(100000, 11); assert(s.onReply(101000, 11, -118, q(-8), q(-8)));
  assert(s.state(111000) == State::Done && s.verdict() == Verdict::Weak && s.replies() == 1);
  // OK reply -> OK.
  s.start(200000, 12); assert(s.onReply(201000, 12, -105, q(0), q(2))); assert(s.verdict() == Verdict::Ok);
  // Good reply -> GOOD, and the page can show what it heard.
  s.start(300000, 13); assert(s.onReply(300500, 13, -85, q(9), q(7.5))); assert(s.verdict() == Verdict::Good);
  assert(s.bestRssiDbm() == -85 && s.bestSnrQuarterDb() == q(7.5));
  // Several repeaters: the best one counts, the count is kept, a worse later reply does not demote.
  s.start(400000, 14);
  assert(s.onReply(400800, 14, -118, q(-8), q(-8)) && s.verdict() == Verdict::Weak);
  assert(s.onReply(401500, 14, -90, q(6), q(6)) && s.verdict() == Verdict::Good);
  assert(s.onReply(402500, 14, -119, q(-9), q(-9)) && s.verdict() == Verdict::Good && s.replies() == 3);
  assert(s.bestRssiDbm() == -90);

  // The window expires: a late reply is ignored and the verdict stays NONE.
  s.start(500000, 15);
  assert(!s.onReply(510000, 15, -80, q(9), q(9)));
  assert(s.state(510000) == State::Done && s.verdict() == Verdict::None && s.replies() == 0);
  assert(s.onReply(509999, 15, -80, q(9), q(9)));         // last millisecond still counts
  // A reply to somebody else's probe (other tag) or to an older probe is ignored.
  s.start(600000, 16);
  assert(!s.onReply(600100, 99, -80, q(9), q(9)) && s.replies() == 0);
  s.start(700000, 17);
  assert(!s.onReply(700100, 16, -80, q(9), q(9)) && s.replies() == 0);   // the old probe's tag
  assert(s.onReply(700100, 17, -80, q(9), q(9)));

  // Cooldown between probes (airtime courtesy): 20 s from the previous probe.
  s.start(800000, 18);
  assert(!s.canStart(800000) && s.waitSeconds(800000) == 20);
  assert(!s.canStart(815000) && s.waitSeconds(815000) == 5);
  assert(!s.canStart(819999) && s.waitSeconds(819999) == 1);
  assert(s.canStart(820000) && s.waitSeconds(820000) == 0);
  // A new probe wipes the old result.
  s.start(820000, 19); assert(s.replies() == 0 && s.verdict() == Verdict::None);

  // The 32-bit millisecond clock wrapping round does not break the window or cooldown.
  uint32_t near = 0xFFFFFFFFu - 4000;
  s.start(near, 20);
  assert(s.state(near + 8000) == State::Listening);       // wrapped to ~4000
  assert(s.onReply(near + 8000, 20, -80, q(9), q(9)));
  assert(s.state(near + 10001) == State::Done && !s.canStart(near + 10001) && s.canStart(near + 20000));
  // A clock slightly behind the send time (a frame that began just before the press) is not 'expired'.
  s.start(50000, 22); assert(s.state(49990) == State::Listening && s.onReply(49990, 22, -80, q(9), q(9)));
  // The reply counter saturates rather than wrapping to zero.
  s.start(1000, 21); for (int i = 0; i < 300; ++i) s.onReply(1001, 21, -80, q(9), q(9));
  assert(s.replies() == 255);
  puts("PASS grading, window, cooldown, tags, wrap-around");
  return 0;
}
'''

# ---------------------------------------------------------------- parts 2 and 3
head_path = root / 'test/ui/check_native_pages.py'
head = head_path.read_text()
head = head[:head.index("code+=block('static int loRaFishBatteryPercent(')")]
ns = {'__file__': str(head_path), '__name__': 'native_pages_head'}
exec(compile(head, 'check_native_pages_head', 'exec'), ns)
prelude, block = ns['code'], ns['block']
source = (root / 'examples/companion_radio/ui-new/UITask.cpp').read_text()
legacy = (root / 'test/ui/legacy_battery_pages.inc').read_text()
page_no = int(re.search(r'LORAFISH_RANGE_PAGE=(\d+);', source).group(1))
assert page_no not in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20), 'page number clash'

# The stock Discovery page sends the same 6-byte probe; ours differs only in the filter (repeaters only).
assert source.count('CTL_TYPE_NODE_DISCOVER_REQ | 1') == 2
assert 'the_mesh.sendZeroHop(req)' in source and 'the_mesh.createControlData(cmd, sizeof(cmd))' in source
# Every use of the probe is behind the colour guard; the RF page hint too.
assert 'if (!loRaFishColorDisplay || (loRaFishPage != 6 && loRaFishPage != LORAFISH_RANGE_PAGE)) return 0;' in source
assert 'if (loRaFishColorDisplay) {  // colour screens only' in source

mocks = r'''
#include <cstring>
#include <cstdlib>
#define CTL_TYPE_NODE_DISCOVER_REQ 0x80
#define CTL_TYPE_NODE_DISCOVER_RESP 0x90
#define ADV_TYPE_REPEATER 2
#define PAYLOAD_TYPE_CONTROL 0x0B
#ifndef LORAFISH_UI
#define LORAFISH_UI 1
#endif
namespace mesh { struct Packet { uint8_t header = 0; uint16_t payload_len = 0; uint8_t payload[184] = {}; }; }
struct MockRNG { uint32_t next = 0x11223344u; void random(uint8_t* d, int n) { memcpy(d, &next, n); next += 0x01010101u; } };
struct MockMesh {
  uint32_t pin = 0; uint32_t getBLEPin() { return pin; }
  MockRNG rng; MockRNG* getRNG() { return &rng; }
  std::vector<std::vector<uint8_t>> sent; std::vector<int> sentTypes; bool poolEmpty = false;
  mesh::Packet* createControlData(const uint8_t* d, size_t n) {
    if (poolEmpty) return nullptr;
    auto* p = new mesh::Packet; p->header = PAYLOAD_TYPE_CONTROL << 2; p->payload_len = n; memcpy(p->payload, d, n); return p;
  }
  void sendZeroHop(mesh::Packet* p) {
    sent.emplace_back(p->payload, p->payload + p->payload_len); sentTypes.push_back((p->header >> 2) & 15); delete p;
  }
} the_mesh;
static uint8_t loRaFishPage = 6;
static constexpr uint8_t LORAFISH_RANGE_PAGE = %d;
ColorVal UIColor::warning_txt = 3;
#include "examples/companion_radio/ui-new/LoRaFishRangeCheck.h"
''' % page_no

native_mock_old = 'struct {uint32_t pin=0;uint32_t getBLEPin(){return pin;}}the_mesh;'
assert native_mock_old in prelude
base = prelude.replace(native_mock_old, '')       # replaced by MockMesh above
real_fns = '\n'.join(block(m) for m in [
    'static void drawLoRaFishHeader(', 'static void drawLoRaFishRFMonitor(',
])
range_fns = '\n'.join([
    'static LoRaFishRangeCheck::Session loRaFishRange;',
    block('static bool sendLoRaFishRangeProbe('), block('static uint8_t selectLoRaFishRange('),
    block('static void noteLoRaFishRangeReply('), block('static void drawLoRaFishRangeCheck('),
])
battery_bits = block('static int loRaFishBatteryPercent(') + '\nstatic LoRaFishBattery::Tracker loRaFishBatteryTracker;\n' + block('static void drawLoRaFishBatteryLeft(')

scenario = r'''
static mesh::Packet reply(uint32_t tag, int snrOutQ) {
  mesh::Packet p; p.payload_len = 14; p.payload[0] = CTL_TYPE_NODE_DISCOVER_RESP | ADV_TYPE_REPEATER;
  p.payload[1] = (uint8_t)(int8_t)snrOutQ; memcpy(&p.payload[2], &tag, 4); return p;
}
static uint32_t lastTag() { uint32_t t; memcpy(&t, &the_mesh.sent.back()[2], 4); return t; }
static std::string page(int w, int h, UITask& task, Recorder** keep = nullptr) {
  Recorder out(w, h); LoRaFishLayout::Page card(out); drawLoRaFishRangeCheck(card, &task);
  std::string all; for (auto& s : out.printed) all += s + "|"; return all;
}
static bool shows(const std::string& all, const char* word) { return all.find(std::string("|") + word + "|") != std::string::npos || all.rfind(std::string(word) + "|", 0) == 0; }
'''

colour_main = r'''
int main() {
  UITask task; loRaFishColorDisplay = true;
  for (auto dims : {std::pair<int,int>{320,170}, {320,240}, {240,135}}) {
    const int W = dims.first, H = dims.second;
    the_mesh.sent.clear(); the_mesh.sentTypes.clear(); the_mesh.rng.next = 0x11223344u;
    loRaFishRange = LoRaFishRangeCheck::Session(); now = 100000; loRaFishPage = 6; the_mesh.poolEmpty = false;
    uint32_t wait = 99;
    // Before any press the page just says READY (and never claims a verdict).
    { auto s = page(W, H, task); assert(shows(s, "READY")); }
    // One press on the RF Monitor page: opens the Range Check page and sends exactly one probe.
    assert(selectLoRaFishRange(now, wait) == 1 && loRaFishPage == LORAFISH_RANGE_PAGE && wait == 99);
    assert(the_mesh.sent.size() == 1 && the_mesh.sentTypes[0] == PAYLOAD_TYPE_CONTROL);   // an ordinary control packet
    auto& p = the_mesh.sent[0];
    assert(p.size() == 6 && p[0] == (CTL_TYPE_NODE_DISCOVER_REQ | 1) && p[1] == (1 << ADV_TYPE_REPEATER));
    { auto s = page(W, H, task); assert(shows(s, "CHECKING")); }

    // --- NONE: nobody answers
    now += 9999; { auto s = page(W, H, task); assert(shows(s, "CHECKING")); }
    now += 1;    { auto s = page(W, H, task); assert(shows(s, "NONE") && s.find("No repeater answered") != std::string::npos); }

    // --- WEAK
    auto fresh = [&]() { now += 20000; wait = 0; assert(selectLoRaFishRange(now, wait) == 1); return lastTag(); };
    uint32_t tag = fresh();
    lorafish_last_rssi = -118; lorafish_last_snr = -8; now += 1500;
    { mesh::Packet r = reply(tag, -8 * 4); noteLoRaFishRangeReply(&r); }
    { auto s = page(W, H, task); assert(shows(s, "CHECKING") && s.find("heard 1") != std::string::npos); }
    now += 9000; { auto s = page(W, H, task); assert(shows(s, "WEAK") && s.find("1 repeater answered") != std::string::npos); }

    // --- OK
    tag = fresh(); lorafish_last_rssi = -105; lorafish_last_snr = 0.5f; now += 1000;
    { mesh::Packet r = reply(tag, 2 * 4); noteLoRaFishRangeReply(&r); }
    now += 10000; { auto s = page(W, H, task); assert(shows(s, "OK") && !shows(s, "GOOD") && !shows(s, "WEAK")); }

    // --- GOOD, two repeaters; shows the best link
    tag = fresh(); lorafish_last_rssi = -118; lorafish_last_snr = -8; now += 800;
    { mesh::Packet r = reply(tag, -8 * 4); noteLoRaFishRangeReply(&r); }
    lorafish_last_rssi = -88; lorafish_last_snr = 7.5f; now += 700;
    { mesh::Packet r = reply(tag, 6 * 4); noteLoRaFishRangeReply(&r); }
    now += 10000; { auto s = page(W, H, task); assert(shows(s, "GOOD") && s.find("2 repeaters answered") != std::string::npos);
                    assert(s.find("Best RSSI -88  SNR 6.0") != std::string::npos); }

    // --- the window expires: a reply after 10 s changes nothing
    tag = fresh(); now += 10000; lorafish_last_rssi = -80; lorafish_last_snr = 9;
    { mesh::Packet r = reply(tag, 9 * 4); noteLoRaFishRangeReply(&r); }
    { auto s = page(W, H, task); assert(shows(s, "NONE")); }
    // --- someone else's reply (another tag), and non-reply control packets, are ignored
    tag = fresh(); now += 500;
    { mesh::Packet r = reply(tag ^ 0xFFu, 9 * 4); noteLoRaFishRangeReply(&r); }
    { mesh::Packet r = reply(tag, 9 * 4); r.payload[0] = CTL_TYPE_NODE_DISCOVER_REQ | ADV_TYPE_REPEATER; noteLoRaFishRangeReply(&r); }
    { mesh::Packet r = reply(tag, 9 * 4); r.payload_len = 13; noteLoRaFishRangeReply(&r); }
    now += 10000; { auto s = page(W, H, task); assert(shows(s, "NONE")); }

    // --- another press too soon: no second packet, the page says how long to wait
    size_t sentBefore = the_mesh.sent.size();
    now += 1500; assert(selectLoRaFishRange(now, wait) == 2 && wait == 8 && the_mesh.sent.size() == sentBefore);   // 12 s after the last probe
    now += 15000; assert(selectLoRaFishRange(now, wait) == 1 && the_mesh.sent.size() == sentBefore + 1);
    // --- the radio cannot queue it: reported, nothing counted
    now += 20000; the_mesh.poolEmpty = true; assert(selectLoRaFishRange(now, wait) == 3 && the_mesh.sent.size() == sentBefore + 1);
    the_mesh.poolEmpty = false;
    // --- Select on other pages is not ours
    for (int pg : {0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20}) {
      loRaFishPage = pg; size_t n = the_mesh.sent.size();
      assert(selectLoRaFishRange(now + 100000, wait) == 0 && loRaFishPage == pg && the_mesh.sent.size() == n);
    }
    // --- the RF Monitor page shows the hint on colour, and still draws inside the screen
    battery = 4000; lorafish_last_rf_ms = 1234; ++lorafish_rf_sample_seq; loRaFishRfHistoryCount = 0;
    { Recorder out(W, H); LoRaFishLayout::Page card(out); drawLoRaFishRFMonitor(card, &task); assert(out.has("L:RANGE CHECK")); }
  }
  puts("PASS colour: one press probes once, NONE / WEAK / OK / GOOD, window expiry, tags, cooldown, text inside 320x170 / 320x240 / 240x135");
  return 0;
}
'''

mono_main = r'''
static void sweep(UITask& task) {
  for (int mv = 0; mv <= 4400; mv += (mv > 3200 && mv < 4300) ? 10 : 400) {
    battery = (uint16_t)mv;
    for (unsigned age : {0u, 1234u}) {
      lorafish_last_rf_ms = age; ++lorafish_rf_sample_seq; loRaFishRfHistoryCount = 0;
      Recorder out(320, 170); LoRaFishLayout::Page card(out); drawLoRaFishRFMonitor(card, &task);
      printf("RF %d:", mv);
      for (auto& s : out.shapes) printf(" [%d,%d,%d,%d,%d]", s.x, s.y, s.w, s.h, (int)s.outline);
      for (auto& p : out.printed) printf(" {%s}", p.c_str());
      printf("\n");
      Recorder small(128, 64); drawLoRaFishRFMonitor(small, &task);
      printf("RF64 %d:", mv);
      for (auto& s : small.shapes) printf(" [%d,%d,%d,%d,%d]", s.x, s.y, s.w, s.h, (int)s.outline);
      for (auto& p : small.printed) printf(" {%s}", p.c_str());
      printf("\n");
    }
  }
}
int main() {
  UITask task; loRaFishColorDisplay = false;
  sweep(task);
  // Select does nothing on a monochrome / e-ink screen, on the RF page or any other.
  uint32_t wait = 0;
  for (int pg = 0; pg < 21; ++pg) {
    loRaFishPage = pg;
    assert(selectLoRaFishRange(now, wait) == 0 && loRaFishPage == pg && the_mesh.sent.empty());
  }
  // A stray reply with no probe sent is ignored.
  mesh::Packet r = reply(5, 36); noteLoRaFishRangeReply(&r); assert(loRaFishRange.replies() == 0);
  return 0;
}
'''
legacy_main = r'''
static void sweep(UITask& task) {
  for (int mv = 0; mv <= 4400; mv += (mv > 3200 && mv < 4300) ? 10 : 400) {
    battery = (uint16_t)mv;
    for (unsigned age : {0u, 1234u}) {
      lorafish_last_rf_ms = age; ++lorafish_rf_sample_seq; loRaFishRfHistoryCount = 0;
      Recorder out(320, 170); LoRaFishLayout::Page card(out); drawLoRaFishRFMonitor(card, &task);
      printf("RF %d:", mv);
      for (auto& s : out.shapes) printf(" [%d,%d,%d,%d,%d]", s.x, s.y, s.w, s.h, (int)s.outline);
      for (auto& p : out.printed) printf(" {%s}", p.c_str());
      printf("\n");
      Recorder small(128, 64); drawLoRaFishRFMonitor(small, &task);
      printf("RF64 %d:", mv);
      for (auto& s : small.shapes) printf(" [%d,%d,%d,%d,%d]", s.x, s.y, s.w, s.h, (int)s.outline);
      for (auto& p : small.printed) printf(" {%s}", p.c_str());
      printf("\n");
    }
  }
}
int main() { UITask task; sweep(task); return 0; }
'''

new_prog_common = base + mocks + battery_bits + '\n' + real_fns + '\n' + range_fns + '\n' + scenario
colour_prog = new_prog_common + colour_main
mono_prog = new_prog_common + mono_main

def build(prog, tmp, name, flags):
    cpp = tmp / (name + '.cpp'); cpp.write_text(prog); exe = tmp / name
    subprocess.run(['g++', '-std=c++17', '-DLORAGOTCHI_NATIVE_UI=1', '-I' + str(root), '-I' + str(root / 'src')] + flags + [str(cpp), '-o', str(exe)], check=True)
    return exe

def run(exe):
    r = subprocess.run([str(exe)], capture_output=True, text=True)
    if r.returncode: raise SystemExit('FAILED %s:\n%s%s' % (exe.name, r.stdout[-600:], r.stderr[-1200:]))
    return r.stdout

with tempfile.TemporaryDirectory(prefix='lrx-range-') as t:
    tmp = Path(t)
    (tmp / 'unit.cpp').write_text(unit)
    subprocess.run(['g++', '-std=c++17', '-Wall', '-I' + str(root), str(tmp / 'unit.cpp'), '-o', str(tmp / 'unit')], check=True)
    print(subprocess.run([str(tmp / 'unit')], check=True, capture_output=True, text=True).stdout.strip())

    for flags in ([], ['-DLILYGO_TDECK=1'], ['-DLORAGOTCHI_SPECIES_EDITION=1']):
        label = ' '.join(flags) or 'default'
        print(run(build(colour_prog, tmp, 'colour', flags)).strip(), '[%s]' % label)

        # Mono: new RF Monitor page vs the frozen pre-battery page that is kept in test/ui/legacy_battery_pages.inc.
        legacy_prog = prelude + block('static void drawLoRaFishHeader(') + '\n' + legacy + '\n' + legacy_main
        old = run(build(legacy_prog, tmp, 'old', flags))
        mono = run(build(mono_prog, tmp, 'mono', flags))
        assert old.count('\n') > 200
        if old != mono:
            for x, y in zip(old.splitlines(), mono.splitlines()):
                if x != y: raise SystemExit('MONO CHANGED (%s):\n old %s\n new %s' % (label, x, y))
            raise SystemExit('MONO CHANGED (line count)')
        print('PASS monochrome/e-ink: RF Monitor drawn identically over %d drawings, Select does nothing, nothing is sent [%s]' % (old.count('\n'), label))
    # Touch watch: its own navigation is left alone, so the select never claims a press even on colour.
    watch = build(mono_prog.replace('loRaFishColorDisplay = false;', 'loRaFishColorDisplay = true;'), tmp, 'watch', ['-DLORAFISH_WATCH_TOUCH=1'])
    run(watch)
    print('PASS touch watch: Range Check stays out of the way (Select never claimed, nothing sent)')
