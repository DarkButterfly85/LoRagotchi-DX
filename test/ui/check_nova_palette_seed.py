#!/usr/bin/env python3
"""Nova colour pictures: the 16-entry palette is seeded in a fixed priority order, so a colour that matters is never snapped.

python3 test/ui/check_nova_palette_seed.py     (Python 3 and g++; no firmware build, no hardware)

Host check of the production code: the sleeping pet scene (drawLoRaFishSleeping with the colour tank, the pet sprite,
header and floor rule), the palette seed (loRaFishNovaPaletteSeed) and the sprite colour code are sliced out of UITask.cpp
and compiled against the real NovaPetLink.h / NovaPetTee.h. The scene is drawn through the tee into a Link; every
picture pixel is compared with what a recording screen (true RGB565, no palette) got from the same calls.

  (a) the sleeping scene with no colour scenery (plain window): overflowed() == 0. With the full colour tank the scene
      itself draws 17-25 colours, more than 16 slots, so some background pixels are always snapped (the tank is reported,
      and every snapped pixel is checked to be a background colour, never a theme, pet or plant colour)
  (b) body, fins, eyes and plant colours are each an exact palette entry, on every theme, pet stage and screen size
  (c) the theme colours take the lowest slots in order (window background, title bkg, title text, primary, secondary,
      accent), then the pet's body, fins and eyes, then the plants, then the background blues
  (d) two consecutive key pictures carry identical palettes
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / 'examples/companion_radio/ui-new/UITask.cpp'
src = UI.read_text()


def block(marker):
    a = src.index(marker)
    i = src.index('{', a)
    j, depth = i + 1, 1
    while depth:
        depth += (src[j] == '{') - (src[j] == '}')
        j += 1
    return src[a:j]


def maybe(marker, wrap=None):
    if marker not in src:
        return ''
    b = block(marker)
    return f'#if {wrap}\n{b}\n#endif\n' if wrap else b + '\n'


def preamble(func, start_marker, end_marker):
    body = block(func)
    a = body.index(start_marker) + len(start_marker)
    return body[a:body.index(end_marker, a)]


colour_def = re.search(r'(// Colour tank scenery.*?\n#endif\n// Colour Air and Land scenes:.*?\n#endif\n)', src, re.S).group(1)

PRE = r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <set>
#include <string>
#include <vector>
#include "examples/companion_radio/LoRaGotchiVersion.h"
#include "examples/companion_radio/LoRaFishSpecies.h"
#include "examples/companion_radio/LoRaFishColour.h"
#include "examples/companion_radio/ui-new/LoRaFishLayout.h"
#include "src/helpers/ui/DisplayDriver.h"
#include "examples/companion_radio/NovaPetLink.h"
#include "examples/companion_radio/ui-new/NovaPetTee.h"
ColorVal UIColor::window_bkg = 0, UIColor::title_bkg = 0, UIColor::title_txt = 1, UIColor::primary_txt = 1,
         UIColor::secondary_txt = 1, UIColor::warning_txt = 1, UIColor::popup_bkg = 0, UIColor::popup_txt = 1, UIColor::corp_blue = 1;
static bool loRaFishColorDisplay=false;
static uint16_t loRaFishSpecies=0;
static uint8_t loRaFishColor=0,loRaFishScaleColor=0,loRaFishEyeColor=0;
static constexpr uint8_t LORAFISH_MONOCHROME_COLOR = 6;
static constexpr uint8_t LORAFISH_MONOCHROME_RENDER_TINT = 7;
struct LoRaFishAppearance { uint8_t scales; uint8_t body; uint8_t eyes; };
static struct { uint8_t evolution=2; } fish;
static struct { uint16_t monoPixelTint=0; bool colorCapable=true; } loragotchiDXGuest;
static bool loragotchiDXReturnedFromMonochrome=false;
static unsigned long loRaFishReturnShakeUntil=0;
static unsigned long tick=0;
static unsigned long millis(){return tick;}
struct UITask{};
#define LORAFISH_SCENERY_CANVAS(d) (d)
static const char* loRaFishDisplayName(){return "x";}
static void loRaFishClock(char* t,size_t,char* d,size_t){t[0]=0;d[0]=0;}
static void drawLoRaFishTankBattery(DisplayDriver&,UITask*,const char*){}

// A screen that keeps the true RGB565 of every pixel (what the real panel would show).
class Rec : public DisplayDriver {
  int cx=0,cy=0,sz=1; uint16_t col=0;
public:
  std::vector<uint16_t> px;
  Rec(int w,int h):DisplayDriver(w,h),px((size_t)w*h,0){}
  bool supportsColor() const override {return true;}
  bool isOn() override {return true;} void turnOn() override {} void turnOff() override {}
  void clear() override {} void endFrame() override {}
  void startFrame(ColorVal b=UIColor::window_bkg) override {std::fill(px.begin(),px.end(),(uint16_t)b);}
  void setTextSize(int s) override {sz=s<1?1:s;} void setColor(ColorVal c) override {col=c;} void setCursor(int x,int y) override {cx=x;cy=y;}
  void fillRect(int x,int y,int w,int h) override {
    for(int j=std::max(0,y);j<std::min(height(),y+h);++j)for(int i=std::max(0,x);i<std::min(width(),x+w);++i)px[(size_t)j*width()+i]=col;}
  void drawRect(int x,int y,int w,int h) override {fillRect(x,y,w,1);fillRect(x,y+h-1,w,1);fillRect(x,y,1,h);fillRect(x+w-1,y,1,h);}
  void drawXbm(int,int,const uint8_t*,int,int) override {}
  uint16_t getTextWidth(const char* s) override {return (uint16_t)(strlen(s)*6);}
  void print(const char* s) override {   // the same 5x7 text the picture copy draws
    const uint8_t* f=NovaPetLink::font5x7();
    for(;*s;++s){unsigned char ch=*s;
      if(ch=='\n'){cx=0;cy+=8*sz;continue;} if(ch=='\r')continue;
      if(cx+6*sz>width()){cx=0;cy+=8*sz;}
      if(ch>=32&&ch<=126){const uint8_t* g=f+(ch-32)*5;
        for(int c=0;c<5;c++)for(int r=0;r<8;r++)if(g[c]&(1<<r))fillRect(cx+c*sz,cy+r*sz,sz,sz);}
      cx+=6*sz;}
  }
};
'''

BODY = colour_def + '\n'
BODY += block('static ColorVal loRaFishColorValue(') + '\n'
BODY += block('static LoRaFishAppearance loRaFishLocalAppearance(') + '\n'
BODY += maybe('static inline void fishPixel(') + maybe('static void fishLine(')
BODY += block('static ColorVal loRaFishJuvenileTint(') + '\n'
for fn in ('static bool drawJuvenileColourSprite(', 'static void maskAdultFishSprite(', 'static void drawAdultFishSprite(', 'static void drawFryFishSprite(',
           'static void drawYoungFishSprite(', 'static void drawElderFishSprite(', 'static void drawFishSpriteForStage(',
           'static void drawFishSprite(', 'static void drawHomeFishSprite(', 'static void drawLoRaFishHeader('):
    BODY += maybe(fn)
BODY += maybe('static void drawCardputerTankDepth(', 'defined(LORAFISH_CARDPUTER_25D) || defined(LORAFISH_COLOUR_TANK)')
BODY += maybe('static void drawTDeckPixelAquarium(', 'defined(LORAFISH_TDECK_PIXEL_ART) || defined(LORAFISH_COLOUR_TANK)')
BODY += maybe('static void drawLoRaFishBubbles(')
BODY += maybe('static void drawLoRaFishColourTank(', 'defined(LORAFISH_COLOUR_TANK)')
BODY += maybe('static bool loRaFishAnimalHome(')
BODY += maybe('static bool loRaFishColourTank(')
BODY += maybe('static void drawLoRaFishNativeScenery(')
BODY += block('static void loRaFishNovaPaletteSeed(NovaPetLink::Link& nova) {') + '\n'   # the definition, not the forward declaration
BODY += block('static void drawLoRaFishSleeping(') + '\n'

MAIN = r'''
struct Spec { const char* name; int w, h; };
struct Theme { const char* name; uint16_t v[9]; };   // bkg, title bkg, title txt, primary, secondary, warning, popup bkg, popup txt, accent
static const Theme themes[] = {
  {"Midnight",{0x0861,0x1193,0xFFFF,0xEF7D,0x9CF3,0xFFE0,0x1082,0xFFFF,0x07FF}},
  {"Paper",   {0xFFFF,0x001F,0xFFFF,0x0000,0x7BEF,0xF800,0xCE79,0x0000,0x041F}},
  {"Lagoon",  {0x0128,0x03B0,0xFFFF,0xDFFF,0x7DDF,0xFEA0,0x032A,0xFFFF,0x4DFF}},
  {"Sunset",  {0x3006,0xA205,0xFFFF,0xFFF1,0xFD20,0xF800,0x5805,0xFFFF,0xF9A6}},
};
// body, scales (fins), eyes alleles: Coral/Tangerine/Gold, Mint/Lagoon/Orchid, two coloured genes, eyes == body
static const uint8_t genes[][3] = {{1,0,2},{4,3,5},{100,8,200},{3,3,3},{3,0,6}};
static std::vector<uint16_t> dedupe(std::vector<uint16_t> v){std::vector<uint16_t> o;for(auto c:v)if(std::find(o.begin(),o.end(),c)==o.end())o.push_back(c);return o;}
static int fails=0;
#define CHECK(cond,...) do{ if(!(cond)){ ++fails; if(fails<=12){printf("FAIL: ");printf(__VA_ARGS__);printf("\n");} } }while(0)

int main(int argc,char** argv){
  const Spec specs[]={SPEC_TABLE};
  const bool tank=TANK_EXPECTED;
  const std::vector<uint16_t> plantsDeep={0x03C8,0x05A8}, plantsFlat={0x04E7,0x05A8};
  long pictures=0, maxOverflow=0; unsigned long long overflowPix=0; std::set<uint16_t> snappedBg;
  for(const Spec& s:specs) for(const Theme& th:themes) for(auto& g:genes) for(int stage=0;stage<4;++stage){
    UIColor::window_bkg=th.v[0];UIColor::title_bkg=th.v[1];UIColor::title_txt=th.v[2];UIColor::primary_txt=th.v[3];
    UIColor::secondary_txt=th.v[4];UIColor::warning_txt=th.v[5];UIColor::popup_bkg=th.v[6];UIColor::popup_txt=th.v[7];UIColor::corp_blue=th.v[8];
    loRaFishColorDisplay=true; loRaFishScaleColor=g[0]; loRaFishColor=g[1]; loRaFishEyeColor=g[2]; fish.evolution=stage;
    // g = {scales, body, eyes}
    const char* tag=s.name;
    NovaPetLink::Link link(NovaPetLink::Format(s.w,s.h,true,false));
    CHECK(link.ok(),"%s: link",tag);
    UITask task;
    std::vector<uint16_t> firstPal;
    for(int k=0;k<2;++k){                                    // two consecutive key pictures, the scene animates in between
      tick=(k==0)?0:3777;
      link.request(1000+k*300);
      loRaFishNovaPaletteSeed(link);
      Rec rec(s.w,s.h);
      { NovaPetTee tee(rec,link,1000+k*300); tee.startFrame(); drawLoRaFishSleeping(tee,&task); tee.endFrame(); }
      while(link.pending()) link.consumed(link.pending());
      link.dropPending();                                    // the next picture is a key picture again
      ++pictures;
      const uint16_t* pal=link.canvas.palette(); const int np=link.canvas.paletteCount();
      std::vector<uint16_t> palv(pal,pal+np);
      if(k==0) firstPal=palv; else CHECK(palv==firstPal,"%s/%s/g%d/s%d: (d) palettes of two key pictures differ",tag,th.name,(int)g[1],stage);
      // the colours that matter, from an independent render of the bare sprite (what the pet draws, nothing else)
      Rec sp(s.w,s.h); sp.startFrame(UIColor::window_bkg); drawHomeFishSprite(sp,s.w/2-5,38+LoRaFishLayout::bodyOffset(s.h),true);
      std::set<uint16_t> petColours; for(auto c:sp.px) if(c!=UIColor::window_bkg) petColours.insert(c);
      std::set<uint16_t> plantColours;
      if(tank){ const auto& pl=(s.h>64)?plantsDeep:plantsFlat; plantColours.insert(pl.begin(),pl.end()); }
      std::set<uint16_t> themeColours={th.v[0],th.v[1],th.v[2],th.v[3],th.v[4],th.v[8]};
      // (b) exact entries; (a) every snapped pixel is a background colour
      unsigned snapped=0, snapPriority=0;
      for(int y=0;y<s.h;y++)for(int x=0;x<s.w;x++){
        const uint8_t b=link.canvas.px[(size_t)y*link.canvas.format().rowBytes()+(x>>1)];
        const uint16_t got=pal[(x&1)?(b&15):(b>>4)], want=rec.px[(size_t)y*s.w+x];
        if(got!=want){ ++snapped; snappedBg.insert(want);
          const bool prio=petColours.count(want)||plantColours.count(want)||themeColours.count(want);
          if(prio){ ++snapPriority; CHECK(false,"%s/%s/g%d/s%d: pixel %d,%d wanted %04X got %04X (a priority colour snapped)",tag,th.name,(int)g[1],stage,x,y,want,got); } }
      }
      CHECK(snapPriority==0,"%s: priority pixels snapped",tag);
      overflowPix+=link.canvas.overflowed(); if((long)link.canvas.overflowed()>maxOverflow)maxOverflow=link.canvas.overflowed();
      if(!tank) CHECK(link.canvas.overflowed()==0 && snapped==0,"%s/%s/g%d/s%d: (a) overflowed()=%u snapped=%u",tag,th.name,(int)g[1],stage,(unsigned)link.canvas.overflowed(),snapped);
      // (c) the order: theme, then the pet (adult stages: body, fins, eyes as the sprite draws them), then plants, then blues
      std::vector<uint16_t> want={th.v[0],th.v[1],th.v[2],th.v[3],th.v[4],th.v[8]};
      if(stage>=2){ want.push_back(LoRaFishColour::rgb565(g[1])); want.push_back(LoRaFishColour::rgb565(g[0]));
        if(g[2]!=6) want.push_back(LoRaFishColour::rgb565(g[2])); }
      std::vector<uint16_t> head=dedupe(want);
      for(size_t i=0;i<head.size()&&i<palv.size();++i){
        if(g[2]==g[1]&&stage>=2&&i>=head.size()-1) break;   // eyes == body: the sprite swaps in an ink colour, checked below
        CHECK(palv[i]==head[i],"%s/%s/g%d/s%d: (c) slot %zu is %04X, expected %04X",tag,th.name,(int)g[1],stage,i,palv[i],head[i]);
      }
      if(tank&&stage>=2&&g[2]!=g[1]&&g[2]!=6){   // plants follow the pet's three colours
        const auto& pl=(s.h>64)?plantsDeep:plantsFlat;
        std::vector<uint16_t> order=dedupe([&]{auto v=head;v.insert(v.end(),pl.begin(),pl.end());return v;}());
        for(size_t i=head.size();i<order.size()&&i<palv.size();++i)
          CHECK(palv[i]==order[i],"%s/%s/g%d/s%d: (c) slot %zu is %04X, expected plant %04X",tag,th.name,(int)g[1],stage,i,palv[i],order[i]);
      }
      for(auto c:petColours){bool f=std::find(palv.begin(),palv.end(),c)!=palv.end(); CHECK(f,"%s/%s/g%d/s%d: (b) pet colour %04X not in the palette",tag,th.name,(int)g[1],stage,c);}
      for(auto c:plantColours){bool f=std::find(palv.begin(),palv.end(),c)!=palv.end(); CHECK(f,"%s/%s/g%d/s%d: (b) plant colour %04X not in the palette",tag,th.name,(int)g[1],stage,c);}
    }
  }
  printf("pictures %ld maxOverflowPixels %ld totalOverflowPixels %llu fails %d\n",pictures,maxOverflow,overflowPix,fails);
  printf("background colours that were snapped (never theme, pet or plant):");for(auto c:snappedBg)printf(" %04X",c);printf("\n");
  (void)argc;(void)argv;
  return fails?1:0;
}
'''

CASES = [
    # name, extra macros, screens (name, w, h), whether the colour tank scenery is drawn
    ('plain-colour-no-scenery', [], [('colour-128x64', 128, 64), ('colour-320x146', 320, 146)], False),
    ('rgb565-128x64', ['-DLORAGOTCHI_RGB565_PANEL=1'], [('st7735-128x64', 128, 64)], True),
    ('rgb565-native', ['-DLORAGOTCHI_RGB565_PANEL=1', '-DLORAGOTCHI_NATIVE_UI=1'],
     [('t190-320x146', 320, 146), ('t114-240x111', 240, 111)], True),
]


def run(case, tmp):
    name, macros, screens, tank = case
    table = ','.join(f'{{"{n}",{w},{h}}}' for n, w, h in screens)
    code = PRE + BODY + MAIN.replace('SPEC_TABLE', table).replace('TANK_EXPECTED', 'true' if tank else 'false')
    cpp = Path(tmp) / f'{name}.cpp'
    cpp.write_text(code)
    exe = Path(tmp) / name
    cc = subprocess.run(['g++', '-std=c++17', '-O1', '-w', '-I', str(ROOT), '-I', str(ROOT / 'src'), '-I', str(ROOT / 'examples/companion_radio'),
                         '-DLORAGOTCHI_DXPRO=0', *macros, str(cpp), '-o', str(exe)], capture_output=True, text=True)
    if cc.returncode:
        print(f'{name}: did not compile\n' + cc.stderr[:4000])
        return False
    p = subprocess.run([str(exe)], capture_output=True, text=True, timeout=300)
    print(f'--- {name}:', p.stdout.strip().replace('\n', '\n    '))
    return p.returncode == 0


def main():
    ok = True
    with tempfile.TemporaryDirectory(prefix='nova-palette-') as tmp:
        for case in CASES:
            ok &= run(case, tmp)
    print('PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


main()
