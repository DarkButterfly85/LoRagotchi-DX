#!/usr/bin/env python3
"""Pet senses: "mesh weather" (quiet / normal / busy) and the brief sparkle it gives the pet.

python3 test/ui/check_mesh_weather.py (Python 3 and g++). No radio, no screen, no flash.
Five parts:
  1. LoRaFishMeshWeather.h on its own, fed by the real RF Monitor+ window:
     quiet / normal / busy counts map to the right level; the level changes only
     after the window rolls on to a new minute; the sparkle is short, happens only
     when the mesh BECOMES busy, and is rate limited however noisy the mesh is.
  2. Temporary, not saved: a few bytes of RAM, no files / radio / Serial in the
     header, and not a single mention in the save, restore, radio or packet code.
  3. Packets untouched: the receive hook (MyMesh::logRxRaw) is exactly as RF Monitor+
     left it and knows nothing about mesh weather; the RF Monitor+ test (which runs
     the real hook and checks it still forwards the frame to the phone and counts)
     is run again.
  4. Colour: the real drawLoRaFishMeshSparkle draws only while sparkling, stays
     inside 320x170 / 320x240 / 240x135, and ends after 5 seconds.
  5. Monochrome / e-ink: the same function draws NOTHING and leaves the state alone,
     so those screens are pixel-identical to before.
"""
from pathlib import Path
import re, subprocess, sys, tempfile

root = Path(__file__).resolve().parents[2]
ui = (root / 'examples/companion_radio/ui-new/UITask.cpp').read_text()
mymesh = (root / 'examples/companion_radio/MyMesh.cpp').read_text()
mymesh_h = (root / 'examples/companion_radio/MyMesh.h').read_text()
weather_h = (root / 'examples/companion_radio/LoRaFishMeshWeather.h').read_text()


def block_of(text, marker):
    a = text.index(marker); i = text.index('{', a); j = i + 1; depth = 1
    while depth: depth += (text[j] == '{') - (text[j] == '}'); j += 1
    return text[a:j]


# ---------------------------------------------------------------- part 1
unit = r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include <vector>
#include "examples/companion_radio/LoRaFishMeshWeather.h"
using namespace LoRaFishMeshWeather;
using LoRaFishRfStats::Window;
static const uint32_t MIN = 60000UL;

static void hear(Window& w, uint32_t t, int n, uint8_t type = 4) {      // n flood frames of a payload type
  for (int i = 0; i < n; ++i) { uint8_t f[6] = {(uint8_t)((type << 2) | 1), 0, 7, 7, 7, 7}; w.record(t, f, 6); }
}

int main() {
  // The mapping itself, edges included.
  assert(levelFor(0) == Quiet && levelFor(1) == Quiet && levelFor(QUIET_MAX) == Quiet);
  assert(levelFor(QUIET_MAX + 1) == Normal && levelFor(BUSY_MIN - 1) == Normal);
  assert(levelFor(BUSY_MIN) == Busy && levelFor(100000) == Busy);
  assert(QUIET_MAX < BUSY_MIN);
  assert(!strcmp(label(Quiet), "quiet") && !strcmp(label(Normal), "normal") && !strcmp(label(Busy), "busy"));

  // Real window counts -> level, only worked out once the window has rolled.
  { Window w; Sense s; uint32_t t = 10 * MIN;
    s.update(t, w); assert(s.level() == Quiet && !s.sparkling());          // nothing heard
    hear(w, t, 200);                                                        // a flood of packets inside the same minute ...
    s.update(t + 1000, w); s.update(t + 30000, w);
    assert(s.level() == Quiet && !s.sparkling());                           // ... changes nothing until the window rolls
    s.update(t + MIN + 1, w);                                               // window rolled on to the next minute
    assert(s.level() == Busy && s.sparkling());
  }
  { Window w; Sense s; uint32_t t = 10 * MIN;
    s.update(t, w);
    hear(w, t, 3); hear(w, t, 1, 2);                                        // 4 packets: quiet
    s.update(t + MIN + 1, w); assert(s.level() == Quiet && !s.sparkling());
    hear(w, t + MIN + 5, 20);                                               // 24 heard: normal
    s.update(t + 2 * MIN + 1, w); assert(s.level() == Normal && !s.sparkling());
    hear(w, t + 2 * MIN + 5, 36);                                           // 60 heard: busy
    s.update(t + 3 * MIN + 1, w); assert(s.level() == Busy && s.sparkling());
  }
  { Window w; Sense s; uint32_t t = 10 * MIN;                               // 59 is still normal, 60 is busy
    s.update(t, w); hear(w, t, 59); s.update(t + MIN + 1, w); assert(s.level() == Normal && !s.sparkling());
    Window w2; Sense s2; s2.update(t, w2); hear(w2, t, 60); s2.update(t + MIN + 1, w2); assert(s2.level() == Busy);
  }
  // Every kind of packet counts toward the weather (adverts, messages, acks ...).
  { Window w; Sense s; uint32_t t = 10 * MIN; s.update(t, w);
    for (uint8_t type : {4, 2, 5, 3, 0, 9}) hear(w, t, 10, type);
    s.update(t + MIN + 1, w); assert(s.level() == Busy);
  }

  // Busy fades back: the level follows the window as old minutes fall off. No sparkle on the way down.
  { Window w; Sense s; uint32_t t = 10 * MIN; s.update(t, w); hear(w, t, 80);
    s.update(t + MIN + 1, w); assert(s.level() == Busy);
    s.update(t + 3 * MIN, w); assert(s.level() == Busy);                    // still inside the window
    s.update(t + 6 * MIN + 1, w); assert(s.level() == Quiet);
    assert(!s.sparkling());
  }

  // The sparkle is short ...
  { Window w; Sense s; uint32_t t = 10 * MIN; s.update(t, w); hear(w, t, 80);
    uint32_t go = t + MIN + 1; s.update(go, w); assert(s.sparkling());
    s.update(go + SPARKLE_MS - 1, w); assert(s.sparkling());
    s.update(go + SPARKLE_MS, w); assert(!s.sparkling());
    assert(s.level() == Busy);                                              // the mesh is still busy, the pet is not still sparkling
    for (uint32_t k = 1; k < 20; ++k) { s.update(go + SPARKLE_MS + k * 7000, w); assert(!s.sparkling()); }   // no repeat while it stays busy
  }
  // ... happens only when the mesh BECOMES busy, and is rate limited however the mesh flips about.
  { Window w; Sense s; uint32_t t = 10 * MIN; s.update(t, w);
    int sparkles = 0; bool was = false;
    for (uint32_t m = 1; m <= 60; ++m) {                                    // an hour: noisy minutes and silent ones, over and over
      uint32_t now = t + m * MIN + 1;
      if ((m / 7) % 2 == 0) hear(w, now - 100, 120);
      for (uint32_t sec = 0; sec < 60; sec += 5) {                          // the screen is redrawn all the time
        s.update(now + sec * 1000UL, w);
        if (s.sparkling() && !was) ++sparkles;
        was = s.sparkling();
      }
    }
    assert(sparkles >= 1);
    assert(sparkles <= (int)(60 * MIN / COOLDOWN_MS) + 1);                  // never more than one per cooldown
  }
  { // Cooldown really blocks a second sparkle that comes too soon, and allows one after it.
    Window w; Sense s; uint32_t t = 10 * MIN; s.update(t, w);
    hear(w, t, 80); s.update(t + MIN + 1, w); assert(s.sparkling());                   // sparkle 1
    s.update(t + 6 * MIN + 1, w); assert(s.level() == Quiet);                           // window emptied
    hear(w, t + 6 * MIN + 2, 80);                                                       // busy again 5 minutes after sparkle 1: cooldown (3 min) is over
    s.update(t + 7 * MIN + 1, w); assert(s.level() == Busy && s.sparkling());          // sparkle 2
    // Sparkle 3 attempted inside the cooldown of sparkle 2: quiet at +13.5, busy again 1 minute later.
    s.update(t + 13 * MIN + 1, w); assert(s.level() == Quiet);
    hear(w, t + 13 * MIN + 2, 80);
    s.update(t + 14 * MIN + 1, w); assert(s.level() == Busy && s.sparkling());          // 7 minutes after: allowed
  }
  { // Two busy edges only 2 minutes apart: the second one stays still.
    Window w; Sense s; uint32_t t = 10 * MIN; s.update(t, w);
    hear(w, t, 80); s.update(t + MIN + 1, w); assert(s.sparkling());
    uint32_t first = t + MIN + 1;
    s.update(first + 6 * MIN, w); assert(s.level() == Quiet);                           // fell quiet
    // (can't get a second edge within 3 minutes through a 5-minute window: the cooldown is a second safety belt)
    assert(COOLDOWN_MS < 5 * MIN);
  }
  { // Busy -> normal -> busy again inside the cooldown: the second sparkle is held back.
    Window w; Sense s; uint32_t b = 10 * MIN; int sparkles = 0; bool was = false;
    auto look = [&](uint32_t at) { s.update(at, w); if (s.sparkling() && !was) ++sparkles; was = s.sparkling(); };
    hear(w, b, 20); look(b);
    look(b + MIN + 1000); hear(w, b + MIN + 5000, 20);
    look(b + 2 * MIN + 1000);
    assert(s.level() == Normal && sparkles == 0);                              // 40 heard
    hear(w, b + 2 * MIN + 5000, 20);
    look(b + 3 * MIN + 40000UL); assert(s.level() == Busy && s.sparkling() && sparkles == 1);   // 60 heard: sparkle
    look(b + 4 * MIN + 1000); look(b + 5 * MIN + 1000);
    assert(s.level() == Normal && !s.sparkling());                             // the busy minutes aged out
    hear(w, b + 5 * MIN + 5000, 40);
    look(b + 6 * MIN + 1000);                                                  // busy again, only 141 s after the sparkle
    assert(s.level() == Busy && !s.sparkling() && sparkles == 1);              // held back by the cooldown
    // Later the same thing is allowed: quiet, then busy well after the cooldown.
    look(b + 12 * MIN + 1000); assert(s.level() == Quiet);
    hear(w, b + 12 * MIN + 5000, 80); look(b + 13 * MIN + 1000); assert(s.sparkling() && sparkles == 2);
  }
  { // A steady busy mesh for half an hour: exactly one sparkle.
    Window w; Sense s; uint32_t t = 10 * MIN; s.update(t, w); int sparkles = 0; bool was = false;
    for (uint32_t m = 0; m < 30; ++m) { hear(w, t + m * MIN, 40);
      for (uint32_t sec = 1; sec < 60; sec += 3) { s.update(t + m * MIN + sec * 1000UL, w); if (s.sparkling() && !was) ++sparkles; was = s.sparkling(); } }
    assert(sparkles == 1);
  }

  // The 32-bit millisecond clock wrapping round is fine.
  { Window w; Sense s; uint32_t t = 0xFFFFFFFFu - 90000UL; s.update(t, w); hear(w, t, 100);
    s.update(t + MIN + 1, w); assert(s.level() == Busy && s.sparkling());
    s.update(t + MIN + 1 + SPARKLE_MS + 5, w); assert(!s.sparkling());       // across the wrap
  }
  // A reader a hair behind the radio (clock slightly earlier) does not blow anything up.
  { Window w; Sense s; hear(w, 10 * MIN + 500, 80); s.update(10 * MIN + 400, w); assert(s.level() == Busy && w.total(10 * MIN + 400) == 80); }   // counts kept, no crash
  // Twinkle frames cycle 0..3.
  { Sense s; for (uint32_t t = 0; t < 4000; t += 50) assert(s.frame(t) < 4);
    assert(s.frame(0) == 0 && s.frame(250) == 1 && s.frame(500) == 2 && s.frame(750) == 3 && s.frame(1000) == 0); }
  // Tiny: a few bytes of RAM.
  assert(sizeof(Sense) <= 16);
  printf("PASS levels quiet/normal/busy, changes only after the window rolls, short + rate-limited sparkle, wrap-safe, %zu bytes\n", sizeof(Sense));
  return 0;
}
'''

# ---------------------------------------------------------------- part 2: temporary, not saved
code_only = re.sub(r'//[^\n]*', '', weather_h)                       # ignore the comments
for banned in ('File', 'Serial', 'millis', 'SPIFFS', 'LittleFS', 'fopen', 'write(', 'save', 'Packet', 'sendFlood', 'sendDirect', 'MyMesh'):
    assert banned not in code_only, 'LoRaFishMeshWeather.h must stay free of %r' % banned
assert re.findall(r'#include\s*[<"]([^>"]+)[>"]', weather_h) == ['stdint.h', 'LoRaFishRfStats.h']

sparkle_fn = block_of(ui, 'static void drawLoRaFishMeshSparkle(')
decl = 'static LoRaFishMeshWeather::Sense loRaFishMeshSense;'
assert ui.count(decl) == 1
stripped = ui.replace(sparkle_fn, '').replace(decl, '')
for needle in ('MeshSense', 'MeshWeather'):
    # only the include line and the aquarium's one call may mention it
    hits = [l.strip() for l in stripped.splitlines() if needle in l]
    allowed = ['#include "../LoRaFishMeshWeather.h"']
    hits = [h for h in hits if h not in allowed and 'drawLoRaFishMeshSparkle' not in h and not h.startswith('//')]
    assert not hits, 'unexpected %s outside the sparkle function: %s' % (needle, hits)
assert stripped.count('drawLoRaFishMeshSparkle(display,x,y);') == 1, 'exactly one call site'
# The save / restore / radio / packet code never hears of it.
for fn in ('static void saveLoRaFish(', 'static bool restoreLoRaFish(', 'static void restoreLoRaFish('):
    if fn in ui:
        body = block_of(ui, fn)
        assert 'MeshSense' not in body and 'MeshWeather' not in body and 'Sparkle' not in body, fn
for text, name in ((mymesh, 'MyMesh.cpp'), (mymesh_h, 'MyMesh.h')):
    assert 'MeshWeather' not in text and 'MeshSense' not in text and 'Sparkle' not in text, name + ' must not know about mesh weather'
# The sparkle function is presentational only: it reads counts and draws, nothing else.
for banned in ('saveLoRaFish', 'happiness', 'dxVisits', 'meal', 'breed', 'loragotchiDX', 'sendFlood', 'sendDirect', 'File ', 'fish.'):
    assert banned not in sparkle_fn, 'sparkle function must be presentational only: %r' % banned
# The one call site is inside the awake, living pet branch (not asleep, not travelling, not an egg or memorial).
agu = block_of(ui, 'static void drawLoRaFishAquarium(')
call = agu.index('drawLoRaFishMeshSparkle(display,x,y);')
awake = agu.index('else if (!homeTraveling && !loRaFishHomeTravelAnimation.active) {')
assert awake < call and call - awake < 400
assert 'LORAFISH_EGG_MINUTES' in agu[call - 200:call] and 'LORAFISH_LIFESPAN_MINUTES' in agu[call - 200:call]
# Mono guard is the very first statement of the function.
first = sparkle_fn[sparkle_fn.index('{') + 1:].lstrip().splitlines()[0]
assert first.startswith('if (!loRaFishColorDisplay) return;'), first
print('PASS temporary + not saved: header has no files/radio/Serial, no mention in save/restore/MyMesh, one call site in the awake living-pet branch, mono guard first')

# ---------------------------------------------------------------- part 3: packets untouched
hook = block_of(mymesh, 'void MyMesh::logRxRaw(')
assert 'lorafish_rf_stats.record(millis(), raw, len);' in hook
assert hook.count('\n') <= 18, 'logRxRaw grew'
assert 'sparkle' not in hook.lower() and 'weather' not in hook.lower() and 'sense' not in hook.lower()
rf = root / 'test/ui/check_rf_monitor_plus.py'
r = subprocess.run([sys.executable, str(rf)], capture_output=True, text=True)
if r.returncode:
    raise SystemExit('RF Monitor+ test failed:\n' + r.stdout[-800:] + r.stderr[-800:])
assert 'real MyMesh::logRxRaw: old behaviour intact' in r.stdout
print('PASS packet handling untouched: logRxRaw unchanged, RF Monitor+ test still shows it records, keeps RSSI/SNR and forwards the phone frame')

# ---------------------------------------------------------------- parts 4 and 5: the real sparkle function
head_path = root / 'test/ui/check_native_pages.py'
head = head_path.read_text()
head = head[:head.index("code+=block('static int loRaFishBatteryPercent(')")]
ns = {'__file__': str(head_path), '__name__': 'native_pages_head'}
exec(compile(head, 'check_native_pages_head', 'exec'), ns)
prelude = ns['code']
prelude += '\n#include "examples/companion_radio/LoRaFishMeshWeather.h"\n' + decl + '\n' + sparkle_fn + '\n'

helpers = r'''
static const unsigned long MIN = 60000UL;
static void hear(unsigned long t, int n) {
  for (int i = 0; i < n; ++i) { uint8_t f[6] = {(uint8_t)((4 << 2) | 1), 0, 7, 7, 7, 7}; lorafish_rf_stats.record((uint32_t)t, f, 6); }
}
'''
colour_main = helpers + r'''
int main() {
  loRaFishColorDisplay = true;
  for (auto dims : {std::pair<int,int>{320,170}, {320,240}, {240,135}}) {
    const int W = dims.first, H = dims.second;
    lorafish_rf_stats = LoRaFishRfStats::Window(); loRaFishMeshSense = LoRaFishMeshWeather::Sense();
    now = 10 * MIN;
    // Quiet mesh: nothing drawn.
    { Recorder out(W, H); drawLoRaFishMeshSparkle(out, W / 2, H / 2); assert(out.shapes.empty()); }
    // Busy, but the window has not rolled: still nothing.
    hear(now, 150);
    { Recorder out(W, H); now += 1000; drawLoRaFishMeshSparkle(out, W / 2, H / 2); assert(out.shapes.empty()); }
    // Window rolls: the pet sparkles. Check pet positions all over the screen, corners included.
    now = 11 * MIN + 1;
    for (int x : {0, 5, W / 2, W - 5, W}) for (int y : {0, 20, H / 2, H - 20, H}) {
      Recorder out(W, H); drawLoRaFishMeshSparkle(out, x, y);       // Recorder aborts on any off-screen fill
      assert(!out.shapes.empty()); assert(out.shapes.size() <= 6);   // 3 twinkles, 1 or 2 rectangles each
      for (auto& s : out.shapes) { assert(s.x >= 2 && s.y >= 17 && s.x + s.w <= W && s.y + s.h <= H - 16); assert(s.w <= 3 && s.h <= 3); }
    }
    // Twinkles move with time.
    { Recorder a(W, H); drawLoRaFishMeshSparkle(a, W / 2, H / 2);
      now += 250; Recorder b(W, H); drawLoRaFishMeshSparkle(b, W / 2, H / 2);
      bool same = a.shapes.size() == b.shapes.size();
      for (size_t i = 0; same && i < a.shapes.size(); ++i) same = a.shapes[i].w == b.shapes[i].w && a.shapes[i].h == b.shapes[i].h;
      assert(!same); }
    // It ends after 5 seconds, and does not come back while the mesh stays busy.
    now = 11 * MIN + 1 + LoRaFishMeshWeather::SPARKLE_MS;
    { Recorder out(W, H); drawLoRaFishMeshSparkle(out, W / 2, H / 2); assert(out.shapes.empty()); }
    for (int k = 0; k < 30; ++k) { now += 20000; hear(now, 30);
      Recorder out(W, H); drawLoRaFishMeshSparkle(out, W / 2, H / 2); assert(out.shapes.empty()); }
    assert(loRaFishMeshSense.level() == LoRaFishMeshWeather::Busy);
  }
  puts("PASS colour: sparkle appears only after a busy window rolls, stays on screen at 320x170 / 320x240 / 240x135, ends after 5 s, no repeat while busy");
  return 0;
}
'''
mono_main = helpers + r'''
int main() {
  loRaFishColorDisplay = false;
  for (auto dims : {std::pair<int,int>{128,64}, {250,122}, {296,128}, {320,170}}) {
    const int W = dims.first, H = dims.second;
    lorafish_rf_stats = LoRaFishRfStats::Window(); loRaFishMeshSense = LoRaFishMeshWeather::Sense();
    now = 10 * MIN; hear(now, 500);                                  // a very busy mesh is being counted ...
    for (int k = 0; k < 20; ++k) {
      now = 10 * MIN + k * 20000UL + 1;
      Recorder out(W, H); drawLoRaFishMeshSparkle(out, W / 2, H / 2);
      assert(out.shapes.empty() && out.printed.empty());             // ... and the mono screen gets not a single pixel of it
      assert(!loRaFishMeshSense.sparkling());
      assert(loRaFishMeshSense.level() == LoRaFishMeshWeather::Normal);   // state untouched too
    }
  }
  puts("PASS monochrome/e-ink: sparkle function draws nothing and touches no state, even on a very busy mesh");
  return 0;
}
'''

def build(prog, tmp, name, flags):
    cpp = tmp / (name + '.cpp'); cpp.write_text(prog); exe = tmp / name
    subprocess.run(['g++', '-std=c++17', '-DLORAGOTCHI_NATIVE_UI=1', '-I' + str(root), '-I' + str(root / 'src')] + flags + [str(cpp), '-o', str(exe)], check=True)
    return exe

def run(exe):
    r = subprocess.run([str(exe)], capture_output=True, text=True)
    if r.returncode: raise SystemExit('FAILED %s:\n%s%s' % (exe.name, r.stdout[-600:], r.stderr[-1200:]))
    return r.stdout.strip()

with tempfile.TemporaryDirectory(prefix='lrx-weather-') as t:
    tmp = Path(t)
    (tmp / 'unit.cpp').write_text(unit)
    subprocess.run(['g++', '-std=c++17', '-Wall', '-I' + str(root), str(tmp / 'unit.cpp'), '-o', str(tmp / 'unit')], check=True)
    print(run(tmp / 'unit'))
    for flags in ([], ['-DLILYGO_TDECK=1'], ['-DLORAGOTCHI_SPECIES_EDITION=1']):
        label = ' '.join(flags) or 'default'
        print(run(build(prelude + colour_main, tmp, 'colour', flags)), '[%s]' % label)
        print(run(build(prelude + mono_main, tmp, 'mono', flags)), '[%s]' % label)
