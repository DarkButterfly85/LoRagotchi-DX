#!/usr/bin/env python3
"""Bounded production driver/layout checks. No physical size/timing claims."""
from pathlib import Path
import ast, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[2]
fixture=ast.parse((ROOT/'test/ui/check_t190_partial.py').read_text())
mock=next(ast.literal_eval(n.value) for n in fixture.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='mock' for t in n.targets))
main=r'''
#include "ST7789LCDDisplay.h"
#include "examples/companion_radio/ui-new/LoRaFishLayout.h"
#include <cassert>
int main(int argc,char**) {
 failCanvas=argc>1;
 ST7789LCDDisplay d; assert(d.width()==320 && d.height()==170); d.begin();
 d.setTextSize(1); assert(d.getTextWidth("Native")==36);
 d.setPartialUpdates(true); d.startFrame(0);d.setColor(7);
 const uint8_t bits[]={255,255};d.drawXbm(1,2,bits,8,2);
 d.fillRect(319,169,1,1);d.endFrame();
 if(!failCanvas) {
   int count=0;for(auto p:panel)count+=p==7;assert(count==17);
   assert(panel[169*320+319]==7);
   for(int y=2;y<4;++y)for(int x=1;x<9;++x)assert(panel[y*320+x]==7);
   const auto before=blits;
   d.startFrame(0);d.setColor(7);d.drawXbm(1,2,bits,8,2);d.fillRect(319,169,1,1);d.endFrame();
   assert(blits==before); // Native composition still suppresses identical frames.
   d.startFrame(0);d.endFrame(); assert(panel[169*320+319]==0);
   assert((runs.back()==std::pair<int,int>(169,1)));
   d.setPartialUpdates(false);d.startFrame(0x1234);d.endFrame();
   for(auto p:panel)assert(p==0x1234);
   d.startFrame(0);d.setColor(8);
   LoRaFishLayout::Region r(d,10,20,30,40);
   r.fillRect(-5,-5,10,10);r.fillRect(29,39,9,9);
   const uint8_t edge[]={255};r.drawXbm(28,38,edge,8,1);
   d.endFrame(); count=0;for(auto p:panel)count+=p==8;assert(count==28);
   assert(panel[20*320+10]==8 && panel[59*320+39]==8);
   assert(panel[20*320+9]==0 && panel[59*320+40]==0);
 }
 if(!failCanvas) {
   d.startFrame(0);d.setColor(9);LoRaFishLayout::Page p(d);
   const uint8_t edge[]={255,255};p.drawXbm(318,56,edge,8,2);d.endFrame();
   assert(panel[162*320+318]==9 && panel[163*320+319]==9);
   int n=0;for(auto pixel:panel)n+=pixel==9;assert(n==4);
 }
 assert(LoRaFishLayout::bodyOffset(64)==0);
 assert(LoRaFishLayout::bodyOffset(135)==35);
 assert(LoRaFishLayout::bodyOffset(170)==53);
 assert(LoRaFishLayout::sidebarWidth(240)==0 && LoRaFishLayout::sidebarWidth(320)==0);
 assert(LoRaFishLayout::bodyOffset(80)==8 && LoRaFishLayout::bodyOffset(128)==32);   // 160x80 and 220x128 panels
 for(int h:{80,111,128,146,216}) {
   int low=999,high=0;
   for(int y=19;y<=41;++y){int p=LoRaFishLayout::habitatY(y,h);assert(p>=34 && p<=h-34);low=std::min(low,p);high=std::max(high,p);}
   assert(high-low>(h-68)*8/10);
   assert(LoRaFishLayout::habitatY(37,h,true)==h-30);
 }
 assert(LoRaFishLayout::habitatY(38,64)==38);
 assert(LoRaFishLayout::pageY(56,170)==162);
 d.setOrientation(true);assert(lastRotation==3);d.turnOff();d.turnOn();assert(lastRotation==3);
 d.startFrame(0);d.endFrame(); // wake invalidates the retained presentation
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'helpers').mkdir()
 for name in ['Wire.h','SPI.h','Adafruit_GFX.h','Adafruit_ST7789.h','helpers/RefCountedDigitalPin.h']:(p/name).write_text('#include "mock.h"'+chr(10))
 (p/'mock.h').write_text(mock);(p/'main.cpp').write_text(main)
 flags=['LORAGOTCHI_NATIVE_UI','HELTEC_VISION_MASTER_T190','LORAGOTCHI_T190_COLOR','LORAFISH_TDECK_FRAMEBUFFER','DISPLAY_WIDTH=170','DISPLAY_HEIGHT=320','DISPLAY_ROTATION=1','PIN_TFT_CS=39','PIN_TFT_DC=47','PIN_TFT_RST=40','PIN_TFT_SDA=48','PIN_TFT_SCL=38','PIN_TFT_VDD_CTL=7','PIN_TFT_LEDA_CTL=17','PIN_TFT_LEDA_CTL_ACTIVE=HIGH']
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Wno-unused-parameter','-I'+t,'-I'+str(ROOT),'-I'+str(ROOT/'src'),'-I'+str(ROOT/'src/helpers/ui'),*['-D'+f for f in flags],str(p/'main.cpp'),str(ROOT/'src/helpers/ui/ST7789LCDDisplay.cpp'),'-o',str(p/'check')],check=True)
 subprocess.run([str(p/'check')],check=True);subprocess.run([str(p/'check'),'allocation-failure'],check=True)
print('PASS native T190: 1:1 text/bitmap/rectangles, edges, clipped regions, full/partial, wake/orientation, allocation fallback')
