#!/usr/bin/env python3
"""Pet senses: "mesh weather" -- the pet sparkles when the mesh suddenly gets much busier than usual.

python3 test/ui/check_mesh_weather.py (Python 3 and g++). No radio, no screen, no flash.
Parts:
  1. LoRaFishRfStats.h keeps the packet total of each finished minute (RAM only); and
     LoRaFishMeshWeather.h on its own, fed by the real RF Monitor+ window: a RELATIVE rule --
     the newest minute must be at least 2.5x the average of the minutes before it AND above a
     small floor. Steady mesh: no sparkle. A sudden 3x minute: sparkle. A small jump on a quiet
     mesh (1 -> 3): none. Nothing in the first 10 minutes. Cooldown holds. A mesh that stays
     high gives one sparkle. Wrap-safe, tiny, mono corner picker keeps clear of the pet.
  2. Temporary, not saved: a few bytes of RAM, no files / radio / Serial in the header, and
     not a single mention in the save, restore, radio or packet code.
  3. Packets untouched: the receive hook (MyMesh::logRxRaw) is exactly as RF Monitor+ left it
     and knows nothing about mesh weather; the RF Monitor+ test is run again.
  4. Colour: the real drawLoRaFishMeshSparkle draws the three yellow twinkles only after a
     spike, stays inside 320x170 / 320x240 / 240x135, ends after 5 seconds.
  5. Monochrome: the same function draws NOTHING unless a sparkle is active (proved by
     comparing a whole page with and without it), then a small plus for 1 s, a dot, and gone,
     in a tank corner that is clear of the pet, every text row, the header (battery / clock),
     the bottom status bar, the poop spots and the bubble columns.
  6. E-ink gets NO animation, by design: the sparkle is compiled out of every e-ink build
     (DISPLAY_CLASS = GxEPDDisplay / E213Display / E290Display), a run-time guard comes before
     everything else, every frame across a surge is identical to the page without the sparkle
     code, and the old MONO_ON_EINK switch no longer exists anywhere.
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

// One mesh, one pet. minute(n) = n packets in a minute, then the screen looks as the minute rolls over.
struct Run {
  Window w; Sense s; uint32_t cur; int idx = 0; int sparkles = 0; bool was = false; std::vector<int> at;
  explicit Run(uint32_t start = 10 * MIN) : cur(start) { s.update(cur, w); }
  void look(uint32_t t) { s.update(t, w); if (s.sparkling() && !was) { ++sparkles; at.push_back(idx); } was = s.sparkling(); }
  void minute(int n, bool peek = true) {
    ++idx; hear(w, cur + 10000, n); cur += MIN;
    if (peek) { look(cur + 1); look(cur + SPARKLE_MS + 10); }
  }
  void minutes(int count, int n) { for (int i = 0; i < count; ++i) minute(n); }
};

int main() {
  // --- the minute history the rule reads (RAM only, 32 minutes)
  { Window w; uint32_t t = 10 * MIN; w.advance(t);
    for (int m = 1; m <= 40; ++m) hear(w, t + (m - 1) * MIN + 5000, m);
    assert(w.finishedMinutes(t + 40 * MIN + 1) == 40);
    for (int k = 0; k < LoRaFishRfStats::HISTORY; ++k) assert(w.minuteAgo((uint8_t)k) == 40 - k);   // 40 ... 9
    assert(w.total(t + 40 * MIN + 1) == 37 + 38 + 39 + 40);   // the 5-minute counts work as before
  }
  { Window w; uint32_t t = 10 * MIN; w.advance(t); hear(w, t + 5000, 7);
    assert(w.finishedMinutes(t + 20 * MIN + 500) == 20);                    // a long silence: the empty minutes are counted
    for (int k = 0; k < 19; ++k) assert(w.minuteAgo((uint8_t)k) == 0);
    assert(w.minuteAgo(19) == 7);
  }
  { Window w; uint32_t t = 10 * MIN; w.advance(t); hear(w, t + 5000, 5);
    assert(w.finishedMinutes(t + 100 * MIN) == 1 + LoRaFishRfStats::HISTORY);   // older than the history: just zeros
    for (int k = 0; k < LoRaFishRfStats::HISTORY; ++k) assert(w.minuteAgo((uint8_t)k) == 0);
  }
  assert(sizeof(Window) < 1000);

  // --- the rule on its own
  assert(!isSpike(30, 90, 9));                           // fewer than 10 earlier minutes: never
  assert(isSpike(30, 100, 10));                          // 10 earlier minutes at 10 each: 3x
  assert(isSpike(25, 100, 10) && !isSpike(24, 100, 10)); // exactly 2.5x counts, a hair under does not
  assert(!isSpike(3, 10, 10));                           // quiet mesh 1 -> 3: below the floor
  assert(!isSpike(SPIKE_FLOOR - 1, 0, 30) && isSpike(SPIKE_FLOOR, 0, 30));   // floor edge, silent baseline
  assert(SPIKE_FLOOR > 3);                               // so 1 -> 3 can never trigger
  assert(SPIKE_TENTHS == 25 && BASELINE_MINUTES == 30 && MIN_BASELINE_MINUTES == 10 && COOLDOWN_MS == 180000UL);

  // --- steady baseline: no sparkle, ever
  { Run r; r.minutes(60, 10); assert(r.sparkles == 0); }
  { Run r; for (int i = 0; i < 60; ++i) r.minute(8 + (i % 5)); assert(r.sparkles == 0); }   // ordinary wobble 8..12
  { Run r; r.minutes(60, 0); assert(r.sparkles == 0); }                                     // dead mesh
  // --- a sudden 3x minute: a sparkle, right when that minute finishes
  { Run r; r.minutes(15, 10); r.minute(30); assert(r.sparkles == 1 && r.at[0] == 16); r.minutes(20, 10); assert(r.sparkles == 1); }
  { Run r; r.minutes(15, 10); r.minute(25); assert(r.sparkles == 1); }                      // exactly 2.5x
  { Run r; r.minutes(15, 10); r.minute(24); assert(r.sparkles == 0); }                      // just under
  { Run r; r.minutes(40, 100); r.minute(300); assert(r.sparkles == 1); }                    // works the same on a busy mesh
  { Run r; r.minutes(40, 100); r.minute(120); assert(r.sparkles == 0); }                    // ... where +20 is nothing
  { Run r; r.minutes(40, 1); r.minute(8); assert(r.sparkles == 1); }                        // a very quiet mesh wakes up properly
  // --- a small jump on a quiet mesh: nothing
  { Run r; r.minutes(20, 1); r.minute(3); assert(r.sparkles == 0); r.minute(1); r.minute(3); r.minute(7); assert(r.sparkles == 0); }
  { Run r; r.minutes(20, 0); r.minute(3); r.minute(7); assert(r.sparkles == 0); }
  // --- nothing in the first 10 minutes
  for (int k = 1; k <= 10; ++k) { Run r; r.minutes(k - 1, 2); r.minute(100); assert(r.sparkles == 0); }   // spike as minute 1..10
  { Run r; r.minutes(10, 2); r.minute(100); assert(r.sparkles == 1 && r.at[0] == 11); }               // 10 earlier minutes exist: allowed
  { Run r; r.minutes(5, 2); r.minute(100); r.minutes(4, 2); assert(r.sparkles == 0); }
  // --- cooldown holds
  { Run r; r.minutes(15, 10); r.minute(30); assert(r.sparkles == 1);
    r.minute(10); r.minute(200); assert(r.sparkles == 1);              // a second jump 2 minutes later: held back
    r.minute(10); r.minute(10); r.minute(400); assert(r.sparkles == 2); // 4 minutes after the first: allowed
  }
  { Run r; r.minutes(15, 10);                                         // spike, calm, spike ... for an hour
    for (int i = 0; i < 30; ++i) { r.minute(200); r.minute(10); }
    assert(r.sparkles >= 1 && r.sparkles <= (int)(60 * MIN / COOLDOWN_MS) + 1);
  }
  // --- a mesh that STAYS high gives one sparkle, not a light show
  { Run r; r.minutes(15, 10); r.minutes(25, 30); assert(r.sparkles == 1); }
  { Run r; r.minutes(30, 10); r.minutes(10, 100); assert(r.sparkles == 1); }   // a 10x surge that lasts 10 minutes: still just one
  // --- minutes nobody looked at (the screen was on another page)
  { Run r; r.minutes(20, 10); for (int i = 0; i < 6; ++i) r.minute(10, false); r.minute(100); assert(r.sparkles == 1); }
  { Run r; r.minutes(20, 10); r.cur += 40 * MIN; r.minute(30); r.minute(0); assert(r.sparkles == 1); }   // after a long silence it wakes
  { Run r; r.minutes(5, 10); r.cur += 60 * MIN; r.minute(30); r.minute(0); r.minute(0); assert(r.sparkles == 1); }
  // --- the sparkle: short, and its mono phases
  { Run r; r.minutes(15, 10); r.minute(30, false); uint32_t go = r.cur + 1; r.s.update(go, r.w);
    assert(r.s.sparkling());
    r.s.update(go + SPARKLE_MS - 1, r.w); assert(r.s.sparkling());
    r.s.update(go + SPARKLE_MS, r.w); assert(!r.s.sparkling());
  }
  { Run r; r.minutes(15, 10); r.minute(30, false); uint32_t go = r.cur + 1; r.s.update(go, r.w); assert(r.s.sparkling());
    assert(r.s.monoStep(go) == 1 && r.s.monoStep(go + MONO_PLUS_MS - 1) == 1);          // the plus, about a second
    assert(r.s.monoStep(go + MONO_PLUS_MS) == 2 && r.s.monoStep(go + MONO_PLUS_MS + MONO_DOT_MS - 1) == 2);   // then the dot
    assert(r.s.monoStep(go + MONO_PLUS_MS + MONO_DOT_MS) == 0 && r.s.monoStep(go + SPARKLE_MS - 1) == 0);     // then nothing
    Sense idle; assert(idle.monoStep(0) == 0 && idle.monoStep(123456) == 0);
  }
  static_assert(MONO_PLUS_MS >= 800 && MONO_PLUS_MS <= 1200, "about one second");
  static_assert(MONO_PLUS_MS + MONO_DOT_MS < SPARKLE_MS, "the mono sparkle ends before the colour one");
  // --- the 32-bit millisecond clock wrapping round is fine
  { Run r(0xFFFFFFFFu - 12 * MIN - 500); r.minutes(15, 10); r.minute(30); assert(r.sparkles == 1); r.minutes(5, 10); assert(r.sparkles == 1);
    Run q(0xFFFFFFFFu - 12 * MIN - 500); q.minutes(30, 10); assert(q.sparkles == 0); }
  // --- twinkle frames cycle 0..3
  { Sense s; for (uint32_t t = 0; t < 4000; t += 50) assert(s.frame(t) < 4);
    assert(s.frame(0) == 0 && s.frame(250) == 1 && s.frame(500) == 2 && s.frame(750) == 3 && s.frame(1000) == 0); }
  // --- mono corner: always inside the tank, never on the pet; only gives up when the pet is by both corners
  for (int w : {128, 160, 240, 320}) {
    for (int px = -10; px <= w + 10; ++px) for (int py = 0; py <= 130; ++py) {
      int cx = -1, cy = -1;
      if (monoSpot(w, px, py, cx, cy)) {
        assert(cx - 1 >= 0 && cx + 1 < w && cy - 1 >= 16);                                 // on screen, under the header line
        assert(cx + 1 < px - PET_HALF_W || cx - 1 > px + PET_HALF_W || cy + 1 < py - PET_ABOVE || cy - 1 > py + PET_BELOW);
      }
    }
    for (int px = 20; px <= w - 20; ++px) for (int py = 30; py <= 60; ++py) { int cx, cy; assert(monoSpot(w, px, py, cx, cy)); }   // the pet's real swim range
  }
  // --- tiny
  assert(sizeof(Sense) <= 16);
  printf("PASS relative rule: steady none, 3x sparkles, 1->3 none, 10-minute warm-up, cooldown, one per jump, wrap-safe, mono phases, corner clear of pet, %zu bytes\n", sizeof(Sense));
  return 0;
}
'''

# ---------------------------------------------------------------- part 2: temporary, not saved
code_only = re.sub(r'//[^\n]*', '', weather_h)                       # ignore the comments
for banned in ('File', 'Serial', 'millis', 'SPIFFS', 'LittleFS', 'fopen', 'write(', 'save', 'Packet', 'sendFlood', 'sendDirect', 'MyMesh'):
    assert banned not in code_only, 'LoRaFishMeshWeather.h must stay free of %r' % banned
assert re.findall(r'#include\s*[<"]([^>"]+)[>"]', weather_h) == ['stdint.h', 'LoRaFishRfStats.h']
assert 'SPIKE_TENTHS' in weather_h and 'SPIKE_FLOOR' in weather_h and 'BASELINE_MINUTES' in weather_h   # the named constants
# The old fixed thresholds are gone.
assert 'QUIET_MAX' not in weather_h and 'BUSY_MIN' not in weather_h and 'levelFor' not in weather_h

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
assert stripped.count('drawLoRaFishMeshSparkle(display,x,y,') == 1, 'exactly one call site'
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
# The one call site is inside the awake, living pet branch (not asleep, not travelling, not an egg or memorial),
# and tells the mono sparkle when a visitor is on the tank.
agu = block_of(ui, 'static void drawLoRaFishAquarium(')
call = agu.index('drawLoRaFishMeshSparkle(display,x,y,')
awake = agu.index('else if (!homeTraveling && !loRaFishHomeTravelAnimation.active) {')
assert awake < call and call - awake < 500
assert 'LORAFISH_EGG_MINUTES' in agu[call - 200:call] and 'LORAFISH_LIFESPAN_MINUTES' in agu[call - 200:call]
assert 'loragotchiDXGuest.present' in agu[call:call + 200]
# E-ink is told apart from other screens, and the run-time guard comes before anything else happens.
assert 'loRaFishEinkDisplay = display && display->isEink();' in ui
assert sparkle_fn.count('loRaFishEinkDisplay') == 1
guard = sparkle_fn.index('loRaFishEinkDisplay')
assert 'return;' in sparkle_fn[guard:guard + 90]
assert guard < sparkle_fn.index('.update(') < sparkle_fn.index('monoStep(')
assert guard < sparkle_fn.index('millis()') < sparkle_fn.index('loRaFishColorDisplay')   # before the colour / mono split too
# Compile time: the e-ink build keeps none of the sparkle, its state or its call to update().
assert '#if LORAFISH_EINK_BUILD' in sparkle_fn and '#else' in sparkle_fn and sparkle_fn.rstrip().endswith('#endif\n}')
eink_stub = sparkle_fn[sparkle_fn.index('#if LORAFISH_EINK_BUILD'):sparkle_fn.index('#else')]
assert 'update(' not in eink_stub and 'fillRect' not in eink_stub and 'millis' not in eink_stub
assert ui.count('#if !LORAFISH_EINK_BUILD\n' + decl + '\n#endif') == 1
# The old switch is gone, everywhere (code, headers, docs, build files).
for sub in ('examples', 'src', 'variants', 'docs', 'boards'):
    for f in (root / sub).rglob('*'):
        if f.is_file() and f.suffix in ('.h', '.cpp', '.c', '.ini', '.md', '.py', '.txt', '.json', '.html'):
            assert 'MONO_ON_EINK' not in f.read_text(errors='ignore'), 'the MONO_ON_EINK switch must not exist: ' + str(f)
assert 'MONO_ON_EINK' not in ui and 'MONO_ON_EINK' not in weather_h
# The e-ink class list in the header is exactly the display drivers that report isEink() == true.
eink_classes = set()
for hp in (root / 'src/helpers/ui').glob('*.h'):
    t = hp.read_text(errors='ignore')
    for m in re.finditer(r'class\s+(\w+)\s*:\s*public\s+\w+\s*\{', t):
        end = t.find('\nclass ', m.end()); body = t[m.end(): end if end > 0 else len(t)]
        if re.search(r'bool\s+isEink\s*\(\s*\)\s*override\s*\{\s*return\s+true\s*;', body): eink_classes.add(m.group(1))
listed = set(re.findall(r'#define\s+LORAFISH_EINK_CLASS_(\w+)\s+1', weather_h))
assert eink_classes and listed == eink_classes, (listed, eink_classes)
# Colour keeps the three yellow twinkles.
assert '0xFFE0' in sparkle_fn and 'dx[3]={-17,15,19}' in sparkle_fn and 'i<3' in sparkle_fn
print('PASS temporary + not saved: header has no files/radio/Serial, no mention in save/restore/MyMesh, one call site in the awake living-pet branch, old fixed thresholds gone')
print('PASS e-ink lock: compile-time stub for %s, run-time guard first, MONO_ON_EINK no longer exists anywhere' % ', '.join(sorted(eink_classes)))

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
if 'loRaFishEinkDisplay' not in prelude:
    prelude += '\nstatic bool loRaFishEinkDisplay=false;\n'
prelude += '\n#include "examples/companion_radio/LoRaFishMeshWeather.h"\n#if !LORAFISH_EINK_BUILD\n' + decl + '\n#endif\n' + sparkle_fn + '\n'

helpers = r'''
static const unsigned long MIN = 60000UL;
static void hear(unsigned long t, int n) {
  for (int i = 0; i < n; ++i) { uint8_t f[6] = {(uint8_t)((4 << 2) | 1), 0, 7, 7, 7, 7}; lorafish_rf_stats.record((uint32_t)t, f, 6); }
}
static void reset() { lorafish_rf_stats = LoRaFishRfStats::Window(); loRaFishMeshSense = LoRaFishMeshWeather::Sense(); now = 10 * MIN; }
// 'count' minutes of 'per' packets each; the screen is redrawn every 5 s like the real UI. Returns the number of redraws that showed a sparkle.
static int play(int count, int per, int W, int H, int px, int py) {
  int lit = 0;
  for (int m = 0; m < count; ++m) {
    hear(now + 500, per);
    for (int s = 0; s < 12; ++s) { now += 5000; Recorder o(W, H); drawLoRaFishMeshSparkle(o, px, py); if (!o.shapes.empty()) ++lit; }
  }
  return lit;
}
'''
colour_main = helpers + r'''
int main() {
  loRaFishColorDisplay = true;
  for (auto dims : {std::pair<int,int>{320,170}, {320,240}, {240,135}}) {
    const int W = dims.first, H = dims.second, PX = W / 2, PY = H / 2;
    // Steady, a small wobble, a quiet 1 -> 3 and the first ten minutes: nothing.
    reset(); assert(play(40, 10, W, H, PX, PY) == 0);
    reset(); assert(play(20, 1, W, H, PX, PY) == 0 && play(1, 3, W, H, PX, PY) == 0 && play(2, 1, W, H, PX, PY) == 0);
    reset(); assert(play(9, 2, W, H, PX, PY) == 0 && play(1, 100, W, H, PX, PY) == 0 && play(2, 2, W, H, PX, PY) == 0);
    // A real jump after the warm-up shows exactly one sparkle (it lasts less than one redraw interval of 5 s).
    reset(); assert(play(15, 10, W, H, PX, PY) == 0 && play(1, 30, W, H, PX, PY) == 0 && play(1, 10, W, H, PX, PY) == 1 && play(10, 10, W, H, PX, PY) == 0);
    // Cooldown: a second jump two minutes later is held back; one four minutes later is allowed.
    reset(); play(15, 10, W, H, PX, PY);
    { int lit = play(1, 30, W, H, PX, PY) + play(1, 10, W, H, PX, PY) + play(1, 200, W, H, PX, PY) + play(1, 10, W, H, PX, PY);
      assert(lit == 1);
      lit = play(1, 10, W, H, PX, PY) + play(1, 10, W, H, PX, PY) + play(1, 400, W, H, PX, PY) + play(1, 10, W, H, PX, PY);
      assert(lit == 1); }
    // The sparkle itself: appears only once the busy minute is finished, stays on screen with the pet anywhere, ends after 5 s.
    reset(); play(15, 10, W, H, PX, PY);
    hear(now + 500, 30);
    now += 30000; { Recorder out(W, H); drawLoRaFishMeshSparkle(out, PX, PY); assert(out.shapes.empty()); }   // minute not finished yet
    now += 31000; const unsigned long go = now;
    for (int x : {0, 5, W / 2, W - 5, W}) for (int y : {0, 20, H / 2, H - 20, H}) {
      Recorder out(W, H); drawLoRaFishMeshSparkle(out, x, y);       // Recorder aborts on any off-screen fill
      assert(!out.shapes.empty()); assert(out.shapes.size() <= 6);   // 3 twinkles, 1 or 2 rectangles each
      for (auto& s : out.shapes) { assert(s.x >= 2 && s.y >= 17 && s.x + s.w <= W && s.y + s.h <= H - 16); assert(s.w <= 3 && s.h <= 3); }
    }
    { Recorder a(W, H); drawLoRaFishMeshSparkle(a, PX, PY);
      now += 250; Recorder b(W, H); drawLoRaFishMeshSparkle(b, PX, PY);       // twinkles move with time
      bool same = a.shapes.size() == b.shapes.size();
      for (size_t i = 0; same && i < a.shapes.size(); ++i) same = a.shapes[i].w == b.shapes[i].w && a.shapes[i].h == b.shapes[i].h;
      assert(!same); }
    now = go + LoRaFishMeshWeather::SPARKLE_MS - 1; { Recorder out(W, H); drawLoRaFishMeshSparkle(out, PX, PY); assert(!out.shapes.empty()); }
    now = go + LoRaFishMeshWeather::SPARKLE_MS;     { Recorder out(W, H); drawLoRaFishMeshSparkle(out, PX, PY); assert(out.shapes.empty()); }
  }
  puts("PASS colour: sparkle only after a relative jump (not steady, not 1->3, not in the first 10 min), cooldown, three twinkles on screen at 320x170 / 320x240 / 240x135, ends after 5 s");
  return 0;
}
'''
mono_main = helpers + r'''
struct Obst { int x, y, w, h; };
// What else is on the mono tank page (from drawLoRaFishHeader / TankBattery / StatusBar / Aquarium / Hygiene / Bubbles).
static std::vector<Obst> obstacles(int W, int H) {
  std::vector<Obst> v;
  v.push_back({0, 0, W, 16});                          // header text, clock, battery icon and its separator line (y 15)
  v.push_back({0, H - 15, W, 15});                     // floor line and the PKT/UNR status bar
  v.push_back({(W - 84) / 2, 17, 84, 11});             // "* EVOLVED! *" / "* MESSAGE *" row
  v.push_back({(W - 108) / 2, 25, 108, 11});           // visiting pet's name row
  v.push_back({(W - 108) / 2, 33, 108, 12});           // "PET DX AWAY" / "DELIVERING..." row
  for (int px : {20, 58, 96}) v.push_back({px, H - 28, 9, 9});   // poop
  v.push_back({13, 16, 7, H - 31});                    // bubble columns (they rise through the whole tank)
  v.push_back({27, 16, 8, H - 31});
  v.push_back({W - 20, 16, 7, H - 31});
  return v;
}
static bool hits(int x, int y, int w, int h, const Obst& o) { return x < o.x + o.w && x + w > o.x && y < o.y + o.h && y + h > o.y; }
static void fixedPage(Recorder& d, int W, int H) {     // stand-in for everything else on the page
  d.fillRect(2, 15, W - 4, 1); d.fillRect(2, H - 15, W - 4, 1);
  d.setCursor(2, 5); d.print("PET"); d.setCursor(4, H - 9); d.print("PKT:12 UNR:0");
  d.fillRect(40, 30, 20, 8);                           // the pet
}
static bool same(const Recorder& a, const Recorder& b) {
  if (a.shapes.size() != b.shapes.size() || a.printed != b.printed) return false;
  for (size_t i = 0; i < a.shapes.size(); ++i) {
    const auto &p = a.shapes[i], &q = b.shapes[i];
    if (p.x != q.x || p.y != q.y || p.w != q.w || p.h != q.h || p.outline != q.outline) return false;
  }
  return true;
}
static std::vector<Recorder::Shape> drawn(int W, int H, int px, int py, bool free = true) {
  Recorder o(W, H); drawLoRaFishMeshSparkle(o, px, py, free); return o.shapes;
}

int main() {
  loRaFishColorDisplay = false; loRaFishEinkDisplay = false;
  for (auto dims : {std::pair<int,int>{128,64}, {128,128}, {240,135}}) {
    const int W = dims.first, H = dims.second, PX = 60, PY = 38;
    const auto obst = obstacles(W, H);
    // Reference page: no sparkle code at all.
    Recorder base(W, H); fixedPage(base, W, H);
    auto page = [&](int px, int py, bool free = true) { Recorder o(W, H); fixedPage(o, W, H); drawLoRaFishMeshSparkle(o, px, py, free); return o; };

    // 1. Idle: steady mesh, quiet jump, the first 10 minutes -- the page is IDENTICAL (shape for shape, text for text).
    reset(); for (int m = 0; m < 40; ++m) { hear(now + 500, 10); for (int s = 0; s < 12; ++s) { now += 5000; assert(same(page(PX, PY), base)); } }
    reset(); for (int m = 0; m < 20; ++m) { hear(now + 500, 1); for (int s = 0; s < 12; ++s) { now += 5000; assert(same(page(PX, PY), base)); } }
    reset(); for (int m = 0; m < 12; ++m) { hear(now + 500, m == 5 ? 100 : 2); for (int s = 0; s < 12; ++s) { now += 5000; assert(same(page(PX, PY), base)); } }
    assert(!loRaFishMeshSense.sparkling());

    // 2. A real jump after the warm-up.
    reset(); assert(play(15, 10, W, H, PX, PY) == 0);
    hear(now + 500, 30);
    now += 30000; assert(same(page(PX, PY), base));                       // minute not finished: nothing
    now += 31000; const unsigned long go = now;
    int plusFrames = 0, dotFrames = 0;
    for (unsigned long t = 0; t < 2600; t += 50) {
      now = go + t;
      Recorder o = page(PX, PY);
      const size_t extra = o.shapes.size() - base.shapes.size();
      if (t < 1000) {                                                      // the plus: 5 pixels
        assert(extra == 2 && o.shapes[base.shapes.size()].w == 3 && o.shapes[base.shapes.size()].h == 1
               && o.shapes[base.shapes.size() + 1].w == 1 && o.shapes[base.shapes.size() + 1].h == 3); ++plusFrames;
      } else if (t < 1300) {                                               // fade step: the centre dot
        assert(extra == 1 && o.shapes.back().w == 1 && o.shapes.back().h == 1); ++dotFrames;
      } else {                                                             // gone: identical to the page without it
        assert(extra == 0 && same(o, base));
      }
      // Only the sparkle was added; everything else is untouched, and it overlaps nothing on the page.
      for (size_t i = 0; i < base.shapes.size(); ++i) assert(o.shapes[i].x == base.shapes[i].x && o.shapes[i].y == base.shapes[i].y && o.shapes[i].w == base.shapes[i].w && o.shapes[i].h == base.shapes[i].h);
      assert(o.printed == base.printed);
      for (size_t i = base.shapes.size(); i < o.shapes.size(); ++i) {
        const auto& s = o.shapes[i];
        for (auto& ob : obst) assert(!hits(s.x, s.y, s.w, s.h, ob));
        assert(!(s.x < 40 + 20 && s.x + s.w > 40 && s.y < 30 + 8 && s.y + s.h > 30));   // nor the stand-in pet
      }
    }
    assert(plusFrames == 20 && dotFrames == 6);
    // ... and it stays gone, for hours, while the mesh stays busy or goes quiet.
    for (int k = 0; k < 400; ++k) { now += 7000; hear(now, 3); assert(same(page(PX, PY), base)); }

    // 3. Wherever the pet is, the sparkle is clear of it and of everything else on the page (or not drawn at all).
    reset(); play(15, 10, W, H, PX, PY); hear(now + 500, 30); now += 61000;
    int drawnCount = 0;
    for (int x = -4; x <= W + 4; x += 2) for (int y = 0; y <= H; y += 2) {
      auto sh = drawn(W, H, x, y);
      if (sh.empty()) continue;
      ++drawnCount; assert(sh.size() == 2);
      for (auto& s : sh) {
        for (auto& ob : obst) assert(!hits(s.x, s.y, s.w, s.h, ob));
        assert(s.x + s.w <= x - 24 || s.x >= x + 24 || s.y + s.h <= y - 17 || s.y >= y + 15);   // clear of the pet's box
      }
    }
    assert(drawnCount > 0);
    for (int x = 20; x <= W - 20; x += 2) for (int y = 34; y <= 42; ++y) assert(!drawn(W, H, x, y).empty());   // the pet's real swim range: always shown
    // A visitor on the tank: nothing is drawn.
    assert(drawn(W, H, PX, PY, false).empty());
  }

  // E-ink (run-time guard): every frame across a surge is identical to the page without the sparkle code,
  // and the sparkle state is never even touched -- on a 1-bit panel and on a (hypothetical) colour-flagged one.
  loRaFishEinkDisplay = true;
  for (bool colour : {false, true}) {
    loRaFishColorDisplay = colour;
    for (auto dims : {std::pair<int,int>{250,122}, {296,128}, {128,64}}) {
      const int W = dims.first, H = dims.second;
      Recorder base(W, H); fixedPage(base, W, H);
      reset();
      long frames = 0;
      for (int m = 0; m < 60; ++m) {                    // quiet, then a 30x surge for 12 minutes, then quiet again
        hear(now + 500, m >= 20 && m < 32 ? 300 : 10);
        for (int s = 0; s < 240; ++s) {                 // a frame every 250 ms, a whole minute of them
          now += 250; Recorder o(W, H); fixedPage(o, W, H); drawLoRaFishMeshSparkle(o, 60, 38, true);
          assert(same(o, base)); assert(!loRaFishMeshSense.sparkling()); ++frames;
          Recorder o2(W, H); fixedPage(o2, W, H); drawLoRaFishMeshSparkle(o2, 20, 20, false); assert(same(o2, base));
        }
      }
      assert(frames == 60 * 240);
    }
  }
  loRaFishColorDisplay = false;
  loRaFishEinkDisplay = false;
  puts("PASS monochrome: page identical to before whenever no sparkle is active (steady, 1->3, first 10 min, after it ends); sparkle = plus 1 s, dot, gone, in a corner clear of pet / text / battery / status bar / poop / bubbles");
  return 0;
}
'''


# What an e-ink BUILD looks like: the sparkle state does not exist, and nothing is ever drawn, whatever the flags say.
page_utils = mono_main[mono_main.index('static void fixedPage'):mono_main.index('static std::vector<Recorder::Shape> drawn')]
eink_main = helpers.replace('loRaFishMeshSense = LoRaFishMeshWeather::Sense(); ', '') + page_utils + r"""
int main() {
  static_assert(LORAFISH_EINK_BUILD == 1, "this program is the e-ink build");
  for (bool colour : {false, true}) for (bool eink : {false, true}) {
    loRaFishColorDisplay = colour; loRaFishEinkDisplay = eink;
    for (auto dims : {std::pair<int,int>{250,122}, {296,128}, {128,64}, {320,170}}) {
      const int W = dims.first, H = dims.second;
      Recorder base(W, H); fixedPage(base, W, H);
      reset();
      for (int m = 0; m < 60; ++m) {
        hear(now + 500, m >= 20 && m < 32 ? 300 : 10);
        for (int s = 0; s < 240; ++s) { now += 250; Recorder o(W, H); fixedPage(o, W, H); drawLoRaFishMeshSparkle(o, 60, 38, true); assert(same(o, base)); }
      }
    }
  }
  puts("PASS e-ink build: sparkle compiled out; every frame across a surge identical to the page without it");
  return 0;
}
"""


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
    for flags in ([], ['-DLILYGO_TDECK=1'], ['-DLORAGOTCHI_SPECIES_EDITION=1'],
                  ['-DDISPLAY_CLASS=SSD1306Display'], ['-DDISPLAY_CLASS=ST7789Display']):    # mono OLED and colour LCD builds keep their sparkle
        label = ' '.join(flags) or 'default'
        print(run(build(prelude + colour_main, tmp, 'colour', flags)), '[%s]' % label)
        print(run(build(prelude + mono_main, tmp, 'mono', flags)), '[%s]' % label)
    for cls in sorted(eink_classes):                                                         # every e-ink build: compiled out
        flags = ['-DDISPLAY_CLASS=' + cls]
        print(run(build(prelude + eink_main, tmp, 'eink', flags)), '[%s]' % ' '.join(flags))
        r = subprocess.run(['g++', '-std=c++17', '-DLORAGOTCHI_NATIVE_UI=1', '-I' + str(root), '-I' + str(root / 'src')] + flags + ['-fsyntax-only', '-x', 'c++', '-'],
                           input=prelude + 'int main(){ loRaFishMeshSense.sparkling(); }', capture_output=True, text=True)
        assert r.returncode != 0, 'the sparkle state must not exist in an e-ink build'
