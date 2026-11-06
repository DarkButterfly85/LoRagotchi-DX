"""Minimal Adafruit boundary mock; production SH1106Display.cpp is compiled unchanged."""
from pathlib import Path


def write_headers(directory):
    directory = Path(directory)
    (directory / "Wire.h").write_text(r'''
#pragma once
#include <cstdint>
#include <vector>
inline void yield() {}
struct TwoWire {
  void setClock(unsigned long) {}
  size_t write(uint8_t) { return 1; }
  uint8_t address=0, present=0x3C;
  std::vector<int> probes;
  void beginTransmission(uint8_t a){address=a;probes.push_back(a);}
  uint8_t endTransmission(){return address==present ? 0 : 2;}
};
inline TwoWire Wire;
''')
    (directory / "Adafruit_GFX.h").write_text("#pragma once\n")
    (directory / "Adafruit_GrayOLED.h").write_text("#pragma once\n")
    (directory / "Adafruit_SH110X.h").write_text(r'''
#pragma once
#include <cassert>
#include <cstring>
#include <utility>
#include "Wire.h"
#define SH110X_BLACK 0
#define SH110X_WHITE 1
#define SH110X_DISPLAYON 0xAF
#define SH110X_DISPLAYOFF 0xAE
namespace MockOLED {
inline bool beginOK=true, ready=false;
inline int beginAddress=-1, begins=0, contrast=-1;
inline std::vector<std::pair<int,int>> events;
inline void reset(){beginOK=true;ready=false;beginAddress=-1;begins=0;contrast=-1;events.clear();Wire.probes.clear();Wire.present=0x3C;}
}
class Adafruit_SH1106G {
public:
  Adafruit_SH1106G(int,int,TwoWire*,int){}
  bool begin(uint8_t addr,bool reset){
    assert(reset);++MockOLED::begins;MockOLED::beginAddress=addr;
    MockOLED::ready=MockOLED::beginOK;
    // Real 2.1.x begin resets contrast to 255 and finishes with DISPLAYON.
    if(MockOLED::ready){MockOLED::contrast=255;MockOLED::events.emplace_back(SH110X_DISPLAYON,0);}
    return MockOLED::ready;
  }
  void oled_command(uint8_t c){assert(MockOLED::ready);MockOLED::events.emplace_back(c,0);}
  void setContrast(uint8_t c){assert(MockOLED::ready);MockOLED::contrast=c;MockOLED::events.emplace_back(0x81,c);}
  void setRotation(uint8_t) {}
  uint8_t* getBuffer(){static uint8_t buffer[2048]={};return buffer;}
  void clearDisplay(){} void display(){} void setTextColor(int){}
  void setTextSize(int){} void cp437(bool){} void setCursor(int,int){}
  void print(const char*){} void fillRect(int,int,int,int,int){}
  void drawRect(int,int,int,int,int){} void drawBitmap(int,int,const uint8_t*,int,int,int){}
  void getTextBounds(const char* s,int,int,int16_t* x,int16_t* y,uint16_t* w,uint16_t* h){*x=*y=0;*w=strlen(s)*6;*h=8;}
};
''')
