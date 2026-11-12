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
inline std::vector<uint16_t> panel;
struct Adafruit_ST7789:Adafruit_GFX {
 template<class...T> Adafruit_ST7789(T...){}
 void init(int w,int h){if(w!=170||h!=320)__builtin_abort();}
 void setRotation(int r){if(r!=1&&r!=3)__builtin_abort();lastRotation=r;rotations++;}
 void setSPISpeed(int){}
 void drawRGBBitmap(int,int,uint16_t*p,int w,int h){panel.assign(p,p+w*h);blits++;}
};
struct RefCountedDigitalPin{void claim(){} void release(){}};
'''
main=r'''
#include "ST7789LCDDisplay.h"
#include <cassert>
int main(int argc,char**) {
 failCanvas=argc>1;
 ST7789LCDDisplay d;assert(d.supportsColor());assert(d.begin());
 assert(levels[7]==LOW&&levels[17]==HIGH&&rotations==1);
 d.startFrame(0);d.setColor(0x1234);
 const uint8_t bits[]={0xff,0xff};d.drawXbm(1,2,bits,8,2);d.endFrame();
 if(!failCanvas){assert(blits==1);int count=0;for(auto p:panel)count+=p==0x1234;assert(count==16);
 // Exactly 8 x 2, one panel pixel per bitmap pixel (no scaling).
 for(int y=0;y<170;y++)for(int x=0;x<320;x++)assert((panel[y*320+x]==0x1234)==(x>=1&&x<9&&y>=2&&y<4));
 d.startFrame(0x55);d.endFrame();for(auto p:panel)assert(p==0x55);
 d.startFrame(0);d.setColor(7);d.fillRect(1,1,1,1);d.endFrame();
 int rectCount=0;for(auto p:panel)rectCount+=p==7;assert(rectCount==1); // one panel pixel
 }
 assert(d.supportsOrientation());
 d.setOrientation(true);assert(lastRotation==3);
 d.setOrientation(true);assert(rotations==2);
 d.turnOff();assert(!d.isOn()&&levels[7]==HIGH&&levels[17]==LOW);
 d.turnOn();assert(d.isOn()&&rotations==3&&lastRotation==3&&levels[7]==LOW);
 d.startFrame();d.drawXbm(0,0,nullptr,8,8);d.fillRect(0,0,-1,1);d.endFrame();
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'helpers').mkdir()
 for name in ['Wire.h','SPI.h','Adafruit_GFX.h','Adafruit_ST7789.h','helpers/RefCountedDigitalPin.h']:(p/name).write_text('#include "mock.h"\n')
 (p/'mock.h').write_text(mock);(p/'main.cpp').write_text(main)
 flags=['HELTEC_VISION_MASTER_T190','LORAGOTCHI_T190_COLOR','LORAFISH_TDECK_FRAMEBUFFER','DISPLAY_WIDTH=170','DISPLAY_HEIGHT=320','DISPLAY_ROTATION=1','PIN_TFT_CS=39','PIN_TFT_DC=47','PIN_TFT_RST=40','PIN_TFT_SDA=48','PIN_TFT_SCL=38','PIN_TFT_VDD_CTL=7','PIN_TFT_LEDA_CTL=17','PIN_TFT_LEDA_CTL_ACTIVE=HIGH']
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Wno-unused-parameter','-I'+t,'-I'+str(root/'src/helpers/ui'),*['-D'+f for f in flags],str(p/'main.cpp'),str(root/'src/helpers/ui/ST7789LCDDisplay.cpp'),'-o',str(p/'check')],check=True)
 subprocess.run([str(p/'check')],check=True);subprocess.run([str(p/'check'),'allocation-failure'],check=True)
print('T190 production driver: RGB565, 1:1 bitmap, full redraw, wake rotation, power polarity and allocation fallback PASS')
