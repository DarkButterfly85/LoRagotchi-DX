#!/usr/bin/env python3
"""Natural idle motion for every animal group (host-compiled C++ model; no firmware build, no hardware).

Ground animals stand / walk / turn / look around. Flyers never stop flapping while airborne (only a landed
flyer may hold a wing frame). Swimmers never fully stop. E-ink call sites keep the legacy drift (no freeze) and the
Efficient 1 FPS mode simply samples the same clock-driven path once a second.
"""
from pathlib import Path
import subprocess, tempfile
ROOT=Path(__file__).resolve().parents[2]
source=r'''
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include "examples/companion_radio/LoRaFishSpecies.h"
using namespace LoRaFishSpecies;
struct S {int x=71,y=39;bool r=false;uint8_t pose=0;uint32_t anim=0;};
S at(uint16_t id,uint8_t stage,uint32_t now,uint32_t offset=0,int width=128,bool idle=true,int floorY=37,int airY=-1) {
 S s;habitatPosition(id,stage,width,now,offset,s.x,s.y,s.r,idle,&s.pose,floorY,airY);
 s.anim=animClock(s.pose,now+offset);return s;
}
static std::vector<S> run(uint16_t id,uint8_t stage,int width,uint32_t offset,uint32_t step,uint32_t seconds,int floorY=37,bool sway=false) {
 std::vector<S> v;
 for(uint32_t t=1000;t<1000+seconds*1000;t+=step) {
  const int airY=sway ? 30+(int)(11*sinf(t/5100.0f)) : -1;
  v.push_back(at(id,stage,t,offset,width,true,floorY,airY));
 }
 return v;
}
// Longest stretch (ms) in which x did not change, restricted to samples where pred(sample) is true.
template<class F> static uint32_t longestStill(const std::vector<S>& v,uint32_t step,F pred) {
 uint32_t best=0,cur=0;
 for(size_t i=1;i<v.size();++i) {
  if(pred(v[i]) && v[i].x==v[i-1].x)cur+=step;else cur=0;
  if(cur>best)best=cur;
 }
 return best;
}
static void checkGround(uint16_t id,uint8_t stage,int width,uint32_t offset) {
 const auto v=run(id,stage,width,offset,10,240);
 uint32_t stand=0,walk=0,turns=0,edges=0;
 for(size_t i=1;i<v.size();++i) {
  assert(v[i].x>=20 && v[i].x<=width-20 && v[i].y==37);          // stays in its tank, on the ground
  assert(v[i].pose==PoseIdle && v[i].anim==1000+i*10+offset);      // ground: live clock, legs step by distance
  assert(abs(v[i].x-v[i-1].x)<=1);                                // no jumps
  if(v[i].x!=v[i-1].x)assert(v[i].r==(v[i].x>v[i-1].x));          // faces the way it walks
  if(i<50)continue;
  if(abs(v[i].x-v[i-50].x)>=2)++walk;else ++stand;
  if(v[i].r!=v[i-1].r)++turns;
  if(v[i].x==20 || v[i].x==width-20)++edges;
 }
 assert(walk*8>=v.size() && stand*8>=v.size());                  // genuinely walks AND genuinely pauses
 assert(turns>=6 && edges>0);                                    // turns and reaches an edge
 assert(longestStill(v,10,[](const S&){return true;})<=6000);    // never frozen for long
}
static void checkFlyer(uint16_t id,uint8_t stage,int width,uint32_t offset,int floorY,bool sway) {
 const auto v=run(id,stage,width,offset,10,300,floorY,sway);
 const int top=sway ? 19 : 29;
 uint32_t landed=0,landRun=0,maxLand=0,airTurns=0;
 for(size_t i=1;i<v.size();++i) {
  const uint32_t now=1000+(uint32_t)i*10+offset;
  assert(v[i].x>=20 && v[i].x<=width-20);                        // inside the tank
  assert(v[i].y>=top && v[i].y<=floorY);                         // between the air rows and the floor
  assert(v[i].pose&PoseOwnsY && v[i].pose&PoseIdle);
  assert(abs(v[i].x-v[i-1].x)<=1);                               // no sideways jumps
  assert(abs(v[i].y-v[i-1].y)<=(sway ? 4 : 3));                  // no vertical jumps (the old 3-row wing bob alone steps up to 2)
  if(v[i].x!=v[i-1].x && v[i].r==v[i-1].r)assert(v[i].r==(v[i].x>v[i-1].x)); // (the flip sample may round 1 px the old way)
  if(v[i].r!=v[i-1].r)++airTurns;
  if(v[i].pose&PoseLanded) {
   ++landed;++landRun;if(landRun>maxLand)maxLand=landRun;
   assert(v[i].y==floorY);                                       // only ever landed ON the floor
   assert(v[i].x==v[i-1].x || !(v[i-1].pose&PoseLanded));        // a landed flyer stands still
   assert(v[i].anim==0);                                         // the one case a wing frame is held
  } else {
   landRun=0;
   assert(v[i].anim==now);                                       // airborne: live clock -> keeps flapping
  }
 }
 assert(maxLand*10<=3700);                                       // landings are short
 assert(landed*10<=v.size()*10/2);                               // mostly in the air
 assert(width<128 || landed>0);                                  // wide enough tanks do land now and then
 assert(airTurns>=4);                                            // gliding turns happen
 assert(longestStill(v,10,[](const S& s){return !(s.pose&PoseLanded);})<=1200); // airborne is never stalled
 // Flap frames really alternate while airborne (280 ms per frame, the sprite's own clock).
 uint32_t flips=0;unsigned last=2;
 for(size_t i=0;i<v.size();++i) {
  if(v[i].pose&PoseLanded)continue;
  const unsigned f=(v[i].anim/280U)&1U;
  if(last!=2 && f!=last)++flips;
  last=f;
 }
 assert(flips>200);
}
static void checkSwimmer(uint16_t id,uint8_t stage,int width,uint32_t offset) {
 const auto v=run(id,stage,width,offset,10,300);
 int lo=999,hi=0;uint32_t hover=0;
 for(size_t i=1;i<v.size();++i) {
  assert(v[i].x>=20 && v[i].x<=width-20);                        // inside the tank
  assert(v[i].y==39);                                            // y stays with the caller's own fish bob
  assert(v[i].pose&PoseIdle && !(v[i].pose&(PoseLanded|PoseOwnsY)));
  assert(v[i].anim!=0);                                          // the tail/fin animation never stops
  assert(abs(v[i].x-v[i-1].x)<=1);                               // no jumps
  // Facing follows the swim direction. The single sample where the turn starts may still step 1 px the old way (rounding).
  if(v[i].x!=v[i-1].x && v[i].r==v[i-1].r)assert(v[i].r==(v[i].x>v[i-1].x));
  if(v[i].pose&PoseHover) {++hover;assert(v[i].anim==(1000+(uint32_t)i*10+offset)/2U);}
  if(v[i].x<lo)lo=v[i].x;
  if(v[i].x>hi)hi=v[i].x;
 }
 assert(hover>0 && hover<v.size()*6/10);                         // hovers, but mostly swims
 assert(longestStill(v,10,[](const S&){return true;})<=1500);    // never still beyond a short interval
 assert((hi-lo)*10>=(width-40)*6);                               // roams most of the tank
}
int main() {
 // ---- group table -------------------------------------------------------------------------------------
 uint32_t nGround=0,nFly=0,nSwim=0;
 for(uint16_t id=0;id<700;++id) {
  const IdleGroup g=idleGroup(id);
  if(!known(id) || id==Crab || id==ShellDweller || id==Jellyfish) {assert(g==IdleNone && !naturalIdle(id));continue;}
  switch(movement(id)) {
   case Walk: case Crawl:assert(g==IdleGround && steppedByDistance(id));++nGround;break;
   case FlyMotion: case Flutter:assert(g==IdleFlyer && !steppedByDistance(id));++nFly;break;
   default:assert(g==IdleSwimmer && !steppedByDistance(id));++nSwim;
  }
 }
 assert(nGround==43 && nFly==14 && nSwim==12); // 36 Land + 7 Air walkers/crawlers; 11 Air + 3 Land flyers; 12 Water swimmers
 assert(idleGroup(Dog)==IdleGround && idleGroup(Worm)==IdleGround && idleGroup(Penguin)==IdleGround);
 assert(idleGroup(Eagle)==IdleFlyer && idleGroup(Butterfly)==IdleFlyer && idleGroup(Dragon)==IdleFlyer);
 assert(idleGroup(TropicalFish)==IdleSwimmer && idleGroup(Whale)==IdleSwimmer);
 // ---- every animal, default tank (128 px), home and visitor slots ---------------------------------------
 for(uint16_t id=0;id<700;++id) {
  if(!naturalIdle(id))continue;
  for(uint32_t offset:{0U,2700U}) {
   switch(idleGroup(id)) {
    case IdleGround:checkGround(id,2,128,offset);break;
    case IdleFlyer:checkFlyer(id,2,128,offset,37,false);break;
    default:checkSwimmer(id,2,128,offset);
   }
  }
 }
 // ---- one animal per kind across tank widths and life stages ---------------------------------------------
 for(int width:{96,128,160,240,320})for(uint8_t stage=0;stage<4;++stage)for(uint32_t offset:{0U,2700U}) {
  for(uint16_t id:{Dog,Worm,Penguin,Snake})checkGround(id,stage,width,offset);
  for(uint16_t id:{Eagle,Butterfly,Dragon,Bat})checkFlyer(id,stage,width,offset,37,false);
  for(uint16_t id:{TropicalFish,Whale,Anglerfish})checkSwimmer(id,stage,width,offset);
 }
 // Tall native panels: the flyer keeps its slow vertical sway and lands on the lower floor row.
 for(int width:{128,240,320})for(uint16_t id:{Eagle,Butterfly,Dragon})checkFlyer(id,2,width,0,42,true);
 // ---- Efficient 1 FPS: the path is a pure function of the clock, so 1 s sampling = a subsample ---------
 for(uint16_t id:{Dog,Worm,Eagle,Butterfly,Bat,TropicalFish,Whale}) {
  const auto fine=run(id,2,128,0,10,200);
  const auto slow=run(id,2,128,0,1000,200);
  for(size_t i=0;i<slow.size();++i) {
   const S& a=slow[i];const S& b=fine[i*100];
   assert(a.x==b.x && a.y==b.y && a.r==b.r && a.pose==b.pose);
  }
  if(idleGroup(id)==IdleSwimmer) { // at 1 frame/s a swimmer still visibly moves nearly every frame
   uint32_t same=0;for(size_t i=1;i<slow.size();++i)if(slow[i].x==slow[i-1].x)++same;
   assert(same*8<slow.size());
  }
  if(idleGroup(id)==IdleGround) { // and a walker is seen both standing and walking
   uint32_t same=0;for(size_t i=1;i<slow.size();++i)if(slow[i].x==slow[i-1].x)++same;
   assert(same>10 && same<slow.size()*8/10);
  }
 }
 // ---- determinism: same time -> same answer however often it is asked, and per slot -------------------
 for(uint16_t id:{Dog,Eagle,TropicalFish}) {
  const auto a=run(id,2,128,0,37,100),b=run(id,2,128,0,37,100);
  for(size_t i=0;i<a.size();++i)assert(a[i].x==b[i].x && a[i].y==b[i].y && a[i].r==b[i].r && a[i].pose==b[i].pose);
  S p=at(id,2,123456),q=at(id,2,123456);assert(p.x==q.x && p.r==q.r && p.y==q.y);
  S g1=at(id,2,123456,2700),g2=at(id,2,123456,2700);assert(g1.x==g2.x && g1.r==g2.r);
 }
 // ---- backward jumps, long gaps and millis() rollover stay inside the tank -----------------------------
 for(uint16_t id:{Dog,Worm,Eagle,Butterfly,TropicalFish}) {
  for(uint32_t t:{0u,900000u,3u,UINT32_MAX-5000u,40u,UINT32_MAX}) {S p=at(id,2,t);assert(p.x>=20 && p.x<=108);}
  for(uint32_t k=0;k<2000u;++k){uint32_t t=UINT32_MAX-30000u+k*37u;S p=at(id,2,t,2700);assert(p.x>=20 && p.x<=108);}
  for(uint32_t t=5000;t<60000;t+=500) {S p=at(id,2,t);assert(p.x>=20 && p.x<=108);}
  S after=at(id,2,160000);assert(after.x>=20 && after.x<=108); // 100 s gap (screen off): resumes cleanly
 }
 // ---- home and visitor are independent timelines ------------------------------------------------------
 for(uint16_t id:{Dog,Eagle,TropicalFish}) {
  int diff=0;for(uint32_t t=0;t<60000;t+=100)if(at(id,2,t).x!=at(id,2,t,2700).x)++diff;
  assert(diff>300);
 }
 // ---- narrow tank: no roaming, no crash -----------------------------------------------------------------
 for(uint16_t id:{Dog,Eagle,TropicalFish}) {S p=at(id,2,5000,0,50);assert(p.x==20);}
 // ---- E-ink call sites pass idleMotion=false: exactly the legacy drift, nothing frozen, no pose ---------
 for(uint16_t id=0;id<700;++id) {
  if(!known(id))continue;
  for(uint8_t stage=0;stage<4;++stage)for(uint32_t now=0;now<40000;now+=113) {
   S p=at(id,stage,now,2700,128,false);
   assert(p.pose==0 && p.anim==now+2700);                        // never a frozen animation clock
   if(airKnown(id) || landKnown(id)) {
    const Movement kind=movement(id);
    uint32_t period=kind==Crawl ? 16000 : kind==Walk ? 10000 : kind==Flutter ? 4200 : 8000;
    if(stage==0)period=period*3/4;else if(stage>=3)period=period*5/4;
    uint32_t t=(now+2700)%period,half=period/2;bool right=t<half;
    assert(p.r==right && p.x==20+(int)(88U*(right?t:period-t)/half) && p.y==habitatY(id,39,now+2700));
   } else if(!waterMotion(id)) {assert(p.x==71 && p.y==39 && p.r==false);} // water fish: caller keeps its own path
  }
 }
 // Crab, snail and jellyfish ignore the flag entirely (their own Water paths).
 for(uint16_t id:{Crab,ShellDweller,Jellyfish})for(uint32_t now=0;now<30000;now+=211) {
  S a=at(id,2,now,2700,128,true),b=at(id,2,now,2700,128,false);
  assert(a.x==b.x && a.y==b.y && a.r==b.r && a.pose==0 && b.pose==0);
 }
 // Animation clock: only a landed flyer is frozen; a hovering swimmer wobbles at half speed.
 assert(animClock(0,5000)==5000 && animClock(PoseIdle,5000)==5000 && animClock(PoseIdle|PoseOwnsY,5000)==5000);
 assert(animClock(PoseIdle|PoseOwnsY|PoseLanded,5000)==0 && animClock(PoseIdle|PoseHover,5000)==2500);
 puts("ok");
}
'''
with tempfile.TemporaryDirectory(prefix='dx-idle-') as tmp:
    cpp=Path(tmp)/'idle.cpp';cpp.write_text(source)
    for edition in ('DX','WATER','AIR','LAND','DXPRO'):
        exe=Path(tmp)/edition
        flags=[] if edition=='DX' else [f'-DLORAGOTCHI_{edition}_EDITION=1'] if edition!='DXPRO' else ['-DLORAGOTCHI_DXPRO=1']
        subprocess.run(['g++','-std=c++17','-O1','-Wall','-Wextra','-Werror','-fsanitize=undefined,address','-I',str(ROOT),*flags,str(cpp),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
        print('PASS natural idle motion, all groups',edition)
ui=(ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text()
# E-ink keeps the legacy path (idleMotion=false), no freeze; 1 FPS mode just samples the same clock-driven path.
assert 'right,!display.isEink(),&pose,idleFloorY' in ui and 'gright,!display.isEink(),&gpose,guestFloorY' in ui
assert 'animClock(pose,(uint32_t)millis())' in ui
assert 'loRaFishFeeding ? 0 : pose' in ui            # a feeding animal is never frozen
assert ui.count('animNow,')>=4                        # sprites get the pose-aware clock
assert 'loRaFishSimulationMode==2 ? 1000' in ui        # the Efficient 1 FPS refresh interval is untouched
for name in ('Air','Land'):
    sprite=(ROOT/f'examples/companion_radio/ui-new/LoRaFish{name}Sprite.h').read_text()
    assert 'steppedByDistance(id) ?' in sprite and '(now/280U)&1U' in sprite   # walkers by distance, flyers by clock
print('PASS call sites: e-ink legacy path, 1 FPS interval, pose-aware clock; ground legs step by distance')
