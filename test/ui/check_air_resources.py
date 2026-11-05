#!/usr/bin/env python3
"""C++11 production sprite/packet resource ceilings with ASan+UBSan.
Host compile/stack is not a target flash/RAM/frame-time measurement.
"""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
code=r'''
#include <array>
#include <cassert>
#include <cstdio>
#include <algorithm>
#include "examples/companion_radio/ui-new/LoRaFishAirSprite.h"
#include "examples/companion_radio/ui-new/LoRaFishWaterSprite.h"
#include "examples/companion_radio/LoRaFishCommit.h"
struct Canvas {
 unsigned calls=0,pixels=0;uint16_t colour=0;
 std::array<uint16_t,128*64+2> buffer={};
 Canvas(){buffer.front()=1234;buffer.back()=5678;}
 void setColor(uint16_t c){colour=c;}
 void fillRect(int x,int y,int w,int h) {
  assert(w>0 && w<=32 && h==1);++calls;pixels+=w;
  for(int yy=std::max(0,y);yy<std::min(64,y+h);++yy)
   for(int xx=std::max(0,x);xx<std::min(128,x+w);++xx)buffer[1+yy*128+xx]=colour;
 }
};
int main() {
 static_assert(sizeof(LoRaFishAirArt::masks)==6912,"Air ROM asset ceiling");
 static_assert(sizeof(LoRaFishWaterArt::masks)==5376,"Water ROM asset ceiling");
 static_assert(LoRaFishSpecies::savedSize==18,"save tail must not grow");
 for(unsigned id=0;id<65536;++id) {
  Canvas d;LoRaFishAirSprite::draw(d,64,32,true,id,2,0,1U,2U,3U,0U);
  assert((d.calls!=0)==LoRaFishSpecies::airKnown(id));
  Canvas w;LoRaFishWaterSprite::draw(w,64,32,true,id,2,0,1U,2U,3U,0U);
  assert((w.calls!=0)==(id>0 && id<15));
 }
 for(unsigned id=256;id<274;++id)for(unsigned stage=0;stage<4;++stage)
 for(unsigned phase=0;phase<2;++phase)for(bool right:{false,true})
 for(int x:{-40,0,20,64,108,128,168})for(int y:{-20,0,20,37,64,84}) {
  Canvas d;LoRaFishAirSprite::draw(d,x,y,right,id,stage,phase*280,1U,2U,3U,0U);
  assert(d.calls<=768 && d.pixels<=768);
  assert(d.buffer.front()==1234 && d.buffer.back()==5678);
 }
 uint8_t key[32]={};LoRaFishCommitFrame frame;
 for(unsigned id:{0U,13U,14U,256U,273U,65535U}) {
  frame.prepare(key,UINT32_MAX,UINT32_MAX,true,247,247,247,65535,2,id,true);
  const char* p=frame.forVisit(key,UINT32_MAX,UINT32_MAX);assert(p && strlen(p)<128);
  uint16_t result;bool present;assert(LoRaFishSpecies::extension(p,result,present) && present && result==id);
 }
 puts("PASS C++11 ASan/UBSan: all 65536 IDs, 12096 clipped/mirrored/staged frames, <=768 pixels/calls, Air 6912B + Water 5376B, unchanged SPC1 and <=127B COMMIT");
}
'''
with tempfile.TemporaryDirectory(prefix='air-resource-') as t:
 p=Path(t);(p/'test.cpp').write_text(code)
 subprocess.run(['g++','-std=c++11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',
   '-I',str(ROOT),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
