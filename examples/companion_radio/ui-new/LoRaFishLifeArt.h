#pragma once
#include <stdint.h>
// Pure pixel art: caller snapshots time once per composed frame. No RNG, writes,
// clock reads or lifecycle mutation. Persisted identity fields supply the seed.
namespace LoRaFishLifeArt {
inline uint32_t mix(uint32_t x) {
  x ^= x >> 16; x *= 0x7feb352dUL; x ^= x >> 15;
  x *= 0x846ca68bUL; return x ^ (x >> 16);
}
inline uint32_t identity(uint32_t seed,uint16_t generation,uint16_t species,
                         uint8_t body,uint8_t scales,uint8_t eyes) {
  return mix(seed ^ ((uint32_t)generation<<16) ^ species ^
      ((uint32_t)body<<24) ^ ((uint32_t)scales<<8) ^ eyes);
}
inline unsigned progress(uint32_t age,uint32_t start,uint32_t duration) {
  if (age<=start) return 0;
  uint32_t elapsed=age-start;
  return elapsed>=duration ? 100 : (unsigned)(elapsed*100/duration);
}
template<class Pixel> void egg(Pixel pixel,int cx,int top,uint32_t key,
                               unsigned progress,uint32_t now,bool mystery) {
  // Shear around the planted base makes an actual tilted shell, not translation.
  int phase=(now/280U)%4U;
  int tilt=phase==1 ? -1 : phase==3 ? 1 : 0;
  static const uint8_t radius[]={2,3,4,5,5,6,6,7,7,7,7,7,7,6,6,5,4,2};
  auto dot=[&](int x,int y,unsigned role) {
    pixel(cx+x+tilt*(17-y)/8,top+y,role);
  };
  for(int y=0;y<18;++y)for(int x=-radius[y];x<=radius[y];++x) {
    bool edge=x==-radius[y] || x==radius[y] || y==0 || y==17;
    dot(x,y,edge ? 1 : 0);
  }
  // Stable speckles, leaving a quiet central space for the mystery glyph.
  for(unsigned i=0;i<9;++i) {
    uint32_t n=mix(key+i*0x9e3779b9UL);
    int y=3+n%12,x=(int)((n>>8)%9)-4;
    if(!mystery || x<=-3 || x>=3) dot(x,y,2);
  }
  // Cracks reflect whole simulation minutes, never wall-clock approximation.
  unsigned length=progress>=80 ? 15 : progress>=60 ? 10 : progress>=40 ? 6 : progress>=20 ? 3 : 0;
  for(unsigned y=0;y<length;++y) {
    int x=(y%4<2 ? -1 : 0);
    if(!mystery || y<4 || y>12) dot(x,y+1,1);
    if(y>7 && progress>=80) dot(x+1+(y-8)/2,y+1,1);
  }
  if(mystery) {
    static const uint8_t question[]={14,17,1,2,4,0,4};
    for(int y=0;y<7;++y)for(int x=0;x<5;++x)
      dot(x-2,y+5,(question[y]&(1<<(4-x))) ? 1 : 0);
  }
  // Warming glitter stays clear of header/footer and adjacent memorial.
  int sx=(phase&1) ? -11 : 11, sy=phase<2 ? 4 : 12;
  pixel(cx+sx,top+sy,2);
  if(phase&1) {
    pixel(cx+sx-1,top+sy,2);pixel(cx+sx+1,top+sy,2);
    pixel(cx+sx,top+sy-1,2);pixel(cx+sx,top+sy+1,2);
  }
}
// 0 rounded headstone, 1 stepped obelisk, 2 winged heart memorial.
template<class Pixel> void memorial(Pixel pixel,int cx,int top,unsigned variant) {
  variant%=3;
  for(int y=0;y<25;++y)for(int x=-12;x<=12;++x) {
    int half=variant==0 ? (y<2 ? 5 : y<5 ? 8 : y<22 ? 10 : 12) :
             variant==1 ? (y<3 ? 2+y : y<20 ? 7 : y<23 ? 10 : 12) :
                          (y<3 ? 5 : y<7 ? 8 : y<11 ? 12 : y<22 ? 8 : 12);
    if(x>=-half && x<=half) {
      bool edge=x==-half || x==half || y==0 || y==24;
      pixel(cx+x,top+y,edge ? 1 : 0);
    }
  }
  // Inset RIP: explicit contrasting pixels, even on light monochrome themes.
  static const uint8_t letters[3][5]={{6,5,6,5,5},{7,2,2,2,7},{6,5,6,4,4}};
  for(int l=0;l<3;++l)for(int y=0;y<5;++y)for(int x=0;x<3;++x)
    if(letters[l][y]&(1<<(2-x)))pixel(cx-5+l*4+x,top+12+y,1);
  // Personal-colour ornament; hollow/outline survives identical trait colours.
  pixel(cx,top+6,2);pixel(cx-1,top+7,2);pixel(cx+1,top+7,2);
  pixel(cx,top+8,2);
}
}
