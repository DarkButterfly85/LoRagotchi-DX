#!/usr/bin/env python3
"""Compile real species choreography across editions; no device timing claims."""
from pathlib import Path
import subprocess, tempfile
ROOT=Path(__file__).resolve().parents[2]
source=r'''
#include <cassert>
#include <cstdint>
#include <initializer_list>
#include "examples/companion_radio/LoRaFishSpecies.h"
using namespace LoRaFishSpecies;
struct P {int x=71,y=39;bool r=false;};
// idleMotion=false is the legacy drift (e-ink call sites); the natural idle motion of every group is covered
// by check_natural_idle.py.
P at(uint16_t id,uint8_t stage,uint32_t now,uint32_t offset=0,int width=128) {
 P p;habitatPosition(id,stage,width,now,offset,p.x,p.y,p.r,false);return p;
}
int main() {
 for(uint16_t id:{(uint16_t)ShellDweller,(uint16_t)Crab,(uint16_t)Jellyfish})
 for(uint8_t stage=0;stage<4;++stage)
 for(int width:{128,160,240,320})
 for(uint32_t t=0;t<80000;t+=17) {
  auto p=at(id,stage,t,2700,width);
  assert(p.x>=20 && p.x<=width-20);
  assert(p.y>=30 && p.y<=37);
  if(id!=Jellyfish)assert(p.y==37);
  auto q=at(id,stage,t+2700,0,width);
  assert(p.x==q.x && p.y==q.y && p.r==q.r);
 }
 // uint32 millis/guest offset rollover is explicit even on 64-bit hosts.
 for(uint16_t id:{(uint16_t)ShellDweller,(uint16_t)Crab,(uint16_t)Jellyfish}) {
  auto p=at(id,2,UINT32_MAX-10,2700),q=at(id,2,2689);
  assert(p.x==q.x && p.y==q.y && p.r==q.r);
  assert(at(id,2,0).r);assert(!at(id,2,id==ShellDweller?16000:id==Crab?6000:9000).r);
 }
 assert(at(ShellDweller,2,1000).x < at(Crab,2,1000).x);
 assert(at(Crab,2,750).x==at(Crab,2,1400).x);
 assert(at(Crab,2,200).x<at(Crab,2,600).x);
 assert(at(Jellyfish,2,0).y==36 && at(Jellyfish,2,600).y==30);
 assert(at(Jellyfish,2,1500).y==33);
 // Generic fish, other water animals and opaque/future IDs are exact no-ops.
 for(uint16_t id=0;id<256;++id)if(!waterMotion(id)) {
  auto p=at(id,2,3456);assert(p.x==71 && p.y==39 && !p.r);
 }
 auto unknown=at(65535,2,123);assert(unknown.x==71 && unknown.y==39 && !unknown.r);
 // Existing Air movement remains byte-for-byte algorithmically equivalent.
 for(uint16_t id=Eagle;id<=Bug;++id)for(uint8_t stage=0;stage<4;++stage)
 for(uint32_t now=0;now<40000;now+=113) {
  auto kind=movement(id);uint32_t period=kind==Crawl?16000:kind==Walk?10000:kind==Flutter?4200:8000;
  if(stage==0)period=period*3/4;else if(stage>=3)period=period*5/4;
  uint32_t t=(now+2700)%period,half=period/2;bool right=t<half;
  auto p=at(id,stage,now,2700);assert(p.r==right);
  assert(p.x==20+(int)(88U*(right?t:period-t)/half));
  assert(p.y==habitatY(id,39,now+2700));
 }
 // Land animals share the Air walk/crawl/fly model: grounded or airborne, always inside the tank.
 for(uint16_t id=Dog;id<=TRex;++id)for(uint8_t stage=0;stage<4;++stage)
 for(int width:{128,160,240})for(uint32_t now=0;now<40000;now+=113) {
  auto p=at(id,stage,now,2700,width);
  assert(p.x>=20 && p.x<=width-20);
  assert(p.y==habitatY(id,39,now+2700));
  auto kind=movement(id);assert(kind==Walk || kind==Crawl || kind==FlyMotion);
  if(kind==Walk || kind==Crawl)assert(p.y==37);
 }
 assert(movement(Dog)==Walk && movement(Snake)==Crawl && movement(Dragon)==FlyMotion);
}
'''
with tempfile.TemporaryDirectory(prefix='dx-motion-') as tmp:
    cpp=Path(tmp)/'motion.cpp';cpp.write_text(source)
    for edition in ('DX','WATER','AIR','LAND'):
        exe=Path(tmp)/edition
        flags=[] if edition=='DX' else [f'-DLORAGOTCHI_{edition}_EDITION=1']
        subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=undefined','-I',str(ROOT),*flags,str(cpp),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
        print('PASS production species motion',edition)
ui=(ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text()
assert 'habitatPosition(loRaFishSpecies,fish.evolution' in ui
assert 'guestMotionSpecies=guestPresent ? loragotchiDXGuest.species :' in ui
assert 'habitatPosition(guestMotionSpecies,guestStage' in ui
assert 'LORAGOTCHI_ANIMAL_EDITION || LoRaFishSpecies::waterMotion(guestMotionSpecies)' in ui
assert ui.index('habitatPosition(loRaFishSpecies') < ui.index('const int foodX=w/2+18;')
assert 'const int homeTargetY=localSleeping ? 38+bodyOffset : y;' in ui
assert 'const int bodyOffset=LoRaFishLayout::bodyOffset(h);' in ui
assert 'gy=LoRaFishLayout::habitatY(gy,h,' in ui
assert '!loRaFishFeeding && !LoRaFishSpecies::waterMotion(loRaFishSpecies)' in ui
print('PASS home/visitor hooks, feed/sleep precedence, wander bubbles guard')
