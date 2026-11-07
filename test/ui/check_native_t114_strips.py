#!/usr/bin/env python3
"""Actual T114 LCD driver + production bubble animation across physical bands."""
from pathlib import Path
import ast,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text()
def block(marker):
 a=s.index(marker);i=s.index('{',a);j=i+1;depth=1
 while depth:depth+=(s[j]=='{')-(s[j]=='}');j+=1
 return s[a:j]
a=s.index('static bool loRaFishRenderClockActive=');b=s.index('// Only pet helpers observe frame time;',a)
clock=s[a:b]
assert s.index('LoRaFishRenderClockScope frameClock;')<s.index('if (banded) {',s.index('LoRaFishRenderClockScope frameClock;'))
assert '#define millis() loRaFishRenderMillis()' in s and '#undef millis' in s
fixture=ast.parse((ROOT/'test/ui/check_t190_partial.py').read_text())
mock=next(ast.literal_eval(n.value) for n in fixture.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='mock' for t in n.targets))
mock=mock.replace('w=320,int h=170','w=240,int h=135').replace('panel(320*170)','panel(240*135)').replace('w!=170||h!=320','w!=135||h!=240').replace('w==320&&y>=0&&y+h<=170','w==240&&y>=0&&y+h<=135')
main=r'''
#include "ST7789LCDDisplay.h"
#include "examples/companion_radio/ui-new/LoRaFishLayout.h"
#include <cassert>
#include <cmath>
static unsigned long live=4321;static unsigned long millis(){return live++;}
'''+clock+chr(10)+'#define millis() loRaFishRenderMillis()'+chr(10)+block('static void drawLoRaFishBubbles(')+chr(10)+'#undef millis'+chr(10)+r'''
struct Memory:DisplayDriver {
 std::vector<uint16_t>pixels=std::vector<uint16_t>(240*135);uint16_t color=0;
 Memory():DisplayDriver(240,135){}
 bool isOn()override{return true;}void turnOn()override{}void turnOff()override{}void clear()override{}
 void startFrame(ColorVal b)override{std::fill(pixels.begin(),pixels.end(),b);}void endFrame()override{}
 void setTextSize(int)override{}void setColor(ColorVal c)override{color=c;}void setCursor(int,int)override{}void print(const char*)override{}
 uint16_t getTextWidth(const char*s)override{return strlen(s)*6;}
 void fillRect(int x,int y,int w,int h)override{for(int j=std::max(0,y);j<std::min(135,y+h);++j)for(int i=std::max(0,x);i<std::min(240,x+w);++i)pixels[j*240+i]=color;}
 void drawRect(int x,int y,int w,int h)override{fillRect(x,y,w,1);fillRect(x,y+h-1,w,1);fillRect(x,y,1,h);fillRect(x+w-1,y,1,h);}
 void drawXbm(int x,int y,const uint8_t*bits,int w,int h)override{for(int j=0;j<h;++j)for(int i=0;i<w;++i)if(bits[j*((w+7)/8)+i/8]&(0x80>>(i&7)))fillRect(x+i,y+j,1,1);}
};
static void scene(DisplayDriver& d){
 d.setColor(7);d.fillRect(0,0,1,135);d.fillRect(239,0,1,135);
 d.fillRect(0,134,240,1);d.fillRect(2,14,18,5);d.fillRect(30,30,19,5);
 LoRaFishLayout::Region r(d,50,0,100,135);r.fillRect(0,15,100,3);r.fillRect(0,127,100,8);
 const uint8_t bits[]={255,255,255};d.drawXbm(180,15,bits,8,3);
 drawLoRaFishBubbles(d);
}
int main(){
 ST7789LCDDisplay d;assert(d.width()==240&&d.height()==135);d.begin();
 assert(d.stripRows()==16&&d.physicalHeight()==135);
 Memory reference;
 for(int frame=0;frame<3;++frame){
  runs.clear();
  {LoRaFishRenderClockScope time;
   const auto stamp=loRaFishRenderMillis();reference.startFrame(0);scene(reference);
   for(int y0=0;y0<d.physicalHeight();y0+=d.stripRows()){
    live+=147;assert(loRaFishRenderMillis()==stamp);
    d.beginStrip(y0);d.startFrame(0);scene(d);d.endStrip();
   }
   assert(panel==reference.pixels);assert(runs.size()==9);
   for(int i=0;i<8;++i)assert((runs[i]==std::pair<int,int>(i*16,16)));
   assert((runs.back()==std::pair<int,int>(128,7)));
  }
  assert(!loRaFishRenderClockActive);auto first=loRaFishRenderMillis();assert(loRaFishRenderMillis()>first);
  if(frame==0){d.setOrientation(true);assert(lastRotation==3);}
  if(frame==1){d.turnOff();d.turnOn();assert(lastRotation==3);}
 }
 puts("PASS production native T114: 240x135 bands match full reference pixels, boundaries 15/16 and 31/32, final 128+7 strip, no gaps/stale pixels, shared animation timestamp, rotation/wake");
}
'''
# Mock drawRect must draw an outline, as the actual Adafruit primitive does.
mock=mock.replace('void drawRect(int x,int y,int w,int h,uint16_t c){fillRect(x,y,w,h,c);}','void drawRect(int x,int y,int w,int h,uint16_t c){fillRect(x,y,w,1,c);fillRect(x,y+h-1,w,1,c);fillRect(x,y,1,h,c);fillRect(x+w-1,y,1,h,c);}')
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'helpers').mkdir()
 for name in ['Wire.h','SPI.h','Adafruit_GFX.h','Adafruit_ST7789.h','helpers/RefCountedDigitalPin.h']:(p/name).write_text('#include "mock.h"'+chr(10))
 (p/'mock.h').write_text(mock);(p/'main.cpp').write_text(main)
 flags=['LORAGOTCHI_NATIVE_UI','HELTEC_T114_WITH_DISPLAY','LORAFISH_STRIP_REDRAW','DISPLAY_WIDTH=135','DISPLAY_HEIGHT=240','DISPLAY_ROTATION=1','DISPLAY_SCALE_X=1.875f','DISPLAY_SCALE_Y=2.109375f','PIN_TFT_CS=39','PIN_TFT_DC=47','PIN_TFT_RST=40','PIN_TFT_SDA=48','PIN_TFT_SCL=38','PIN_TFT_VDD_CTL=7','PIN_TFT_LEDA_CTL=17']
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Wno-unused-parameter','-I'+t,'-I'+str(ROOT),'-I'+str(ROOT/'src'),'-I'+str(ROOT/'src/helpers/ui'),*['-D'+f for f in flags],str(p/'main.cpp'),str(ROOT/'src/helpers/ui/ST7789LCDDisplay.cpp'),'-o',str(p/'check')],check=True)
 subprocess.run([str(p/'check')],check=True)
