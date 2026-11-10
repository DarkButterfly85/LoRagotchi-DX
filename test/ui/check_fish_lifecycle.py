#!/usr/bin/env python3
"""Run production lifecycle/save/load functions with a controlled clock and RAM files.

Usage: python3 test/ui/check_fish_lifecycle.py (Python 3 and g++ required).
Exercises both ESP32 and nRF52 storage branches; no radio or real flash is touched.
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / 'examples/companion_radio/ui-new/UITask.cpp').read_text()


def block(marker):
    start = SOURCE.index(marker)
    end = SOURCE.index('{', start) + 1
    depth = 1
    while depth:
        depth += (SOURCE[end] == '{') - (SOURCE[end] == '}')
        end += 1
    return SOURCE[start:end]


def declaration(name):
    return re.search(r'^static [^\n]*\b' + name + r'\b.*?;', SOURCE, re.M | re.S).group(0)


parts = [r'''
#include <algorithm>
#include "examples/companion_radio/ui-new/LoRaFishLifeArt.h"
#include "examples/companion_radio/LoRaFishColour.h"
#include "examples/companion_radio/LoRaFishSpecies.h"
#include <cassert>
#include <cstdint>
static uint8_t loRaFishPartial = 0;
static uint8_t loRaFishOrientation = 0;
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>
#include "examples/companion_radio/ui-new/LoRaFishHappiness.h"
#include "examples/companion_radio/ui-new/LoRaFishSafeSave.h"
using std::min;
#define LORAFISH_UI 1
#define FILE_READ 0
#define FILE_WRITE 1
#define FILE_O_READ FILE_READ
#define FILE_O_WRITE FILE_WRITE
static unsigned long clockMs = 0;
unsigned long millis() { return (uint32_t)clockMs; }
static int64_t localEpochBase=43200;
static int64_t loRaFishLocalEpoch() { return localEpochBase + clockMs/1000; }
static long randomChoice = 0;
long random(long lo, long) { return lo + randomChoice; }
static int settingsWrites = 0;
static std::map<std::string, std::vector<uint8_t>> files;
struct File {
  std::string path;
  size_t pos = 0;
  bool writing = false;
  explicit operator bool() const { return files.count(path); }
  size_t size() const { return files.at(path).size(); }
  size_t write(const uint8_t* bytes, size_t count) {
    auto& data = files[path];
    data.insert(data.end(), bytes, bytes + count);
    return count;
  }
  size_t write(uint8_t byte) { return write(&byte, 1); }
  size_t read(uint8_t* bytes, size_t count) {
    const auto& data = files.at(path);
    count = min(count, data.size() - pos);
    if (count) memcpy(bytes, data.data() + pos, count);
    pos += count;
    return count;
  }
  bool seek(size_t offset) { pos=offset; return pos<=size(); }
  void close() { if (writing && path == "/lorafish.cfg") ++settingsWrites; }
};
struct MemoryFS {
  File open(const char* path, int mode) {
    if (mode == FILE_WRITE) files[path].clear();
    return {path, 0, mode == FILE_WRITE};
  }
  bool exists(const char* path) { return files.count(path); }
  bool remove(const char* path) { return files.erase(path); }
  bool rename(const char* from, const char* to) {
    if (!files.count(from)) return false;
    auto data = files[from]; files.erase(from); files[to] = data; return true;
  }
} SPIFFS, InternalFS;
struct {
  template<typename... Args> void printf(const char*, Args...) {}
  void println(const char*) {}
} Serial;
static void loRaFishSyncDXAppearance() {}
static uint8_t loRaFishThemeCount() { return 6; }
static void saveLoRaFishSettings();
static void saveLoRaFish();
static void advanceLoRaFishHappiness(uint32_t);
static void tickLoRaFish();
struct { bool away=false, pending=false, committing=false; } loragotchiDXHome;
struct {
  bool present=false, colorCapable=true;
  uint16_t species=0;
  uint8_t stage=2, scalesColor=3, color=4, eyesColor=5;
} loragotchiDXGuest;
#include "examples/companion_radio/LoRaFishGuestReturn.h"
static LoRaFishGuestReturn loragotchiDXGuestReturn;
''']

parts += [block('struct ' + name + ' {') + ';' for name in
          ['LoRaFishStateV1', 'LoRaFishState', 'LoRaFishAppearance']]
names = '''loRaFishMysterySelected loRaFishMemorialCaptured loRaFishMemorialKey loRaFishMemorialBody loRaFishMemorialScales loRaFishSpecies loRaFishEggSpecies loRaFishMysterySeed loRaFishNeedsPetSetup loRaFishPetSetupField LORAFISH_PET_SETUP_PAGE loRaFishMonoDisplayColour loRaFishMonoDisplayColourKnown LORAFISH_MONO_DISPLAY_COLOUR_COUNT LORAFISH_MAGIC LORAFISH_MAGIC_V1 LORAFISH_EGG_MINUTES
LORAFISH_LIFESPAN_MINUTES LORAFISH_PACKETS_PER_FEED LORAFISH_MONOCHROME_COLOR
LORAFISH_MAX_POOP fish fishLastMinute fishLastSave fishReaction fishReactionUntil
loRaFishGeneration loRaFishPendingEgg loRaFishEggAppearance loRaFishMemorialEggSide
loRaFishAdoptionEligible loRaFishColor loRaFishScaleColor loRaFishEyeColor loRaFishNeedsAppearanceSetup
loRaFishEvolutionFlashUntil loRaFishHatchMelodyPlayed loRaFishPoopCount
loRaFishNextPoopAt loRaFishCleaning loRaFishFeeding loRaFishFeedChasing
loRaFishFeedLastXValid loRaFishFeedStarted loRaFishNextAutoFeed loRaFishPage
loRaFishColorField loRaFishColorDisplay loRaFishAppearanceLoaded loRaFishSimulationMode
loRaFishTimeoutAwakeSetting loRaFishTheme loRaFishSleepHour loRaFishWakeHour
loRaFishUtcOffsetQuarters loRaFishTimeoutAsleepSetting loRaFishBrightnessSetting
loRaFishAlwaysOnDimSetting loRaFishDimSlow loRaFishBuzzerVolume loRaFishWakeSound loRaFishSleepSound
loRaFishMessageSound lastWrittenLoRaFish haveLastWrittenLoRaFish
loRaFishHappiness lastWrittenLoRaFishHappiness haveLastWrittenLoRaFishHappiness
loRaFishHappyLastMs loRaFishHappyLastSavedMs LORAFISH_HAPPY_SETTINGS_MAGIC LORAFISH_AQUARIUM_SETTINGS_MAGIC
LORAFISH_SETTINGS_SIZE LORAFISH_CHECKPOINT_MS LORAFISH_SAVE_RETRY_MS
lastWrittenLoRaFishSettings haveLastWrittenLoRaFishSettings
loRaFishSettingsPending loRaFishSettingsMenuOpen loRaFishSettingsSaveFailed loRaFishSaveFailed loRaFishSettingsLastAttempt loRaFishLastAttempt'''.split()
parts += [declaration(name) for name in names]
markers = [
    'static LoRaFishAppearance loRaFishLocalAppearance(',
    'static LoRaFishAppearance loRaFishGuestAppearance(',
    'static bool loRaFishCanBreed(',
    'static uint8_t inheritLoRaFishColor(',
    'static bool loRaFishGuestSameSpecies(',
    'static bool breedLoRaFishWithGuest(',
    'static uint8_t fishEvolutionForAge(',
    'static void encodeLoRaFishSettings(',
    'static const char* loRaFishRecordKey(',
    'static bool writeLoRaFishRecord(',
    'struct LoRaFishPetStore {',
    'static bool loRaFishPetRecordValid(',
    'static void saveLoRaFishSettings() {',
    'static void loadLoRaFishSettings() {',
    'static void serviceLoRaFishSettingsMenu(',
    'static bool sameLoRaFishRecord(',
    'static void saveLoRaFish() {',
    'static void loadLoRaFish() {',
    'static void resetLoRaFishPet() {',
]
# Optional extraction allows running this regression against the pre-fix source.
if 'static void ensureLoRaFishOffspring(' in SOURCE:
    markers.append('static void ensureLoRaFishOffspring(')
markers.append('static uint32_t loRaFishLifeArtKey(')
markers += ['static void hatchLoRaFishOffspring(', 'static void advanceLoRaFishHappiness(uint32_t until) {', 'static void checkpointLoRaFish(', 'static void flushLoRaFish(', 'static void tickLoRaFish() {']
parts += [block(marker) + (';\nstatic LoRaFishPetStore loRaFishPetStore;' if marker.startswith('struct LoRaFishPetStore') else '') for marker in markers]
parts.append(r'''
static void resetAt(uint32_t age, bool egg=false) {
  files.clear(); loRaFishMysterySelected=false; loRaFishMemorialCaptured=false; loRaFishMemorialKey=0; loRaFishNeedsPetSetup=false; loRaFishMysterySeed=0;
  loRaFishSpecies=loRaFishEggSpecies=0;
  clockMs=0; fishLastMinute=fishLastSave=0;
  haveLastWrittenLoRaFish=false; haveLastWrittenLoRaFishSettings=false;
  loRaFishSaveFailed=loRaFishSettingsSaveFailed=false;
  loRaFishLastAttempt=loRaFishSettingsLastAttempt=0;
  loRaFishHappiness={}; haveLastWrittenLoRaFishHappiness=false; loRaFishHappyLastMs=loRaFishHappyLastSavedMs=0;
  fish={LORAFISH_MAGIC,age,10,1,2,80,fishEvolutionForAge(age),9,20000};
  loRaFishGeneration=7; loRaFishPendingEgg=egg;
  loRaFishEggAppearance={1,2,3}; loRaFishNeedsAppearanceSetup=false;
  loRaFishColor=4; loRaFishScaleColor=5; loRaFishEyeColor=6;
  loRaFishMemorialEggSide=-1;
  loRaFishColorDisplay=false; loRaFishSimulationMode=false;
  loragotchiDXHome={}; loragotchiDXGuest={false,true,0,2,3,4,5};
  settingsWrites=0;loRaFishAdoptionEligible=false;
}
static void minute() { clockMs+=60000; tickLoRaFish(); }
static void traits(uint8_t scales, uint8_t body, uint8_t eyes) {
  assert(loRaFishEggAppearance.scales==scales);
  assert(loRaFishEggAppearance.body==body);
  assert(loRaFishEggAppearance.eyes==eyes);
}
static void reboot() {
  clockMs=0; fishLastMinute=fishLastSave=0;
  haveLastWrittenLoRaFish=false; haveLastWrittenLoRaFishSettings=false;
  loRaFishSaveFailed=loRaFishSettingsSaveFailed=false;
  loRaFishLastAttempt=loRaFishSettingsLastAttempt=0;
  loRaFishHappiness={}; haveLastWrittenLoRaFishHappiness=false; loRaFishHappyLastMs=loRaFishHappyLastSavedMs=0;
  fish={LORAFISH_MAGIC,0,0,0,0,80,0};
  loRaFishGeneration=1; loRaFishPendingEgg=false; loRaFishEggAppearance={0,0,0};
  loRaFishColor=loRaFishScaleColor=loRaFishEyeColor=0;
  loadLoRaFish(); loadLoRaFishSettings();
}
static void pass(const char* name) { printf("PASS: %s\n", name); fflush(stdout); }
int main() {
  resetAt(42); LoRaFishStateV1 old={LORAFISH_MAGIC_V1,42,31,12,7,66,1};
  files["/lorafish.dat"]=std::vector<uint8_t>((uint8_t*)&old,(uint8_t*)&old+sizeof(old));
  reboot(); assert(fish.ageMinutes==42 && fish.rfEvents==31 && fish.messages==12 && fish.txAcks==7);
  assert(fish.happiness==66 && fish.dxVisits==0 && fish.longestUptimeMinutes==0);
  assert(loRaFishSpecies==LoRaFishSpecies::TropicalFish && !loRaFishMysterySelected);
  pass("LFM1 state migration retains lifecycle/counters and honest legacy species/provenance");
  // Provenance is explicit, never inferred from matching seed/species.
  resetAt(0); loRaFishMysterySeed=123; loRaFishSpecies=LoRaFishSpecies::mystery(123);
  saveLoRaFishSettings(); saveLoRaFish(); reboot(); assert(!loRaFishMysterySelected);
  loRaFishMysterySelected=true; saveLoRaFishSettings(); reboot(); assert(loRaFishMysterySelected);
  auto modern=files["/lorafish.cfg"];
  for(size_t n=90;n<106;++n) {
    files["/lorafish.cfg"]=modern; files["/lorafish.cfg"].resize(n);
    loadLoRaFishSettings(); assert(!loRaFishMysterySelected && !loRaFishMemorialCaptured);
  }
  for(unsigned i=90;i<106;++i) {
    files["/lorafish.cfg"]=modern; files["/lorafish.cfg"][i]^=128;
    loadLoRaFishSettings(); assert(!loRaFishMysterySelected && !loRaFishMemorialCaptured);
  }
  resetAt(LORAFISH_LIFESPAN_MINUTES-1,true); loRaFishMysterySelected=true;
  minute(); assert(loRaFishMemorialCaptured);
  const auto key=loRaFishMemorialKey; const auto body=loRaFishMemorialBody, scales=loRaFishMemorialScales;
  loRaFishSpecies=14; loRaFishMysterySeed=999; loRaFishColor=20; loRaFishScaleColor=30; loRaFishEyeColor=40;
  saveLoRaFishSettings(); reboot();
  assert(loRaFishMemorialCaptured && loRaFishMemorialKey==key && loRaFishLifeArtKey(false)==key);
  assert(loRaFishMemorialBody==body && loRaFishMemorialScales==scales);
  const int writes=settingsWrites; for(int i=0;i<100;++i)tickLoRaFish(); assert(settingsWrites==writes);
  for(int i=0;i<5;++i)minute();
  assert(!loRaFishMysterySelected && !loRaFishMemorialCaptured && loRaFishGeneration==8);
  reboot(); assert(!loRaFishMysterySelected && !loRaFishMemorialCaptured);
  pass("explicit provenance, legacy/truncated/corrupt tail, frozen deceased snapshot, visitor successor and reload");

  // Check the millisecond immediately before/at the end-of-life minute boundary.
  resetAt(LORAFISH_LIFESPAN_MINUTES-1);
  clockMs=59999; tickLoRaFish();
  assert(!loRaFishPendingEgg && settingsWrites==0);
  clockMs=60000; tickLoRaFish();
  assert(fish.ageMinutes==LORAFISH_LIFESPAN_MINUTES && loRaFishPendingEgg);
  assert(loRaFishGeneration==7 && loRaFishMemorialEggSide==0 && settingsWrites==1);
  traits(5,4,6);
  for (int i=0; i<100; ++i) tickLoRaFish();
  assert(settingsWrites==1);
  minute(); traits(5,4,6); assert(settingsWrites==1);
  pass("solo egg created/persisted once at end of life, never early");

  // Actual file serializers restore the pending egg and parent across restart.
  resetAt(LORAFISH_LIFESPAN_MINUTES-1); minute(); reboot();
  assert(fish.ageMinutes==LORAFISH_LIFESPAN_MINUTES);
  assert(loRaFishGeneration==7 && loRaFishPendingEgg); traits(5,4,6);
  tickLoRaFish(); assert(settingsWrites==1);
  for (int i=0; i<4; ++i) minute();
  assert(loRaFishPendingEgg && loRaFishGeneration==7);
  clockMs+=59999; tickLoRaFish(); assert(loRaFishGeneration==7);
  ++clockMs; tickLoRaFish();
  assert(!loRaFishPendingEgg && loRaFishGeneration==8 && fish.ageMinutes==0);
  assert(loRaFishScaleColor==5 && loRaFishColor==4 && loRaFishEyeColor==6);
  assert(fish.dxVisits==9 && fish.longestUptimeMinutes==20000);
  assert(settingsWrites==2);
  reboot(); assert(loRaFishGeneration==8 && fish.ageMinutes==0 && !loRaFishPendingEgg);
  for (int i=0; i<4; ++i) minute();
  assert(fish.ageMinutes==4 && !loRaFishPendingEgg);
  minute(); assert(fish.ageMinutes==LORAFISH_EGG_MINUTES && loRaFishGeneration==8);
  pass("restart preserves egg, succession, device records, and both five-minute stages");

  resetAt(LORAFISH_LIFESPAN_MINUTES-1, true);
  minute(); traits(1,2,3); assert(settingsWrites==1); // Happy checkpoint, not a new egg.
  for (int i=0; i<5; ++i) minute();
  assert(loRaFishGeneration==8 && !loRaFishPendingEgg && fish.ageMinutes==0);
  assert(loRaFishScaleColor==1 && loRaFishColor==2 && loRaFishEyeColor==3);
  assert(settingsWrites==2);
  pass("pre-existing visitor egg is neither replaced nor delayed");

  // Firmware upgrades must recover older saves already stuck on the memorial.
  for (uint32_t age : {LORAFISH_LIFESPAN_MINUTES, LORAFISH_LIFESPAN_MINUTES+30}) {
    resetAt(age); saveLoRaFishSettings(); saveLoRaFish(); reboot();
    const int before=settingsWrites;
    tickLoRaFish(); assert(loRaFishPendingEgg && settingsWrites==before+1); traits(5,4,6);
    tickLoRaFish(); assert(settingsWrites==before+1);
    for (int i=0; i<5 && loRaFishGeneration==7; ++i) minute();
    assert(loRaFishGeneration==8 && fish.ageMinutes==0);
  }
  pass("old memorial saves recover without reset, including overdue succession");

  resetAt(LORAFISH_LIFESPAN_MINUTES-2);
  clockMs=10*60000UL; tickLoRaFish();
  assert(loRaFishGeneration==8 && fish.ageMinutes==0 && !loRaFishPendingEgg);
  assert(settingsWrites==2);
  pass("delayed tick crossing death and succession produces exactly one successor");

  for (int state=0; state<4; ++state) {
    resetAt(LORAFISH_LIFESPAN_MINUTES-1);
    loragotchiDXHome.away=state==1;
    loragotchiDXHome.pending=state==2;
    loragotchiDXHome.committing=state==3;
    minute(); assert(loRaFishPendingEgg); traits(5,4,6);
    assert(loragotchiDXHome.away==(state==1));
    assert(loragotchiDXHome.pending==(state==2));
    assert(loragotchiDXHome.committing==(state==3));
  }
  pass("fallback is independent of home/travel state and leaves transport unchanged");

  resetAt(LORAFISH_LIFESPAN_MINUTES-1);
  loRaFishColor=loRaFishScaleColor=loRaFishEyeColor=LORAFISH_MONOCHROME_COLOR;
  minute(); traits(6,6,6);
  pass("monochrome traits remain monochrome");

  for (uint32_t age : {0U, 5U, 60U, 360U, 4320U}) {
    resetAt(age); tickLoRaFish(); minute();
    assert(!loRaFishPendingEgg && settingsWrites==0);
  }
  resetAt(LORAFISH_LIFESPAN_MINUTES-1);
  loRaFishNeedsAppearanceSetup=true;
  minute(); assert(!loRaFishPendingEgg && fish.ageMinutes==LORAFISH_LIFESPAN_MINUTES-1);
  pass("young fish and paused appearance setup never auto-breed");

  for (randomChoice=0; randomChoice<=240; randomChoice+=240) {
    resetAt(5000);
    assert(!breedLoRaFishWithGuest() && !loRaFishPendingEgg);
    loragotchiDXGuest.present=true;
    assert(breedLoRaFishWithGuest() && settingsWrites==1);
    if (randomChoice==0) traits(5,4,6); else traits(3,4,5);
    assert(!breedLoRaFishWithGuest() && settingsWrites==1);
    reboot(); assert(loRaFishPendingEgg && loRaFishGeneration==7);
    if (randomChoice==0) traits(5,4,6); else traits(3,4,5);
  }
  pass("live visitor breeding and persisted inherited traits are unchanged");

  for (uint32_t age : {LORAFISH_LIFESPAN_MINUTES, LORAFISH_LIFESPAN_MINUTES+1}) {
    resetAt(age); loragotchiDXGuest.present=true;
    assert(!loRaFishCanBreed() && !breedLoRaFishWithGuest() && settingsWrites==0);
  }
  pass("memorial-stage fish cannot visitor-breed before the next tick");

  resetAt(LORAFISH_LIFESPAN_MINUTES-1); minute();
  resetLoRaFishPet();
  assert(loRaFishGeneration==1 && !loRaFishPendingEgg && fish.ageMinutes==0);
  reboot(); tickLoRaFish(); assert(loRaFishGeneration==1 && !loRaFishPendingEgg);
  pass("explicit pet reset still clears the pending egg and restarts generation one");

  resetAt(LORAFISH_LIFESPAN_MINUTES-1); loRaFishGeneration=65535;
  for (int i=0; i<6; ++i) minute();
  assert(loRaFishGeneration==65535 && fish.ageMinutes==0 && !loRaFishPendingEgg);
  fish.ageMinutes=LORAFISH_LIFESPAN_MINUTES-1;
  minute(); assert(loRaFishPendingEgg); traits(5,4,6);
  pass("successive generations retain fallback, and generation counter does not wrap");
}
''')

if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='lorafish-lifecycle-') as directory:
        cpp = Path(directory) / 'lifecycle.cpp'
        cpp.write_text('\n'.join(parts))
        for platform in ('ESP32', 'NRF52_PLATFORM'):
            executable = Path(directory) / platform
            subprocess.run(['g++', '-std=c++17', '-I', str(ROOT), '-D' + platform, str(cpp), '-o', str(executable)],
                           check=True)
            print(f'Lifecycle/save/load checks: {platform}', flush=True)
            subprocess.run([str(executable)], check=True)
