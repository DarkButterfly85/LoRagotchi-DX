#!/usr/bin/env python3
"""Accurate battery: Li-ion curve + time-left on colour screens; mono/e-ink unchanged.

python3 test/ui/check_accurate_battery.py (Python 3 and g++). No hardware, no
battery, no screen. Three parts:
  1. LoRaFishBattery.h on its own: known voltages -> known percentages,
     interpolation, clamping, and the time-left estimator on made-up discharges.
  2. Monochrome/e-ink: the real drawLoRaFishTankBattery and drawLoRaFishRFMonitor
     are run over every voltage and compared, shape by shape and word by word,
     with frozen copies of the code from before this change.
  3. Colour: the same real functions show the curve percentage and the estimate.
"""
from pathlib import Path
import subprocess, tempfile

root = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------- part 1
unit = r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include "examples/companion_radio/ui-new/LoRaFishBattery.h"
using namespace LoRaFishBattery;
static const uint32_t MIN = 60000UL;

int main() {
  // Known voltages -> known percentages (the published curve points).
  struct { uint16_t mv; int pct; } known[] = {
    {4200,100},{4150,95},{4110,90},{4080,85},{4020,80},{3980,75},{3950,70},{3910,65},{3870,60},
    {3850,55},{3840,50},{3820,45},{3800,40},{3790,35},{3770,30},{3750,25},{3730,20},{3710,15},
    {3690,10},{3610,5},{3300,0}};
  for (auto& k : known) { if (percent(k.mv) != k.pct) { printf("%u mV -> %d, wanted %d\n", k.mv, percent(k.mv), k.pct); return 1; } }
  // Between points it interpolates: halfway 4080..4110 (85..90) is 87.5 -> 88; 3690..3610 etc.
  assert(tenthsPercent(4095) == 875 && percent(4095) == 88);
  assert(tenthsPercent(3845) == 525);
  assert(tenthsPercent(3450) == 20 && tenthsPercent(3530) == 35);
  // Outside the range it clamps; the curve never goes backwards.
  assert(percent(0) == 0 && percent(2900) == 0 && percent(3299) == 0 && percent(4300) == 100 && percent(65535) == 100);
  int last = -1;
  for (int mv = 2500; mv <= 4500; ++mv) { int t = tenthsPercent((uint16_t)mv); assert(t >= last && t <= 1000); last = t; }
  // It is NOT the old straight line in the middle (that read 44% at 3.7 V; a real cell is nearly empty-ish there).
  assert(percent(3700) == 13 && legacyPercent(3700) == 44);
  // The old line is unchanged: 3.3 V = 0, 4.2 V = 100, truncating integer maths.
  assert(legacyPercent(3300) == 0 && legacyPercent(4200) == 100 && legacyPercent(3750) == 50 && legacyPercent(0) == 0 && legacyPercent(5000) == 100);
  for (int mv = 0; mv <= 65535; ++mv) {
    int want = (mv - 3300) * 100 / 900; want = want < 0 ? 0 : want > 100 ? 100 : want;
    assert(legacyPercent((uint16_t)mv) == want);
  }

  // Time left: steady 10% per hour from 80%.
  { Tracker t; char text[16];
    assert(t.minutesLeft() == -1);
    // 80% = 4020 mV; 70% = 3950 mV. Feed voltages that sit exactly on curve points hour by hour.
    t.sample(0 * MIN, 4020, false);
    assert(t.minutesLeft() == -1);                     // too little history
    t.sample(2 * MIN, 3980, false);                    // too soon: ignored (5 min cadence)
    assert(t.n == 1);
    t.sample(5 * MIN, 4020, false); t.sample(10 * MIN, 4020, false); t.sample(15 * MIN, 4020, false);
    assert(t.minutesLeft() == -1);                     // under 20 min of history
    t.sample(20 * MIN, 4020, false);
    assert(t.minutesLeft() == -1);                     // flat: no measurable drain
    Tracker d;                                         // genuine slow drain: 800 -> 700 tenths in 60 min
    uint16_t mvs[] = {4020, 4015, 4005, 3995, 3985, 3980, 3975, 3970, 3965, 3960, 3955, 3950};
    for (int i = 0; i < 12; ++i) d.sample(i * 5 * MIN, mvs[i], false);
    int32_t left = d.minutesLeft();
    assert(left > 300 && left < 520);                  // 70%/ (~10%/h) ~ 6-8 h
    formatLeft(d, text, sizeof text); assert(text[0] == '~' && strchr(text, 'h'));
    // Faster drain -> shorter time
    Tracker f; for (int i = 0; i < 12; ++i) f.sample(i * 5 * MIN, (uint16_t)(4150 - i * 20), false);
    assert(f.minutesLeft() > 0 && f.minutesLeft() < left);
    // Plugging in forgets everything and says CHG
    d.sample(70 * MIN, 4100, true); assert(d.n == 0 && d.minutesLeft() == -1);
    formatLeft(d, text, sizeof text); assert(!strcmp(text, "CHG"));
    // A jump up (charged while unnoticed) restarts the history
    Tracker j; for (int i = 0; i < 5; ++i) j.sample(i * 5 * MIN, 3800, false); j.sample(25 * MIN, 4100, false); assert(j.n == 1);
    // Unknown -> "--"
    Tracker u; formatLeft(u, text, sizeof text); assert(!strcmp(text, "--"));
    // Very slow drain is capped, not overflowed
    Tracker s; for (int i = 0; i < 12; ++i) s.sample(i * 5 * MIN, i == 11 ? 3999 : 4000, false);
    formatLeft(s, text, sizeof text); assert(!strcmp(text, ">99h") || text[0] == '~' || !strcmp(text, "--"));
    // Time counter wrapping around 2^32 ms does not break it
    Tracker w; uint32_t base = 0xFFFFFFFFUL - 30 * MIN;
    for (int i = 0; i < 12; ++i) w.sample(base + i * 5 * MIN, mvs[i], false);
    assert(w.n == 12 && w.minutesLeft() > 300 && w.minutesLeft() < 520);
    // Ring buffer keeps the newest 12
    for (int i = 12; i < 30; ++i) w.sample(base + i * 5 * MIN, 3950, false);
    assert(w.n == 12);
  }
  { char t[16];
    struct { uint16_t remaining, drop; const char* want; } cases[] = {
      {100,600,"~5m"},{400,300,"~40m"},{590,300,"~59m"},{600,300,"~1.0h"},{550,50,"~5.5h"},
      {599,30,"~9.9h"},{600,30,"~10h"},{500,10,"~25h"},{900,1,">99h"}};
    for (auto& c : cases) {
      Tracker x; x.n = 4; x.charging = false;   // 4 readings over 30 min: minutes left = remaining * 30 / drop
      x.t[0] = 0; x.t[1] = 10 * MIN; x.t[2] = 20 * MIN; x.t[3] = 30 * MIN;
      x.p[0] = c.remaining + c.drop; x.p[1] = x.p[0]; x.p[2] = c.remaining; x.p[3] = c.remaining;
      formatLeft(x, t, sizeof t);
      if (strcmp(t, c.want)) { printf("wanted %s got %s\n", c.want, t); return 1; }
    }
  }
  printf("PASS curve points, interpolation, clamping, legacy line, time-left estimator\n");
  return 0;
}
'''

# ---------------------------------------------------------------- parts 2 and 3
head = (root / 'test/ui/check_native_pages.py').read_text()
head = head[:head.index("code+=block('static int loRaFishBatteryPercent(')")]
ns = {'__file__': str(root / 'test/ui/check_native_pages.py'), '__name__': 'native_pages_head'}
exec(compile(head, 'check_native_pages_head', 'exec'), ns)
prelude, block = ns['code'], ns['block']
legacy = (root / 'test/ui/legacy_battery_pages.inc').read_text()

TRACE = r'''
static void dump(const char* tag, int mv, Recorder& out) {
  printf("%s %d:", tag, mv);
  for (auto& s : out.shapes) printf(" [%d,%d,%d,%d,%d]", s.x, s.y, s.w, s.h, (int)s.outline);
  for (auto& p : out.printed) printf(" {%s}", p.c_str());
  printf("\n");
}
static void sweep(UITask& task, const char* tag) {
  for (int mv = 0; mv <= 4400; mv += (mv > 3200 && mv < 4300) ? 10 : 400) {
    battery = (uint16_t)mv;
    for (const char* clock : {"23:59", "9:05"}) {
      Recorder out(128, 64); drawLoRaFishTankBattery(out, &task, clock); dump(tag, mv, out);
    }
    for (unsigned age : {0u, 1234u}) {
      lorafish_last_rf_ms = age; ++lorafish_rf_sample_seq; loRaFishRfHistoryCount = 0;
      Recorder out(320, 170); LoRaFishLayout::Page card(out); drawLoRaFishRFMonitor(card, &task); dump("RF", mv, out);
    }
  }
}
'''
legacy_prog = prelude + '\n' + block('static void drawLoRaFishHeader(') + '\n' + legacy + '\n' + TRACE + r'''
int main() { UITask task; sweep(task, "TANK"); return 0; }
'''
new_prog = prelude + '\n' + block('static int loRaFishBatteryPercent(') + '\nstatic LoRaFishBattery::Tracker loRaFishBatteryTracker;\n' \
    + block('static void drawLoRaFishBatteryLeft(') + '\n' + block('static void drawLoRaFishHeader(') + '\n' \
    + block('static void drawLoRaFishTankBattery(') + '\n' + block('static void drawLoRaFishRFMonitor(') + '\n' + TRACE + r'''
int main() {
  UITask task;
  const char* mode = getenv("BATT_MODE");
  loRaFishColorDisplay = mode && mode[0] == 'c';
  if (loRaFishColorDisplay) {
    // Feed a believable discharge (about 10% an hour) so an estimate is on screen.
    uint16_t mvs[] = {4020, 4015, 4005, 3995, 3985, 3980, 3975, 3970, 3965, 3960, 3955, 3950};
    for (int i = 0; i < 12; ++i) loRaFishBatteryTracker.sample((uint32_t)i * 300000UL, mvs[i], false);
  }
  sweep(task, "TANK");
  return 0;
}
'''

def build_and_run(prog, tmp, name, flags, env=None):
    cpp = tmp / (name + '.cpp'); cpp.write_text(prog); exe = tmp / name
    subprocess.run(['g++', '-std=c++17', '-DLORAGOTCHI_NATIVE_UI=1', '-I' + str(root), '-I' + str(root / 'src')] + flags + [str(cpp), '-o', str(exe)], check=True)
    import os
    e = dict(os.environ); e.update(env or {})
    return subprocess.run([str(exe)], check=True, capture_output=True, text=True, env=e).stdout

with tempfile.TemporaryDirectory(prefix='lrx-battery-') as t:
    tmp = Path(t)
    (tmp / 'unit.cpp').write_text(unit)
    subprocess.run(['g++', '-std=c++17', '-Wall', '-I' + str(root), str(tmp / 'unit.cpp'), '-o', str(tmp / 'unit')], check=True)
    print(subprocess.run([str(tmp / 'unit')], check=True, capture_output=True, text=True).stdout.strip())
    for flags in ([], ['-DLILYGO_TDECK=1'], ['-DLORAGOTCHI_SPECIES_EDITION=1']):
        label = ' '.join(flags) or 'default'
        old = build_and_run(legacy_prog, tmp, 'old', flags)
        mono = build_and_run(new_prog, tmp, 'mono', flags, {'BATT_MODE': 'mono'})
        colour = build_and_run(new_prog, tmp, 'colour', flags, {'BATT_MODE': 'colour'})
        assert old.count('\n') > 100
        if old != mono:
            a, b = old.splitlines(), mono.splitlines()
            for x, y in zip(a, b):
                if x != y: raise SystemExit('MONO CHANGED (%s):\n old %s\n new %s' % (label, x, y))
            raise SystemExit('MONO CHANGED (line count)')
        print('PASS monochrome/e-ink battery icon and RF monitor identical to before over %d drawings [%s]' % (old.count('\n'), label))
        # Colour: ends of the scale agree with the old line, the middle does not, and the estimate is on screen.
        ol, cl = old.splitlines(), colour.splitlines()
        assert len(ol) == len(cl)
        diff = [i for i, (o, c) in enumerate(zip(ol, cl)) if o != c]
        assert diff, 'colour output should differ somewhere (curve + estimate)'
        assert any('{~' in c or '{>99h}' in c for c in cl), 'estimate text missing on colour RF monitor'
        assert not any('{~' in o or '{--}' in o or '{CHG}' in o for o in ol), 'old code must not show an estimate'
        assert any('BAT 13%' in c for c in cl if c.startswith('RF 3700:')), 'curve percentage missing at 3.70 V (13%)'
        assert any('BAT 44%' in o for o in ol if o.startswith('RF 3700:')), 'legacy percentage at 3.70 V changed'
        for mv in (0, 3300, 4200, 4400):
            for o, c in zip(ol, cl):
                if o.startswith('TANK %d:' % mv): assert o == c, 'tank icon should agree at %d mV: %s vs %s' % (mv, o, c)
        print('PASS colour: curve percentage + time-left estimate drawn, ends of scale agree with the old line [%s]' % label)
