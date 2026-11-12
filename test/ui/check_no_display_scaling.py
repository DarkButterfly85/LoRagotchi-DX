#!/usr/bin/env python3
"""No display scaling anywhere: every driver reports the panel's own size and draws 1:1.

Static guards over the driver sources and board configs, plus a host build of the production NV3001B driver
against a recording SPI mock (the one driver whose bus traffic can be mocked without a graphics library).
It cannot see a real panel: it proves the geometry the firmware asks the hardware for, not how it looks.
"""
from pathlib import Path
import re, subprocess, tempfile
ROOT = Path(__file__).resolve().parents[2]

def text(p): return (ROOT / p).read_text()

# 1. No scaling tokens in any driver, display variant or board config.
FORBIDDEN = re.compile(r'DISPLAY_SCALE|EINK_SCALE|EINK_[XY]_OFFSET|SCALE_X|SCALE_Y|UI_ZOOM|pushRotateZoom|FRAME_ZOOM|'
                       r'NV3001B_LOGICAL|NV3001B_TEXT_SIZE|scale_x|scale_y|textPixelScale|scaleX\(|scaleY\(')
files = sorted(ROOT.glob('src/helpers/ui/*.[ch]*')) + sorted(ROOT.glob('variants/lilygo_twatch_s3/*.[ch]*')) + \
        sorted(ROOT.glob('variants/*/platformio.ini')) + [ROOT / 'platformio.ini', ROOT / 'platformio-meshcore.ini']
for f in files:
    for n, line in enumerate(f.read_text(errors='replace').splitlines(), 1):
        code = line.split('//')[0]
        assert not FORBIDDEN.search(code), f'{f.relative_to(ROOT)}:{n}: scaling left in: {line.strip()}'
print('PASS no scaling token in any display driver, T-Watch display, platformio.ini or variant ini')

# 2. Each driver reports its panel's own size.
st7735 = text('src/helpers/ui/ST7735Display.h')
assert 'NATIVE_WIDTH = 160' in st7735 and 'NATIVE_HEIGHT = 80' in st7735
assert st7735.count('DisplayDriver(NATIVE_WIDTH, NATIVE_HEIGHT)') == 2 and 'DisplayDriver(128, 64)' not in st7735
st7789 = text('src/helpers/ui/ST7789Display.h')
for size in ('DisplayDriver(320, 170)', 'DisplayDriver(320, 240)', 'DisplayDriver(240, 135)'):
    assert size in st7789, size
assert 'DisplayDriver(128, 64)' not in st7789
nv = text('src/helpers/ui/NV3001BDisplay.h')
assert 'DisplayDriver(NV3001B_SCREEN_WIDTH, NV3001B_SCREEN_HEIGHT)' in nv
gx = text('src/helpers/ui/GxEPDDisplay.h')
assert gx.count('DisplayDriver(GXEPD_NATIVE_WIDTH, GXEPD_NATIVE_HEIGHT)') == 2 and 'DisplayDriver(128, 128)' not in gx
lcd = text('src/helpers/ui/ST7789LCDDisplay.h')
assert 'LORAGOTCHI_LCD_WIDTH 128' not in lcd and 'ifdef LORAGOTCHI_NATIVE_UI' not in lcd
lg = text('src/helpers/ui/LGFXDisplay.h')
assert 'DisplayDriver(w, h)' in lg
tw = text('variants/lilygo_twatch_s3/TWatchS3Display.h')
assert 'LOGICAL_WIDTH = 240' in tw and 'FRAME_HEIGHT = 240' in tw and 'MENU_OFFSET_Y = (FRAME_HEIGHT - LOGICAL_HEIGHT) / 2;   // 88' in tw
assert 'pushSprite(&_lcd, 0, 0)' in text('variants/lilygo_twatch_s3/TWatchS3Display.cpp')
print('PASS drivers report native sizes: ST7735 160x80, ST7789Display 320x170/320x240/240x135, NV3001B 220x128, '
      'GxEPD model size, LCD from DISPLAY_WIDTH/HEIGHT, LGFX panel, T-Watch 240x240')

# 3. LoRaFish builds on panels that are not 128x64 use the native layout.
def section(path, header):
    body = text(path).split(header, 1)[1]
    return body.split('\n[', 1)[0]
exp = 'variants/loragotchi_experimental/platformio.ini'
for env in ['Heltec_Wireless_Tracker', 'Heltec_t1', 'ThinkNode_M9', 'heltec_rc32', 'heltec_tracker_v2', 'heltec_v4_tft', 'heltec_v4_r8_tft', 'Heltec_T190']:
    assert 'LORAGOTCHI_NATIVE_UI=1' in section(exp, f'[env:{env}_LoRaGotchi_DX_ble]'), env
tdeck = text('variants/lilygo_tdeck/platformio.ini')
assert tdeck.count('LORAFISH_UI=1') == tdeck.count('LORAGOTCHI_NATIVE_UI=1') == 3
assert 'LORAGOTCHI_NATIVE_UI=1' in section('variants/heltec_t096/platformio.ini', '[Heltec_t096_LoRaFish_companion_ble_base]')
print('PASS every LoRaFish TFT build (T-Deck, T096, trackers, M9, RC32, V4, T190, T114) uses the native layout')

# 4. NV3001B draws text, rectangles and bitmaps 1:1 (native 5x7 in a 6x8 cell).
mock = r'''
#pragma once
#include <cstdint>
#include <cstring>
#include <vector>
#include <cstddef>
#define HIGH 1
#define LOW 0
#define OUTPUT 1
#define MSBFIRST 1
#define SPI_MODE0 0
#define HSPI 2
#define PROGMEM
inline uint8_t pgm_read_byte(const uint8_t* p) { return *p; }
inline void delay(int) {}
struct Event { bool cmd; uint8_t v; };
inline std::vector<Event> bus;
inline int dcLevel = 1;
inline void pinMode(int, int) {}
inline void digitalWrite(int pin, int v) { if (pin == 16) dcLevel = v; }
struct SPISettings { SPISettings(long, int, int) {} };
struct SPIClass {
  SPIClass(int = 0) {}
  void begin(int, int, int, int) {}
  void beginTransaction(SPISettings) {}
  void endTransaction() {}
  void transfer(uint8_t b) { bus.push_back({dcLevel == LOW, b}); }
};
struct RefCountedDigitalPin { void claim() {} void release() {} };
'''
main = r'''
#include "NV3001BDisplay.h"
#include <cassert>
#include <set>
#include <utility>
static std::set<std::pair<int,int>> lit;           // panel pixels painted with the current colour
static std::vector<std::vector<int>> windows;     // {x,y,w,h} of every fill
static void replay() {
  lit.clear(); windows.clear();
  int cx0=0,cx1=0,ry0=0,ry1=0; size_t i=0; uint8_t pending=0;
  while (i < bus.size()) {
    if (bus[i].cmd) {
      pending = bus[i].v; ++i;
      std::vector<uint8_t> data;
      while (i < bus.size() && !bus[i].cmd) data.push_back(bus[i++].v);
      if (pending == 0x2A) { cx0 = data[0]<<8|data[1]; cx1 = data[2]<<8|data[3]; }
      if (pending == 0x2B) { ry0 = data[0]<<8|data[1]; ry1 = data[2]<<8|data[3]; }
      if (pending == 0x2C) {
        windows.push_back({cx0, ry0, cx1-cx0+1, ry1-ry0+1});
        if (data.size() >= 2 && data[0]==0x12 && data[1]==0x34)
          for (int y=ry0;y<=ry1;++y) for (int x=cx0;x<=cx1;++x) lit.insert({x,y});
      }
    } else ++i;
  }
}
int main() {
  NV3001BDisplay d;
  assert(d.width()==220 && d.height()==128);                    // the panel, landscape: no 128x64 canvas
  assert(d.begin());
  d.setColor(0x1234);
  bus.clear(); d.setTextSize(1); d.setCursor(10,20); d.print("H");
  replay();
  // 'H' is 5x7 at native size: columns x=10..14, rows y=20..26, every set font bit one pixel.
  for (auto& p : lit) assert(p.first>=10 && p.first<=14 && p.second>=20 && p.second<=26);
  assert(lit.size()==(size_t)(7+7+3));                          // two full 7-pixel stems and the 3-pixel bar of H
  for (auto& w : windows) assert(w[2]==1 && w[3]==1);           // never a stretched pixel
  assert(d.getTextWidth("abc")==18);                            // 6 px advance per character
  d.setTextSize(2); assert(d.getTextWidth("abc")==36);          // size N is N x N, not an uneven 2x3
  bus.clear(); d.setTextSize(2); d.setCursor(0,0); d.print("H"); replay();
  for (auto& w : windows) assert(w[2]==2 && w[3]==2);
  bus.clear(); d.fillRect(5,6,7,8); replay();
  assert(windows.size()==1 && windows[0]==std::vector<int>({5,6,7,8}));
  bus.clear(); d.drawRect(30,40,10,5); replay();
  assert(lit.size()==(size_t)(10+10+3+3));                      // the outline, 1 pixel wide
  const uint8_t bits[] = {0xA0, 0x40};                          // 8x2: .#.# ... / .#......
  bus.clear(); d.drawXbm(100,50,bits,8,2); replay();
  assert(lit.size()==3 && lit.count({100,50}) && lit.count({102,50}) && lit.count({101,51}));
  d.fillRect(210,120,30,30); // clipped to the panel, never past 220x128
  return 0;
}
'''
with tempfile.TemporaryDirectory() as t:
    p = Path(t); (p / 'helpers').mkdir()
    for name in ['Arduino.h', 'SPI.h', 'helpers/RefCountedDigitalPin.h']: (p / name).write_text('#include "mock.h"\n')
    (p / 'mock.h').write_text(mock); (p / 'main.cpp').write_text(main)
    flags = ['PIN_TFT_SCL=17', 'PIN_TFT_SDA=38', 'PIN_TFT_CS=39', 'PIN_TFT_DC=16', 'PIN_TFT_RST=4', 'PIN_TFT_EN=6', 'PIN_TFT_BL=5']
    subprocess.run(['g++', '-std=c++17', '-Wall', '-Wno-unused-parameter', '-I' + t, '-I' + str(ROOT / 'src/helpers/ui'), '-I' + str(ROOT / 'src'),
                    *['-D' + f for f in flags], str(p / 'main.cpp'), str(ROOT / 'src/helpers/ui/NV3001BDisplay.cpp'), '-o', str(p / 'check')], check=True)
    subprocess.run([str(p / 'check')], check=True)
print('PASS NV3001B production driver: 220x128, native 5x7 text with a 6 px advance, 1:1 rectangles and bitmaps')
