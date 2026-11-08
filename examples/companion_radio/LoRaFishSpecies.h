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
  return LORAGOTCHI_LAND_EDITION ? landKnown(id) : LORAGOTCHI_AIR_EDITION ? airKnown(id) : waterKnown(id);
}
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
// Home/visitor hook; other Water and all existing Air paths stay exact.
inline void habitatPosition(uint16_t id,uint8_t stage,int width,uint32_t now,
                            uint32_t offset,int& x,int& y,bool& right) {
  if(waterMotion(id)) {waterPosition(id,stage,width,now,offset,x,y,right);return;}
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
