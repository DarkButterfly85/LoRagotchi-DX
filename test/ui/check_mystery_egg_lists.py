#!/usr/bin/env python3
"""ANIMAL SET stays visible in normal builds; Mystery egg is selectable on every environment screen.

python3 test/ui/check_mystery_egg_lists.py   (Python 3 and g++; no firmware build, no hardware)

Real UITask handlers (same extraction as check_menu_navigation), built WITHOUT LORAGOTCHI_TESTER_FIRMWARE:
  DX-Pro   Options > Display shows 'Animal set'. Opening it gives the environment list
           Water, Air, Land, Mystery egg. Each environment's animal list has Mystery egg at the TOP,
           followed by that environment's animals in the old order. Picking Mystery egg stores an animal
           of that environment (any environment for the top-level egg); picking an animal stores it.
  Water    (single-environment species edition) the species list has Mystery egg first, then the animals.
Species IDs, the settings file and the egg wire format are not touched (see check_tester_options.py,
check_dxpro_registry.py and check_egg_adoption.py).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''
#include <string>
static std::vector<std::string> rows(UITask& task) {
  std::vector<std::string> out;
  task.display.clearBounds(); drawLoRaFishValuePicker(task.display);
  for (auto& s : task.display.printed) if (s.size() > 2 && (s[0] == '>' || s[0] == ' ') && s[1] == ' ') out.push_back(s);
  return out;
}
static void rewind() { while (loRaFishValuePicker.value() != 0) loRaFishValuePicker.move(); }
static void gotoValue(uint8_t v) { while (loRaFishValuePicker.value() != v) loRaFishValuePicker.move(); }
int main() {
  UITask task;
  loRaFishColorDisplay = false; loRaFishNeedsPetSetup = false; loRaFishNeedsAppearanceSetup = false;
  loRaFishMysterySeed = 0; loRaFishMysterySelected = false;
#if LORAGOTCHI_DXPRO
  static_assert(!kLoRaFishTesterFirmware, "normal build: tester gate off");
  // 1. Options > Display offers ANIMAL SET without the tester flag; Pet species / pet colours stay hidden.
  loRaFishSpecies = LoRaFishSpecies::Dog;
  loRaFishOrientationSupported = loRaFishPartialSupported = loRaFishDimSlowSupported = false;
  bool seen = false;
  for (uint8_t o = 0; o < loRaFishDisplayOptionCount(); ++o) {
    loRaFishDisplayOption = o; task.display.clearBounds(); drawLoRaFishDisplayMenu(task.display);
    for (auto& s : task.display.printed) { if (s == "Animal set") seen = true; assert(s != "Pet species" && s != "Pet colours"); }
  }
  assert(seen);
  loRaFishPage = 12; loRaFishDisplayOption = loRaFishDisplayRowIndex(LoRaFishDisplayRow::Species);
  assert(loRaFishDisplayRowAt(loRaFishDisplayOption) == LoRaFishDisplayRow::Species);
  task.handleLongPress(KEY_ENTER);                     // the real handler opens step one
  assert(loRaFishPage == 15 && loRaFishValuePicker.active() && loRaFishValuePicker.key() == LoRaFishSetting::SpeciesSet);
  // 2. Environment screen: Water, Air, Land, Mystery egg.
  assert(loRaFishValuePicker.count() == 4);
  rewind();
  auto env = rows(task);
  assert(env.size() == 4 && env[0] == "> Water" && env[1] == "  Air" && env[2] == "  Land" && env[3] == "  Mystery egg");
  cancelLoRaFishValue();
  for (uint8_t set = 0; set < LoRaFishSpecies::setCount; ++set) {
    loRaFishPage = 15; openLoRaFishValue(LoRaFishSetting::Species);
    gotoValue(set);
    selectLoRaFishValue();                             // choose the environment
    assert(loRaFishValuePicker.active() && loRaFishValuePicker.key() == LoRaFishSetting::Species);
    assert(loRaFishValuePicker.count() == LoRaFishSpecies::setSize(set) + 1);
    rewind();
    auto list = rows(task);
    assert(!list.empty() && list[0] == "> Mystery egg");   // Mystery egg is at the TOP of this environment's list
    assert(list.size() > 1 && list[1] == std::string("  ") + LoRaFishSpecies::label(LoRaFishSpecies::setSelectionId(set, 0)));
    selectLoRaFishValue();                             // Mystery egg of this environment
    assert(loRaFishMysterySelected && loRaFishMysterySeed && LoRaFishSpecies::setOf(loRaFishSpecies) == set);
    assert(loRaFishSpecies == LoRaFishSpecies::setMystery(loRaFishMysterySeed, set));
    // A named animal (position k is animal k-1) stores exactly that animal and clears the egg flag.
    for (int k : {1, 2, (int)LoRaFishSpecies::setSize(set)}) {
      loRaFishPage = 15; openLoRaFishValue(LoRaFishSetting::Species);
      gotoValue(set); selectLoRaFishValue();
      gotoValue(k); selectLoRaFishValue();
      assert(!loRaFishMysterySelected && loRaFishSpecies == LoRaFishSpecies::setSelectionId(set, k - 1));
    }
  }
  // 3. The fourth environment entry: Mystery egg across every environment.
  loRaFishPage = 15; openLoRaFishValue(LoRaFishSetting::Species);
  gotoValue(3); selectLoRaFishValue();
  assert(!loRaFishValuePicker.active() && loRaFishMysterySelected);
  assert(loRaFishSpecies == LoRaFishSpecies::anyMystery(loRaFishMysterySeed) && LoRaFishSpecies::known(loRaFishSpecies));
  bool hit[3] = {false, false, false};                   // all three environments are reachable from the one egg
  for (uint32_t seed = 1; seed < 4000; ++seed) hit[LoRaFishSpecies::setOf(LoRaFishSpecies::anyMystery(seed))] = true;
  assert(hit[0] && hit[1] && hit[2]);
  loRaFishPage = 12; openLoRaFishValue(LoRaFishSetting::Species);
  assert(loRaFishValuePicker.value() == LoRaFishSpecies::setOf(loRaFishSpecies));   // preselects the current environment
  cancelLoRaFishValue();
#else
  // Single-environment species edition: Mystery egg first, then the animals in the old order.
  openLoRaFishValue(LoRaFishSetting::Species);
  assert(loRaFishValuePicker.key() == LoRaFishSetting::Species && loRaFishValuePicker.count() == LoRaFishSpecies::selectableCount + 1);
  rewind(); task.display.clearBounds(); drawLoRaFishValuePicker(task.display);
  bool egg = false;
  for (auto& s : task.display.printed) if (s == "Mystery egg") egg = true;
  assert(egg);
  selectLoRaFishValue();
  assert(loRaFishMysterySelected && loRaFishMysterySeed && loRaFishSpecies == LoRaFishSpecies::mystery(loRaFishMysterySeed));
  openLoRaFishValue(LoRaFishSetting::Species);
  assert(loRaFishValuePicker.value() == 0);               // egg selected -> cursor on the egg
  gotoValue(1); selectLoRaFishValue();
  assert(!loRaFishMysterySelected && loRaFishSpecies == LoRaFishSpecies::selectionId(0));
  openLoRaFishValue(LoRaFishSetting::Species);
  assert(loRaFishValuePicker.value() == 1);               // an animal selected -> cursor on that animal
  cancelLoRaFishValue();
#endif
  puts("ok");
}
'''


def build_and_run(pro):
    import check_menu_navigation as f
    code = '\n'.join(f.parts[:-1]) + f.parts[-1].split('int main(){')[0] + MAIN
    code = code.replace('class UITask;\n', 'class UITask;\nstatic uint8_t loRaFishProSet = 0;\n', 1)
    with tempfile.TemporaryDirectory(prefix='mystery-egg-') as t:
        cpp = Path(t) / 'egg.cpp'
        cpp.write_text(code)
        out = Path(t) / 'egg'
        cmd = ['g++', '-std=c++17', '-w', '-DPIN_USER_BTN=0', '-DLORAGOTCHI_WATER_EDITION=' + ('0' if pro else '1'),
               '-DLORAGOTCHI_AIR_EDITION=0', '-I', str(ROOT), '-I', str(ROOT / 'src'), str(cpp), '-o', str(out)]
        if pro:
            cmd.insert(2, '-DLORAGOTCHI_DXPRO=1')
        subprocess.run(cmd, check=True, timeout=240)
        res = subprocess.run([str(out)], check=True, timeout=60, capture_output=True, text=True)
        assert res.stdout.strip().endswith('ok'), res.stdout


if __name__ == '__main__':
    build_and_run(True)
    print('PASS DX-Pro: Animal set visible without tester flag; environments Water/Air/Land/Mystery egg; Mystery egg first in each list')
    build_and_run(False)
    print('PASS Water edition: Mystery egg first in the species list')
