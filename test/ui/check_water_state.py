#!/usr/bin/env python3
"""Actual production lifecycle/settings migration + persisted Mystery choices.
RAM file mocks, both storage branches. No physical power-cut guarantee.
"""
from pathlib import Path
import subprocess,tempfile
import check_fish_lifecycle as f
code='\n'.join(f.parts[:-1])+f.parts[-1].split('int main() {',1)[0]
code+=f.block('static void ensureLoRaFishMysterySeed(')+f.block('static void chooseLoRaFishMysteryColours(')
code+=r'''
int main() {
  for(unsigned id=0;id<15;++id) {
    resetAt(5000);loRaFishSpecies=id;loRaFishEggSpecies=14-id;loRaFishMysterySeed=0x12345678;
    loRaFishNeedsPetSetup=true;saveLoRaFishSettings();saveLoRaFish();reboot();
    assert(loRaFishSpecies==id && loRaFishEggSpecies==14-id && loRaFishMysterySeed==0x12345678 && loRaFishNeedsPetSetup);
    assert(loRaFishPage==LORAFISH_PET_SETUP_PAGE);assert(fish.ageMinutes==5000);
  }
  pass("all 15 identities, pending species and setup/mystery state survive real serializers");
  resetAt(5000);loRaFishSpecies=65535;loRaFishEggSpecies=54321;saveLoRaFishSettings();saveLoRaFish();reboot();
  assert(loRaFishSpecies==65535 && loRaFishEggSpecies==54321);
  assert(LoRaFishSpecies::renderId(loRaFishSpecies)==0);
  auto full=files["/lorafish.cfg"];
  for(unsigned length:{24,36,44,54,60}) {
    files["/lorafish.cfg"]={full.begin(),full.begin()+length};reboot();
    assert(loRaFishSpecies==0 && loRaFishEggSpecies==0 && !loRaFishNeedsPetSetup);
    assert(loRaFishScaleColor==5 && loRaFishColor==4 && loRaFishEyeColor==6);
  }
  for(unsigned length=60;length<78;++length) {
    files["/lorafish.cfg"]={full.begin(),full.begin()+length};reboot();
    assert(loRaFishSpecies==0 && loRaFishEggSpecies==0);
  }
  for(unsigned bit=60*8;bit<78*8;++bit) {
    auto corrupt=full;corrupt[bit/8]^=1<<(bit%8);files["/lorafish.cfg"]=corrupt;reboot();
    assert(loRaFishSpecies==0 && loRaFishEggSpecies==0);
  }
  pass("legacy prefixes, every truncated tail, every single-bit corrupt tail fall back without changing genes");
  for(unsigned id=0;id<15;++id) {
    resetAt(LORAFISH_LIFESPAN_MINUTES);loRaFishSpecies=id;ensureLoRaFishOffspring();
    assert(loRaFishEggSpecies==id);saveLoRaFish();reboot();assert(loRaFishEggSpecies==id);
    hatchLoRaFishOffspring();assert(loRaFishSpecies==id && loRaFishGeneration==8);
  }
  resetAt(5000);loRaFishSpecies=9;loragotchiDXGuest.present=true;loragotchiDXGuest.species=12;
  randomChoice=0;assert(breedLoRaFishWithGuest());assert(loRaFishEggSpecies==9);
  resetAt(5000);loRaFishSpecies=9;loragotchiDXGuest.present=true;loragotchiDXGuest.species=12;
  randomChoice=1;assert(breedLoRaFishWithGuest());assert(loRaFishEggSpecies==12);
  pass("solo inheritance and both parent species paths use stable saved egg identity");
  resetAt(0);resetLoRaFishPet();assert(loRaFishNeedsPetSetup && !loRaFishMysterySeed && !loRaFishSpecies);
  randomChoice=123;chooseLoRaFishMysteryColours();
  uint32_t seed=loRaFishMysterySeed;auto appearance=loRaFishLocalAppearance();
  loRaFishSpecies=LoRaFishSpecies::mystery(seed);auto species=loRaFishSpecies;
  saveLoRaFishSettings();saveLoRaFish();reboot();assert(seed==loRaFishMysterySeed && species==loRaFishSpecies);
  randomChoice=456;chooseLoRaFishMysteryColours();
  assert(loRaFishMysterySeed==seed && loRaFishColor==appearance.body && loRaFishScaleColor==appearance.scales && loRaFishEyeColor==appearance.eyes);
  ensureLoRaFishMysterySeed();assert(LoRaFishSpecies::mystery(loRaFishMysterySeed)==species);
  assert(loRaFishNeedsPetSetup);loRaFishNeedsPetSetup=false;saveLoRaFishSettings();reboot();assert(!loRaFishNeedsPetSetup);
  pass("Mystery colours and creature resolve once, independent of order/navigation/reboot; start completion persists");
}
'''
with tempfile.TemporaryDirectory(prefix='water-state-') as tmp:
    p=Path(tmp);(p/'test.cpp').write_text(code)
    for platform in ('ESP32','NRF52_PLATFORM'):
        exe=p/platform
        subprocess.run(['g++','-std=c++17','-DLORAGOTCHI_WATER_EDITION=1','-I',str(f.ROOT),'-D'+platform,str(p/'test.cpp'),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
