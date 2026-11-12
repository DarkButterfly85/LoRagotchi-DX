#!/usr/bin/env python3
"""Options menu hides the pet colour and plain pet species rows unless LORAGOTCHI_TESTER_FIRMWARE is defined.
The DX-Pro ANIMAL SET row (step one of the species picker) is visible in every build.

python3 test/ui/check_tester_options.py   (Python 3 and g++; no firmware build, no hardware)

A  the row list itself (LoRaFishMenu.h) is compiled with and without the flag and checked for every
   board capability combination: hidden rows absent, order of the rest unchanged, no gaps, navigation
   (a modulo over the visible count) can never land on a hidden row, hidden rows map back to row 0.
B  the real UITask handlers are compiled (same extraction as check_menu_navigation) with and without
   the flag: the Display list never offers pet colours or species, no picker for them can be opened,
   every visible row opens and returns to its own position, the stored pet values are untouched, and
   pet setup still offers the species and colour choices.
C  the settings file encoding is byte-for-byte the code on origin/orion (skipped with a note if git
   history is not available), and the flag is not set by any build definition.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parents[2]
UI_PATH = 'examples/companion_radio/ui-new/UITask.cpp'
UI = (ROOT / UI_PATH).read_text()
FLAG = 'LORAGOTCHI_TESTER_FIRMWARE'


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, timeout=240, **kw)


# ---- A: row list --------------------------------------------------------------------------
ROWS_CPP = r'''
#include <cassert>
#include <cstdio>
#include <vector>
#include "examples/companion_radio/ui-new/LoRaFishMenu.h"
using R = LoRaFishDisplayRow;
int main() {
#ifdef LORAGOTCHI_TESTER_FIRMWARE
  const bool tester = true;
  static_assert(kLoRaFishTesterFirmware, "flag must switch the gate on");
#else
  const bool tester = false;
  static_assert(!kLoRaFishTesterFirmware, "gate must default to off");
#endif
  for (int mask = 0; mask < 64; ++mask) {
    LoRaFishDisplayRows rows;
    rows.colourDisplay = mask & 1; rows.speciesEdition = mask & 2;
    rows.orientation = mask & 4; rows.partial = mask & 8; rows.dimSlow = mask & 16; rows.animalSet = mask & 32;
    assert(rows.tester == tester);
    // Expected list in the legacy order, with the pet rows removed unless tester.
    std::vector<R> want = {R::Timeout, R::Brightness, R::Theme};
    if (!rows.colourDisplay || tester) want.push_back(R::Colour);   // mono "Screen colour" always stays
    want.push_back(R::Rendering);
    if (rows.speciesEdition && (rows.animalSet || tester)) want.push_back(R::Species);
    if (rows.orientation) want.push_back(R::Orientation);
    if (rows.partial) want.push_back(R::DisplayUpdate);
    if (rows.dimSlow) want.push_back(R::DimSlow);
    assert(rows.count() == want.size());
    for (unsigned i = 0; i < want.size(); ++i) {
      assert(rows.at(i) == want[i]);                 // no blank rows, order unchanged
      assert(rows.index(want[i]) == i);              // stable identity <-> position
    }
    const bool petColoursHidden = rows.colourDisplay && !tester;
    assert(rows.available(R::Colour) == !petColoursHidden);
    assert(rows.available(R::Species) == (rows.speciesEdition && (rows.animalSet || tester)));
    if (rows.speciesEdition && rows.animalSet) assert(rows.available(R::Species));   // ANIMAL SET never hidden
    if (!rows.available(R::Species)) assert(rows.index(R::Species) == 0);
    // Navigation as the menu does it: (value +/- 1) modulo count never reaches a hidden row.
    const unsigned n = rows.count();
    for (unsigned start = 0; start < n; ++start) {
      unsigned next = (start + 1) % n, prev = (start + n - 1) % n;
      for (unsigned p : {next, prev}) {
        assert(p < n);
        const R r = rows.at(p);
        assert(rows.available(r));
        if (!tester && !rows.animalSet) assert(r != R::Species);
        if (!tester && rows.colourDisplay) assert(r != R::Colour);
      }
    }
  }
  puts("ok");
}
'''


def part_a():
    with tempfile.TemporaryDirectory(prefix='tester-rows-') as t:
        src = Path(t) / 'rows.cpp'
        src.write_text(ROWS_CPP)
        for flagged in (False, True):
            out = Path(t) / ('rows%d' % flagged)
            cmd = ['g++', '-std=c++17', '-I', str(ROOT), str(src), '-o', str(out)]
            if flagged:
                cmd.insert(2, '-D%s=1' % FLAG)
            run(cmd)
            res = run([str(out)], capture_output=True, text=True)
            assert res.stdout.strip() == 'ok'
    print('PASS A  row list: hidden without the flag, present with it, order kept, navigation skips hidden rows')


# ---- B: real UITask handlers ----------------------------------------------------------------
B_MAIN = r'''
#include <set>
static std::set<std::string> labels;
static void collectLabels(UITask& task) {
  for (uint8_t option = 0; option < loRaFishDisplayOptionCount(); ++option) {
    loRaFishDisplayOption = option;
    task.display.clearBounds(); drawLoRaFishDisplayMenu(task.display);
    for (auto& s : task.display.printed) if (s != ">") labels.insert(s);
  }
}
static bool petKey(LoRaFishSetting k) {
  return (!LORAGOTCHI_DXPRO && k == LoRaFishSetting::Species) || k == LoRaFishSetting::Scales ||
         k == LoRaFishSetting::Body || k == LoRaFishSetting::Eyes;
}
int main() {
  UITask task;
#ifdef LORAGOTCHI_TESTER_FIRMWARE
  const bool tester = true;
#else
  const bool tester = false;
#endif
  const bool speciesEdition = LORAGOTCHI_SPECIES_EDITION != 0;
  for (bool colour : {false, true}) {
    loRaFishColorDisplay = colour; loRaFishNeedsPetSetup = false; loRaFishNeedsAppearanceSetup = false;
    loRaFishOrientationSupported = true; loRaFishPartialSupported = true; loRaFishDimSlowSupported = true;
    loRaFishScaleColor = 2; loRaFishColor = 3; loRaFishEyeColor = 4; loRaFishSpecies = 1;
    const auto scale = loRaFishScaleColor; const auto body = loRaFishColor; const auto eyes = loRaFishEyeColor; const auto species = loRaFishSpecies;
    const bool petColourVisible = !colour || tester, speciesVisible = speciesEdition && (tester || LORAGOTCHI_DXPRO);
    labels.clear(); collectLabels(task);
    assert(labels.count("Screen timeout") && labels.count("Brightness") && labels.count("Firmware theme"));
    assert(labels.count("Game rendering") && labels.count("Orientation") && labels.count("Display update") && labels.count("Slow when dimmed"));
    assert(labels.count("Pet colours") == (colour && tester));
    assert(labels.count("Screen colour") == !colour);          // mono screen colour is not a pet option
    assert(labels.count(LORAGOTCHI_DXPRO ? "Animal set" : "Pet species") == speciesVisible);
    assert(labels.count(LORAGOTCHI_DXPRO ? "Pet species" : "Animal set") == 0);
    const unsigned expected = 3 + petColourVisible + 1 + speciesVisible + 3;
    assert(loRaFishDisplayOptionCount() == expected);
    // Walk the list with the real Next key, open every row and come back to it.
    loRaFishPage = 5; loRaFishOption = LoRaFishOption::Display;
    task.handleLongPress(KEY_ENTER);
    assert(loRaFishPage == 12 && loRaFishDisplayOption == 0);
    bool sawPetColours = false, sawSpecies = false;
    for (unsigned pos = 0; pos < expected; ++pos) {
      assert(loRaFishPage == 12 && loRaFishDisplayOption == pos);
      task.display.clearBounds(); drawLoRaFishDisplayMenu(task.display);
      assert(!task.display.printed.empty());                   // never a blank list
      task.handleLongPress(KEY_ENTER);
      assert(loRaFishPage != 12);
      if (loRaFishPage == 9) sawPetColours = true;
      if (loRaFishValuePicker.active()) {
        if (loRaFishValuePicker.key() == LoRaFishSetting::Species || loRaFishValuePicker.key() == LoRaFishSetting::SpeciesSet) {
          sawSpecies = true;   // DX-Pro opens ANIMAL SET (step one); other species builds open the species list
          assert(LORAGOTCHI_DXPRO ? loRaFishValuePicker.key() == LoRaFishSetting::SpeciesSet : loRaFishValuePicker.key() == LoRaFishSetting::Species);
        }
        if (!tester) assert(!petKey(loRaFishValuePicker.key()));
      }
      task.handleDoubleClick(KEY_PREV);
      assert(loRaFishPage == 12 && !loRaFishValuePicker.active());
      assert(loRaFishDisplayOption == pos);                    // Back lands on the row that was opened
      shortPress(KEY_NEXT);
    }
    assert(loRaFishDisplayOption == 0);                        // wrapped past the last visible row
    shortPress(KEY_PREV);
    assert(loRaFishDisplayOption == expected - 1);             // and backwards from the first
    assert(sawPetColours == (colour && tester));
    assert(sawSpecies == speciesVisible);
    // Hidden settings keep their stored value.
    assert(loRaFishScaleColor == scale && loRaFishColor == body && loRaFishEyeColor == eyes && loRaFishSpecies == species);
    // A stale index past the visible rows selects nothing.
    loRaFishPage = 12; loRaFishDisplayOption = expected;
    task.handleLongPress(KEY_ENTER);
    assert(loRaFishPage == 12 && !loRaFishValuePicker.active() && loRaFishDisplayOption == 0);
    task.handleDoubleClick(KEY_PREV);
    loRaFishPage = 0;
    // Pet setup is not part of Options and keeps its choices in every build.
    if (colour) {
      loRaFishNeedsPetSetup = true; loRaFishPage = LORAFISH_PET_SETUP_PAGE; loRaFishPetSetupField = 2;
      task.handleLongPress(KEY_ENTER);
      assert(loRaFishPage == 9);                               // 'Choose colours'
      loRaFishNeedsPetSetup = false; loRaFishPage = 0;
    }
#if LORAGOTCHI_SPECIES_EDITION
    loRaFishNeedsPetSetup = true; loRaFishPage = LORAFISH_PET_SETUP_PAGE; loRaFishPetSetupField = 0;
    task.handleLongPress(KEY_ENTER);
    assert(loRaFishValuePicker.active() && (loRaFishValuePicker.key() == (LORAGOTCHI_DXPRO ? LoRaFishSetting::SpeciesSet : LoRaFishSetting::Species)));
    cancelLoRaFishValue(); loRaFishNeedsPetSetup = false; loRaFishPage = 0;
#endif
  }
  puts("ok");
}
'''


def part_b():
    import check_menu_navigation as f
    code = '\n'.join(f.parts[:-1]) + f.parts[-1].split('int main(){')[0] + B_MAIN
    code = code.replace('class UITask;\n', 'class UITask;\nstatic uint8_t loRaFishProSet = 0;   // DX-Pro set chosen in picker step one\n', 1)
    with tempfile.TemporaryDirectory(prefix='tester-options-') as t:
        cpp = Path(t) / 'options.cpp'
        cpp.write_text(code)
        for edition in ('0', '1', 'pro'):                               # 0: DX (no species row), 1: species edition
            for flagged in (False, True):
                out = Path(t) / ('options-%s-%d' % (edition, flagged))
                cmd = ['g++', '-std=c++17', '-w', '-DPIN_USER_BTN=0', '-DLORAGOTCHI_WATER_EDITION=' + ('0' if edition == 'pro' else edition),
                       '-DLORAGOTCHI_AIR_EDITION=0', '-I', str(ROOT), '-I', str(ROOT / 'src'), str(cpp), '-o', str(out)]
                if edition == 'pro':
                    cmd.insert(2, '-DLORAGOTCHI_DXPRO=1')
                if flagged:
                    cmd.insert(2, '-D%s=1' % FLAG)
                run(cmd)
                res = run([str(out)], capture_output=True, text=True)
                assert res.stdout.strip().endswith('ok'), res.stdout
    print('PASS B  real handlers: DX, species and DX-Pro editions, mono and colour, with and without the flag')


# ---- C: stored format and build flags -----------------------------------------------------------
def function_text(text, signature):
    a = text.index(signature)
    b = text.index('\n}\n', a)
    return text[a:b + 3]


def part_c():
    assert 'LORAFISH_SETTINGS_SIZE = 112;' in UI
    enc = function_text(UI, 'static void encodeLoRaFishSettings(')
    base = subprocess.run(['git', '-C', str(ROOT), 'show', 'origin/orion:' + UI_PATH], capture_output=True, text=True)
    if base.returncode == 0:
        old = base.stdout
        assert enc == function_text(old, 'static void encodeLoRaFishSettings('), 'settings encoder changed'
        assert function_text(UI, 'static void loadLoRaFishSettings(') == function_text(old, 'static void loadLoRaFishSettings('), 'settings loader changed'
        m = re.search(r'LORAFISH_SETTINGS_SIZE = \d+;', old)
        assert m and m.group(0) in UI, 'settings size changed'
        note = 'identical to origin/orion'
    else:
        note = 'origin/orion not available, size pinned at 112 only'
    # Hidden settings are still written: the encoder still reads all four pet values.
    for field in ('loRaFishScaleColor', 'loRaFishColor', 'loRaFishEyeColor', 'loRaFishSpecies'):
        assert field in enc, field
    # No build definition may switch the tester gate on.
    for p in list(ROOT.glob('**/platformio.ini')) + list(ROOT.glob('boards/**/*.json')) + list(ROOT.glob('.github/**/*.yml')) + [ROOT / 'platformio.ini']:
        if '.pio' in p.parts or not p.is_file():
            continue
        assert FLAG not in p.read_text(errors='ignore'), '%s defines %s' % (p, FLAG)
    assert '#define ' + FLAG not in UI
    print('PASS C  settings encoding %s; flag is not defined by any build file' % note)


if __name__ == '__main__':
    part_a()
    part_b()
    part_c()
