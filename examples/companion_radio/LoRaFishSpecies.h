#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "LoRaGotchiVersion.h"

// Shared registry: Water 0..14, Air 256..273, Land 512..550; 15..255, 274..511 and 551+ reserved.
// IDs are permanent protocol identities, not menu positions.
namespace LoRaFishSpecies {
enum : uint16_t {
  TropicalFish=0, Blowfish=1, Shark=2, Dolphin=3, Whale=4, Seal=5, Shrimp=6,
  Squid=7, Lobster=8, Crab=9, Octopus=10, Jellyfish=11, ShellDweller=12, SeaStar=13, Anglerfish=14,
  Eagle=256, Bird=257, Owl=258, Duck=259, Swan=260, Penguin=261, Parrot=262,
  Flamingo=263, Peacock=264, Turkey=265, Rooster=266, Dove=267, Bat=268,
  Honeybee=269, Butterfly=270, Fly=271, Worm=272, Bug=273,
  // Land: ground mammals 512..539, amphibious/reptiles 540..544, mythic 545..550.
  Dog=512, Cat=513, Horse=514, Cow=515, Elephant=516, Pig=517, Ram=518, Sheep=519, Goat=520,
  Giraffe=521, Kangaroo=522, Llama=523, Deer=524, Mouse=525, Hamster=526, Rabbit=527,
  Hedgehog=528, Koala=529, Panda=530, Sloth=531, Otter=532, Skunk=533, Badger=534, Hippo=535,
  Rhino=536, Camel=537, BactrianCamel=538, Bison=539,
  Frog=540, Crocodile=541, Lizard=542, Turtle=543, Snake=544,
  Unicorn=545, Dragon=546, DragonFace=547, Phoenix=548, Sauropod=549, TRex=550
};
static constexpr uint8_t count=15;
static constexpr uint8_t airCount=18;
static constexpr uint8_t landCount=39;
inline bool waterKnown(uint16_t id) { return id<count; }
inline bool airKnown(uint16_t id) { return id>=Eagle && id<=Bug; }
inline bool landKnown(uint16_t id) { return id>=Dog && id<=TRex; }
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
    if(id==Dragon || id==DragonFace || id==Phoenix)return FlyMotion;
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
// ---- Natural idle motion (pilot: Dog, the canine of the Land set) --------------------------------
// Replaces the fixed-speed triangle wave with a stand / walk / look-around cycle. Presentation only:
// nothing here is saved, sent or compared across devices. No heap, no per-frame allocation, no
// per-frame randomness: a random number is drawn only when a phase STARTS, and positions inside a
// phase are a closed-form function of millis(), so the result is identical however often it is drawn.
// Two slots exist: 0 = the home animal (offset 0), 1 = a visitor (offset != 0), each with its own seed.
inline bool naturalIdle(uint16_t id) { return id==Dog; }
namespace naturalidle {
struct Slot {
  uint32_t rng, start, end, lookAt;
  int32_t x0q, dq, spd;     // phase start x, walk distance, walk speed; units of 1/16 px inside the roam span
  int16_t span; uint16_t id;
  int8_t dir;               // walk direction, +1 right / -1 left
  bool valid, walking, faceRight, look, edge;
};
inline uint32_t roll(Slot& s,uint32_t lo,uint32_t hi) {
  s.rng^=s.rng<<13; s.rng^=s.rng>>17; s.rng^=s.rng<<5; // xorshift32
  return lo+s.rng%(hi-lo+1U);
}
// Stand about 1-3 s. After an edge turn, or sometimes at random, look around: the animal faces the
// other way part-way through the pause and then walks the way it is looking.
inline void startStand(Slot& s,uint32_t at) {
  const uint32_t d=s.edge ? roll(s,1400U,2600U) : roll(s,1000U,3000U);
  s.walking=false; s.start=at; s.end=at+d;
  s.look=s.edge || (d>=1800U && roll(s,0U,99U)<40U);
  s.lookAt=at+d*45U/100U;
}
// Walk about 2-4.5 s, cut short at the screen edge (then the next pause is a forced turn-around).
inline void startWalk(Slot& s,uint32_t at,int32_t spanq,int32_t speedq) {
  s.dir=s.look ? (s.faceRight ? -1 : 1) : (roll(s,0U,1U) ? 1 : -1);
  const int32_t margin=spanq/4<160 ? spanq/4 : 160; // never start a walk into a wall within 10 px
  if(s.x0q<margin)s.dir=1;
  else if(s.x0q>spanq-margin)s.dir=-1;
  s.faceRight=s.dir>0;
  uint32_t w=roll(s,2000U,4500U);
  int32_t full=(int32_t)(((uint32_t)speedq*w)/1000U);
  const int32_t room=s.dir>0 ? spanq-s.x0q : s.x0q;
  s.edge=full>=room;
  if(s.edge) {full=room; w=((uint32_t)room*1000U+(uint32_t)speedq-1U)/(uint32_t)speedq;}
  s.walking=true; s.start=at; s.end=at+w; s.dq=full; s.spd=speedq;
}
inline int32_t walkEnd(const Slot& s) { return s.x0q+s.dir*s.dq; }
inline void position(Slot& s,uint16_t id,uint8_t stage,int span,uint32_t now,bool seedGuest,int& x,bool& right) {
  const int32_t spanq=span*16;
  const uint32_t period=stage==0 ? 7500U : stage>=3 ? 12500U : 10000U; // same pace as the old drift
  int32_t speedq=(int32_t)((uint32_t)span*32000U/period);
  if(speedq<1)speedq=1;
  const bool fresh=!s.valid || s.id!=id || s.span!=span || (int32_t)(now-s.start)<0;
  if(fresh) {
    s.rng=((uint32_t)id*2654435761U)^(seedGuest ? 0x9E3779B9U : 0x7F4A7C15U);
    if(!s.rng)s.rng=1U;
    s.id=id; s.span=(int16_t)span; s.valid=true; s.edge=false;
    s.x0q=(int32_t)roll(s,0U,(uint32_t)spanq); s.faceRight=roll(s,0U,1U)!=0;
    startStand(s,now);
  } else if((int32_t)(now-s.end)>8000) { // not drawn for a while (screen off / other page): rest where it was
    if(s.walking)s.x0q=walkEnd(s);
    s.edge=false; startStand(s,now);
  }
  for(uint8_t guard=0;guard<8 && (int32_t)(now-s.end)>=0;++guard) {
    const uint32_t at=s.end;
    if(s.walking) {s.x0q=walkEnd(s); startStand(s,at);}
    else startWalk(s,at,spanq,speedq);
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
}
// Home/visitor hook; other Water and all existing Air paths stay exact.
// idleMotion=false (e-ink call sites) keeps the legacy drift: e-ink gets no new animation.
inline void habitatPosition(uint16_t id,uint8_t stage,int width,uint32_t now,
                            uint32_t offset,int& x,int& y,bool& right,bool idleMotion=true) {
  if(waterMotion(id)) {waterPosition(id,stage,width,now,offset,x,y,right);return;}
  if(!airKnown(id) && !landKnown(id))return;
  const Movement kind=movement(id);
  if(idleMotion && naturalIdle(id)) {
    static naturalidle::Slot slots[2]; // home, visitor: static storage only
    const int span=width>40 ? width-40 : 1;
    if(span>=16) naturalidle::position(slots[offset!=0 ? 1 : 0],id,stage,span,now+offset,offset!=0,x,right);
    else x=20; // tank too narrow to roam
    y=habitatY(id,y,now+offset);
    return;
  }
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
      case Dog: case Otter: case Mouse: case Hamster: return "PUP";
      case Cat: case Rabbit: case Skunk: return "KIT";
      case Horse: case Unicorn: return "FOAL";
      case Pig: return "PIGLET";
      case Ram: case Sheep: return "LAMB";
      case Goat: return "KID";
      case Kangaroo: case Koala: return "JOEY";
      case Llama: return "CRIA";
      case Deer: return "FAWN";
      case Hedgehog: return "HOGLET";
      case Panda: case Sloth: case Badger: return "CUB";
      case Frog: return "TADPOLE";
      case Crocodile: case Lizard: case Turtle: case Snake:
      case Dragon: case DragonFace: case Phoenix: case Sauropod: case TRex: return "HATCHLING";
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
    "Frog","Crocodile","Lizard","Turtle","Snake","Unicorn","Dragon","Dragon face","Phoenix",
    "Sauropod","T-Rex"};
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
