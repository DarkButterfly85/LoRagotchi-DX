#!/usr/bin/env python3
"""Pixel checks of production sprites on a host RGB565 display (not hardware).

Optional --preview-dir emits production-rendered PPM frames; no image library
is needed by CI. Legacy signatures cover adults, OLEDs, Mono/tint and flashes.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]

def block(source, marker):
    start = source.index(marker)
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def run(source, variant, output, verify):
    names = [
        'static ColorVal loRaFishColorValue(',
        'static inline void fishPixel(', 'static void fishLine(',
        'static void maskAdultFishSprite(', 'static void drawAdultFishSprite(',
        'static ColorVal loRaFishJuvenileTint(', 'static bool drawJuvenileColourSprite(',
        'static void drawFryFishSprite(', 'static void drawYoungFishSprite(',
        'static void drawElderFishSprite(', 'static void drawCardputerFishDepth(',
        'static void drawFishSpriteForStage(', 'static bool loRaFishDrawTravelAnimation(',
        'static void drawFishSprite(', 'static void drawHomeFishSprite(',
    ]
    cpp = r'''
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <string>
#include "examples/companion_radio/LoRaFishColour.h"
using ColorVal=uint16_t;
namespace UIColor { ColorVal window_bkg=0,primary_txt=1; }
static bool loRaFishColorDisplay;
static constexpr uint8_t LORAFISH_MONOCHROME_COLOR=6,LORAFISH_MONOCHROME_RENDER_TINT=7;
static struct { ColorVal monoPixelTint=0xBDF7; } loragotchiDXGuest;
static unsigned long tick=10000;
static unsigned long millis(){return tick;}
static unsigned long loRaFishReturnShakeUntil=0;
static bool loragotchiDXReturnedFromMonochrome=false;
static struct { uint8_t evolution=0; } fish;
struct LoRaFishAppearance { uint8_t scales,body,eyes; };
static LoRaFishAppearance home;
static LoRaFishAppearance loRaFishLocalAppearance(){return home;}
struct LoRaFishTravelAnimation {
 bool pending=false,active=false,entering=false;
 uint8_t stage=2;
 LoRaFishAppearance appearance={0,0,0};
 unsigned long started=0;
 int startX=0,endX=0,y=20;
};
static constexpr unsigned long LORAFISH_TRAVEL_ANIMATION_MS=1000;
struct DisplayDriver {
 std::array<ColorVal,64*40> pixels;
 ColorVal color=0;
 DisplayDriver(){pixels.fill(UIColor::window_bkg);}
 void setColor(ColorVal c){color=c;}
 void fillRect(int x,int y,int w,int h){
  for(int yy=std::max(y,0);yy<std::min(y+h,40);++yy)
   for(int xx=std::max(x,0);xx<std::min(x+w,64);++xx)pixels[yy*64+xx]=color;
 }
 ColorVal at(int x,int y)const{return pixels[y*64+x];}
 unsigned long long hash()const {
  unsigned long long h=14695981039346656037ULL;
  for(ColorVal c:pixels)for(unsigned b:{unsigned(c&255),unsigned(c>>8)}){h^=b;h*=1099511628211ULL;}
  return h;
 }
 void ppm(const std::string& file)const {
  FILE* f=fopen(file.c_str(),"wb");assert(f);fprintf(f,"P6\n64 40\n255\n");
  for(ColorVal c:pixels){unsigned char b[]={static_cast<unsigned char>(((c>>11)&31)*255/31),static_cast<unsigned char>(((c>>5)&63)*255/63),static_cast<unsigned char>((c&31)*255/31)};fwrite(b,1,3,f);}fclose(f);
 }
};
'''
    cpp += '\n'.join(block(source, name) for name in names if name in source)
    cpp += r'''
int main(int argc,char** argv){
 const ColorVal backgrounds[]={0x0861,0xFFFF,0x0128,0x3006};
 const ColorVal foregrounds[]={0xEF7D,0x0000,0xDFFF,0xFFF1};
 // First six are representative genetics; last three are preserved paths.
 const LoRaFishAppearance cases[]={{4,0,0},{5,1,1},{4,2,2},{0,3,3},{1,4,4},{3,208,208},{6,6,6},{7,7,7},{3,255,0}};
 for(unsigned mode=0;mode<2;++mode)for(unsigned theme=0;theme<4;++theme){
  loRaFishColorDisplay=mode;
  UIColor::window_bkg=mode?backgrounds[theme]:(theme==1?1:0);
  UIColor::primary_txt=mode?foregrounds[theme]:(theme==1?0:1);
  for(unsigned c=0;c<9;++c)for(unsigned stage=0;stage<4;++stage)for(unsigned right=0;right<2;++right){
   DisplayDriver d;drawFishSpriteForStage(d,32,20,right,stage,cases[c]);
   char key[80];snprintf(key,sizeof(key),"m%u-t%u-c%u-s%u-r%u",mode,theme,c,stage,right);
   if(!mode||c>=6||stage>=2)printf("%s %016llx\n",key,d.hash());
   if(argc>1 && mode && c<6)d.ppm(std::string(argv[1])+"/"+key+".ppm");
   // Real home/travel callers must produce the same sprite at the same position.
   home=cases[c];fish.evolution=stage;DisplayDriver h;drawHomeFishSprite(h,32,20,right);assert(h.pixels==d.pixels);
   if(right){LoRaFishTravelAnimation a;a.active=true;a.stage=stage;a.appearance=cases[c];a.started=tick-500;a.startX=12;a.endX=52;
    DisplayDriver t;assert(loRaFishDrawTravelAnimation(t,a));assert(t.pixels==d.pixels);
    a.started=tick-1000;DisplayDriver end;assert(!loRaFishDrawTravelAnimation(end,a));assert(!a.active);
   }
  }
 }
 // Sample a complete travel cycle and all three Cardputer fin-glint phases.
 // Compare the real animation caller against a body-local sprite at each tick.
 loRaFishColorDisplay=true;UIColor::window_bkg=0x0861;UIColor::primary_txt=0xEF7D;
 for(unsigned stage=0;stage<2;++stage)for(unsigned c=0;c<6;++c){
  for(unsigned elapsed=0;elapsed<1000;elapsed+=25){
   tick=10000+elapsed;
   LoRaFishTravelAnimation a;a.active=true;a.stage=stage;a.appearance=cases[c];
   a.started=10000;a.startX=-20;a.endX=84;
   DisplayDriver actual,expected;
   assert(loRaFishDrawTravelAnimation(actual,a));
   const int x=-20+(int)(104*(elapsed/1000.0f));
   drawFishSpriteForStage(expected,x,20,true,stage,cases[c]);
   assert(actual.pixels==expected.pixels);
   if(argc>1 && c==5 && elapsed%100==0){
    char key[80];snprintf(key,sizeof(key),"motion-s%u-ms%u.ppm",stage,elapsed);
    actual.ppm(std::string(argv[1])+"/"+key);
   }
  }
 }
#ifdef VERIFY_JUVENILE
 loRaFishColorDisplay=true;
 for(unsigned theme=0;theme<4;++theme){
  UIColor::window_bkg=backgrounds[theme];UIColor::primary_txt=foregrounds[theme];
  for(unsigned allele=0;allele<=247;++allele){
   if(!LoRaFishColour::valid(allele)||allele==6)continue;
   for(unsigned stage=0;stage<2;++stage){
    LoRaFishAppearance a={uint8_t(8+(allele+97)%240),uint8_t(allele),uint8_t(allele)};
    DisplayDriver r,l;drawFishSpriteForStage(r,32,20,true,stage,a);drawFishSpriteForStage(l,32,20,false,stage,a);
    assert(r.at(32,20)==loRaFishJuvenileTint(a.body,stage?5:2));
    assert(r.at(32+(stage?-11:-8),20)==loRaFishJuvenileTint(stage?a.scales:a.body,stage?6:5));
    assert(r.at(32+(stage?3:2),19)!=r.at(32,20)); // eye cannot disappear into fill
#ifndef LORAFISH_CARDPUTER_25D
#ifndef LORAFISH_TDECK_PIXEL_ART
    for(int y=0;y<40;++y)for(int x=1;x<64;++x)assert(r.at(x,y)==l.at(64-x,y));
#endif
#endif
    // Eye alleles never add juvenile confetti. Fry ignore scales entirely.
    a.eyes=6;if(!stage)a.scales=6;DisplayDriver other;drawFishSpriteForStage(other,32,20,true,stage,a);assert(other.pixels==r.pixels);
    // Body-local regions cannot crawl with time or world position.
    DisplayDriver moved;drawFishSpriteForStage(moved,35,22,true,stage,a);
    for(int y=6;y<32;++y)for(int x=14;x<49;++x)assert(r.at(x,y)==moved.at(x+3,y+2));
   }
  }
  // Mixed Mono genes remain neutral; don't manufacture colour from Mono 6.
  for(unsigned stage=0;stage<2;++stage){
   DisplayDriver d;drawFishSpriteForStage(d,32,20,true,stage,{0,6,0});assert(d.at(32,20)==UIColor::primary_txt);
  }
 }
#endif
}
'''
    with tempfile.TemporaryDirectory(prefix='dx-juvenile-render-') as tmp:
        path = Path(tmp)
        (path / 'render.cpp').write_text(cpp)
        command = ['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                   '-Wno-unused-function', '-I', str(ROOT), str(path/'render.cpp'), '-o', str(path/'render')]
        if variant != 'plain':
            command.append('-D' + variant)
        if verify:
            command.append('-DVERIFY_JUVENILE')
        subprocess.run(command, check=True)
        if output:
            output.mkdir(parents=True, exist_ok=True)
        result = subprocess.run([str(path/'render')] + ([str(output)] if output else []),
                                check=True, text=True, capture_output=True)
        return dict(line.split() for line in result.stdout.splitlines())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview-dir', type=Path)
    parser.add_argument('--record-baseline-from', type=Path,
                        help='Maintenance only: capture pre-change preserved-path pixel signatures')
    args = parser.parse_args()
    source = (args.record_baseline_from or ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text()
    reference = Path(__file__).with_name('juvenile_legacy_pixels.json')
    results = {}
    for variant in ('plain', 'LORAFISH_TDECK_PIXEL_ART', 'LORAFISH_CARDPUTER_25D'):
        output = args.preview_dir / variant if args.preview_dir else None
        results[variant] = run(source, variant, output, not args.record_baseline_from)
    if args.record_baseline_from:
        reference.write_text(json.dumps(results, indent=2, sort_keys=True)+'\n')
    else:
        expected = json.loads(reference.read_text())
        assert results == expected, 'Preserved adult/elder/OLED/Mono/tint/flash pixels changed'
        print(f'PASS {sum(map(len, results.values()))} legacy pixel signatures; '
              '246 chromatic alleles × 4 themes × 2 juvenile stages × 3 display styles; '
              'mirroring, translated regions, neutral eyes, home/travel callers, '
              '1440 travel frames and travel expiry')


if __name__ == '__main__':
    main()
