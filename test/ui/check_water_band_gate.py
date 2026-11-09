#!/usr/bin/env python3
"""Water tank bands only where two adult sprites fit (waterBandsEnabled).

Compiles the production LoRaFishSpecies.h, LoRaFishWaterSprite.h and the exact loRaFishWaterBands /
loRaFishBandY text sliced out of UITask.cpp. A recording display measures the real sprite height.
No panel is involved: this proves rows and the gate, not how the tank looks on a screen.
"""
from pathlib import Path
import subprocess, tempfile, re
ROOT=Path(__file__).resolve().parents[2]
ui=(ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text()
start=ui.index('#if LORAGOTCHI_WATER_EDITION || LORAGOTCHI_DXPRO\n// Bands need room')
helper=ui[start:ui.index('static void drawLoRaFishAquarium(')]

harness=r'''
#define LORAGOTCHI_WATER_EDITION 1
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <algorithm>
#include "examples/companion_radio/LoRaFishSpecies.h"
#include "examples/companion_radio/ui-new/LoRaFishWaterSprite.h"
''' + helper + r'''
using namespace LoRaFishSpecies;
struct Recorder {
  int lo=1<<30, hi=-(1<<30);
  void setColor(int){}
  void fillRect(int,int y,int,int h){ if(h<=0)return; lo=std::min(lo,y); hi=std::max(hi,y+h); }
};
int main() {
  // Threshold: exactly 2 adult sprites + a 4 row gap, for any sprite height.
  assert(bandGapRows==4);
  for(int s:{1,8,15,24,25,32})for(int rows=0;rows<=200;++rows)
    assert(waterBandsEnabled(16,16+rows,s)==(rows>=2*s+4));
  assert(!waterBandsEnabled(16,16+51,24) && waterBandsEnabled(16,16+52,24)); // 24*2+4 = 52
  assert(!waterBandsEnabled(16,67,0) && !waterBandsEnabled(16,67,-24));      // no sprite height, no bands
  assert(!waterBandsEnabled(70,16,24) && !waterBandsEnabled(16,16,24));      // empty or reversed tank
  assert(waterBandsEnabled(100,152,24) && !waterBandsEnabled(100,151,24));   // depends on the span, not the origin

  // Real sprite height: draw every Water species, stage and animation frame; measure the rows used.
  int tallest=0;
  for(uint16_t id=0;id<count;++id){
    if(!waterKnown(id)||!id)continue;           // species 0 (the DX fish) is drawn by the legacy fish path
    for(uint8_t stage=0;stage<4;++stage)for(uint32_t now:{0u,280u})for(bool right:{false,true}){
      Recorder r;LoRaFishWaterSprite::draw(r,100,100,right,id,stage,now,1,2,3,0);
      int rows=r.hi-r.lo;
      assert(rows>0 && rows<=LoRaFishWaterSprite::adultRows);
      if(stage>=2)assert(rows<=24);
      tallest=std::max(tallest,rows);
    }
  }
  assert(tallest==24 && LoRaFishWaterSprite::adultRows==tallest);
  static_assert(sizeof(LoRaFishWaterArt::masks[0][0])*8/2/32==24,"mask is 32x24 at 2 bits per pixel");

  const int heights[]={64,80,82,83,84,100,122,128,135,170,240,320};
  for(int h:heights){
    const bool on=loRaFishWaterBands(h);
#ifdef LORAGOTCHI_NATIVE_UI
    // Native: the real panel height is the tank. Rows = (h-15)-16 = h-31 >= 52  <=>  h >= 83.
    assert(on==(h>=83 && h>64));
    assert(on==waterBandsEnabled(16,h-15,LoRaFishWaterSprite::adultRows));
#else
    // Fixed-row canvases draw inside the 64 px reference frame: 33 rows, never room for two bands.
    assert(!on);
#endif
    for(uint32_t id=0;id<400;++id)for(int y=-60;y<=220;++y){
      const int out=loRaFishBandY((uint16_t)id,y,h);
      if(!on){assert(out==y);continue;}                      // shared tank: the pre-band row, untouched
      const bool floorWalker=waterMotion((uint16_t)id) && id!=Jellyfish;
      if(floorWalker){assert(out==y);continue;}
#ifdef LORAGOTCHI_NATIVE_UI
      assert(out==bandFit((uint16_t)id,BandTall,y,19,41));
      BandRows br=bandRows(band((uint16_t)id),BandTall);
      assert(out>=br.top && out<=br.bottom);
#endif
    }
  }
#ifdef LORAGOTCHI_NATIVE_UI
  assert(!loRaFishWaterBands(64) && !loRaFishWaterBands(82) && loRaFishWaterBands(83));
  assert(loRaFishWaterBands(135) && loRaFishWaterBands(170) && loRaFishWaterBands(240));
#else
  assert(!loRaFishWaterBands(135) && !loRaFishWaterBands(128) && !loRaFishWaterBands(64));
#endif
  return 0;
}
'''
configs=(('native panels',['-DLORAGOTCHI_NATIVE_UI=1']),
         ('64 px / fixed-row canvases',[]),
         ('T-Watch tall tank',['-DLORAFISH_FISH_WANDER','-DLORAFISH_TALL_TANK']))
with tempfile.TemporaryDirectory(prefix='dx-bandgate-') as tmp:
    cpp=Path(tmp)/'gate.cpp';cpp.write_text(harness)
    for n,(name,flags) in enumerate(configs):
        exe=Path(tmp)/f'g{n}'
        subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=undefined','-I',str(ROOT),*flags,str(cpp),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
        print('PASS Water band gate:',name)

# Text: the gate is the first thing the band hook does, uses the real sprite height and tank rules.
body=helper[helper.index('static int loRaFishBandY('):]
assert body.split('{',1)[1].lstrip().startswith('using namespace LoRaFishSpecies;\n  if(!loRaFishWaterBands(h))return y;')
assert 'waterBandsEnabled(16,frame-15,LoRaFishWaterSprite::adultRows)' in helper
assert not re.search(r'waterBandsEnabled\([^)]*\b(24|52)\b',helper)      # no hard-coded height or threshold
assert re.search(r'stage==1\?19:\(unsigned\)adultRows;',(ROOT/'examples/companion_radio/ui-new/LoRaFishWaterSprite.h').read_text())
assert 'waterBandsEnabled' not in ui.replace(helper,'')                   # only the Water hook asks
for name in ('examples/companion_radio/MyMesh.cpp','examples/companion_radio/DataStore.cpp','examples/companion_radio/LoRaFishCommit.h','examples/companion_radio/LoRaFishVisit.h','examples/companion_radio/LoRaFishBreeding.h'):
    p=ROOT/name
    if p.exists():assert 'waterBandsEnabled' not in p.read_text(),name
print('PASS Water band gate hooks: first statement, real sprite height, no wire/save use')
