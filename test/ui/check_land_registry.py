#!/usr/bin/env python3
"""Land registry, edition gate, wire capability, discovery marker and sprite-budget checks.

Host-compiled production headers only (all four edition configurations). Art is
DRAFT first-pass procedural art; this checks structure/bounds, not appearance.
Note: the owner's species list contains 39 animals (28 land, 5 amphibious, 6 mythic);
the kickoff text said 34. The registry follows the explicit list.
"""
from pathlib import Path
import re,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
code=r'''
#include <array>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <set>
#include <string>
#include "examples/companion_radio/LoRaFishSpecies.h"
#include "examples/companion_radio/ui-new/LoRaFishText.h"
#include "examples/companion_radio/ui-new/LoRaFishLandSprite.h"
#include "examples/companion_radio/ui-new/LoRaFishAirSprite.h"
#include "examples/companion_radio/ui-new/LoRaFishWaterSprite.h"
using namespace LoRaFishSpecies;
struct Canvas {
 unsigned calls=0;
 void setColor(uint16_t){}
 void fillRect(int,int,int w,int h){assert(w>0 && w<=32 && h==1);++calls;}
};
static const char* const expectedNames[]={"Dog","Cat","Horse","Cow","Elephant","Pig","Ram","Sheep",
 "Goat","Giraffe","Kangaroo","Llama","Deer","Mouse","Hamster","Rabbit","Hedgehog","Koala","Panda",
 "Sloth","Otter","Skunk","Badger","Hippo","Rhino","Camel","Bactrian camel","Bison","Frog","Crocodile",
 "Lizard","Turtle","Snake","Unicorn","Dragon","Griffin","Phoenix","Sauropod","T-Rex"};
int main() {
 static_assert(landCount==39,"owner list: 28 land + 5 amphibious + 6 mythic");
 static_assert(sizeof(LoRaFishLandArt::masks)==39*2*192,"Land ROM asset budget");
 static_assert(savedSize==18,"save tail must not grow");
 static_assert(Dog==512 && TRex==512+landCount-1,"stable contiguous Land block");
 assert(sizeof(expectedNames)/sizeof(*expectedNames)==landCount);
 // Registry: count, unique IDs and names, no collision with Water or Air.
 std::set<std::string> names;std::set<unsigned> ids;
 for(unsigned i=0;i<landCount;++i) {
  const unsigned id=Dog+i;
  assert(landKnown(id) && known(id) && !waterKnown(id) && !airKnown(id));
  assert(strcmp(label(id),expectedNames[i])==0);
  assert(strcmp(label(id),"Unknown (fish)")!=0);
  names.insert(label(id));ids.insert(id);
  assert(strlen(lifeStage(id,0))>0 && strlen(lifeStage(id,0))<=11 && strlen(lifeStage(id,1))<=11);
  assert(!strcmp(lifeStage(id,2),"ADULT") && !strcmp(lifeStage(id,3),"ELDER"));
  assert(strcmp(lifeStage(id,0),"FRY"));
  const Movement m=movement(id);assert(m!=Swim && m!=Flutter);
  assert(renderId(id)==id);
 }
 assert(names.size()==landCount && ids.size()==landCount);
 for(unsigned i=0;i<count;++i){assert(names.count(label(i))==0);assert(!landKnown(i));}
 for(unsigned id=Eagle;id<=Bug;++id){assert(names.count(label(id))==0);assert(!landKnown(id));}
 assert(!landKnown(511) && !landKnown(551) && !known(511) && !known(551) && !known(274));
 // Edition gate (Land IDs only in Land builds; Water/Air unchanged), whole 16-bit range.
 for(unsigned id=0;id<65536;++id) {
  const bool w=id<15,a=id>=256&&id<=273,l=id>=512&&id<=550;
  assert(waterKnown(id)==w && airKnown(id)==a && landKnown(id)==l && known(id)==(w||a||l));
  const bool expect=LORAGOTCHI_LAND_EDITION ? l : LORAGOTCHI_AIR_EDITION ? a : w;
  assert(editionKnown(id)==expect);
  assert(renderId(id)==(known(id)?id:0));
 }
 // Selection menu: Land lists the 39 Land species; other builds keep their exact old tables.
 assert(selectableCount==(LORAGOTCHI_LAND_EDITION?39:LORAGOTCHI_AIR_EDITION?18:15));
 assert(freshSpecies==(LORAGOTCHI_LAND_EDITION?512:LORAGOTCHI_AIR_EDITION?256:0));
 for(unsigned i=0;i<selectableCount;++i) {
  const uint16_t id=selectionId(i);assert(editionKnown(id) && selectionIndex(id)==i);
 }
 assert(selectionId(selectableCount)==freshSpecies && selectionId(255)==freshSpecies);
 for(uint32_t seed=0;seed<5000;++seed)assert(editionKnown(mystery(seed)));
 // Wire capability: Land IDs travel only on an explicit L1 ACK; everything else degrades to fish.
 const char* none="LFG1|ACK|1|2";const char* s1="LFG1|ACK|1|2|S1";
 const char* a1="LFG1|ACK|1|2|S1|A1";const char* l1="LFG1|ACK|1|2|S1|L1";
 assert(acknowledged(s1) && acknowledged(a1) && acknowledged(l1) && !acknowledged(none));
 assert(!acknowledged("LFG1|ACK|1|2|S1|L2") && !acknowledged("LFG1|ACK|1|2|S1|L1|junk"));
 assert(landAcknowledged(l1) && !landAcknowledged(s1) && !landAcknowledged(a1) && !landAcknowledged(none));
 assert(!airAcknowledged(l1) && airAcknowledged(a1));
 for(unsigned id=Dog;id<=TRex;++id) {
  assert(wireSpecies(id,l1)==id);
  assert(wireSpecies(id,s1)==TropicalFish && wireSpecies(id,a1)==TropicalFish && wireSpecies(id,none)==TropicalFish);
  assert(!wireFallback(id,l1) && wireFallback(id,s1) && wireFallback(id,a1));
 }
 for(unsigned id=Eagle;id<=Bug;++id){assert(wireSpecies(id,a1)==id && wireSpecies(id,l1)==TropicalFish);assert(!wireFallback(id,a1) && wireFallback(id,l1));}
 for(unsigned id=0;id<15;++id){assert(wireSpecies(id,s1)==id && wireSpecies(id,l1)==id && !wireFallback(id,none));}
 // Sprites: Land sprite draws exactly Land IDs; Air/Water sprites never draw Land IDs.
 for(unsigned id=0;id<65536;++id) {
  Canvas c;LoRaFishLandSprite::draw(c,64,32,true,id,2,0,1U,2U,3U,0U);
  assert((c.calls!=0)==landKnown(id));
  if(landKnown(id)) {Canvas e;LoRaFishLandSprite::draw(e,64,32,true,id,0,280,1U,2U,3U,0U);assert(e.calls);}
  Canvas a;LoRaFishAirSprite::draw(a,64,32,true,id,2,0,1U,2U,3U,0U);assert((a.calls!=0)==airKnown(id));
  Canvas w;LoRaFishWaterSprite::draw(w,64,32,true,id,2,0,1U,2U,3U,0U);assert((w.calls!=0)==(id>0 && id<15));
 }
 for(unsigned id=Dog;id<=TRex;++id)for(unsigned stage=0;stage<4;++stage)for(unsigned phase=0;phase<2;++phase)
 for(bool right:{false,true})for(int x:{-40,0,64,168})for(int y:{-20,37,84}) {
  Canvas c;LoRaFishLandSprite::draw(c,x,y,right,id,stage,phase*280,1U,2U,3U,0U);assert(c.calls<=768);
 }
 // Discovery markers: Land emoji count only in Land builds; Air/Water markers keep working elsewhere.
 const char dog[]="\xF0\x9F\x90\x95",rhino[]="\xF0\x9F\xA6\x8F",eagle[]="\xF0\x9F\xA6\x85",plain[]="Alice";
 assert(LoRaFishText::hasFish(dog,sizeof(dog))==(LORAGOTCHI_LAND_EDITION!=0));
 assert(LoRaFishText::hasFish(rhino,sizeof(rhino))==(LORAGOTCHI_LAND_EDITION!=0));
 assert(LoRaFishText::hasFish(eagle,sizeof(eagle))==(LORAGOTCHI_AIR_EDITION!=0));
 assert(!LoRaFishText::hasFish(plain,sizeof(plain)));
 char out[16];LoRaFishText::display(out,sizeof(out),dog,sizeof(dog));
 assert(!strcmp(out,LORAGOTCHI_LAND_EDITION?"[L]":" "));
 std::puts("ok");
}
'''
with tempfile.TemporaryDirectory(prefix='land-registry-') as t:
 p=Path(t);(p/'test.cpp').write_text(code)
 for edition in ('DX','WATER','AIR','LAND'):
  flags=[] if edition=='DX' else ['-DLORAGOTCHI_%s_EDITION=1'%edition]
  subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
    '-I',str(ROOT),'-I',str(ROOT/'src'),*flags,str(p/'test.cpp'),'-o',str(p/('t'+edition))],check=True)
  subprocess.run([str(p/('t'+edition))],check=True)
  print('PASS Land registry/gate/wire/sprite bounds in',edition,'build')
# Two editions at once is a configuration error.
r=subprocess.run(['g++','-std=c++17','-fsyntax-only','-DLORAGOTCHI_LAND_EDITION=1','-DLORAGOTCHI_AIR_EDITION=1',
  '-I',str(ROOT),'-x','c++','-'],input='#include "examples/companion_radio/LoRaGotchiVersion.h"\n',text=True,capture_output=True)
assert r.returncode!=0 and 'Select one habitat edition' in r.stderr
# Generator names, art header comments and firmware labels stay in step (no Pillow needed).
gen=(ROOT/'tools/land/generate_sprites.py').read_text()
names=re.findall(r"'([^']+)'",gen.split('NAMES = [',1)[1].split(']',1)[0])
art=(ROOT/'examples/companion_radio/ui-new/LoRaFishLandArt.h').read_text()
assert re.findall(r'// (\d+) ([^\n]+)\n',art)==[(str(512+i),n) for i,n in enumerate(names)]
assert len(names)==39 and len(set(names))==39
header=(ROOT/'examples/companion_radio/LoRaFishSpecies.h').read_text()
labels=re.findall(r'"([^"]+)"',header.split('landNames[]={',1)[1].split('};',1)[0])
assert labels==names,(labels,names)
print('PASS 39 Land species: registry, names, IDs 512..550 unique, no Water/Air collision, editions gated, art/labels in step')
