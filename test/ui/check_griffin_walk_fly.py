#!/usr/bin/env python3
"""Land Griffin (547) walks, takes off, flies for a few seconds, lands and walks again (host-compiled C++ model).

No firmware build, no hardware. Checks, for every edition build and several tank widths/stages/slots:
  * the Griffin starts on foot and only takes off after a whole ground spell (12 s or more) of walking;
  * a flight (climb + cruise + descent) lasts about 4-8 s, stays on screen and ends on the floor row;
  * the Griffin spends most of its time on the ground, really walks there, and flaps while airborne;
  * e-ink keeps the legacy drift for the Griffin (it is not a sniffer, so it is not on the walker path);
  * every other animal, and the Griffin's e-ink path, produce bit-for-bit the motion of the previous release
    (golden hashes taken from the code before this change);
  * the same clock-driven path at 1 FPS, millis() rollover, long gaps, narrow tanks;
  * sprite frames: legs step by distance on foot, wings flap on the clock in the air; Land art untouched.
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
#include <initializer_list>
#include <vector>
#include "examples/companion_radio/LoRaFishSpecies.h"
#include "examples/companion_radio/ui-new/LoRaFishLandSprite.h"
using namespace LoRaFishSpecies;
struct S {int x=71,y=39;bool r=false;uint8_t pose=0;uint32_t anim=0;};
static S at(uint16_t id,uint8_t stage,uint32_t now,uint32_t offset=0,int width=128,bool idle=true,int floorY=37,int airY=-1) {
 S s;habitatPosition(id,stage,width,now,offset,s.x,s.y,s.r,idle,&s.pose,floorY,airY);
 s.anim=animClock(s.pose,now+offset);return s;
}
static std::vector<S> run(uint16_t id,uint8_t stage,int width,uint32_t offset,uint32_t step,uint32_t seconds,int floorY,bool sway,uint32_t from=1000) {
 std::vector<S> v;
 for(uint32_t t=from;t<from+seconds*1000;t+=step) {
  const int airY=sway ? 30+(int)(11*sinf(t/5100.0f)) : -1;
  v.push_back(at(id,stage,t,offset,width,true,floorY,airY));
 }
 return v;
}
static bool onFoot(const S& s) {return (s.pose&PoseGround)!=0;}
// One tank: walks first, then flies, lands, walks again; always inside the tank and never jumping.
static void checkGriffin(uint8_t stage,int width,uint32_t offset,int floorY,bool sway) {
 const uint32_t step=10;
 const auto v=run(Griffin,stage,width,offset,step,400,floorY,sway);
 const int top=sway ? 19 : 29;
 const int span=width-40;
 uint32_t groundMs=0,spellMs=0,flightMs=0,flights=0,spells=0,walkedMs=0,maxFlightMs=0,minFlightMs=1u<<30,minSpellMs=1u<<30;
 int flightLo=999,flightHi=0,widestFlight=0;
 bool first=true,wasOnFoot=true;
 uint32_t flips=0;unsigned lastFrame=2;
 for(size_t i=0;i<v.size();++i) {
  const S& p=v[i];
  const uint32_t now=1000+(uint32_t)i*step+offset;
  assert(p.x>=20 && p.x<=width-20);                                        // inside the tank
  assert(p.y>=top && p.y<=floorY);                                         // between the air rows and the floor
  assert((p.pose&PoseOwnsY) && (p.pose&PoseIdle) && !(p.pose&PoseHover) && !(p.pose&PoseSniff));
  if(i) {
   // On foot: 1 px steps. Airborne at the 94 px/s speed cap of wide tanks the shared glide-turn easing (same code as the
   // other flyers, see the known Phoenix sideways-jump check) rounds to at most 2 px between 10 ms samples.
   assert(abs(p.x-v[i-1].x)<=(onFoot(p)&&onFoot(v[i-1]) ? 1 : 2));       // no sideways jumps
   assert(abs(p.y-v[i-1].y)<=(sway ? 4 : 3));                              // no vertical jumps
   if(p.x!=v[i-1].x && p.r==v[i-1].r)assert(p.r==(p.x>v[i-1].x));          // faces the way it moves
  }
  if(onFoot(p)) {
   assert(p.y==floorY);                                                    // on foot = on the floor row
   assert((p.pose&PoseLanded) && p.anim==0);                               // landed-style pose (sprite steps by distance instead)
   assert(steppedByPose(Griffin,p.pose));
   groundMs+=step;
   if(i>=50 && abs(p.x-v[i-50].x)>=2 && onFoot(v[i-50]))walkedMs+=step;   // moved 2+ px in the last half second
   if(!wasOnFoot) {                                                         // a flight just ended: it ends on the floor
    ++flights;
    if(flightMs>maxFlightMs)maxFlightMs=flightMs;
    if(flightMs<minFlightMs)minFlightMs=flightMs;
    if(flightHi-flightLo>widestFlight)widestFlight=flightHi-flightLo;
    flightMs=0;flightLo=999;flightHi=0;spellMs=0;
   }
   spellMs+=step;
   wasOnFoot=true;
  } else {
   assert(!(p.pose&PoseLanded) && p.anim==now);                            // airborne: live clock, wings flap, never frozen
   assert(!steppedByPose(Griffin,p.pose));
   if(wasOnFoot) {                                                          // take-off: it has been walking for a whole spell first
    assert(first ? i*step>=12000-step : spellMs>=12000-step);
    if(spellMs<minSpellMs)minSpellMs=spellMs;
    ++spells;first=false;
   }
   flightMs+=step;
   if(p.x<flightLo)flightLo=p.x;
   if(p.x>flightHi)flightHi=p.x;
   const unsigned f=(p.anim/280U)&1U;
   if(lastFrame!=2 && f!=lastFrame)++flips;
   lastFrame=f;
   wasOnFoot=false;
  }
 }
 assert(flights>=8);                                                       // lots of 400 s: at least 8 complete flights
 assert(minFlightMs>=4000 && maxFlightMs<=9000);                          // a flight (climb, cruise, descent) is about 4-8 s
 assert(groundMs*100>=v.size()*step*65);                                  // spends most of the time on the ground
 assert(walkedMs>=groundMs/4);                                            // and really walks there, not just stands
 assert(widestFlight>=span/8);                                            // the flight crosses part of the screen
 assert(flips>flights*10);                                                // wings keep flapping while airborne
 assert(spells>=flights);
 // longest airborne stall
 uint32_t cur=0,best=0;
 for(size_t i=1;i<v.size();++i) {
  if(!onFoot(v[i]) && v[i].x==v[i-1].x)cur+=step;else cur=0;
  if(cur>best)best=cur;
 }
 assert(best<=1200);
}
static uint64_t sig(const std::vector<S>& v) {uint64_t h=1469598103934665603ULL;for(const S& s:v){h^=(uint64_t)(s.x+1000);h*=1099511628211ULL;h^=(uint64_t)(s.y+1000);h*=1099511628211ULL;h^=s.r;h*=1099511628211ULL;h^=s.pose;h*=1099511628211ULL;}return h;}
struct Mock {
 std::vector<uint8_t> px=std::vector<uint8_t>(96*64,0);uint16_t col=0;
 void setColor(uint16_t c){col=c;}
 void fillRect(int x,int y,int w,int h){for(int j=y;j<y+h;++j)for(int i=x;i<x+w;++i)if(i>=0&&i<96&&j>=0&&j<64)px[j*96+i]=(uint8_t)col;}
};
static Mock draw(uint16_t id,int x,uint32_t now,bool stepped) {
 Mock m;LoRaFishLandSprite::draw(m,x,32,true,id,2,now,(uint16_t)1,(uint16_t)2,(uint16_t)3,(uint16_t)0,false,stepped);return m;
}
int main() {
 // ---- identity: the Griffin is the only walk-fly animal; its kind and IDs are unchanged ----------------------
 assert(Griffin==547 && movement(Griffin)==FlyMotion && idleGroup(Griffin)==IdleFlyer && !steppedByDistance(Griffin));
 for(uint16_t id=0;id<700;++id)assert(walkFly(id)==(id==Griffin));
 assert(Dragon==546 && Phoenix==548);
 assert(steppedByPose(Dog,PoseIdle) && !steppedByPose(Eagle,PoseIdle|PoseGround) && !steppedByPose(Griffin,PoseIdle|PoseOwnsY));
 assert(steppedByPose(Griffin,PoseIdle|PoseOwnsY|PoseLanded|PoseGround));
 // ---- e-ink: the Griffin keeps the legacy drift (not on the walker path), no new animation ------------------------
 assert(!sniffer(Griffin) && !idleMotionFor(Griffin,true) && idleMotionFor(Griffin,false));
 for(uint8_t stage=0;stage<4;++stage)for(uint32_t now=0;now<40000;now+=113) {
  const S p=at(Griffin,stage,now,2700,128,false);
  assert(p.pose==0 && p.anim==now+2700);                                  // legacy: no pose, no frozen clock
  uint32_t period=8000;if(stage==0)period=period*3/4;else if(stage>=3)period=period*5/4;
  const uint32_t t=(now+2700)%period,half=period/2;const bool right=t<half;
  assert(p.r==right && p.x==20+(int)(88U*(right?t:period-t)/half) && p.y==habitatY(Griffin,39,now+2700));
 }
 // ---- the walk-fly path itself -----------------------------------------------------------------------------
 for(int width:{96,128,160,240,320})for(uint8_t stage:{0,2,3})for(uint32_t offset:{0U,2700U}) {
  checkGriffin(stage,width,offset,37,false);
 }
 for(int width:{128,240,320})checkGriffin(2,width,0,42,true);              // tall native panels: slow sway, lower floor row
 // ---- first thing it does is stand/walk on the ground ----------------------------------------------------------
 for(int width:{96,128,240})for(uint32_t offset:{0U,2700U}) {
  for(uint32_t t=1000;t<1000+11900;t+=50)assert(onFoot(at(Griffin,2,t,offset,width)));
 }
 // ---- tanks too small to fly in: it simply walks -----------------------------------------------------------------
 for(int width:{80,86}) {
  uint32_t moved=0;const auto v=run(Griffin,2,width,0,10,200,37,false);
  for(size_t i=0;i<v.size();++i) {assert(onFoot(v[i]) && v[i].y==37 && v[i].x>=20 && v[i].x<=width-20);if(i&&v[i].x!=v[i-1].x)++moved;}
  assert(moved>100);
 }
 {S p=at(Griffin,2,5000,0,50);assert(p.x==20);}
 // ---- same clock-driven path at 1 FPS, determinism, visitor slot, long gaps and millis() rollover ------------------
 {
  const auto fine=run(Griffin,2,128,0,10,200,37,false),slow=run(Griffin,2,128,0,1000,200,37,false);
  for(size_t i=0;i<slow.size();++i) {const S& a=slow[i];const S& b=fine[i*100];assert(a.x==b.x && a.y==b.y && a.r==b.r && a.pose==b.pose);}
  assert(sig(run(Griffin,2,128,0,37,100,37,false))==sig(run(Griffin,2,128,0,37,100,37,false)));
  int diff=0;for(uint32_t t=0;t<120000;t+=100)if(at(Griffin,2,t).x!=at(Griffin,2,t,2700).x)++diff;
  assert(diff>600);
  for(uint32_t t:{0u,900000u,3u,UINT32_MAX-5000u,40u,UINT32_MAX}) {S p=at(Griffin,2,t);assert(p.x>=20 && p.x<=108);}
  for(uint32_t k=0;k<3000u;++k){uint32_t t=UINT32_MAX-30000u+k*37u;S p=at(Griffin,2,t,2700);assert(p.x>=20 && p.x<=108 && p.y>=29 && p.y<=37);}
  for(uint32_t t=5000;t<90000;t+=500) {S p=at(Griffin,2,t);assert(p.x>=20 && p.x<=108);}
  S after=at(Griffin,2,260000);assert(after.x>=20 && after.x<=108 && onFoot(after) && after.y==37); // long gap (screen off): rests on the floor
 }
 // ---- sprite frames: legs step by distance on foot, wings flap on the clock in the air; art untouched ---------------
 {
  // Same picture drawn dx columns further right? (the frame is chosen from x on foot, so compare after shifting)
  auto same=[](const Mock& a,const Mock& b,int dx) {
   for(int j=0;j<64;++j)for(int i=0;i<96;++i){const int k=i+dx;const uint8_t q=(k>=0&&k<96)?b.px[j*96+k]:a.px[j*96+i];if(a.px[j*96+i]!=q)return false;}
   return true;
  };
  assert(!same(draw(Griffin,40,0,true),draw(Griffin,45,0,true),5));      // on foot: the frame follows the distance walked (5 px per step)
  assert(same(draw(Griffin,40,0,true),draw(Griffin,50,0,true),10));      // ... two steps later it is the same frame again
  assert(same(draw(Griffin,40,0,true),draw(Griffin,40,5000,true),0));    // ... and the clock does not matter
  assert(!same(draw(Griffin,40,0,false),draw(Griffin,40,280,false),0));  // airborne: the frame follows the clock
  assert(same(draw(Griffin,40,0,false),draw(Griffin,45,0,false),5));     // ... and not the position
  assert(!same(draw(Dog,40,0,false),draw(Dog,45,0,false),5) && same(draw(Dog,40,0,false),draw(Dog,40,280,false),0)); // other walkers still step by distance
  assert(!same(draw(Dragon,40,0,false),draw(Dragon,40,280,false),0) && same(draw(Dragon,40,0,false),draw(Dragon,45,0,false),5)); // Dragon still flaps on the clock
  assert(sizeof(LoRaFishLandArt::masks)==landCount*2*192);               // still two frames per species, same table size
 }
 // ---- every other animal (and the Griffin's e-ink path): bit-for-bit the previous motion ---------------------------
 {
  for(uint16_t id=0;id<700;++id) {
   if(!known(id))continue;
   uint64_t h=1469598103934665603ULL;
   auto mix=[&](uint64_t v){h^=v;h*=1099511628211ULL;};
   for(int idle=0;idle<2;++idle) {
    if(idle && id==Griffin)continue;
    for(uint8_t stage:{0,2})for(int width:{96,128,240})for(uint32_t offset:{0U,2700U})for(int fl:{37,42}) {
     for(uint32_t t=500;t<90000;t+=97) {
      int x=71,y=39;bool r=false;uint8_t pose=0;
      habitatPosition(id,stage,width,t,offset,x,y,r,idle!=0,&pose,fl,fl==42 ? 30+(int)(t%11) : -1);
      mix((uint64_t)(x+1000));mix((uint64_t)(y+1000));mix(r);mix(pose);mix(animClock(pose,t+offset));
     }
    }
   }
   printf("%u:%016llx\n",(unsigned)id,(unsigned long long)h);
  }
 }
 puts("ok");
}
'''
# Golden motion hashes (x, y, facing, pose, animation clock) of every registered animal, taken from the release
# before the Griffin change. The Griffin appears with idle=false only (its natural idle motion is the change).
GOLDEN={0:'3e39e0dd7bc82757',1:'85b9a45facfe2283',2:'9b864331a887e2a3',3:'e13a0df4ac4da15f',4:'950b2c9ae41dd1c3',5:'73e6a9a228741191',6:'b9834d63977bf6e9',7:'e8d75a6cd89e3d93',8:'5c3b539e3530a693',9:'89012fb669ff402b',10:'9188b2c4973c60d9',11:'7dc259c478a3702b',12:'2b72d027e759e9e7',13:'8b6f1e2eb7049d5d',14:'e21f961c3b986527',256:'afcc0e0389b1b950',257:'05618650d41cfa2e',258:'b14757d8de0d0824',259:'c3629ff6270cbe80',260:'e9b937bb2374a253',261:'4ba5fdba1181b935',262:'edd4a48288972fc5',263:'6a9987997e15ac47',264:'ad37804c0667ba37',265:'a1a24c4e1a361f73',266:'eed3c8af52008229',267:'af92f1b2f1ec74fe',268:'b5e2343432ebd266',269:'8bf76dbe2b08590b',270:'d31c8959b39e94bb',271:'c41aa5de021abc74',272:'0d44fc98d19add9f',273:'6d9c296efc1cabb1',512:'02672bfa73020923',513:'8810de4924f49459',514:'954418aa0247f59f',515:'3eee8590ae434b63',516:'006474da216ca4a5',517:'23e0fb5ff35ed8ab',518:'4c2c3ed34760bd37',519:'bacda1f88ea687d9',520:'21759e486071268d',521:'6fcecc8a04f435a5',522:'cfbf6baa2953eb1b',523:'1e834d22166cdc1f',524:'9deb6fda2151640b',525:'1c2f78c23c9bae5f',526:'48ad3b96aa4e2a91',527:'dc0f0fdf4f14e451',528:'ecb7e6ae58a9c049',529:'f1e044b039981c2d',530:'4d9dd0419a6f3655',531:'ee58099a0c2124d9',532:'5c700916f1e6b1d5',533:'bbe92c7a6619ae81',534:'9327ba7bc3df02bb',535:'ee5df2f8db289877',536:'27472fb12195c7dd',537:'670a3f2bef8fab7d',538:'537b15bf897155f5',539:'2399059a7fbffcf9',540:'4f798df4107d838b',541:'6fbcf7692cdd6775',542:'c6df9eed5570f5c1',543:'784dacdcfbee9331',544:'d527a5bb4f58d7fb',545:'1a48c743e3b8fdff',546:'2252deddb7c38165',547:'6e440b2ec53ce1f7',548:'e7aeeb160779e012',549:'452a3cee69f61fc1',550:'feabaeff112aab31',551:'9d33afd29d362f15',552:'82bcd3a82c099133',553:'3ea51e55d2061123',554:'4dd6efb43971a7cf'}
with tempfile.TemporaryDirectory(prefix='dx-griffin-') as tmp:
    cpp=Path(tmp)/'griffin.cpp';cpp.write_text(source)
    for edition in ('DX','WATER','AIR','LAND','DXPRO'):
        exe=Path(tmp)/edition
        flags=[] if edition=='DX' else [f'-DLORAGOTCHI_{edition}_EDITION=1'] if edition!='DXPRO' else ['-DLORAGOTCHI_DXPRO=1']
        subprocess.run(['g++','-std=c++17','-O1','-Wall','-Wextra','-Werror','-fsanitize=undefined,address','-I',str(ROOT),*flags,str(cpp),'-o',str(exe)],check=True)
        out=subprocess.run([str(exe)],check=True,capture_output=True,text=True).stdout.split()
        assert out[-1]=='ok'
        got={int(k):v for k,v in (line.split(':') for line in out[:-1])}
        assert got==GOLDEN,[k for k in GOLDEN if got.get(k)!=GOLDEN[k]]
        print('PASS Griffin walk-then-fly, other animals unchanged',edition)
ui=(ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text()
# Call sites: e-ink still decides through idleMotionFor (the Griffin is not a sniffer), both sprite calls pass the pose.
assert ui.count('LoRaFishSpecies::steppedByPose(species,pose));')==2
assert 'right,LoRaFishSpecies::idleMotionFor(loRaFishSpecies,display.isEink()),&pose,idleFloorY' in ui
assert 'gright,LoRaFishSpecies::idleMotionFor(guestMotionSpecies,display.isEink()),&gpose,guestFloorY' in ui
sprite=(ROOT/'examples/companion_radio/ui-new/LoRaFishLandSprite.h').read_text()
assert 'stepped || LoRaFishSpecies::steppedByDistance(id)' in sprite and '(now/280U)&1U' in sprite
print('PASS call sites: e-ink gating unchanged, sprite gets the on-foot flag')
