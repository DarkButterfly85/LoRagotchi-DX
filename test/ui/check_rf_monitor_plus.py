#!/usr/bin/env python3
"""RF Monitor+: what kinds of packets the pet heard (last ~5 minutes) and how far they travelled.

python3 test/ui/check_rf_monitor_plus.py (Python 3 and g++). No radio, no screen,
no flash. Four parts:
  1. LoRaFishRfStats.h on its own: reading a frame header, counts per type,
     average hops, the five-minute window rolling over, clock wrap-around.
  2. The real MyMesh::logRxRaw: it still does everything it did before (last
     RSSI/SNR, sample counter, the push frame to the phone) and additionally counts.
  3. Colour: the real RF Monitor page shows the counts and hops, and they fall
     off when the window rolls over; text stays inside 320x170 / 320x240 / 240x135.
  4. Monochrome / e-ink: the real RF Monitor page draws exactly what it drew
     before this change, even with packets counted.
"""
from pathlib import Path
import subprocess, tempfile

root = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------- part 1
unit = r'''
#include <cassert>
#include <cstdio>
#include <vector>
#include "examples/companion_radio/LoRaFishRfStats.h"
using namespace LoRaFishRfStats;
static const uint32_t MIN = 60000UL;

// A raw frame: header, optional transport codes, path length byte, path, payload.
static std::vector<uint8_t> frame(uint8_t route, uint8_t type, int hops, int hashSize = 1, int payload = 5) {
  std::vector<uint8_t> f; f.push_back((uint8_t)((type << 2) | route));
  if (route == 0 || route == 3) for (int i = 0; i < 4; ++i) f.push_back(0xAA);
  f.push_back((uint8_t)(((hashSize - 1) << 6) | hops));
  for (int i = 0; i < hops * hashSize; ++i) f.push_back(0x11);
  for (int i = 0; i < payload; ++i) f.push_back(0x22);
  return f;
}
static void rec(Window& w, uint32_t t, uint8_t route, uint8_t type, int hops, int hashSize = 1) {
  auto f = frame(route, type, hops, hashSize); w.record(t, f.data(), (int)f.size());
}

int main() {
  // Reading a header.
  { auto f = frame(1, 4, 2); Frame x = parse(f.data(), (int)f.size());
    assert(x.ok && x.group == Adv && x.flood && x.hops == 2); }
  { auto f = frame(0, 5, 3); Frame x = parse(f.data(), (int)f.size());       // transport flood: skips 4 code bytes
    assert(x.ok && x.group == Chan && x.flood && x.hops == 3); }
  { auto f = frame(2, 3, 1); Frame x = parse(f.data(), (int)f.size());       // direct: counted, but not a "travelled" number
    assert(x.ok && x.group == Ack && !x.flood); }
  { auto f = frame(3, 2, 0); Frame x = parse(f.data(), (int)f.size()); assert(x.ok && x.group == Dm && !x.flood); }
  { auto f = frame(1, 4, 2, 2); Frame x = parse(f.data(), (int)f.size());    // 2-byte path hashes: hops still the count
    assert(x.ok && x.hops == 2); }
  // Rubbish and truncated frames are ignored, never counted, never crash.
  assert(!parse(nullptr, 10).ok);
  { uint8_t two[2] = {0x11, 0}; assert(!parse(two, 2).ok); }
  { auto f = frame(1, 4, 3); assert(!parse(f.data(), (int)f.size() - 6).ok); }   // path cut short
  { auto f = frame(1, 4, 3, 1, 0); assert(!parse(f.data(), (int)f.size()).ok); }  // no payload at all
  { auto f = frame(0, 4, 0); assert(!parse(f.data(), 3).ok); }                    // transport codes cut short
  { auto f = frame(1, 4, 0); f[1] = 0xC0; assert(!parse(f.data(), (int)f.size()).ok); }  // 4-byte hashes: not valid
  // Every payload type lands in exactly one group.
  { const Group want[16] = {Req, Req, Dm, Ack, Adv, Chan, Chan, Req, Req, Other, Ack, Other, Other, Other, Other, Other};
    for (int t = 0; t < 16; ++t) assert(groupOf((uint8_t)t) == want[t]); }
  assert(!strcmp(label(Adv), "ADV") && !strcmp(label(Dm), "DM") && !strcmp(label(Chan), "CHAN"));
  assert(!strcmp(label(Ack), "ACK") && !strcmp(label(Req), "REQ") && !strcmp(label(Other), "OTHER"));

  // Counts per type, and the hops of flood packets.
  { Window w; uint32_t t = 1000;
    assert(w.total(t) == 0 && w.averageHopsTenths(t, Adv) == -1);
    for (int i = 0; i < 5; ++i) rec(w, t, 1, 4, 0);
    for (int i = 0; i < 4; ++i) rec(w, t, 1, 4, 1);
    for (int i = 0; i < 3; ++i) rec(w, t, 0, 4, 2);                          // transport flood counts too
    for (int i = 0; i < 4; ++i) rec(w, t, 1, 2, 3);
    rec(w, t, 1, 5, 1); rec(w, t, 1, 6, 1);
    rec(w, t, 2, 3, 2); rec(w, t, 3, 3, 1);                                  // direct ACKs
    rec(w, t, 1, 9, 0);
    assert(w.count(t, Adv) == 12 && w.count(t, Dm) == 4 && w.count(t, Chan) == 2);
    assert(w.count(t, Ack) == 2 && w.count(t, Req) == 0 && w.count(t, Other) == 1 && w.total(t) == 21);
    assert(w.averageHopsTenths(t, Adv) == 8);                                // (0*5+1*4+2*3)/12 = 0.83 -> 0.8
    assert(w.averageHopsTenths(t, Dm) == 30 && w.averageHopsTenths(t, Chan) == 10);
    assert(w.averageHopsTenths(t, Ack) == -1);                               // direct only: no hop number
    assert(w.averageHopsTenths(t, Req) == -1 && w.count(t, 99) == 0 && w.averageHopsTenths(t, 99) == -1);
    assert(w.averageHopsTenths(t, Other) == 0);                              // heard straight from the sender
    uint8_t junk[2] = {1, 2}; w.record(t, junk, 2); w.record(t, nullptr, 0); assert(w.total(t) == 21);
  }
  // Rounding: 1+2 hops over 2 packets = 1.5.
  { Window w; rec(w, 0, 1, 4, 1); rec(w, 0, 1, 4, 2); assert(w.averageHopsTenths(0, Adv) == 15); }

  // The window rolls over: only the last five minute-buckets count.
  { Window w;
    rec(w, 0, 1, 4, 1);                                  // minute 0
    rec(w, 200 * 1000UL, 1, 5, 1);                       // minute 3
    assert(w.count(200 * 1000UL, Adv) == 1 && w.count(200 * 1000UL, Chan) == 1);
    assert(w.count(5 * MIN - 1, Adv) == 1);              // still inside 5 minutes of the first packet
    assert(w.count(5 * MIN, Adv) == 0);                  // minute 0 has rolled off ...
    assert(w.count(5 * MIN, Chan) == 1);                 // ... minute 3 has not
    assert(w.count(7 * MIN, Chan) == 1);                 // a bucket lives 4 to 5 minutes, so minute 3 is still there at minute 7
    assert(w.count(8 * MIN, Chan) == 0 && w.total(8 * MIN) == 0);
    // New packets after a long silence start fresh.
    rec(w, 100 * MIN, 1, 4, 0); assert(w.count(100 * MIN, Adv) == 1 && w.total(100 * MIN) == 1);
    // A steady stream: after 12 minutes of 2 ADV a minute, the window holds between 8 and 10.
    Window s; for (uint32_t m = 0; m < 12; ++m) { rec(s, m * MIN + 100, 1, 4, 0); rec(s, m * MIN + 30000, 1, 4, 0); }
    uint32_t now = 11 * MIN + 30000; assert(s.count(now, Adv) >= 8 && s.count(now, Adv) <= 10);
    // Hops roll off with their packets.
    Window h; rec(h, 0, 1, 4, 3); rec(h, 4 * MIN + 10, 1, 4, 1);
    assert(h.averageHopsTenths(4 * MIN + 10, Adv) == 20);
    assert(h.averageHopsTenths(5 * MIN, Adv) == 10);
    // A reader slightly behind the radio's last write does not wipe the window.
    Window b; rec(b, 10 * MIN + 500, 1, 4, 0); assert(b.count(10 * MIN + 400, Adv) == 1);
  }
  // The 32-bit millisecond clock wrapping round does not break the window.
  { Window w; uint32_t t0 = 0xFFFFFFFFu - 90000UL;
    rec(w, t0, 1, 4, 1); rec(w, t0 + 2 * MIN, 1, 4, 1);                      // second one is after the wrap
    assert(w.count(t0 + 2 * MIN, Adv) == 2);
    assert(w.count(t0 + 4 * MIN + 59999, Adv) == 1 || w.count(t0 + 4 * MIN + 59999, Adv) == 2);
    assert(w.count(t0 + 6 * MIN, Adv) == 0 || w.count(t0 + 6 * MIN, Adv) == 1);
    assert(w.count(t0 + 8 * MIN, Adv) == 0);
  }
  // Counts saturate instead of wrapping.
  { Window w; for (int i = 0; i < 70000; ++i) rec(w, 5, 1, 4, 0); assert(w.count(5, Adv) == 65535); }
  printf("PASS frame reading, counts per type, hops, window roll-over, wrap-around, saturation\n");
  return 0;
}
'''

# ---------------------------------------------------------------- part 2: the real receive hook
mymesh = (root / 'examples/companion_radio/MyMesh.cpp').read_text()
def block_of(text, marker):
    a = text.index(marker); i = text.index('{', a); j = i + 1; depth = 1
    while depth: depth += (text[j] == '{') - (text[j] == '}'); j += 1
    return text[a:j]
hook = block_of(mymesh, 'void MyMesh::logRxRaw(')
assert 'lorafish_rf_stats.record(millis(), raw, len);' in hook
# Reception is untouched: the hook only gained that one line.
assert hook.count('\n') <= 18, 'logRxRaw grew more than expected'
hook_prog = r'''
#include <cassert>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <vector>
#include "examples/companion_radio/LoRaFishRfStats.h"
float lorafish_last_rssi = -127.0f, lorafish_last_snr = 0.0f; unsigned long lorafish_last_rf_ms = 0; uint32_t lorafish_rf_sample_seq = 0;
LoRaFishRfStats::Window lorafish_rf_stats;
static unsigned long g_ms = 1000; static unsigned long millis() { return g_ms; }
#define MAX_FRAME_SIZE 172
#define PUSH_CODE_LOG_RX_DATA 0x88
struct Link { bool up = false; std::vector<std::vector<uint8_t>> frames; bool isConnected() { return up; } void writeFrame(const uint8_t* d, int n) { frames.emplace_back(d, d + n); } };
struct MyMesh { Link* _serial; uint8_t out_frame[MAX_FRAME_SIZE]; void logRxRaw(float snr, float rssi, const uint8_t raw[], int len); };
''' + hook + r'''
int main() {
  Link link; MyMesh m; m._serial = &link;
  const uint8_t advert[] = {0x11, 0x02, 0xA1, 0xB2, 0xC3, 0xC4, 0xC5};      // flood ADVERT, 2 hops
  const uint8_t dmDirect[] = {0x0A, 0x00, 0x99, 0x98, 0x97};                // direct TXT_MSG
  // Phone not connected: the old things still update, and the packet is counted.
  m.logRxRaw(-3.5f, -97.0f, advert, sizeof(advert));
  assert(lorafish_last_rssi == -97.0f && lorafish_last_snr == -3.5f && lorafish_last_rf_ms == 1000 && lorafish_rf_sample_seq == 1);
  assert(lorafish_rf_stats.count(1000, LoRaFishRfStats::Adv) == 1 && lorafish_rf_stats.averageHopsTenths(1000, LoRaFishRfStats::Adv) == 20);
  assert(link.frames.empty());
  // Phone connected: exactly the same push frame as before (code, snr x4, rssi, raw bytes).
  link.up = true; g_ms = 2000;
  m.logRxRaw(6.0f, -80.0f, dmDirect, sizeof(dmDirect));
  assert(link.frames.size() == 1 && link.frames[0].size() == 3 + sizeof(dmDirect));
  assert(link.frames[0][0] == 0x88 && (int8_t)link.frames[0][1] == 24 && (int8_t)link.frames[0][2] == -80);
  assert(!memcmp(&link.frames[0][3], dmDirect, sizeof(dmDirect)));
  assert(lorafish_rf_sample_seq == 2 && lorafish_rf_stats.count(2000, LoRaFishRfStats::Dm) == 1);
  // Garbage is counted by nothing but the old counters still tick.
  const uint8_t junk[] = {0x11, 0xC5}; m.logRxRaw(1.0f, -90.0f, junk, sizeof(junk));
  assert(lorafish_rf_sample_seq == 3 && lorafish_rf_stats.total(2000) == 2);
  puts("PASS real MyMesh::logRxRaw: old behaviour intact (RSSI/SNR, sample count, phone frame) + packets counted");
  return 0;
}
'''

# ---------------------------------------------------------------- parts 3 and 4: the real page
head_path = root / 'test/ui/check_native_pages.py'
head = head_path.read_text()
head = head[:head.index("code+=block('static int loRaFishBatteryPercent(')")]
ns = {'__file__': str(head_path), '__name__': 'native_pages_head'}
exec(compile(head, 'check_native_pages_head', 'exec'), ns)
prelude, block = ns['code'], ns['block']
legacy = (root / 'test/ui/legacy_battery_pages.inc').read_text()

battery_bits = block('static int loRaFishBatteryPercent(') + '\nstatic LoRaFishBattery::Tracker loRaFishBatteryTracker;\n' + block('static void drawLoRaFishBatteryLeft(')
real = battery_bits + '\n' + block('static void drawLoRaFishHeader(') + '\n' + block('static void drawLoRaFishRfTypes(') + '\n' + block('static void drawLoRaFishRFMonitor(') + '\n'

helpers = r'''
static void feed(uint32_t t, uint8_t route, uint8_t type, int hops, int n = 1) {
  for (int i = 0; i < n; ++i) {
    uint8_t f[40]; int k = 0; f[k++] = (uint8_t)((type << 2) | route);
    if (route == 0 || route == 3) { for (int j = 0; j < 4; ++j) f[k++] = 0; }
    f[k++] = (uint8_t)hops; for (int j = 0; j < hops; ++j) f[k++] = 1; f[k++] = 7; f[k++] = 7;
    lorafish_rf_stats.record(t, f, k);
  }
}
static void load(uint32_t t) {
  feed(t, 1, 4, 0, 5); feed(t, 1, 4, 1, 4); feed(t, 1, 4, 2, 3);   // 12 ADV, 0.8 hops
  feed(t, 1, 2, 3, 4);                                              // 4 DM, 3.0 hops
  feed(t, 2, 3, 1, 2);                                              // 2 ACK, direct
  feed(t, 1, 5, 1, 1000);                                           // CHAN saturates the display at 999+
}
'''
colour_main = helpers + r'''
static std::string all(Recorder& out) { std::string s; for (auto& p : out.printed) s += p + "|"; return s; }
int main() {
  UITask task; loRaFishColorDisplay = true; battery = 3900;
  for (auto dims : {std::pair<int,int>{320,170}, {320,240}, {240,135}}) {
    const int W = dims.first, H = dims.second;
    lorafish_rf_stats = LoRaFishRfStats::Window(); now = 1000000;
    // Nothing heard yet: all zero, dashes for hops.
    { Recorder out(W, H); LoRaFishLayout::Page card(out); drawLoRaFishRFMonitor(card, &task); auto s = all(out);
      assert(out.has("RF MONITOR+ 5m") && out.has("ADV 0 h--") && out.has("DM 0 h--") && out.has("CHAN 0 h--"));
      assert(out.has("ACK 0 h--") && out.has("REQ 0 h--") && out.has("OTHER 0 h--")); }
    load(now - 1000);
    { Recorder out(W, H); LoRaFishLayout::Page card(out); drawLoRaFishRFMonitor(card, &task);
      assert(out.has("ADV 12 h0.8") && out.has("DM 4 h3.0") && out.has("ACK 2 h--") && out.has("CHAN 999+ h1.0"));
      assert(out.has("REQ 0 h--") && out.has("OTHER 0 h--"));
      assert(out.has("RF MONITOR+ 5m")); }
    // Four minutes later the counts are still there; at five they have rolled off.
    now += 4 * 60000UL - 1000; { Recorder out(W, H); LoRaFishLayout::Page card(out); drawLoRaFishRFMonitor(card, &task); assert(out.has("ADV 12 h0.8")); }
    now += 1000 + 60000UL;     { Recorder out(W, H); LoRaFishLayout::Page card(out); drawLoRaFishRFMonitor(card, &task);
                                 assert(out.has("ADV 0 h--") && !out.has("ADV 12 h0.8")); }
    // The classic parts are all still there on colour.
    { Recorder out(W, H); LoRaFishLayout::Page card(out); lorafish_last_rf_ms = 0; drawLoRaFishRFMonitor(card, &task); assert(out.has("RX --")); }
  }
  // A narrow colour screen drops the table but keeps the classic page.
  { lorafish_rf_stats = LoRaFishRfStats::Window(); load(now);
    Recorder out(150, 135); LoRaFishLayout::Page card(out); drawLoRaFishRFMonitor(card, &task);
    assert(out.has("RF MONITOR+") && !out.has("ADV 12 h0.8")); }
  puts("PASS colour: counts per type + hops on the real RF Monitor page, window rolls over, text inside 320x170 / 320x240 / 240x135");
  return 0;
}
'''
mono_main = helpers + r'''
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
  now = 1000000; load(now - 1000);          // a busy mesh is being counted ...
  now = 5000;                               // same clock as the frozen reference drawing
  sweep(task);                              // ... and the monochrome page still shows none of it
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
legacy_prog = prelude + block('static void drawLoRaFishHeader(') + '\n' + legacy + '\n' + legacy_main

def build(prog, tmp, name, flags, std=['-DLORAGOTCHI_NATIVE_UI=1']):
    cpp = tmp / (name + '.cpp'); cpp.write_text(prog); exe = tmp / name
    subprocess.run(['g++', '-std=c++17', *std, '-I' + str(root), '-I' + str(root / 'src')] + flags + [str(cpp), '-o', str(exe)], check=True)
    return exe

def run(exe):
    r = subprocess.run([str(exe)], capture_output=True, text=True)
    if r.returncode: raise SystemExit('FAILED %s:\n%s%s' % (exe.name, r.stdout[-600:], r.stderr[-1200:]))
    return r.stdout

with tempfile.TemporaryDirectory(prefix='lrx-rfplus-') as t:
    tmp = Path(t)
    (tmp / 'unit.cpp').write_text(unit)
    subprocess.run(['g++', '-std=c++17', '-Wall', '-I' + str(root), str(tmp / 'unit.cpp'), '-o', str(tmp / 'unit')], check=True)
    print(run(tmp / 'unit').strip())
    (tmp / 'hook.cpp').write_text(hook_prog)
    subprocess.run(['g++', '-std=c++17', '-Wall', '-I' + str(root), str(tmp / 'hook.cpp'), '-o', str(tmp / 'hook')], check=True)
    print(run(tmp / 'hook').strip())

    for flags in ([], ['-DLILYGO_TDECK=1'], ['-DLORAGOTCHI_SPECIES_EDITION=1']):
        label = ' '.join(flags) or 'default'
        print(run(build(prelude + real + colour_main, tmp, 'colour', flags)).strip(), '[%s]' % label)
        old = run(build(legacy_prog, tmp, 'old', flags))
        mono = run(build(prelude + real + mono_main, tmp, 'mono', flags))
        assert old.count('\n') > 200
        if old != mono:
            for x, y in zip(old.splitlines(), mono.splitlines()):
                if x != y: raise SystemExit('MONO CHANGED (%s):\n old %s\n new %s' % (label, x, y))
            raise SystemExit('MONO CHANGED (line count)')
        print('PASS monochrome/e-ink: RF Monitor drawn identically over %d drawings, even while packets are counted [%s]' % (old.count('\n'), label))
