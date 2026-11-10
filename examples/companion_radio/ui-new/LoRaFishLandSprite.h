#pragma once
#include "../LoRaFishSpecies.h"
#include "LoRaFishLandArt.h"

// Same semantic-mask renderer as LoRaFishAirSprite; art is DRAFT first-pass (see
// tools/land/generate_sprites.py). Palette resolved at runtime by the same
// genetics/theme converter as legacy fish. No framebuffer, heap or per-species
// RGB assets; max footprint is 32x24 pixels.
// noseDown (sniff phase, LoRaFishSpecies::PoseSniff): the head-down picture is NOT stored art. The head
// columns of the normal walking frame are sheared downwards at draw time using LoRaFishSpecies::sniffHead
// (first head column + nose drop in mask rows), so the art stays at its 14976-byte budget. Same code on
// colour, mono and e-ink builds; it only changes which source row each column reads.
namespace LoRaFishLandSprite {
template<class Display, class Colour>
inline void draw(Display& d,int x,int y,bool right,uint16_t id,uint8_t stage,
                 uint32_t now,Colour body,Colour fins,Colour eyes,Colour background,bool noseDown=false) {
  if (!LoRaFishSpecies::landKnown(id)) return; // caller preserves legacy fish
  // Natural-idle animals step by distance walked, so a standing animal holds one still frame.
  const unsigned phase=LoRaFishSpecies::steppedByDistance(id) ? (unsigned)(((x<0?-x:x)/5)&1) : (now/280U)&1U;
  const unsigned width=stage==0?20:stage==1?26:32;
  const unsigned height=stage==0?15:stage==1?19:24;
  const uint8_t* mask=LoRaFishLandArt::masks[id-LoRaFishSpecies::Dog][phase];
  const LoRaFishSpecies::SniffHead head=noseDown ? LoRaFishSpecies::sniffHead(id) : LoRaFishSpecies::SniffHead{0,0};
  const Colour palette[]={background,body,fins,eyes};
  // Coalesce equal semantic pixels into horizontal runs. Transparent pixels
  // never erase other pets.
  for(unsigned dy=0;dy<height;++dy) {
    const unsigned sy=dy*24/height;
    auto roleAt=[&](unsigned dx) -> uint8_t {
      const unsigned col=dx*32/width;
      unsigned row=sy;
      if(head.drop && col>=head.hx) {
        // Nose-down shear: the drop grows from 0 at the first head column to head.drop at the right edge.
        const unsigned shift=(head.drop*(col-head.hx+1U)+(32U-head.hx)/2U)/(32U-head.hx);
        if(row<shift)return 0;
        row-=shift;
      }
      const unsigned bit=row*32+col;
      return (mask[bit/4]>>((bit%4)*2))&3;
    };
    for(unsigned dx=0;dx<width;) {
      const unsigned start=dx;const uint8_t role=roleAt(dx++);
      while(dx<width && roleAt(dx)==role)++dx;
      if(!role)continue;
      const int left=right ? (int)start-(int)width/2 : (int)width/2-(int)dx+1;
      d.setColor(palette[role]);
      d.fillRect(x+left,y+(int)dy-(int)height/2,(int)(dx-start),1);
    }
  }
}
}
