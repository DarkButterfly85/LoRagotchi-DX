#!/usr/bin/env python3
"""Host production pixel/lifecycle regression; no device or flash claims."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
source=r'''
#include <cassert>
#include <array>
#include <set>
#include <cstdint>
#include "examples/companion_radio/ui-new/LoRaFishLifeArt.h"
using namespace LoRaFishLifeArt;
using Image=std::array<unsigned char,128*64>;
Image draw(unsigned stage,unsigned phase,bool mystery,unsigned variant,int side=1) {
 Image image{};
 auto p=[&](int x,int y,unsigned role){assert(x>=0&&x<128&&y>=22&&y<49);image[y*128+x]=role+1;};
 memorial(p,64-side*18,22,variant);
 egg(p,64+side*18,27,12345,stage,phase*280,mystery);
 return image;
}
int main(){
 std::set<Image> variants;
 for(unsigned v=0;v<3;++v){
  variants.insert(draw(0,0,false,v));
  for(int side:{-1,1})for(unsigned phase=0;phase<4;++phase)for(unsigned stage=0;stage<=100;stage+=20){
   auto a=draw(stage,phase,true,v,side);assert(a==draw(stage,phase,true,v,side));
   // Explicit question mark survives speckles and all crack stages, upright phase.
   if(phase==0){int cx=64+side*18;assert(a[32*128+cx]==2);assert(a[38*128+cx]==2);assert(a[37*128+cx]==1);}
  }
 }
 assert(variants.size()==3);
 std::set<Image> stages,phases;
 for(unsigned s=0;s<100;s+=20)stages.insert(draw(s,0,false,0));
 for(unsigned p=0;p<4;++p)phases.insert(draw(0,p,false,0));
 assert(stages.size()==5&&phases.size()==4);
 for(unsigned start:{0U,10080U})for(unsigned m=0;m<=5;++m)
  assert(progress(start+m,start,5)==m*20);
 assert(progress(0,10080,5)==0);assert(progress(UINT32_MAX,10080,5)==100);
 std::set<unsigned> choices;
 for(unsigned g=1;g<40;++g)choices.insert(identity(0,g,0,6,6,6)%3);
 assert(choices.size()==3);
 // Physical strip replay is exact; no incremental render-time state.
 auto full=draw(80,3,true,2);Image strips{};
 for(int y0=0;y0<64;y0+=8){auto frame=draw(80,3,true,2);for(int y=y0;y<y0+8;++y)for(int x=0;x<128;++x)strips[y*128+x]=frame[y*128+x];}
 assert(full==strips);
}
'''
with tempfile.TemporaryDirectory(prefix='dx-life-art-') as tmp:
 cpp=Path(tmp)/'test.cpp';cpp.write_text(source)
 exe=Path(tmp)/'test'
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=undefined','-I',str(ROOT),str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
ui=(ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text()
a=ui.index('static uint32_t loRaFishLifeArtKey(');b=ui.index('static void drawLoRaFishTankStatusBar',a)
assert 'random(' not in ui[a:b] and 'millis(' not in ui[a:b] and 'saveLoRaFish' not in ui[a:b]
assert ui.index('loRaFishLifeArtFrameMs=(uint32_t)loRaFishRenderMillis();')<ui.index('for (int y0 = 0; y0 < panelRows;')
print('PASS production egg stages, mystery glyph, tilt/glitter, three memorials, bounds, stable identity, strips')

assert 'const bool mystery=!offspring && loRaFishMysterySelected;' in ui
assert 'const LoRaFishAppearance a={loRaFishMemorialScales,loRaFishMemorialBody,0};' in ui
assert 'const int side=(loRaFishLifeArtKey(false)&1)' in ui
print('PASS render callers use explicit provenance and frozen memorial colour/key/side')
