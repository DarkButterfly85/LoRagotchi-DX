#!/usr/bin/env python3
"""Compile the production LCD driver against bounded recording panel/canvas mocks."""
from pathlib import Path
import subprocess, tempfile
root=Path(__file__).resolve().parents[2]
config=(root/'variants/loragotchi_experimental/platformio.ini').read_text()
t190=config.split('[env:Heltec_T190_LoRaGotchi_DX_ble]',1)[1].split('[env:',1)[0]
assert 'build_unflags = -DST7789 -DDISPLAY_CLASS=ST7789Display' in t190
for setting in ['DISPLAY_CLASS=ST7789LCDDisplay','DISPLAY_ROTATION=1','DISPLAY_WIDTH=170','DISPLAY_HEIGHT=320','LORAFISH_TDECK_FRAMEBUFFER=1','-<helpers/ui/ST7789Display.cpp>']:
 assert setting in t190,setting
assert config.count('LORAGOTCHI_T190_COLOR=1')==1
board=(root/'variants/heltec_t190/platformio.ini').read_text()
for pin in ['PIN_TFT_SCL=38','PIN_TFT_SDA=48','PIN_TFT_CS=39','PIN_TFT_DC=47','PIN_TFT_RST=40','PIN_TFT_VDD_CTL=7','PIN_TFT_LEDA_CTL=17','PIN_TFT_LEDA_CTL_ACTIVE=HIGH','PIN_VEXT_EN_ACTIVE=HIGH']:
 assert pin in board,pin
mock=r'''
#pragma once
#include <cstdint>
#include <cassert>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <vector>
#include <algorithm>
using std::min;
#define HIGH 1
#define LOW 0
#define OUTPUT 1
#define HSPI 2
#define ST77XX_WHITE 65535
#define ST77XX_BLACK 0
#define ST77XX_BLUE 31
#define ST77XX_ORANGE 0xfc00
#define ST77XX_CYAN 0x7ff
inline std::vector<int> levels(64,-1);
inline void pinMode(int,int){}
inline void digitalWrite(int p,int v){levels[p]=v;}
inline uint8_t pgm_read_byte(const uint8_t*p){return *p;}
struct SerialMock {template<class...T> void printf(T...){} void println(const char*){}};
inline SerialMock Serial;
struct TwoWire {};
struct SPIClass {SPIClass(int=0){} void begin(int s,int m,int d,int c){if(s!=38||m!=-1||d!=48||c!=39)__builtin_abort();}};
inline SPIClass SPI;
inline SPIClass SPI1;
inline bool failCanvas=false;
struct Adafruit_GFX {
 int W,H; std::vector<uint16_t> pixels; int textSize=1;
 Adafruit_GFX(int w=320,int h=170):W(w),H(h),pixels(w*h){}
 int width()const{return W;} int height()const{return H;}
 void fillScreen(uint16_t c){std::fill(pixels.begin(),pixels.end(),c);}
 void fillRect(int x,int y,int w,int h,uint16_t c){for(int j=std::max(0,y);j<std::min(H,y+h);j++)for(int i=std::max(0,x);i<std::min(W,x+w);i++)pixels[j*W+i]=c;}
 void drawRect(int x,int y,int w,int h,uint16_t c){fillRect(x,y,w,h,c);}
 void drawPixel(int x,int y,uint16_t c){fillRect(x,y,1,1,c);}
 void setTextColor(uint16_t){} void setTextSize(int s){textSize=s;} void cp437(bool){} void setCursor(int,int){} void print(const char*){}
 void getTextBounds(const char*s,int,int,int16_t*x,int16_t*y,uint16_t*w,uint16_t*h){*x=*y=0;*w=strlen(s)*6*textSize;*h=8*textSize;}
};
struct GFXcanvas16:Adafruit_GFX {using Adafruit_GFX::Adafruit_GFX; uint16_t*getBuffer(){return failCanvas?nullptr:pixels.data();}};
inline int rotations=0, blits=0, lastRotation=-1;
inline std::vector<uint16_t> panel(320*170);
inline std::vector<std::pair<int,int>> runs;
inline bool failShadow=false; inline int allocations=0;
inline void* shadowMalloc(size_t n){assert(n==108800);++allocations;return failShadow?nullptr:std::malloc(n);}
struct Adafruit_ST7789:Adafruit_GFX {
 template<class...T> Adafruit_ST7789(T...){}
 void init(int w,int h){if(w!=170||h!=320)__builtin_abort();}
 void setRotation(int r){if(r!=1&&r!=3)__builtin_abort();lastRotation=r;rotations++;}
 void setSPISpeed(int){}
 void drawRGBBitmap(int x,int y,uint16_t*p,int w,int h){assert(x==0&&w==320&&y>=0&&y+h<=170);std::copy(p,p+w*h,panel.begin()+y*w);runs.push_back({y,h});blits++;}
 void fillScreen(uint16_t c){std::fill(panel.begin(),panel.end(),c);}
};
struct RefCountedDigitalPin{void claim(){} void release(){}};
'''
main=r'''
#include "ST7789LCDDisplay.h"
#include <cassert>
static ST7789LCDDisplay d;
static std::vector<uint16_t> expected(320*170);
static void present(int rows,int count){runs.clear();d.endFrame();int n=0;for(auto r:runs)n+=r.second;assert(n==rows&&int(runs.size())==count);assert(panel==expected);}
static void frame(uint16_t c=0){d.startFrame(c);std::fill(expected.begin(),expected.end(),c);}
static void rect(int x,int y,int w,int h,uint16_t c){d.setColor(c);d.fillRect(x,y,w,h);int x0=x,x1=x+w,y0=y,y1=y+h;for(int j=std::max(0,y0);j<std::min(170,y1);++j)for(int i=std::max(0,x0);i<std::min(320,x1);++i)expected[j*320+i]=c;}
int main(int argc,char**){
 if(argc>1){failCanvas=true;d.begin();assert(allocations==0);failCanvas=false;d.setPartialUpdates(true);frame();d.endFrame();assert(allocations==0);d.turnOff();d.turnOn();frame();present(170,1);frame();present(0,0);d.setPartialUpdates(false);return 0;}
 assert(d.supportsPartialUpdates());d.begin();frame();present(170,1);frame();present(170,1);assert(allocations==0);
 d.setPartialUpdates(true);assert(allocations==0);frame();present(170,1);assert(allocations==1);frame();present(0,0);
 frame();rect(4,10,5,2,7);present(2,1);
 frame();rect(20,12,5,2,7);present(4,1);
 frame();rect(20,12,5,2,7);rect(0,30,128,10,99);present(10,1);
 frame();rect(20,12,5,2,7);present(10,1);
 frame(42);present(170,1);frame();present(170,1);
 frame();rect(1,1,1,1,4);rect(127,63,1,1,5);present(2,2);
 frame();d.clear();std::fill(expected.begin(),expected.end(),0);present(2,2);
 frame(77);present(170,1);d.clear();for(auto p:panel)assert(p==0);frame(77);present(170,1);frame(77);present(0,0);
 d.forceFullRefresh();frame(77);present(170,1);d.begin();frame(77);present(170,1);
 d.setOrientation(true);frame(77);present(170,1);d.turnOff();d.turnOn();frame(77);present(170,1);
 d.setPartialUpdates(false);frame(77);present(170,1);frame(77);present(170,1);
 failShadow=true;d.setPartialUpdates(true);frame(77);present(170,1);frame(77);present(170,1);
 failShadow=false;frame(77);present(170,1);frame(77);present(0,0);
 frame(1);d.turnOff();runs.clear();d.endFrame();assert(runs.empty());d.turnOn();frame(77);present(170,1);
 d.setPartialUpdates(false);
 puts("T190 exact row runs/restoration/clear/transitions/allocation: PASS");
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'helpers').mkdir()
 for name in ['Wire.h','SPI.h','Adafruit_GFX.h','Adafruit_ST7789.h','helpers/RefCountedDigitalPin.h']:(p/name).write_text('#include "mock.h"\n')
 (p/'mock.h').write_text(mock);(p/'main.cpp').write_text(main)
 flags=['HELTEC_VISION_MASTER_T190','LORAGOTCHI_T190_COLOR','LORAFISH_TDECK_FRAMEBUFFER','DISPLAY_WIDTH=170','DISPLAY_HEIGHT=320','DISPLAY_ROTATION=1','PIN_TFT_CS=39','PIN_TFT_DC=47','PIN_TFT_RST=40','PIN_TFT_SDA=48','PIN_TFT_SCL=38','PIN_TFT_VDD_CTL=7','PIN_TFT_LEDA_CTL=17','PIN_TFT_LEDA_CTL_ACTIVE=HIGH']
 source=(root/'src/helpers/ui/ST7789LCDDisplay.cpp').read_text().replace('malloc(bytes)','shadowMalloc(bytes)')
 (p/'driver.cpp').write_text(source)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Wno-unused-parameter','-I'+t,'-I'+str(root/'src/helpers/ui'),*['-D'+f for f in flags],str(p/'main.cpp'),str(p/'driver.cpp'),'-o',str(p/'check')],check=True)
 subprocess.run([str(p/'check')],check=True)
 subprocess.run([str(p/'check'),'canvas-failure'],check=True)
 subprocess.run(['g++','-std=c++17','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g','-I'+t,'-I'+str(root/'src/helpers/ui'),*['-D'+f for f in flags],str(p/'main.cpp'),str(p/'driver.cpp'),'-o',str(p/'sanitized')],check=True)
 # The preexisting composition canvas has application lifetime; exclude its leak.
 import os
 env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0')
 subprocess.run([str(p/'sanitized')],check=True,env=env)
 subprocess.run([str(p/'sanitized'),'canvas-failure'],check=True,env=env)
 # Compile the actual shared driver without T190 capability in strip and full-frame modes.
 for extra in ([], ['-DLORAFISH_STRIP_REDRAW','-DHELTEC_T114_WITH_DISPLAY'], ['-DLORAFISH_TDECK_FRAMEBUFFER']):
  shared=[f for f in flags if f not in ['HELTEC_VISION_MASTER_T190','LORAGOTCHI_T190_COLOR','LORAFISH_TDECK_FRAMEBUFFER']]
  subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Wno-unused-parameter','-I'+t,'-I'+str(root/'src/helpers/ui'),*['-D'+f for f in shared],*extra,'-c',str(root/'src/helpers/ui/ST7789LCDDisplay.cpp'),'-o',str(p/'shared.o')],check=True)
