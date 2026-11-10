#!/usr/bin/env python3
"""Water build and DX-Pro move the 12 swimming fish identically (host-compiled; no firmware build, no hardware).

The 12 swimmers are every Water-set species except crab, snail (shell-dweller) and jellyfish. The same
production LoRaFishSpecies.h and the exact loRaFishBandY text from UITask.cpp are compiled once as the
Water edition and once as DX-Pro; every position, facing, pose, animation clock and band row must match
sample for sample. Also proves the shared gate macro is on for Water and DX-Pro, off for plain DX, and
that crab / snail / jellyfish still use their own Water paths in both builds.
"""
from pathlib import Path
import hashlib, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[2]
ui=(ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text()
start=ui.index('#if LORAGOTCHI_WATER_EDITION || LORAGOTCHI_DXPRO\n// Bands need room')
helper=ui[start:ui.index('static void drawLoRaFishAquarium(')]

source=r'''
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <algorithm>
#include "examples/companion_radio/LoRaFishSpecies.h"
#include "examples/companion_radio/ui-new/LoRaFishWaterSprite.h"
''' + helper + r'''
using namespace LoRaFishSpecies;
static constexpr uint16_t swimmers[]={TropicalFish,Blowfish,Shark,Dolphin,Whale,Seal,Shrimp,Squid,Lobster,Octopus,SeaStar,Anglerfish};
static_assert(sizeof(swimmers)/sizeof(swimmers[0])==12,"12 swimming fish");
static uint32_t fnv(uint32_t h,uint32_t v){for(int i=0;i<4;++i){h^=(v>>(i*8))&0xFFU;h*=16777619U;}return h;}
int main() {
  assert(LORAGOTCHI_HABITAT_MOTION==1);   // the call-site gate in UITask.cpp is open in this build
  uint32_t hash=2166136261U,samples=0,moved=0;
  for(uint16_t id:swimmers) {
    assert(idleGroup(id)==IdleSwimmer);
    for(uint8_t stage=0;stage<4;++stage)for(int width:{96,128,160,240})for(uint32_t offset:{0U,2700U}) {
      int px=-1;
      for(uint32_t now=1000;now<181000;now+=250) { // 3 minutes, 4 samples a second
        int x=71,y=39;bool right=false;uint8_t pose=0;
        habitatPosition(id,stage,width,now,offset,x,y,right,true,&pose,37,-1);
        assert(pose&PoseIdle && x>=20 && x<=(width>40?width-40:1)+20);
        const uint32_t anim=animClock(pose,now+offset);
        assert(anim!=0);                                   // the tail never freezes
        if(px!=-1 && x!=px)++moved;
        px=x;
        // Band rows: native (tall) and fixed-row (64 px) call sites, bob 36..40 / sway 19..41.
        const int fixedY=loRaFishBandY(id,36+(int)(now/700U%5U),64);
        assert(fixedY>=36 && fixedY<=40);                  // bands off on a 64 px panel: shared tank, unchanged
        int nativeY=0;
#ifdef LORAGOTCHI_NATIVE_UI
        nativeY=loRaFishBandY(id,19+(int)(now/300U%23U),122);
        const BandRows t=bandRows(band(id),BandTall);
        assert(loRaFishWaterBands(122) && nativeY>=t.top && nativeY<=t.bottom); // tall panel: inside its own band
#endif
        hash=fnv(hash,(uint32_t)x);hash=fnv(hash,(uint32_t)y);hash=fnv(hash,right);hash=fnv(hash,pose);
        hash=fnv(hash,anim);hash=fnv(hash,(uint32_t)fixedY);hash=fnv(hash,(uint32_t)nativeY);
        ++samples;
      }
    }
  }
  assert(moved*10>samples*7);                              // a fish moves between most samples
  // Crab, snail, jellyfish: their own Water path, identical to waterPosition, never the idle slots.
  for(uint16_t id:{(uint16_t)Crab,(uint16_t)ShellDweller,(uint16_t)Jellyfish})for(uint32_t now=0;now<60000;now+=211) {
    int x=71,y=39,wx=71,wy=39;bool r=false,wr=false;uint8_t pose=9;
    habitatPosition(id,2,128,now,2700,x,y,r,true,&pose,37,-1);
    waterPosition(id,2,128,now,2700,wx,wy,wr);
    assert(pose==0 && x==wx && y==wy && r==wr);
    hash=fnv(hash,(uint32_t)x);hash=fnv(hash,(uint32_t)y);hash=fnv(hash,r);
  }
  printf("%08x %u\n",hash,samples);
}
'''
gate=r'''
#include <cstdio>
#include "examples/companion_radio/LoRaGotchiVersion.h"
int main(){printf("%d\n",(int)(LORAGOTCHI_HABITAT_MOTION));}
'''
with tempfile.TemporaryDirectory(prefix='dx-parity-') as tmp:
    cpp=Path(tmp)/'parity.cpp';cpp.write_text(source)
    g=Path(tmp)/'gate.cpp';g.write_text(gate)
    out={}
    for name,flag in (('WATER','-DLORAGOTCHI_WATER_EDITION=1'),('DXPRO','-DLORAGOTCHI_DXPRO=1')):
        for native in (False,True):
            exe=Path(tmp)/f'{name}{int(native)}'
            # LORAGOTCHI_NATIVE_UI only selects which band table row loRaFishBandY uses (tall panels, h>64).
            flags=[flag]+(['-DLORAGOTCHI_NATIVE_UI=1'] if native else [])
            subprocess.run(['g++','-std=c++17','-O1','-Wall','-Wextra','-Werror','-fsanitize=undefined,address','-I',str(ROOT),*flags,str(cpp),'-o',str(exe)],check=True)
            out[(name,native)]=subprocess.run([str(exe)],check=True,capture_output=True,text=True).stdout.strip()
    for native in (False,True):
        assert out[('WATER',native)]==out[('DXPRO',native)],(native,out)
        print('PASS Water == DX-Pro for the 12 swimmers (native panel rows:',native,') ->',out[('WATER',native)])
    # Gate macro: on for Water/Air/Land/DX-Pro, off for plain DX.
    for flags,want in (([],'0'),(['-DLORAGOTCHI_WATER_EDITION=1'],'1'),(['-DLORAGOTCHI_AIR_EDITION=1'],'1'),
                       (['-DLORAGOTCHI_LAND_EDITION=1'],'1'),(['-DLORAGOTCHI_DXPRO=1'],'1')):
        exe=Path(tmp)/'gate'
        subprocess.run(['g++','-std=c++17','-I',str(ROOT),*flags,str(g),'-o',str(exe)],check=True)
        got=subprocess.run([str(exe)],check=True,capture_output=True,text=True).stdout.strip()
        assert got==want,(flags,got)
    print('PASS gate macro LORAGOTCHI_HABITAT_MOTION: Water/Air/Land/DX-Pro on, plain DX off')
# Call sites really use the shared gate (home and visitor), not an edition list.
assert ui.count('if (LORAGOTCHI_HABITAT_MOTION || LoRaFishSpecies::waterMotion(')==2
assert 'LORAGOTCHI_ANIMAL_EDITION || LoRaFishSpecies::waterMotion(' not in ui
assert 'right,LoRaFishSpecies::idleMotionFor(loRaFishSpecies,display.isEink()),&pose,idleFloorY' in ui
assert 'gright,LoRaFishSpecies::idleMotionFor(guestMotionSpecies,display.isEink()),&gpose,guestFloorY' in ui
print('PASS UITask.cpp call sites: one shared gate for home and visitor; e-ink uses the legacy path except Land sniff walkers (idleMotionFor)')

