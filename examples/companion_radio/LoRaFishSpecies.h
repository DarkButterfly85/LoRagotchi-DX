#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>

// Water registry v1. IDs are permanent protocol identities, not menu positions.
namespace LoRaFishSpecies {
enum : uint16_t {
  TropicalFish=0, Blowfish=1, Shark=2, Dolphin=3, Whale=4, Seal=5, Shrimp=6,
  Squid=7, Lobster=8, Crab=9, Octopus=10, Jellyfish=11, ShellDweller=12, SeaStar=13
};
static constexpr uint8_t count=14;
inline bool known(uint16_t id) { return id < count; }
inline uint16_t renderId(uint16_t id) { return known(id) ? id : (uint16_t)TropicalFish; }
inline const char* label(uint16_t id) {
  static const char* const names[]={"Tropical fish","Blowfish","Shark","Dolphin","Whale",
    "Seal","Shrimp","Squid","Lobster","Crab","Octopus","Jellyfish","Shell-dweller","Sea star"};
  return known(id) ? names[id] : "Unknown (fish)";
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
  return !strcmp(p,"S1");
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
inline uint16_t mystery(uint32_t seed) { return (uint16_t)(mix(seed)%count); }
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
