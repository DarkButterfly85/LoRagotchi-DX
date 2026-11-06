#!/usr/bin/env python3
"""Compile production presenter/transport against simulated controller RAM + Wire."""
from pathlib import Path
import tempfile, subprocess
root = Path(__file__).resolve().parents[2]
wire = r'''
#pragma once
#include <vector>
#include <stddef.h>
#include <stdint.h>
#include <cassert>
inline void yield() {}
struct TwoWire {
 std::vector<uint8_t> tx; uint8_t ram[16][132]={};
 int page=0,col=0,end=127,first=0,offset=0,calls=0,bytes=0,fail=-1,shortAt=-1; bool ssd=false;
 unsigned long clock=100000;
 void setClock(unsigned long value) { clock=value; }
 void beginTransmission(int addr) { assert(addr==0x3c || addr==0x3d); tx.clear(); }
 size_t write(uint8_t b) { tx.push_back(b); return calls==shortAt ? 0 : 1; }
 int endTransmission() {
  ++calls; assert(clock==400000); assert(tx.size()<=17); if(calls==fail) return 4;
  if(tx[0]==0) {
   if(ssd) { assert(tx.size()==9 && tx[1]==0x20 && tx[2]==0 && tx[3]==0x21 && tx[6]==0x22); first=col=tx[4]; end=tx[5]; page=tx[7]; assert(tx[8]==page); }
   else { assert(tx.size()==4); page=tx[1]-0xb0; col=((tx[2]&15)<<4)|tx[3]; }
  } else { assert(tx[0]==0x40); for(size_t i=1;i<tx.size();++i) { assert(page<16 && col<132); ram[page][col++]=tx[i]; ++bytes; if(ssd && col>end) col=first; } }
  return 0;
 }
};
'''
source = r'''
#include "MonoI2CPageSink.h"
#include "MonoPagePresenter.h"
#include <cstring>
#include <cstdio>
template<int P> void exercise(bool ssd,int offset) {
 TwoWire w; w.ssd=ssd; w.offset=offset;
 MonoI2CPageSink sink(w,0x3d,ssd,offset); MonoPagePresenter<128,P> presenter;
 uint8_t frame[P*128]={};
 auto show=[&]() { assert(presenter.present(frame,sink)); assert(w.clock==100000); for(int p=0;p<P;++p) assert(!memcmp(frame+p*128,w.ram[p]+offset,128)); };
 show(); assert(w.bytes==128*P); int b=w.bytes; show();
#ifndef LORAFISH_MONO_FULL_FRAMES
 assert(w.bytes==b);
#endif
 // Fish moves, old background restored; then alert overlays and disappears.
 frame[5]=0x80; frame[130]=7; show(); frame[5]=0; frame[12]=0x80; show();
 uint8_t saved[sizeof(frame)]; memcpy(saved,frame,sizeof(frame));
 memset(frame+128,255,100); show(); memcpy(frame,saved,sizeof(frame)); show();
 memset(frame,0xaa,sizeof(frame)); show(); memset(frame,0,sizeof(frame)); show();
 // Wake/reset: unchanged frame must repair externally lost controller RAM.
 memset(w.ram,0xff,sizeof(w.ram)); presenter.invalidate(); show();
 // NACK at command and at data, including a partly sent frame, invalidates all.
 for(int step: {1,2,5}) { frame[0]^=255; frame[255]^=255; presenter.invalidate(); w.fail=w.calls+step; assert(!presenter.present(frame,sink)); assert(w.clock==100000); w.fail=-1; b=w.bytes; show(); assert(w.bytes-b==128*P); }
 // Wire buffer enqueue failure despite ACK also invalidates and retries.
 frame[10]^=255; w.shortAt=w.calls; assert(!presenter.present(frame,sink)); w.shortAt=-1; b=w.bytes; show(); assert(w.bytes-b==128*P);
 b=w.bytes; assert(presenter.present(frame,sink,false)); assert(w.bytes-b==128*P);
 b=w.bytes; assert(presenter.present(frame,sink,false)); assert(w.bytes-b==128*P);
 presenter.invalidate(); b=w.bytes; show(); assert(w.bytes-b==128*P);
 assert(!presenter.present(nullptr,sink)); b=w.bytes; show(); assert(w.bytes-b==128*P);
 assert(!sink.writePage(0,128,frame,1)); assert(!sink.writePage(0,0,frame,0));
}
int main() { exercise<8>(true,0); exercise<8>(false,2); exercise<16>(false,0); puts("mono controller pixels, retry, wake, alert and fallback PASS"); }
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp); (p/'Wire.h').write_text(wire); (p/'test.cpp').write_text(source)
 for flags in [[], ['-DLORAFISH_MONO_FULL_FRAMES']]:
  subprocess.run(['g++','-std=c++11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',*flags,'-I'+tmp,'-I'+str(root/'src/helpers/ui'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
  subprocess.run([str(p/'test')],check=True)
