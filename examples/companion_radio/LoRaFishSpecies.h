#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "LoRaGotchiVersion.h"

// Shared registry: Water 0..14, Air 256..273, Land 512..554; 15..255, 274..511 and 555+ reserved.
// IDs are permanent protocol identities, not menu positions.
namespace LoRaFishSpecies {
enum : uint16_t {
  TropicalFish=0, Blowfish=1, Shark=2, Dolphin=3, Whale=4, Seal=5, Shrimp=6,
  Squid=7, Lobster=8, Crab=9, Octopus=10, Jellyfish=11, ShellDweller=12, SeaStar=13, Anglerfish=14,
  Eagle=256, Bird=257, Owl=258, Duck=259, Swan=260, Penguin=261, Parrot=262,
  Flamingo=263, Peacock=264, Turkey=265, Rooster=266, Dove=267, Bat=268,
  Honeybee=269, Butterfly=270, Fly=271, Worm=272, Bug=273,
  // Land: ground mammals 512..539, amphibious/reptiles 540..544, mythic 545..550, later additions 551..554 (appended; no ID is renumbered).
  Dog=512, Cat=513, Horse=514, Cow=515, Elephant=516, Pig=517, Ram=518, Sheep=519, Goat=520,
  Giraffe=521, Kangaroo=522, Llama=523, Deer=524, Mouse=525, Hamster=526, Rabbit=527,
  Hedgehog=528, Koala=529, Panda=530, Sloth=531, Otter=532, Skunk=533, Badger=534, Hippo=535,
  Rhino=536, Camel=537, BactrianCamel=538, Bison=539,
  Frog=540, Crocodile=541, Lizard=542, Turtle=543, Snake=544,
  Unicorn=545, Dragon=546, Griffin=547, Phoenix=548, Sauropod=549, TRex=550,
  Wolf=551, Fox=552, Bear=553, Kitsune=554
};
static constexpr uint8_t count=15;
static constexpr uint8_t airCount=18;
static constexpr uint8_t landCount=43;
inline bool waterKnown(uint16_t id) { return id<count; }
inline bool airKnown(uint16_t id) { return id>=Eagle && id<=Bug; }
inline bool landKnown(uint16_t id) { return id>=Dog && id<=Kitsune; }
inline bool known(uint16_t id) { return waterKnown(id) || airKnown(id) || landKnown(id); }
// Known AND belongs to this build's habitat (Land build: Land IDs; Air build: Air IDs; otherwise Water IDs).
inline bool editionKnown(uint16_t id) {
  // DX-Pro owns every set, so any known ID belongs to it.
  return LORAGOTCHI_DXPRO ? known(id)
       : LORAGOTCHI_LAND_EDITION ? landKnown(id) : LORAGOTCHI_AIR_EDITION ? airKnown(id) : waterKnown(id);
}
// Set-then-species menu (DX-Pro). Sets are the three ID ranges; only the species ID is persisted, so the
// set is always derived from the ID and no save or wire field is added. Pure helpers, any build may call them.
static constexpr uint8_t setCount=3; // 0 Water, 1 Air, 2 Land
inline uint8_t setOf(uint16_t id) { return landKnown(id) ? 2 : airKnown(id) ? 1 : 0; }
inline uint8_t setSize(uint8_t set) { return set==2 ? landCount : set==1 ? airCount : count; }
inline uint16_t setBase(uint8_t set) { return set==2 ? (uint16_t)Dog : set==1 ? (uint16_t)Eagle : (uint16_t)TropicalFish; }
inline const char* setLabel(uint8_t set) { return set==2 ? "Land" : set==1 ? "Air" : "Water"; }
inline uint16_t setSelectionId(uint8_t set,uint8_t index) {
  return setBase(set)+(index<setSize(set) ? index : 0);
}
inline uint8_t setSelectionIndex(uint16_t id) { return known(id) ? (uint8_t)(id-setBase(setOf(id))) : 0; }
// Menu offsets are never persisted or sent. Legacy saves remain fish.
static constexpr uint8_t selectableCount=LORAGOTCHI_LAND_EDITION ? landCount : LORAGOTCHI_AIR_EDITION ? airCount : count;
static constexpr uint16_t freshSpecies=LORAGOTCHI_LAND_EDITION ? Dog : LORAGOTCHI_AIR_EDITION ? Eagle : TropicalFish;
inline uint16_t selectionId(uint8_t index) {
  return index<selectableCount ? (LORAGOTCHI_LAND_EDITION ? Dog+index : LORAGOTCHI_AIR_EDITION ? Eagle+index : index) : freshSpecies;
}
inline uint8_t selectionIndex(uint16_t id) {
  return LORAGOTCHI_LAND_EDITION ? (landKnown(id) ? id-Dog : 0)
       : LORAGOTCHI_AIR_EDITION ? (airKnown(id) ? id-Eagle : 0) : (waterKnown(id) ? id : 0);
}
enum Movement : uint8_t { Swim, FlyMotion, Flutter, Walk, Crawl };
inline Movement movement(uint16_t id) {
  if(landKnown(id)) {
    if(id==Frog || id==Crocodile || id==Lizard || id==Turtle || id==Snake)return Crawl;
    if(id==Dragon || id==Griffin || id==Phoenix)return FlyMotion;
    return Walk;
  }
  if(!airKnown(id))return Swim;
  if(id==Worm || id==Bug)return Crawl;
  if(id==Penguin || id==Flamingo || id==Peacock || id==Turkey || id==Rooster)return Walk;
  if(id==Honeybee || id==Butterfly || id==Fly)return Flutter;
  return FlyMotion;
}
inline int habitatY(uint16_t id,int swimY,uint32_t now) {
  switch(movement(id)) {
    case Walk: case Crawl:return 37;
    case Flutter:return 30+(int)((now/140U)%3U);
    case FlyMotion:return 29+(int)((now/280U)%2U);
    default:return swimY;
  }
}
// Pure presentation only; ShellDweller is the existing snail-like sprite.
inline bool waterMotion(uint16_t id) {
  return id==ShellDweller || id==Crab || id==Jellyfish;
}
inline void waterPosition(uint16_t id,uint8_t stage,int width,uint32_t now,
                          uint32_t offset,int& x,int& y,bool& right) {
  if(!waterMotion(id))return;
  uint32_t period=id==ShellDweller ? 32000U : id==Crab ? 12000U : 18000U;
  if(stage==0)period=period*3U/4U;
  else if(stage>=3)period=period*5U/4U;
  const uint32_t clock=now+offset; // explicit Arduino millis rollover
  const uint32_t t=clock%period, half=period/2U;
  right=t<half;
  const uint32_t leg=t%half;
  uint32_t progress=leg;
  if(id==Crab) {
    // Sideways bursts: 700ms scuttle, 800ms rest; facing holds at rest.
    const uint32_t beat=1500U, moving=700U;
    const uint32_t within=leg%beat;
    progress=(leg/beat)*beat+(within<moving ? within*beat/moving : beat);
    if(progress>half)progress=half;
  }
  const int span=width>40 ? width-40 : 1;
  x=20+(int)((uint32_t)span*(right ? progress : half-progress)/half);
  y=37; // grounded centre; no inherited fish bob
  if(id==Jellyfish) {
    // Quick upward bell stroke followed by a slow settling drift.
    const uint32_t pulse=clock%2400U;
    y=pulse<600U ? 36-(int)(6U*pulse/600U)
                 : 30+(int)(6U*(pulse-600U)/1800U);
  }
}
// ---- Natural idle motion (all animals) -----------------------------------------------------------
// Replaces the fixed-speed triangle wave with a short cycle of phases per animal group. Presentation
// only: nothing here is saved, sent or compared across devices. No heap, no per-frame allocation, no
// per-frame randomness: a random number is drawn only when a phase STARTS, and positions inside a
// phase are a closed-form function of millis(), so the result is identical however often it is drawn
// (30 fps, 10 fps or the Efficient 1 FPS mode all see the same path; they only sample it).
// Two slots exist: 0 = the home animal (offset 0), 1 = a visitor (offset != 0), each with its own seed.
//
//   Ground (Walk and Crawl kinds, all sets): stand, walk, turn at the edge, look around.
//   Flyers (FlyMotion and Flutter kinds):    cruise, glide-turn (swoop), optional landing; wings keep
//                                            flapping the whole time they are airborne and stop ONLY
//                                            while landed on the floor.
//   Swimmers (fish, Swim kind):              drift, hover with a slow tail wobble, slow turn at the
//                                            edge. They never stop: gills need moving water.
// Crab, snail and jellyfish (waterMotion) keep their existing Water paths, unchanged.
enum IdleGroup : uint8_t { IdleNone, IdleGround, IdleFlyer, IdleSwimmer };
inline IdleGroup idleGroup(uint16_t id) {
  if(!known(id) || waterMotion(id))return IdleNone;
  switch(movement(id)) {
    case Walk: case Crawl:return IdleGround;
    case FlyMotion: case Flutter:return IdleFlyer;
    default:return IdleSwimmer;
  }
}
inline bool naturalIdle(uint16_t id) { return idleGroup(id)!=IdleNone; }
// ---- Sniff (Land walkers only) -------------------------------------------------------------------
// During a walk some Land animals slow down and put the nose to the ground for a moment, then walk on.
// The "head down" picture costs NO extra art bytes: the sprite code shears the head columns of the
// normal walking frame downwards (LoRaFishLandSprite). This table says, per Land animal, from which
// mask column (0..31) the head/neck starts and how many mask rows (of 24) the nose drops by at the
// right-hand edge; {0,0} = never sniffs (Koala and Sloth hang from a branch; crawlers, Dragon, Griffin
// and Phoenix have their own movement). Presentation only: nothing here is saved or sent.
struct SniffHead { uint8_t hx, drop; };
static constexpr SniffHead sniffTable[landCount]={
  {19,5},{19,4},{18,8},{20,6},{22,3},{20,6},{21,5},{21,5},{19,5},{14,10},   // Dog Cat Horse Cow Elephant Pig Ram Sheep Goat Giraffe
  {14,4},{15,8},{17,7},{17,4},{18,4},{18,5},{20,4},{0,0},{14,5},{0,0},     // Kangaroo Llama Deer Mouse Hamster Rabbit Hedgehog Koala Panda Sloth
  {21,4},{20,5},{21,4},{19,5},{19,5},{19,8},{19,8},{19,4},                // Otter Skunk Badger Hippo Rhino Camel Bactrian Bison
  {0,0},{0,0},{0,0},{0,0},{0,0},                                            // Frog Crocodile Lizard Turtle Snake
  {18,8},{0,0},{0,0},{0,0},{17,10},{17,5},                                  // Unicorn Dragon Griffin Phoenix Sauropod TRex
  {19,6},{19,5},{17,6},{20,5}                                               // Wolf Fox Bear Kitsune (walkers)
};
inline SniffHead sniffHead(uint16_t id) { return landKnown(id) ? sniffTable[id-Dog] : SniffHead{0,0}; }
inline bool sniffer(uint16_t id) { return sniffHead(id).drop!=0; }
// Whether the natural idle motion is used. E-ink keeps the legacy drift (never frozen) EXCEPT for Land
// walkers that sniff: the owner allows e-ink to get different frames (not more frames) for them.
inline bool idleMotionFor(uint16_t id,bool eink) { return !eink || sniffer(id); }
// Ground animals step their legs by distance walked, so a standing animal holds one still frame.
inline bool steppedByDistance(uint16_t id) { return idleGroup(id)==IdleGround; }
// Walk-then-fly (Land Griffin only): it stays a FlyMotion animal (legacy drift on e-ink, habitatY, layout flags)
// but its natural idle motion walks on the ground for a while, takes off, flies a few seconds and lands again.
// On the ground (PoseGround) its legs step by distance walked like any Land walker; in the air the two
// frames flap on the clock like the other flyers. Presentation only: nothing is saved or sent.
inline bool walkFly(uint16_t id) { return id==Griffin; }
// Pose bits reported to the call site (0 = legacy path was used; the call site keeps its old behaviour).
enum : uint8_t {
  PoseIdle=1,    // the natural idle motion produced this position
  PoseLanded=2,  // flyer standing on the floor: the ONLY case in which a flap animation may pause
  PoseHover=4,   // swimmer hovering: slow tail/fin wobble, still moving
  PoseOwnsY=8,   // y was set by the motion; the call site must not overwrite it
  PoseSniff=16,  // Land walker with its nose down (sniff phase); the sprite draws the head-down picture
  PoseGround=32  // walk-fly animal on the ground: legs step by distance walked (see steppedByPose)
};
inline bool steppedByPose(uint16_t id,uint8_t pose) {
  return steppedByDistance(id) || (walkFly(id) && (pose&PoseGround)!=0);
}
// Clock handed to the sprite animation. Airborne: the real clock (never stops). Landed: frozen frame.
// Hovering fish: half speed, a slow wobble that still moves.
inline uint32_t animClock(uint8_t pose,uint32_t now) {
  return (pose&PoseLanded) ? 0U : (pose&PoseHover) ? now/2U : now;
}
namespace naturalidle {
enum FlyPhase : uint8_t { FlyCruise, FlyTurn, FlyDescend, FlyPerch, FlyAscend, FlyGround };
enum SwimPhase : uint8_t { SwimDrift, SwimHover };
struct Slot {
  uint32_t rng, start, end, lookAt;
  uint32_t groundEnd, landAt; // walk-fly: end of the ground spell / when to start the landing
  int32_t x0q, dq, spd;     // phase start x, distance moved, speed; units of 1/16 px inside the roam span
  int16_t span; uint16_t id;
  int16_t rq;               // flyer glide-turn radius, 1/16 px
  int8_t dir;               // direction of travel, +1 right / -1 left
  int8_t dip;               // flyer: rows the animal swoops down in the middle of a turn
  uint8_t ph;               // flyer / swimmer phase (FlyPhase / SwimPhase)
  bool valid, walking, faceRight, look, edge;
  bool sniff, resumed;      // ground: in a sniff phase / this walk resumes after a sniff (no second sniff)
};
inline uint32_t roll(Slot& s,uint32_t lo,uint32_t hi) {
  s.rng^=s.rng<<13; s.rng^=s.rng>>17; s.rng^=s.rng<<5; // xorshift32
  return lo+s.rng%(hi-lo+1U);
}
// Fixed-point easing, u in 0..1024. smooth = smoothstep, bump = 0 -> 1 -> 0 parabola.
inline int32_t smooth(uint32_t u) { return (int32_t)(u*u*(3U*1024U-2U*u)/(1024U*1024U)); }
inline int32_t bump(uint32_t u) { return (int32_t)(4U*u*(1024U-u)/1024U); }
inline uint32_t fraction(const Slot& s,uint32_t now) { // 0..1024 through the current phase
  const uint32_t len=s.end-s.start;
  if(!len)return 1024U;
  const uint32_t e=now-s.start;
  return e>=len ? 1024U : e*1024U/len;
}
inline void seed(Slot& s,uint16_t id,int span,bool seedGuest) {
  s.rng=((uint32_t)id*2654435761U)^(seedGuest ? 0x9E3779B9U : 0x7F4A7C15U);
  if(!s.rng)s.rng=1U;
  s.id=id; s.span=(int16_t)span; s.valid=true; s.edge=false; s.look=false; s.walking=false;
  s.sniff=false; s.resumed=false;
  s.dq=0; s.rq=0; s.dip=0; s.ph=0; s.groundEnd=0; s.landAt=0;
}

// ======== Ground group: stand / walk / look around ====================================================
// sniffPct: chance (%) that a finished walk is followed by a sniff (only Land animals with a head-down
// picture, see sniffer()); sniffLo/Hi: sniff length in ms; sniff speed is 30% of the walking speed.
struct Gait { uint16_t standLo,standHi,edgeLo,edgeHi,walkLo,walkHi,period,sniffPct,sniffLo,sniffHi; };
// Walk is the pilot gait (Dog). Crawl is the same cycle, slower, with longer pauses.
inline Gait gaitFor(uint16_t id) {
  return movement(id)==Crawl ? Gait{1500U,4500U,2000U,3500U,1800U,4000U,16000U,0U,0U,0U}
                             : Gait{1000U,3000U,1400U,2600U,2000U,4500U,10000U,35U,1200U,2400U};
}
// Stand about 1-3 s. After an edge turn, or sometimes at random, look around: the animal faces the
// other way part-way through the pause and then walks the way it is looking.
inline void startStand(Slot& s,uint32_t at,const Gait& g) {
  const uint32_t d=s.edge ? roll(s,g.edgeLo,g.edgeHi) : roll(s,g.standLo,g.standHi);
  s.walking=false; s.sniff=false; s.resumed=false; s.start=at; s.end=at+d;
  s.look=s.edge || (d>=g.standLo+800U && roll(s,0U,99U)<40U);
  s.lookAt=at+d*45U/100U;
}
// Walk about 2-4.5 s, cut short at the screen edge (then the next pause is a forced turn-around).
// keepDir: resume after a sniff, same direction (no draw, no wall margin: the edge test below covers walls).
inline void startWalk(Slot& s,uint32_t at,int32_t spanq,int32_t speedq,const Gait& g,bool keepDir=false) {
  if(!keepDir) {
    s.dir=s.look ? (s.faceRight ? -1 : 1) : (roll(s,0U,1U) ? 1 : -1);
    const int32_t margin=spanq/4<160 ? spanq/4 : 160; // never start a walk into a wall within 10 px
    if(s.x0q<margin)s.dir=1;
    else if(s.x0q>spanq-margin)s.dir=-1;
  }
  s.faceRight=s.dir>0; s.sniff=false; s.resumed=keepDir;
  uint32_t w=roll(s,g.walkLo,g.walkHi);
  int32_t full=(int32_t)(((uint32_t)speedq*w)/1000U);
  const int32_t room=s.dir>0 ? spanq-s.x0q : s.x0q;
  s.edge=full>=room;
  if(s.edge) {full=room; w=((uint32_t)room*1000U+(uint32_t)speedq-1U)/(uint32_t)speedq;}
  s.walking=true; s.start=at; s.end=at+w; s.dq=full; s.spd=speedq;
}
// Sniff: still walking the same way, at 30% speed with the nose down, for about 1.2-2.4 s; cut short at a wall.
inline void startSniff(Slot& s,uint32_t at,int32_t room,int32_t speedq,const Gait& g) {
  const int32_t spd=speedq*30/100>0 ? speedq*30/100 : 1;
  uint32_t w=roll(s,g.sniffLo,g.sniffHi);
  int32_t full=(int32_t)(((uint32_t)spd*w)/1000U);
  s.edge=full>=room;
  if(s.edge) {full=room; w=((uint32_t)room*1000U+(uint32_t)spd-1U)/(uint32_t)spd;}
  s.walking=true; s.sniff=true; s.start=at; s.end=at+w; s.dq=full; s.spd=spd;
}
inline int32_t walkEnd(const Slot& s) { return s.x0q+s.dir*s.dq; }
inline void position(Slot& s,uint16_t id,uint8_t stage,int span,uint32_t now,bool seedGuest,int& x,bool& right) {
  const int32_t spanq=span*16;
  const Gait g=gaitFor(id);
  const uint32_t period=stage==0 ? g.period*3U/4U : stage>=3 ? g.period*5U/4U : g.period; // pace of the old drift
  int32_t speedq=(int32_t)((uint32_t)span*32000U/period);
  if(speedq<1)speedq=1;
  const bool fresh=!s.valid || s.id!=id || s.span!=span || (int32_t)(now-s.start)<0;
  if(fresh) {
    seed(s,id,span,seedGuest);
    s.x0q=(int32_t)roll(s,0U,(uint32_t)spanq); s.faceRight=roll(s,0U,1U)!=0;
    startStand(s,now,g);
  } else if((int32_t)(now-s.end)>8000) { // not drawn for a while (screen off / other page): rest where it was
    if(s.walking)s.x0q=walkEnd(s);
    s.edge=false; startStand(s,now,g);
  }
  for(uint8_t guard=0;guard<8 && (int32_t)(now-s.end)>=0;++guard) {
    const uint32_t at=s.end;
    if(s.walking) {
      s.x0q=walkEnd(s);
      const int32_t room=s.dir>0 ? spanq-s.x0q : s.x0q;
      if(s.sniff) {                     // sniff over: walk on the same way unless it ended at a wall
        if(s.edge)startStand(s,at,g); else startWalk(s,at,spanq,speedq,g,true);
      } else if(g.sniffPct && sniffer(id) && !s.edge && !s.resumed && roll(s,0U,99U)<g.sniffPct && room>=128) {
        startSniff(s,at,room,speedq,g); // draws only here, at the start of a phase
      } else startStand(s,at,g);
    }
    else startWalk(s,at,spanq,speedq,g);
  }
  int32_t xq=s.x0q;
  if(s.walking) {
    int32_t d=(int32_t)(((uint32_t)s.spd*(now-s.start))/1000U);
    if(d>s.dq)d=s.dq;
    xq+=s.dir*d;
    right=s.dir>0;
  } else {
    right=(s.look && (int32_t)(now-s.lookAt)>=0) ? !s.faceRight : s.faceRight;
  }
  if(xq<0)xq=0;
  if(xq>spanq)xq=spanq;
  x=20+(xq+8)/16;
}

// ======== Flyer group: cruise / glide-turn / landing ==================================================
// Wings are never touched here: the sprite keeps flapping from the real clock in every phase except
// FlyPerch (standing on the floor), which is reported as PoseLanded.
inline int32_t flyRoom(const Slot& s,int32_t spanq) { return s.dir>0 ? spanq-s.x0q : s.x0q; }
// Straight flight. It is cut short one turn-radius before the wall, so the glide-turn always fits.
inline void startCruise(Slot& s,uint32_t at,int32_t spanq,int32_t speedq,bool flutter) {
  const int32_t reserve=speedq*17/40; // largest glide-turn radius (1.7 s turn at cruise speed / 4)
  int32_t room=flyRoom(s,spanq)-reserve;
  if(room<0)room=0;
  uint32_t w=flutter ? roll(s,700U,1800U) : roll(s,1800U,4200U);
  int32_t full=(int32_t)(((uint32_t)speedq*w)/1000U);
  s.edge=full>=room;
  if(s.edge) {full=room; w=((uint32_t)room*1000U+(uint32_t)speedq-1U)/(uint32_t)speedq;}
  s.ph=FlyCruise; s.start=at; s.end=at+w; s.dq=full; s.spd=speedq;
  s.faceRight=s.dir>0;
}
// Glide-turn: the animal keeps its speed, banks out and swoops down a few rows, and comes back the
// other way. x = x0 + dir*R*bump(u), R = v*T/4 so the entry and exit speed equal the cruise speed.
inline void startTurn(Slot& s,uint32_t at,int32_t spanq,int32_t speedq,bool flutter,bool big) {
  const uint32_t t=flutter ? roll(s,600U,900U) : roll(s,1100U,1700U);
  s.ph=FlyTurn; s.start=at; s.end=at+t; s.dq=0; s.spd=speedq;
  int32_t r=(int32_t)(((uint32_t)speedq*t)/4000U);
  const int32_t room=flyRoom(s,spanq); // never bank out past the wall, even when a flight starts next to one
  if(r>room)r=room;
  s.rq=(int16_t)r;
  s.dip=(int8_t)(flutter ? 2 : big ? 5 : 3);
  s.faceRight=s.dir>0; // facing flips half-way, at the top of the bank
}
inline void startDescend(Slot& s,uint32_t at) {
  const uint32_t t=roll(s,900U,1300U);
  s.ph=FlyDescend; s.start=at; s.end=at+t; s.dq=(int32_t)roll(s,112U,176U); s.faceRight=s.dir>0;
}
inline void startPerch(Slot& s,uint32_t at) {
  const uint32_t t=roll(s,1500U,3500U);
  s.ph=FlyPerch; s.start=at; s.end=at+t; s.dq=0; s.look=roll(s,0U,99U)<50U; s.lookAt=at+t*45U/100U;
}
inline void startAscend(Slot& s,uint32_t at,int32_t spanq,int32_t speedq) {
  // Take off the way the animal is looking, unless the wall is too close for the climb-out.
  bool face=s.faceRight;
  if(s.look)face=!face;
  s.dir=face ? 1 : -1;
  if(flyRoom(s,spanq)<176+speedq*17/40+16)s.dir=(spanq-s.x0q>s.x0q) ? 1 : -1;
  s.faceRight=s.dir>0;
  const uint32_t t=roll(s,900U,1300U);
  s.ph=FlyAscend; s.start=at; s.end=at+t; s.dq=(int32_t)roll(s,112U,176U);
}
// Geometry at the end of the current phase (also used to resume after a long gap).
inline void flyFinish(Slot& s) {
  switch(s.ph) {
    case FlyCruise: case FlyDescend: case FlyAscend:s.x0q+=s.dir*s.dq;break;
    case FlyTurn:s.dir=(int8_t)-s.dir; s.faceRight=s.dir>0;break;
    default:break;
  }
}
inline void flyNext(Slot& s,uint32_t at,int32_t spanq,int32_t speedq,bool flutter,bool landOK) {
  const uint8_t was=s.ph;
  if(was==FlyDescend) {startPerch(s,at);return;}
  if(was==FlyPerch) {startAscend(s,at,spanq,speedq);return;}
  const int32_t reserve=speedq*17/40;
  if(was==FlyTurn || was==FlyAscend) {
    // Just turned away from a wall (or took off): plenty of room ahead, so sometimes settle for a rest.
    if(was==FlyTurn && landOK && roll(s,0U,99U)<30U && flyRoom(s,spanq)>=176+reserve) {startDescend(s,at);return;}
    startCruise(s,at,spanq,speedq,flutter);return;
  }
  // A cruise just ended.
  const int32_t room=flyRoom(s,spanq);
  if(s.edge || room<reserve+16) {startTurn(s,at,spanq,speedq,flutter,roll(s,0U,99U)<20U);return;}
  const uint32_t pick=roll(s,0U,99U);
  if(landOK && pick<30U && room>=176+reserve) {startDescend(s,at);return;}
  if(pick<55U) {startTurn(s,at,spanq,speedq,flutter,pick>=45U);return;} // mid-air swoop and reverse
  startCruise(s,at,spanq,speedq,flutter);
}
// Draw-time geometry of the current flyer phase (shared by every flyer; pure function of the slot and the clock).
inline void flyOutput(const Slot& s,uint32_t now,int32_t spanq,int& x,bool& right,int& y,int floorY,int airY,uint8_t& pose) {
    const uint32_t u=fraction(s,now);
  int32_t xq=s.x0q;
  const int airborneY=airY>=0 ? airY : y; // caller's row for this instant (tall panels pass their own slow sway)
  int outY=airborneY;
  pose=PoseIdle|PoseOwnsY;
  switch(s.ph) {
    case FlyCruise: {
      int32_t d=(int32_t)(((uint32_t)s.spd*(now-s.start))/1000U);
      if(d>s.dq)d=s.dq;
      xq+=s.dir*d; right=s.dir>0; break;
    }
    case FlyTurn:
      xq+=s.dir*(int32_t)(((int64_t)s.rq*bump(u))/1024);
      right=u<512U ? s.dir>0 : s.dir<0;
    {
      int dip=s.dip; // a swoop never dips below the floor, even when a tall panel's sway is already low
      if(airborneY+dip>floorY)dip=floorY>airborneY ? floorY-airborneY : 0;
      outY=airborneY+dip*bump(u)/1024; break;
    }
    case FlyDescend:
      xq+=s.dir*(int32_t)(((int64_t)s.dq*smooth(u))/1024);
      right=s.dir>0;
      outY=airborneY+(floorY-airborneY)*smooth(u)/1024; break;
    case FlyPerch:
      right=(s.look && (int32_t)(now-s.lookAt)>=0) ? !s.faceRight : s.faceRight;
      outY=floorY; pose|=PoseLanded; break;
    case FlyGround: { // walk-fly animal on foot: stand / walk exactly like a Land walker, legs step by distance
      if(s.walking) {
        int32_t d=(int32_t)(((uint32_t)s.spd*(now-s.start))/1000U);
        if(d>s.dq)d=s.dq;
        xq+=s.dir*d; right=s.dir>0;
      } else right=(s.look && (int32_t)(now-s.lookAt)>=0) ? !s.faceRight : s.faceRight;
      outY=floorY; pose|=PoseLanded|PoseGround; break;
    }
    default: // FlyAscend
      xq+=s.dir*(int32_t)(((int64_t)s.dq*smooth(u))/1024);
      right=s.dir>0;
      outY=floorY+(airborneY-floorY)*smooth(u)/1024; break;
  }
  if(xq<0)xq=0;
  if(xq>spanq)xq=spanq;
  x=20+(xq+8)/16; y=outY;
}

// y: in = airborne base row (wing bob from habitatY), out = row to draw. floorY = standing row.
inline void positionFlyer(Slot& s,uint16_t id,uint8_t stage,int span,uint32_t now,bool seedGuest,
                          int& x,bool& right,int& y,int floorY,int airY,uint8_t& pose) {
  const int32_t spanq=span*16;
  const bool flutter=movement(id)==Flutter;
  const uint32_t base=flutter ? 4200U : 8000U;
  const uint32_t period=stage==0 ? base*3U/4U : stage>=3 ? base*5U/4U : base;
  int32_t speedq=(int32_t)((uint32_t)span*32000U/period);
  if(speedq>1500)speedq=1500; // ~94 px/s: wide panels glide at the same speed instead of streaking
  if(speedq<16)speedq=16;
  const bool landOK=span>=48;
  const bool fresh=!s.valid || s.id!=id || s.span!=span || (int32_t)(now-s.start)<0;
  if(fresh) {
    seed(s,id,span,seedGuest);
    s.x0q=(int32_t)roll(s,0U,(uint32_t)spanq); s.dir=roll(s,0U,1U) ? 1 : -1;
    if(flyRoom(s,spanq)<spanq/2)s.dir=(int8_t)-s.dir; // first flight heads for the roomier side
    startCruise(s,now,spanq,speedq,flutter);
  } else if((int32_t)(now-s.end)>8000) { // not drawn for a while: carry on from where it was
    const bool grounded=s.ph==FlyDescend || s.ph==FlyPerch;
    flyFinish(s);
    if(s.x0q<0)s.x0q=0;
    if(s.x0q>spanq)s.x0q=spanq;
    if(grounded) startPerch(s,now); else startCruise(s,now,spanq,speedq,flutter);
  }
  for(uint8_t guard=0;guard<8 && (int32_t)(now-s.end)>=0;++guard) {
    const uint32_t at=s.end;
    flyFinish(s);
    flyNext(s,at,spanq,speedq,flutter,landOK);
  }
  flyOutput(s,now,spanq,x,right,y,floorY,airY,pose);
}

// ======== Walk-fly group (Land Griffin only): walk / take off / fly / land ==================================
// Same closed-form, millis()-driven scheme as the two groups above (one random draw when a phase starts,
// nothing accumulated per frame), so every frame rate samples the same path.
//   Ground spell, 12-20 s: the Land walker gait (stand 1-3 s, walk 2-4.5 s, turn at the edge, look around; no sniff).
//   Take-off at the end of a stand, only if the tank is at least 48 px of roam wide: climb 0.9-1.3 s.
//   Flight: cruise legs of 1.2-2.4 s with glide-turns at the walls, 3.5-6 s from take-off to the start of the
//           landing, so a whole flight (climb + cruise + descent) is about 4.5-7 s, a little longer if a wall turn
//           has to come first.
//   Landing: descent 0.9-1.3 s to the floor row, then the next ground spell.
// Reported as PoseGround|PoseLanded while on foot (legs step by distance, the sprite clock may rest) and as an
// ordinary airborne flyer in between (wings flap on the clock, never frozen).
inline void startGroundSpell(Slot& s,uint32_t at,const Gait& g) {
  s.ph=FlyGround; s.edge=false;
  startStand(s,at,g);
  s.groundEnd=at+roll(s,12000U,20000U);
}
// One cruise leg of the flight: like startCruise but short, and never past the time the landing is due.
inline void startGlideLeg(Slot& s,uint32_t at,int32_t spanq,int32_t speedq) {
  const int32_t reserve=speedq*17/40;
  int32_t room=flyRoom(s,spanq)-reserve;
  if(room<0)room=0;
  uint32_t w=roll(s,1200U,2400U);
  const int32_t left=(int32_t)(s.landAt-at);
  if(left<400)w=400U; else if(w>(uint32_t)left)w=(uint32_t)left;
  int32_t full=(int32_t)(((uint32_t)speedq*w)/1000U);
  s.edge=full>=room;
  if(s.edge) {full=room; w=((uint32_t)room*1000U+(uint32_t)speedq-1U)/(uint32_t)speedq;}
  s.ph=FlyCruise; s.start=at; s.end=at+w; s.dq=full; s.spd=speedq;
  s.faceRight=s.dir>0;
}
inline void walkFlyNext(Slot& s,uint32_t at,int32_t spanq,int32_t speedq,const Gait& g) {
  const uint8_t was=s.ph;
  if(was==FlyDescend) {startGroundSpell(s,at,g);return;}
  const int32_t reserve=speedq*17/40;
  const int32_t room=flyRoom(s,spanq);
  const bool landDue=(int32_t)(at-s.landAt)>=0;
  const bool landRoom=room>=176+reserve;
  if(was==FlyAscend) {startGlideLeg(s,at,spanq,speedq);return;}
  if(was==FlyTurn) {
    if(landDue && landRoom)startDescend(s,at); else startGlideLeg(s,at,spanq,speedq);
    return;
  }
  // A cruise leg just ended.
  if(landDue) {
    if(landRoom)startDescend(s,at); else startTurn(s,at,spanq,speedq,false,false); // turn away from the wall first
    return;
  }
  if(s.edge || room<reserve+16) {startTurn(s,at,spanq,speedq,false,false);return;}
  const uint32_t pick=roll(s,0U,99U);
  if(pick<30U)startTurn(s,at,spanq,speedq,false,pick>=24U); else startGlideLeg(s,at,spanq,speedq);
}
inline void positionWalkFly(Slot& s,uint16_t id,uint8_t stage,int span,uint32_t now,bool seedGuest,
                            int& x,bool& right,int& y,int floorY,int airY,uint8_t& pose) {
  const int32_t spanq=span*16;
  const Gait g=gaitFor(id);
  const uint32_t walkPeriod=stage==0 ? g.period*3U/4U : stage>=3 ? g.period*5U/4U : g.period;
  int32_t walkq=(int32_t)((uint32_t)span*32000U/walkPeriod);
  if(walkq<1)walkq=1;
  const uint32_t flyPeriod=stage==0 ? 6000U : stage>=3 ? 10000U : 8000U; // same pace as the other flyers
  int32_t flyq=(int32_t)((uint32_t)span*32000U/flyPeriod);
  if(flyq>1500)flyq=1500;
  if(flyq<16)flyq=16;
  const bool takeoffOK=span>=48;
  const bool fresh=!s.valid || s.id!=id || s.span!=span || (int32_t)(now-s.start)<0;
  if(fresh) {
    seed(s,id,span,seedGuest);
    s.x0q=(int32_t)roll(s,0U,(uint32_t)spanq); s.faceRight=roll(s,0U,1U)!=0; s.dir=s.faceRight ? 1 : -1;
    startGroundSpell(s,now,g);
  } else if((int32_t)(now-s.end)>8000) { // not drawn for a while: land where it was and rest
    if(s.ph==FlyGround) {if(s.walking)s.x0q=walkEnd(s);} else flyFinish(s);
    if(s.x0q<0)s.x0q=0;
    if(s.x0q>spanq)s.x0q=spanq;
    startGroundSpell(s,now,g);
  }
  for(uint8_t guard=0;guard<8 && (int32_t)(now-s.end)>=0;++guard) {
    const uint32_t at=s.end;
    if(s.ph==FlyGround) {
      if(s.walking) {s.x0q=walkEnd(s); startStand(s,at,g);}
      else if(takeoffOK && (int32_t)(at-s.groundEnd)>=0) {
        startAscend(s,at,spanq,flyq);
        s.landAt=at+roll(s,3500U,6000U);
      } else startWalk(s,at,spanq,walkq,g);
    } else {
      flyFinish(s);
      walkFlyNext(s,at,spanq,flyq,g);
    }
  }
  flyOutput(s,now,spanq,x,right,y,floorY,airY,pose);
}

// ======== Swimmer group: drift / hover / slow turn =====================================================
// A segment moves a distance D over a time T with a gentle ease: x = x0 + dir*D*(u + smooth(u))/2.
// Blending in a straight line keeps at least half the average speed at the ends, so a fish slows
// down at the edge and while turning, but never comes to a stop.
inline int32_t swimRoom(const Slot& s,int32_t spanq) { return s.dir>0 ? spanq-s.x0q : s.x0q; }
inline void startDrift(Slot& s,uint32_t at,int32_t spanq,int32_t speedq) {
  uint32_t t=roll(s,3000U,6000U);
  int32_t full=(int32_t)(((uint32_t)speedq*t)/1000U);
  const int32_t room=swimRoom(s,spanq);
  s.edge=full>=room;
  if(s.edge) {full=room; t=((uint32_t)room*1000U+(uint32_t)speedq-1U)/(uint32_t)speedq;}
  s.ph=SwimDrift; s.start=at; s.end=at+t; s.dq=full; s.faceRight=s.dir>0;
}
// Hover: a short, slow, tail-wobbling pause. With turn=true the animal swings round first (facing
// flips as the hover starts, at nearly its slowest) and eases away from the wall.
inline void startHover(Slot& s,uint32_t at,int32_t spanq,bool turn) {
  if(turn)s.dir=(int8_t)-s.dir;
  int32_t full=(int32_t)roll(s,112U,192U);
  const int32_t room=swimRoom(s,spanq);
  if(full>room)full=room;
  s.ph=SwimHover; s.start=at; s.end=at+roll(s,1500U,2800U); s.dq=full; s.faceRight=s.dir>0; s.edge=false;
}
inline void swimNext(Slot& s,uint32_t at,int32_t spanq,int32_t speedq) {
  const bool hovered=s.ph==SwimHover;
  const bool atWall=s.edge; // the drift that just ended ran into the edge
  // Too close to a wall to drift usefully: swing round and ease away.
  if(!hovered && (atWall || swimRoom(s,spanq)<160)) {startHover(s,at,spanq,true);return;}
  const uint32_t pick=roll(s,0U,99U);
  if(!hovered && pick<30U) {startHover(s,at,spanq,pick<10U);return;} // mid-tank pause, sometimes a turn
  if(swimRoom(s,spanq)<160) {startHover(s,at,spanq,true);return;}
  startDrift(s,at,spanq,speedq);
}
inline void positionSwimmer(Slot& s,uint16_t id,uint8_t stage,int span,uint32_t now,bool seedGuest,
                            int& x,bool& right,uint8_t& pose) {
  const int32_t spanq=span*16;
  // Gentle drift: half the pace of the old swim (legacy period 8000 -> 16000 at adult stage).
  const uint32_t period=stage==0 ? 12000U : stage>=3 ? 20000U : 16000U;
  int32_t speedq=(int32_t)((uint32_t)span*32000U/period);
  if(speedq<16)speedq=16;
  const bool fresh=!s.valid || s.id!=id || s.span!=span || (int32_t)(now-s.start)<0;
  if(fresh) {
    seed(s,id,span,seedGuest);
    s.x0q=(int32_t)roll(s,0U,(uint32_t)spanq); s.dir=roll(s,0U,1U) ? 1 : -1;
    startDrift(s,now,spanq,speedq);
  } else if((int32_t)(now-s.end)>8000) { // not drawn for a while: carry on from where it was
    s.x0q+=s.dir*s.dq;
    if(s.x0q<0)s.x0q=0;
    if(s.x0q>spanq)s.x0q=spanq;
    s.edge=false; startHover(s,now,spanq,false);
  }
  for(uint8_t guard=0;guard<8 && (int32_t)(now-s.end)>=0;++guard) {
    const uint32_t at=s.end;
    s.x0q+=s.dir*s.dq;
    swimNext(s,at,spanq,speedq);
  }
  const uint32_t u=fraction(s,now);
  int32_t xq=s.x0q+s.dir*(int32_t)(((int64_t)s.dq*((int32_t)u+smooth(u)))/2048);
  if(xq<0)xq=0;
  if(xq>spanq)xq=spanq;
  x=20+(xq+8)/16; right=s.dir>0;
  pose=PoseIdle; // y stays with the caller's own fish bob
  if(s.ph==SwimHover)pose|=PoseHover;
}
}
// Home/visitor hook; crab, snail, jellyfish and all legacy paths stay exact.
// idleMotion=false keeps the legacy drift (no freeze). Call sites pass idleMotionFor(id,isEink()): true on
// every non-e-ink display, and on e-ink only for the Land walkers that sniff (owner decision: different
// frames, not more frames). All other e-ink pets keep the legacy drift.
// The Efficient 1 FPS mode needs no special case: it only redraws less often, and every position
// above is a pure function of the clock, so the same motion is simply sampled once a second.
// pose (optional) reports PoseIdle/PoseLanded/PoseHover/PoseOwnsY; floorY is the row a flyer lands on;
// airY (>=0) replaces the flyer's cruising row (tall native panels sway it slowly; -1 = habitatY wing bob).
inline void habitatPosition(uint16_t id,uint8_t stage,int width,uint32_t now,
                            uint32_t offset,int& x,int& y,bool& right,bool idleMotion=true,
                            uint8_t* pose=nullptr,int floorY=37,int airY=-1) {
  uint8_t p=0;
  if(pose)*pose=0;
  if(waterMotion(id)) {waterPosition(id,stage,width,now,offset,x,y,right);return;}
  const IdleGroup group=idleMotion ? idleGroup(id) : IdleNone;
  if(group!=IdleNone) {
    static naturalidle::Slot slots[2]; // home, visitor: static storage only
    naturalidle::Slot& slot=slots[offset!=0 ? 1 : 0];
    const int span=width>40 ? width-40 : 1;
    if(span>=16) {
      const bool guest=offset!=0;
      if(group==IdleGround) {
        naturalidle::position(slot,id,stage,span,now+offset,guest,x,right);
        y=habitatY(id,y,now+offset); p=PoseIdle;
        if(slot.sniff && slot.walking)p|=PoseSniff; // nose down: Land walkers only (sniffer())
      } else if(group==IdleFlyer) {
        y=habitatY(id,y,now+offset);
        if(walkFly(id))naturalidle::positionWalkFly(slot,id,stage,span,now+offset,guest,x,right,y,floorY,airY,p);
        else naturalidle::positionFlyer(slot,id,stage,span,now+offset,guest,x,right,y,floorY,airY,p);
      } else {
        naturalidle::positionSwimmer(slot,id,stage,span,now+offset,guest,x,right,p);
      }
    } else {
      x=20; // tank too narrow to roam
      if(group!=IdleSwimmer)y=habitatY(id,y,now+offset);
    }
    if(pose)*pose=p;
    return;
  }
  if(!airKnown(id) && !landKnown(id))return;
  const Movement kind=movement(id);
  uint32_t period=kind==Crawl ? 16000U : kind==Walk ? 10000U : kind==Flutter ? 4200U : 8000U;
  if(stage==0)period=period*3U/4U;
  else if(stage>=3)period=period*5U/4U;
  const uint32_t t=(now+offset)%period, half=period/2U;
  right=t<half;
  const int span=width>40 ? width-40 : 1;
  x=20+(int)((uint32_t)span*(right?t:period-t)/half);
  y=habitatY(id,y,now+offset);
}
// Water tank bands (Water build only; habitatPosition above and the Air/Land builds are untouched).
// The tank is split by a fixed row: swimmers that live at the top of the water (air-breathers and
// drifters) sit in the SURFACE band, everything else in the UNDERWATER band. The band is a data
// field of the species (table below), never derived from a name or from the movement kind.
// Rows are sprite-centre rows in the 64 px reference frame that LoRaFishLayout::habitatY() consumes.
enum Band : uint8_t { Surface, Underwater };
struct BandEntry { uint16_t id; Band band; };
static constexpr BandEntry bandTable[]={
  {TropicalFish,Underwater},{Blowfish,Underwater},{Shark,Underwater},{Dolphin,Surface},{Whale,Surface},
  {Seal,Surface},{Shrimp,Underwater},{Squid,Underwater},{Lobster,Underwater},{Crab,Underwater},
  {Octopus,Underwater},{Jellyfish,Surface},{ShellDweller,Underwater},{SeaStar,Underwater},{Anglerfish,Underwater},
  // Air-set swimmers: not drawn by a Water build today, listed so a future visit rule can place them.
  {Duck,Surface},{Swan,Surface},{Penguin,Underwater}
};
// Unlisted and future IDs use the fish row (Underwater), exactly where the DX fish has always swum.
inline Band band(uint16_t id) {
  for(size_t i=0;i<sizeof(bandTable)/sizeof(bandTable[0]);++i)
    if(bandTable[i].id==id)return bandTable[i].band;
  return Underwater;
}
enum BandLayout : uint8_t { BandCompact, BandTall, BandWander };
struct BandRows { int8_t top, bottom; };
// BandCompact: 64 px panels and the Cardputer/T-Deck 2D canvas (fish natural rows 36..40).
// BandTall: native panels taller than 64 px (habitatY input domain 18..42).
// BandWander: T-Watch S3 tall tank (wander rows 29..49).
inline BandRows bandRows(Band b,BandLayout l) {
  static constexpr BandRows rows[3][2]={{{28,32},{36,40}},{{18,29},{30,42}},{{29,38},{39,49}}};
  return rows[l][b];
}
// First row that belongs to the underwater band; rows above it are surface or open water.
inline int bandBoundary(BandLayout l) { return l==BandCompact ? 34 : l==BandTall ? 30 : 39; }
// Map the species' own natural row range [natTop,natBottom] linearly onto its band, so the
// sprite, speed and bob shape are unchanged and only the vertical envelope moves. When the
// natural range already equals the band (an underwater fish on a 64 px panel) this is the identity.
inline int bandFit(uint16_t id,BandLayout l,int y,int natTop,int natBottom) {
  const BandRows r=bandRows(band(id),l);
  if(y<natTop)y=natTop;
  if(y>natBottom)y=natBottom;
  if(natBottom<=natTop)return y<r.top ? r.top : y>r.bottom ? r.bottom : y;
  return r.top+(y-natTop)*(r.bottom-r.top)/(natBottom-natTop);
}
// The bands only exist where the tank can hold two adult sprites one above the other with a gap
// between them. Smaller tanks keep the single shared tank (a local display decision: it changes no
// wire field, visit rule, breeding rule or save). tankTopRow is the first row below the header rule,
// tankBottomRow the floor rule row; maxAdultSpriteRows is the tallest adult sprite drawn.
static constexpr int bandGapRows=4;
inline bool waterBandsEnabled(int tankTopRow,int tankBottomRow,int maxAdultSpriteRows) {
  return maxAdultSpriteRows>0 && tankBottomRow>tankTopRow &&
         tankBottomRow-tankTopRow>=2*maxAdultSpriteRows+bandGapRows;
}
inline uint16_t renderId(uint16_t id) { return known(id) ? id : (uint16_t)TropicalFish; }
// Species-aware display names; protocol stage values and evolution timing remain unchanged.
inline const char* lifeStage(uint16_t id, uint8_t stage) {
  if (stage >= 3) return "ELDER";
  if (stage == 2) return "ADULT";
  if (stage == 1) {
    if (id == Butterfly) return "CHRYSALIS";
    if (id == Honeybee || id == Fly) return "PUPA";
    if (id == Frog) return "FROGLET";
    return "JUVENILE";
  }
  if (landKnown(id)) {
    switch (id) {
      case Dog: case Otter: case Mouse: case Hamster: case Wolf: return "PUP";
      case Cat: case Rabbit: case Skunk: case Fox: case Kitsune: return "KIT";
      case Horse: case Unicorn: return "FOAL";
      case Pig: return "PIGLET";
      case Ram: case Sheep: return "LAMB";
      case Goat: return "KID";
      case Kangaroo: case Koala: return "JOEY";
      case Llama: return "CRIA";
      case Deer: return "FAWN";
      case Hedgehog: return "HOGLET";
      case Panda: case Sloth: case Badger: case Bear: return "CUB";
      case Frog: return "TADPOLE";
      case Crocodile: case Lizard: case Turtle: case Snake:
      case Dragon: case Griffin: case Phoenix: case Sauropod: case TRex: return "HATCHLING";
      default: return "CALF"; // Cow, Elephant, Giraffe, Hippo, Rhino, camels, Bison
    }
  }
  if (!airKnown(id)) return "FRY";
  switch (id) {
    case Duck: return "DUCKLING";
    case Eagle: return "EAGLET";
    case Swan: return "CYGNET";
    case Owl: return "OWLET";
    case Penguin: case Bird: case Parrot: case Flamingo:
    case Peacock: case Turkey: case Rooster: case Dove: return "CHICK";
    case Butterfly: return "CATERPILLAR";
    case Honeybee: case Fly: case Bug: return "LARVA";
    case Bat: return "PUP";
    case Worm: return "HATCHLING";
    default: return "HATCHLING";
  }
}
inline const char* label(uint16_t id) {
  static const char* const names[]={"Tropical fish","Blowfish","Shark","Dolphin","Whale",
    "Seal","Shrimp","Squid","Lobster","Crab","Octopus","Jellyfish","Shell-dweller","Sea star","Anglerfish"};
  static const char* const airNames[]={"Eagle","Bird","Owl","Duck","Swan","Penguin",
    "Parrot","Flamingo","Peacock","Turkey","Rooster","Dove","Bat",
    "Honeybee","Butterfly","Fly","Worm","Bug"};
  static const char* const landNames[]={"Dog","Cat","Horse","Cow","Elephant","Pig","Ram","Sheep",
    "Goat","Giraffe","Kangaroo","Llama","Deer","Mouse","Hamster","Rabbit","Hedgehog","Koala",
    "Panda","Sloth","Otter","Skunk","Badger","Hippo","Rhino","Camel","Bactrian camel","Bison",
    "Frog","Crocodile","Lizard","Turtle","Snake","Unicorn","Dragon","Griffin","Phoenix",
    "Sauropod","T-Rex","Wolf","Fox","Bear","Kitsune"};
  return waterKnown(id) ? names[id] : airKnown(id) ? airNames[id-Eagle] :
         landKnown(id) ? landNames[id-Dog] : "Unknown (fish)";
}
// Capability ACK is exact and transaction-bound by the caller. Legacy ACKs
// select the original nine-field COMMIT (some older RX parsers require n==9).
inline bool acknowledged(const char* text) {
  if (!text || strncmp(text,"LFG1|ACK|",9)) return false;
  const char* p=text+9;
  for(unsigned field=0;field<2;++field) {
    if(*p<'0' || *p>'9')return false;
    uint32_t value=0;
    do {unsigned digit=(unsigned)(*p++-'0');
      if(value>(UINT32_MAX-digit)/10U)return false;
      value=value*10+digit;
    } while(*p>='0' && *p<='9');
    if(*p++!='|')return false;
  }
  return !strcmp(p,"S1") || !strcmp(p,"S1|A1") || !strcmp(p,"S1|L1");
}
// A1 is explicit Air capability; S1 alone is not permission for Air IDs.
inline bool airAcknowledged(const char* text) {
  if(!acknowledged(text))return false;
  const size_t n=strlen(text);return n>=6 && !strcmp(text+n-6,"|S1|A1");
}
// L1 is explicit Land capability, advertised only by Land builds.
inline bool landAcknowledged(const char* text) {
  if(!acknowledged(text))return false;
  const size_t n=strlen(text);return n>=6 && !strcmp(text+n-6,"|S1|L1");
}
inline uint16_t wireSpecies(uint16_t id,const char* ack) {
  if(landKnown(id))return landAcknowledged(ack) ? id : (uint16_t)TropicalFish;
  if(!airKnown(id))return id; // retain existing opaque uint16 S1 forwarding
  return airKnown(id) && airAcknowledged(ack) ? id : (uint16_t)TropicalFish;
}
// True when this species cannot be sent to the peer that produced 'ack' and
// would be shown there as the legacy fish.
inline bool wireFallback(uint16_t id,const char* ack) {
  return (airKnown(id) && !airAcknowledged(ack)) || (landKnown(id) && !landAcknowledged(ack));
}
// Missing means legacy tropical fish. Invalid/duplicate fields reject the COMMIT
// without changing its reservation. Unknown IDs are retained, not reinterpreted.
inline bool extension(const char* text, uint16_t& id, bool& present) {
  id=TropicalFish; present=false;
  if (!text) return false;
  const char* p=text;
  while ((p=strstr(p,"|S1"))) {
    if (p[3] && p[3]!='|') {p+=3;continue;} // unrelated future field, e.g. S10
    if (p[3]!='|') return false; // truncated recognized extension
    if (present) return false;
    present=true; p+=4;
    if (*p<'0' || *p>'9') return false;
    uint32_t value=0;
    do {
      const unsigned digit=(unsigned)(*p++-'0');
      if (value>(65535U-digit)/10U) return false;
      value=value*10+digit;
    } while (*p>='0' && *p<='9');
    if (*p && *p!='|') return false;
    id=(uint16_t)value;
  }
  return true;
}
inline uint16_t checksum(const uint8_t* p,size_t n) {
  uint16_t crc=0xFFFF;
  while(n--) { crc^=(uint16_t)*p++ << 8;
    for(unsigned i=0;i<8;++i) crc=(uint16_t)((crc<<1)^((crc&0x8000)?0x1021:0));
  }
  return crc;
}
// SPC1 tail: IDs + one mystery seed + setup flag + reserved + CRC16.
static constexpr size_t savedSize=18;
inline uint32_t mix(uint32_t x) { x^=x>>16; x*=0x7feb352dUL; x^=x>>15; x*=0x846ca68bUL; return x^(x>>16); }
inline uint16_t mystery(uint32_t seed) { return (uint16_t)(selectionId((uint8_t)(mix(seed)%selectableCount))); }
// Mystery egg inside a chosen set: the same formula a single-set build uses, so one seed gives one animal.
inline uint16_t setMystery(uint32_t seed,uint8_t set) { return setSelectionId(set,(uint8_t)(mix(seed)%setSize(set))); }
// DX-Pro step-one Mystery egg: one seed picks any animal from every environment (Water, Air, Land in order).
inline uint16_t anyMystery(uint32_t seed) {
  uint16_t i=(uint16_t)(mix(seed)%(uint16_t)(count+airCount+landCount));
  for(uint8_t set=0;set<setCount;++set) { if(i<setSize(set)) return setSelectionId(set,(uint8_t)i); i-=setSize(set); }
  return TropicalFish;
}
inline uint8_t mysteryColour(uint32_t seed,unsigned role) { return (uint8_t)(8+mix(seed+0x9e3779b9UL*(role+1))%240); }
inline void encode(uint8_t* p,uint16_t local,uint16_t egg,uint32_t seed,bool setup) {
  memcpy(p,"SPC1",4); p[4]=local; p[5]=local>>8; p[6]=egg; p[7]=egg>>8;
  for(unsigned i=0;i<4;++i)p[8+i]=(uint8_t)(seed>>(i*8));
  p[12]=setup?1:0; p[13]=0; p[14]=1; p[15]=0; // tail version 1
  const uint16_t crc=checksum(p,16); p[16]=crc; p[17]=crc>>8;
}
inline bool decode(const uint8_t* p,size_t n,uint16_t& local,uint16_t& egg,uint32_t& seed,bool& setup) {
  if(n!=savedSize || memcmp(p,"SPC1",4) || p[12]>1 || p[13] || p[14]!=1 || p[15] ||
      checksum(p,16)!=(uint16_t)(p[16]|p[17]<<8)) return false;
  local=(uint16_t)(p[4]|p[5]<<8); egg=(uint16_t)(p[6]|p[7]<<8);
  seed=0;for(unsigned i=0;i<4;++i)seed|=(uint32_t)p[8+i]<<(i*8);
  setup=p[12]!=0; return true;
}
}
