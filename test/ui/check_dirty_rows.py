#!/usr/bin/env python3
"""Compile the production T096 endFrame against a pixel-accurate SPI sink.
No target execution, radio, display timing or energy measurements.
"""
from pathlib import Path
import subprocess
import tempfile
root = Path(__file__).resolve().parents[2]
src = (root/'src/helpers/ui/ST7735Display.cpp').read_text()
body = src[src.index('void ST7735Display::endFrame() {'):]
assert 'presentedPixelsValid = false;' in src.split('void ST7735Display::_resetAndInit() {',1)[1].split('// Pulse Reset',1)[0]
fixture = r'''
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cassert>
#include <cstdio>
static bool failAlloc=false;
static void* testMalloc(size_t n) { return failAlloc ? nullptr : std::malloc(n); }
#define malloc testMalloc
#define LOW 0
#define HIGH 1
static uint16_t canvas[160*80], panel[160*80];
static int windows=0, bytes=0, row=0;
struct TFT_eSprite { void* getPointer() { return canvas; } } spriteObject;
static TFT_eSprite* sprite=&spriteObject;
static uint16_t* presentedPixels=nullptr;
static bool presentedPixelsValid=false;
static void set_CS(int) {}
static void setAddrWindow(int x,int y,int w,int h) {
  assert(x==0 && w==160 && h==1 && y>=0 && y<80); row=y; ++windows;
}
struct SPI {
 void beginTransaction(int) {} void endTransaction() {}
 void transfer(void* p,void*,int n) { assert(n==320); memcpy(panel+160*row,p,n); bytes+=n; }
 void transferBytes(uint8_t* p,void* out,int n) { transfer(p,out,n); }
} bus;
static SPI* _spi=&bus;
static int _spiSettings=0;
struct ST7735Display { bool _partial=false; void endFrame(); void setPartialUpdates(bool); void forceFullRefresh(); } driver;
'''
main = r'''
static void present(int expected) {
 windows=bytes=0; driver.endFrame();
 assert(windows==expected && bytes==expected*320);
 assert(memcmp(panel,canvas,sizeof(canvas))==0);
}
int main() {
#ifdef LORAFISH_T096_DIRTY_ROWS
 driver.setPartialUpdates(true); present(80); present(0);
 // Moving fish: old bounds erased by full composition, new bounds painted.
 for(int y=30;y<35;++y) for(int x=20;x<30;++x) canvas[y*160+x]=0xF800;
 present(5);
 memset(canvas,0,sizeof(canvas));
 for(int y=32;y<37;++y) for(int x=60;x<70;++x) canvas[y*160+x]=0xF800;
 present(7); present(0);
 // Popup appears and disappears; no stale overlay survives.
 for(int y=20;y<50;++y) for(int x=5;x<150;++x) canvas[y*160+x]=0xFFFF;
 present(30);
 memset(canvas,0,sizeof(canvas)); present(30);
 // Navigation/theme changes and return; compare against the entire desired frame.
 for(auto& p:canvas) p=0x1234;
 present(80); memset(canvas,0,sizeof(canvas)); present(80);
 // Reinitialization must repaint even an identical desired frame.
 memset(panel,0xFF,sizeof(panel)); presentedPixelsValid=false; present(80);
 // Low RAM fallback; later allocation recovery must establish a full baseline.
 free(presentedPixels); presentedPixels=nullptr; presentedPixelsValid=false;
 failAlloc=true; present(80); present(80);
 failAlloc=false; present(80); present(0);
 driver.setPartialUpdates(false); present(80); present(80);
 driver.setPartialUpdates(true); present(80); present(0); driver.forceFullRefresh(); present(80);
 free(presentedPixels);
#else
 present(80); present(80); canvas[159+79*160]=42; present(80);
#endif
 puts("dirty-row transport: PASS");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    cpp=Path(tmp)/'test.cpp'; binary=Path(tmp)/'test'
    cpp.write_text(fixture+body+main)
    for flags in ([], ['-DLORAFISH_T096_DIRTY_ROWS'], ['-DLORAFISH_T096_DIRTY_ROWS','-DESP_PLATFORM']):
        subprocess.run(['g++','-std=c++11','-Wall','-Wextra',*flags,str(cpp),'-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True)
