#!/usr/bin/env python3
"""The pet identity (/lorafish.id) inside the real UITask.cpp functions, on RAM files, both storage branches.

python3 test/ui/check_lorafish_identity_ui.py     (Python 3 and g++; no firmware build, no hardware)

Reuses the production save/load/reset code that check_fish_lifecycle.py cuts out of UITask.cpp, plus the
identity block (loadLoRaFishIdentity, syncLoRaFishIdentity, setLoRaFishPetName) and loRaFishDisplayName.
  - an existing pet with no /lorafish.id: nothing is created, nothing changes (a, e)
  - a name set with the "nova petname" setter creates /lorafish.id only; /lorafish.dat is byte for byte
    the same; after a reboot the name, species and colours are back (b)
  - species/colours changed later follow into the file at the next settings save (b)
  - a damaged /lorafish.id changes nothing and does not crash (c); a species this firmware does not know
    is not overwritten by a stand-in
  - a name longer than 16 is refused through the same setter (d)
  - a reset pet loses the name; the header shows the name when there is one, the radio name otherwise
"""
from pathlib import Path
import subprocess, tempfile
import check_fish_lifecycle as f

code = '\n'.join(f.parts[:-1]) + f.parts[-1].split('int main() {', 1)[0]
code = code.replace('#include <algorithm>', '#include <algorithm>\n#include "examples/companion_radio/ui-new/LoRaFishText.h"', 1)
code += '\nstatic const char* loRaFishMeshNodeName = "Radio";\n' + f.block('static const char* loRaFishDisplayName(')
code += r'''
using LoRaFishIdentity::NameResult;
static std::vector<uint8_t> bytesOf(const char* p) { return files.count(p) ? files[p] : std::vector<uint8_t>(); }
int main() {
  static_assert(sizeof(LoRaFishState) == 32, "pet record");
  // a. an existing pet, no identity file: saving and rebooting never creates one
  resetAt(5000); loRaFishColor = 4; loRaFishScaleColor = 5; loRaFishEyeColor = 6;
  saveLoRaFishSettings(); saveLoRaFish();
  assert(!files.count("/lorafish.id") && !files.count("/lorafish.idt") && !files.count("/lorafish.idb"));
  const auto petBefore = bytesOf("/lorafish.dat");
  assert(petBefore.size() == 32 + 8);                       // 32 byte record + SafeSave trailer, as before
  reboot();
  assert(fish.ageMinutes == 5000 && loRaFishColor == 4 && loRaFishScaleColor == 5 && loRaFishEyeColor == 6 && !loRaFishIdName[0]);
  saveLoRaFishSettings(); saveLoRaFish();
  assert(!files.count("/lorafish.id"));
  assert(!strcmp(loRaFishDisplayName(), "Radio"));          // no pet name: the radio name, as today
  puts("PASS a: existing pet without /lorafish.id behaves unchanged and no file is created");

  // b. a name creates the file (only that file) and survives a reboot with the species and colours
  const auto cfgBefore = bytesOf("/lorafish.cfg");
  loRaFishSpecies = LoRaFishSpecies::Dog;                   // set before the name, saved with the settings
  saveLoRaFishSettings(); saveLoRaFish();
  assert(files.count("/lorafish.id"));                      // species changed from the start-up pet: file created
  files.erase("/lorafish.id"); files.erase("/lorafish.idb"); reboot();   // start again with no file, species Dog from the cfg
  assert(loRaFishSpecies == LoRaFishSpecies::Dog && !files.count("/lorafish.id"));
  const auto petFile = bytesOf("/lorafish.dat");
  const auto cfgFile = bytesOf("/lorafish.cfg");
  assert(setLoRaFishPetName("Bubbles") == LoRaFishIdentity::NameOk);
  assert(files.count("/lorafish.id") && files["/lorafish.id"].size() == 35);
  assert(bytesOf("/lorafish.dat") == petFile && bytesOf("/lorafish.cfg") == cfgFile);   // nothing else written
  assert(!strcmp(loRaFishDisplayName(), "Bubbles"));
  loRaFishColor = 100; loRaFishScaleColor = 8; loRaFishEyeColor = 247; loRaFishSpecies = LoRaFishSpecies::Kitsune;
  saveLoRaFishSettings();                                   // species and colours follow into the file
  reboot();
  assert(!strcmp(loRaFishIdName, "Bubbles") && loRaFishSpecies == LoRaFishSpecies::Kitsune);
  assert(loRaFishColor == 100 && loRaFishScaleColor == 8 && loRaFishEyeColor == 247);
  assert(fish.ageMinutes == 5000 && sizeof(fish) == 32);
  { uint8_t rec[LoRaFishSafeSave::kMaxRecord]; size_t n = 0;
    assert(LoRaFishSafeSave::load(loRaFishPetStore, loRaFishPetRecordValid, rec, &n) == LoRaFishSafeSave::Main && n == 32); }
  puts("PASS b: name, species and colours round-trip through /lorafish.id; the pet record and settings are untouched by the name");

  // c. a damaged file changes nothing and cannot crash the load
  for (size_t at = 0; at < 35; ++at) {
    auto good = files["/lorafish.id"]; auto bakGood = files.count("/lorafish.idb") ? files["/lorafish.idb"] : std::vector<uint8_t>();
    files.erase("/lorafish.idb");
    files["/lorafish.id"][at] ^= 0x10;
    reboot();
    assert(!loRaFishIdName[0] && loRaFishSpecies == LoRaFishSpecies::Kitsune && loRaFishColor == 100);   // cfg still has them
    assert(!strcmp(loRaFishDisplayName(), "Radio"));
    files["/lorafish.id"] = good; if (!bakGood.empty()) files["/lorafish.idb"] = bakGood;
  }
  files.erase("/lorafish.idb");                             // (with a good backup the previous copy would be used: that is SafeSave's job)
  files["/lorafish.id"].clear(); reboot(); assert(!loRaFishIdName[0]);
  files.erase("/lorafish.id"); reboot(); assert(!loRaFishIdName[0] && loRaFishSpecies == LoRaFishSpecies::Kitsune);
  puts("PASS c: a damaged, empty or missing /lorafish.id falls back to the defaults");

  // an unknown species (saved by newer firmware) is kept as it is and is not replaced by a stand-in
  resetAt(5000); saveLoRaFish(); assert(setLoRaFishPetName("Old") == LoRaFishIdentity::NameOk);
  loRaFishSpecies = 600; saveLoRaFishSettings();
  uint8_t keep[35]; memcpy(keep, files["/lorafish.id"].data(), 35);
  assert(files["/lorafish.id"].size() == 35);               // file not rewritten with a stand-in species
  reboot(); assert(loRaFishSpecies == 600 && !strcmp(loRaFishIdName, "Old"));
  assert(!memcmp(keep, files["/lorafish.id"].data(), 35));
  puts("PASS: an unknown species is neither overwritten nor replaced");

  // d. names
  assert(setLoRaFishPetName("0123456789ABCDEFG") == LoRaFishIdentity::NameTooLong && !strcmp(loRaFishIdName, "Old"));
  assert(setLoRaFishPetName("0123456789ABCDEF") == LoRaFishIdentity::NameOk && !strcmp(loRaFishIdName, "0123456789ABCDEF"));
  assert(strlen(loRaFishDisplayName()) == 15);              // the header has room for 15 characters, like the radio name
  assert(setLoRaFishPetName("") == LoRaFishIdentity::NameOk && !strcmp(loRaFishDisplayName(), "Radio"));
  puts("PASS d: 17 bytes refused, 16 accepted, header keeps its 15 character room, empty name clears");

  // reset: a new pet does not keep the old name
  resetAt(5000); assert(setLoRaFishPetName("Rex") == LoRaFishIdentity::NameOk);
  resetLoRaFishPet(); assert(!loRaFishIdName[0]);
  reboot(); assert(!loRaFishIdName[0]);
  puts("PASS: a reset pet loses the name (also after a reboot)");
  return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='lfid-ui-') as tmp:
    p = Path(tmp); (p / 'test.cpp').write_text(code)
    for platform in ('ESP32', 'NRF52_PLATFORM'):
        exe = p / platform
        subprocess.run(['g++', '-std=c++17', '-w', '-DLORAGOTCHI_DXPRO=1', '-DLORAGOTCHI_WATER_EDITION=0', '-DLORAGOTCHI_AIR_EDITION=0',
                        '-I', str(f.ROOT), '-I', str(f.ROOT / 'src'), '-D' + platform, str(p / 'test.cpp'), '-o', str(exe)], check=True)
        print('storage branch', platform)
        subprocess.run([str(exe)], check=True, timeout=120)
