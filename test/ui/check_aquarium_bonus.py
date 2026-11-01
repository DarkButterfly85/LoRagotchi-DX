#!/usr/bin/env python3
"""Production reward/timing/serializers on ESP32 and nRF52 host storage mocks."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
fixture = Path(__file__).with_name('check_fish_happiness.py')
ns = {'__file__': str(fixture), '__name__': 'bonus_fixture'}
exec(compile(fixture.read_text().split('with tempfile.TemporaryDirectory(', 1)[0],
             str(fixture), 'exec'), ns)
parts = ns['parts'][:-1] + [ns['parts'][-1].split('int main() {', 1)[0]]
parts.append(r'''
int main() {
  resetHappy();
  assert(loRaFishHappiness.aquarium(true,fish.happiness));saveLoRaFish();
  assert(fish.happiness==85 && loRaFishHappiness.aquariumCooldownMs==21600000);
  const auto written=files;
  for(int i=0;i<1000;i++) {
    assert(!loRaFishHappiness.aquarium(true,fish.happiness));saveLoRaFish();
  }
  assert(fish.happiness==85 && files==written);
  pass("+5 per eligible return, repeated attempts neither reward nor change saved bytes");

  const auto writes=settingsWrites;
  reboot();assert(fish.happiness==85 && loRaFishHappiness.aquariumCooldownMs==21600000);
  assert(!loRaFishHappiness.aquarium(true,fish.happiness));
  pass("reward cap and Happy survive real boot-order serializers");

  // Full sleep interval avoids unrelated Happy decay during this exact-boundary test.
  loRaFishHappiness.advance(21599999,true,23*3600000,0,23,0,fish.happiness);
  assert(loRaFishHappiness.aquariumCooldownMs==1 && !loRaFishHappiness.aquarium(true,fish.happiness));
  loRaFishHappiness.advance(1,true,23*3600000,0,23,0,fish.happiness);
  assert(loRaFishHappiness.aquariumCooldownMs==0 && fish.happiness==85);
  assert(loRaFishHappiness.aquarium(true,fish.happiness) && fish.happiness==90);
  pass("six-hour boundary exact, sleeping time counts, expiry alone earns nothing");

  resetHappy();loRaFishHappiness.aquarium(true,fish.happiness);saveLoRaFish();
  advance(300000);saveLoRaFish();
  const auto remaining=loRaFishHappiness.aquariumCooldownMs;
  reboot();assert(loRaFishHappiness.aquariumCooldownMs==remaining && remaining==21300000);
  advance(120000);reboot();
  assert(loRaFishHappiness.aquariumCooldownMs==remaining);
  pass("checkpoint restores remaining cooldown; abrupt reboot can lengthen, never shorten healthy saved cap");

  resetHappy();loRaFishHappiness.aquarium(true,fish.happiness);saveLoRaFish();
  files["/lorafish.cfg"].resize(36);reboot();
  assert(fish.happiness==85 && loRaFishGeneration==7 && loRaFishHappiness.aquariumCooldownMs==0);
  assert(files["/lorafish.dat"].size()==sizeof(LoRaFishState));
  pass("legacy 36-byte settings retain pet and care settings with no pre-existing aquarium cap");

  for(size_t length=37;length<44;length++) {
    resetHappy();loRaFishHappiness.aquarium(true,fish.happiness);saveLoRaFish();
    files["/lorafish.cfg"].resize(length);reboot();
    assert(loRaFishHappiness.aquariumCooldownMs==21600000 && fish.happiness==85);
  }
  for(size_t offset:{size_t(36),size_t(40)}) {
    resetHappy();loRaFishHappiness.aquarium(true,fish.happiness);saveLoRaFish();
    for(size_t i=offset;i<offset+4;i++)files["/lorafish.cfg"][i]=255;
    reboot();assert(loRaFishHappiness.aquariumCooldownMs==21600000 && fish.happiness==85);
  }
  pass("truncated, unknown and out-of-range new tail conservatively restore full cap");

  resetHappy();loRaFishHappiness.aquarium(true,fish.happiness);
  resetLoRaFishPet();assert(loRaFishHappiness.aquariumCooldownMs==21600000);
  loRaFishPendingEgg=true;hatchLoRaFishOffspring();
  assert(loRaFishHappiness.aquariumCooldownMs==21600000 && loRaFishHappiness.awakeMs==0);
  pass("pet reset and succession cannot bypass device-level reward cap");

  for(uint8_t happy:{uint8_t(0),uint8_t(94),uint8_t(95),uint8_t(99),uint8_t(100)}) {
    resetHappy(60,happy);assert(loRaFishHappiness.aquarium(true,fish.happiness));
    assert(fish.happiness==min(int(happy)+5,100));
    assert(loRaFishHappiness.aquariumCooldownMs==21600000);
  }
  resetHappy();assert(!loRaFishHappiness.aquarium(false,fish.happiness));
  assert(fish.happiness==80 && loRaFishHappiness.aquariumCooldownMs==0);
  pass("Happy saturates at 100, full-Happy visit consumes cap, ineligible fish earn nothing");

  resetHappy();clockMs=0xFFFFFF00U;
  fishLastMinute=fishLastSave=loRaFishHappyLastMs=loRaFishHappyLastSavedMs=clockMs;
  loRaFishHappiness.aquarium(true,fish.happiness);saveLoRaFish();
  clockMs+=1000;tickLoRaFish();assert(loRaFishHappiness.aquariumCooldownMs==21599000);
  pass("production care clock decrements aquarium cap correctly across millis rollover");

  resetHappy(360);loRaFishHappiness.aquarium(true,fish.happiness);saveLoRaFish();
  loragotchiDXGuest.present=true;
  assert(loRaFishCanBreed());
  loragotchiDXGuestReturn.status=LoRaFishGuestReturn::Pending;
  assert(!loRaFishCanBreed());loragotchiDXGuestReturn.status=LoRaFishGuestReturn::Failed;
  assert(!loRaFishCanBreed());loragotchiDXGuestReturn.status=LoRaFishGuestReturn::Idle;
  pass("returning or unconfirmed visitors cannot be used for breeding");
}
''')
with tempfile.TemporaryDirectory(prefix='aquarium-bonus-') as tmp:
    cpp = Path(tmp) / 'bonus.cpp'
    cpp.write_text('\n'.join(parts))
    for platform in ('ESP32', 'NRF52_PLATFORM'):
        exe = Path(tmp) / platform
        subprocess.run(['g++', '-std=c++17', '-I', str(root), '-D' + platform,
                        str(cpp), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
