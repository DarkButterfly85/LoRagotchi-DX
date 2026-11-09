#!/usr/bin/env python3
"""Natural idle motion pilot (Dog): host-compiled, no firmware build, no device timing claims."""
from pathlib import Path
import subprocess, tempfile
ROOT=Path(__file__).resolve().parents[2]
source=r'''
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <initializer_list>
#include <vector>
#include "examples/companion_radio/LoRaFishSpecies.h"
using namespace LoRaFishSpecies;
struct P {int x=71,y=39;bool r=false;};
P at(uint16_t id,uint8_t stage,uint32_t now,uint32_t offset=0,int width=128,bool idle=true) {
 P p;habitatPosition(id,stage,width,now,offset,p.x,p.y,p.r,idle);return p;
}
int main() {

 // Sample every 10 ms; "moving" = position changed over the last 200 ms (pace is ~18 px/s, so >=3 px).
 for(int width:{128,160,240,320})for(uint8_t stage=0;stage<4;++stage)for(uint32_t offset:{0U,2700U}) {
  std::vector<P> v;
  for(uint32_t t=1000;t<400000;t+=10)v.push_back(at(Dog,stage,t,offset,width));
  uint32_t stand=0,walk=0,turns=0,edges=0;
  for(size_t i=1;i<v.size();++i) {
   assert(v[i].x>=20 && v[i].x<=width-20 && v[i].y==37);
   assert(abs(v[i].x-v[i-1].x)<=1); // no teleporting: <=1 px per 10 ms
   if(i<20)continue;
   const bool moving=abs(v[i].x-v[i-20].x)>=2;
   if(v[i].x!=v[i-1].x)assert(v[i].r==(v[i].x>v[i-1].x)); // faces the way it walks
   if(moving)++walk;else ++stand;
   if(v[i].r!=v[i-1].r)++turns;
   if(v[i].x==20 || v[i].x==width-20)++edges;
  }
  assert(walk*8>=v.size() && stand*8>=v.size()); // genuinely pauses AND genuinely walks
  assert(turns>20);   // look-arounds / edge turns happen
  assert(edges>0);    // reaches an edge over time
 }
 // Phase lengths on a 128 px tank at adult pace: pauses ~1-3 s, walks <= ~4.5 s.
 {
  std::vector<int> v;for(uint32_t t=5000;t<400000;t+=10)v.push_back(at(Dog,2,t).x);
  uint32_t runs=0,longWalks=0;size_t start=0;bool moving=false;
  for(size_t i=10;i<v.size();++i) {
   const bool m=v[i]!=v[i-10]; // changed within 100 ms
   if(m!=moving) {
    const uint32_t d=(uint32_t)(i-start)*10;
    if(moving){assert(d<=4800);if(d>=1900)++longWalks;++runs;}
    else assert(d>=700 && d<=3500);
    moving=m;start=i;
   }
  }
  assert(runs>30 && longWalks*2>runs);
 }
 // Same time -> same answer however often it is asked (render is idempotent), per slot.
 {
  P a=at(Dog,2,123456),b=at(Dog,2,123456);assert(a.x==b.x && a.r==b.r);
  P g1=at(Dog,2,123456,2700),g2=at(Dog,2,123456,2700);assert(g1.x==g2.x && g1.r==g2.r);
 }
 // Backward time jumps and long gaps (screen off) restart cleanly inside the tank.
 for(uint32_t t:{0u,900000u,3u,UINT32_MAX-5000u,40u,UINT32_MAX}) {P p=at(Dog,2,t);assert(p.x>=20 && p.x<=108);}
 // millis() rollover through the visitor offset stays bounded.
 for(uint32_t k=0;k<2000u;++k){uint32_t t=UINT32_MAX-30000u+k*37u;P p=at(Dog,2,t,2700);assert(p.x>=20 && p.x<=108);}
 // Home and visitor are independent timelines.
 {
  int diff=0;for(uint32_t t=0;t<60000;t+=100)if(at(Dog,2,t).x!=at(Dog,2,t,2700).x)++diff;
  assert(diff>300);
 }
 // Narrow tank: no roaming, no crash.
 {P p=at(Dog,2,5000,0,50);assert(p.x==20 && p.y==37);}
 // E-ink call sites pass idleMotion=false: exactly the legacy triangle wave.
 for(uint8_t stage=0;stage<4;++stage)for(uint32_t now=0;now<40000;now+=113) {
  P p=at(Dog,stage,now,2700,128,false);
  uint32_t period=10000;if(stage==0)period=7500;else if(stage>=3)period=12500;
  uint32_t t=(now+2700)%period,half=period/2;bool right=t<half;
  assert(p.r==right && p.x==20+(int)(88U*(right?t:period-t)/half) && p.y==37);
 }
 // Every other Land animal, and all Air and Water animals, are unchanged by the flag (legacy path).
 for(uint16_t id=0;id<600;++id) {
  if(id==Dog)continue;
  for(uint32_t now=0;now<30000;now+=211) {
   P a=at(id,2,now,2700,128,true),b=at(id,2,now,2700,128,false);
   assert(a.x==b.x && a.y==b.y && a.r==b.r);
  }
 }
 assert(naturalIdle(Dog) && !naturalIdle(Cat) && !naturalIdle(Eagle) && !naturalIdle(Crab));
}
'''
with tempfile.TemporaryDirectory(prefix='dx-idle-') as tmp:
    cpp=Path(tmp)/'idle.cpp';cpp.write_text(source)
    for edition in ('DX','WATER','AIR','LAND','DXPRO'):
        exe=Path(tmp)/edition
        flags=[] if edition=='DX' else [f'-DLORAGOTCHI_{edition}_EDITION=1'] if edition!='DXPRO' else ['-DLORAGOTCHI_DXPRO=1']
        subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=undefined,address','-I',str(ROOT),*flags,str(cpp),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
        print('PASS natural idle motion',edition)
ui=(ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text()
assert 'right,!display.isEink());' in ui and 'gright,!display.isEink());' in ui
sprite=(ROOT/'examples/companion_radio/ui-new/LoRaFishLandSprite.h').read_text()
assert 'naturalIdle(id)' in sprite
print('PASS call sites pass !isEink(); Dog legs step by distance walked')
