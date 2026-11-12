#!/usr/bin/env python3
"""DX-Pro registry visibility: all three registries visible with no ID collisions in DX-Pro builds, and the
single-edition builds (DX, Water, Air, Land) still see only their own registry.

Host-compiled production headers only (no hardware, no panel). Also checks the set-then-species menu helpers,
the discovery markers, the unchanged ACK wire strings, and that DX-Pro cannot be combined with an edition flag.
"""
from pathlib import Path
import re,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
code=r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include <set>
#include <string>
#include "examples/companion_radio/LoRaFishSpecies.h"
#include "examples/companion_radio/ui-new/LoRaFishText.h"
using namespace LoRaFishSpecies;
int main() {
 // Three disjoint registries, 76 species, unique IDs and unique names, nothing else known.
 static_assert(count==15 && airCount==18 && landCount==43,"registry sizes");
 static_assert(Eagle==256 && Dog==512 && Kitsune==512+landCount-1 && Bug==256+airCount-1,"stable ID blocks");
 std::set<unsigned> ids;std::set<std::string> names;unsigned total=0;
 for(unsigned id=0;id<65536;++id) {
  const bool w=id<15,a=id>=256&&id<=273,l=id>=512&&id<=554;
  assert(waterKnown(id)==w && airKnown(id)==a && landKnown(id)==l && known(id)==(w||a||l));
  assert((int)w+(int)a+(int)l<=1); // no ID is in two registries
  if(known(id)){++total;ids.insert(id);names.insert(label(id));assert(strcmp(label(id),"Unknown (fish)"));}
 }
 assert(total==76 && ids.size()==76 && names.size()==76);
 // Visibility per build: DX-Pro owns all three, a single edition owns only its own.
 for(unsigned id=0;id<65536;++id) {
  const bool w=id<15,a=id>=256&&id<=273,l=id>=512&&id<=554;
  const bool expect=LORAGOTCHI_DXPRO ? (w||a||l) : LORAGOTCHI_LAND_EDITION ? l : LORAGOTCHI_AIR_EDITION ? a : w;
  assert(editionKnown(id)==expect);
 }
 // Sets: sizes, derivation from the ID, and a lossless set -> species -> ID -> set round trip, all 76 once.
 static_assert(setCount==3,"Water, Air, Land");
 assert(setSize(0)==15 && setSize(1)==18 && setSize(2)==43);
 assert(!strcmp(setLabel(0),"Water") && !strcmp(setLabel(1),"Air") && !strcmp(setLabel(2),"Land"));
 std::set<unsigned> menu;
 for(uint8_t set=0;set<setCount;++set)for(uint8_t i=0;i<setSize(set);++i) {
  const uint16_t id=setSelectionId(set,i);
  assert(known(id) && setOf(id)==set && setSelectionIndex(id)==i);
  menu.insert(id);
 }
 assert(menu==ids); // the two-step menu reaches every species exactly once
 for(uint8_t set=0;set<setCount;++set) { // out-of-range index falls back to the set's first species
  assert(setSelectionId(set,setSize(set))==setBase(set) && setSelectionId(set,255)==setBase(set));
  for(uint32_t seed=0;seed<4000;++seed)assert(setOf(setMystery(seed,set))==set);
 }
 assert(setOf(9999)==0 && setSelectionIndex(9999)==0); // unknown IDs stay fish-like
 // Mystery egg inside a set uses the formula the single-set build uses today (one seed, one animal).
 for(uint32_t seed=0;seed<5000;++seed) {
  if(LORAGOTCHI_LAND_EDITION)assert(setMystery(seed,2)==mystery(seed));
  else if(LORAGOTCHI_AIR_EDITION)assert(setMystery(seed,1)==mystery(seed));
  else assert(setMystery(seed,0)==mystery(seed));
 }
 // Single-edition menu tables are exactly the old ones; DX-Pro starts on the fish like Water.
 assert(selectableCount==(LORAGOTCHI_LAND_EDITION?43:LORAGOTCHI_AIR_EDITION?18:15));
 assert(freshSpecies==(LORAGOTCHI_LAND_EDITION?512:LORAGOTCHI_AIR_EDITION?256:0));
 // Wire strings unchanged: the visitor still accepts only the same four ACK forms.
 assert(acknowledged("LFG1|ACK|1|2|S1") && acknowledged("LFG1|ACK|1|2|S1|A1") && acknowledged("LFG1|ACK|1|2|S1|L1"));
 assert(!acknowledged("LFG1|ACK|1|2") && !acknowledged("LFG1|ACK|1|2|S1|C1"));
 assert(wireSpecies(Dog,"LFG1|ACK|1|2|S1|L1")==Dog && wireSpecies(Dog,"LFG1|ACK|1|2|S1")==TropicalFish);
 assert(wireSpecies(Eagle,"LFG1|ACK|1|2|S1|A1")==Eagle && wireSpecies(Eagle,"LFG1|ACK|1|2|S1|L1")==TropicalFish);
 assert(wireSpecies(Shark,"LFG1|ACK|1|2|S1")==Shark);
 // Discovery markers: DX-Pro knows all three sets, a single edition only its own, DX only the fish.
 const char shark[]="\xF0\x9F\xA6\x88",dolphin[]="\xF0\x9F\x90\xAC",eagle[]="\xF0\x9F\xA6\x85",dog[]="\xF0\x9F\x90\x95",plain[]="Alice";
 assert(LoRaFishText::hasFish(shark,sizeof(shark)));
 assert(LoRaFishText::hasFish(dolphin,sizeof(dolphin))==(LORAGOTCHI_SPECIES_EDITION!=0));
 assert(LoRaFishText::hasFish(eagle,sizeof(eagle))==(LORAGOTCHI_AIR_EDITION||LORAGOTCHI_DXPRO));
 assert(LoRaFishText::hasFish(dog,sizeof(dog))==(LORAGOTCHI_LAND_EDITION||LORAGOTCHI_DXPRO));
 assert(!LoRaFishText::hasFish(plain,sizeof(plain)));
 static_assert(sizeof(savedSize)>0 && savedSize==18,"save tail must not grow");
 std::printf("%s species=%u\n",LORAGOTCHI_EDITION_NAME,total);
}
'''
with tempfile.TemporaryDirectory(prefix='dxpro-registry-') as t:
 p=Path(t);(p/'test.cpp').write_text(code)
 for build,flags,name in (('DX',[],'DX'),('WATER',['-DLORAGOTCHI_WATER_EDITION=1'],'WATER'),
                          ('AIR',['-DLORAGOTCHI_AIR_EDITION=1'],'AIR'),('LAND',['-DLORAGOTCHI_LAND_EDITION=1'],'LAND'),
                          ('DXPRO',['-DLORAGOTCHI_DXPRO=1'],'DX-PRO')):
  exe=str(p/('t'+build))
  subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(ROOT),'-I',str(ROOT/'src'),
    *flags,str(p/'test.cpp'),'-o',exe],check=True)
  out=subprocess.run([exe],check=True,capture_output=True,text=True).stdout.strip()
  assert out==name+' species=76',out
  print('PASS',build,'build sees',{'DXPRO':'Water+Air+Land (76)','DX':'Water registry only','WATER':'Water registry only','AIR':'Air registry only','LAND':'Land registry only'}[build])
# DX-Pro and a single edition together is a configuration error.
for other in ('WATER','AIR','LAND'):
 r=subprocess.run(['g++','-std=c++17','-fsyntax-only','-DLORAGOTCHI_DXPRO=1','-DLORAGOTCHI_%s_EDITION=1'%other,
   '-I',str(ROOT),'-x','c++','-'],input='#include "examples/companion_radio/LoRaGotchiVersion.h"\n',text=True,capture_output=True)
 assert r.returncode!=0 and 'LORAGOTCHI_DXPRO already includes every habitat set' in r.stderr,other
# Source wiring: the menu has the extra step, the ACK keeps its legacy strings, nothing hard-codes a board.
menu=(ROOT/'examples/companion_radio/ui-new/LoRaFishMenu.h').read_text()
assert re.search(r'DisplayUpdate,\s*\n?\s*SpeciesSet',menu) and menu.index('Species,')<menu.index('SpeciesSet') # appended, old values keep numbers
ui=(ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text()
for needle in ('LoRaFishSetting::SpeciesSet','LoRaFishSpecies::setMystery','LoRaFishAirSprite::draw','LoRaFishLandSprite::draw'):
 assert needle in ui,needle
mesh=(ROOT/'examples/companion_radio/MyMesh.cpp').read_text()
assert mesh.count('S1|L1')==1 and mesh.count('S1|A1')==1 # no new wire suffix
for f in ('LoRaFishSpecies.h','ui-new/LoRaFishMenu.h'):
 src=(ROOT/'examples/companion_radio'/f).read_text()
 assert not re.search(r'ESP32|ARDUINO_|nrf52|NRF52|PIN_|DISPLAY_CLASS',src),f # registry/menu data has no board or chip assumptions
print('PASS DX-Pro: three registries, 76 unique IDs, set-then-species menu reaches every species once, wire strings unchanged, single editions unchanged')
