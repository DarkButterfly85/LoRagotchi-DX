#!/usr/bin/env python3
"""Compile actual menu functions through native layout regions at target sizes."""
from pathlib import Path
import subprocess,tempfile
import check_menu_navigation as menus
ROOT=menus.root
source=chr(10).join(menus.parts)
source=source[:source.index('int main(')]
source=source.replace('BoundsDisplay():DisplayDriver(128,64){}','BoundsDisplay(int w=128,int h=64):DisplayDriver(w,h){}')
source='#include "examples/companion_radio/ui-new/LoRaFishLayout.h"'+chr(10)+source
source+=r'''
int main() {
 for(auto dims:{std::pair<int,int>{320,170},{320,240},{240,135},{128,64}}) {
  BoundsDisplay output(dims.first,dims.second);
  const int width=std::min(dims.first,224),top=(dims.second-64)/2;
  LoRaFishLayout::Region card(output,(dims.first-width)/2,top,width,64);
  for(bool advancing:{true,false}) {
   output.advancing=advancing;
   for(bool colour:{true,false}) {
    loRaFishColorDisplay=colour;
    for(uint8_t selected=0;selected<4;++selected) {
     loRaFishPetSetupField=selected;loRaFishColorField=selected;loRaFishSoundField=selected;
     loRaFishTimeField=loRaFishTimeoutField=selected%3;
     loRaFishNeedsPetSetup=true;
     output.clearBounds();drawLoRaFishPetSetup(card);
     loRaFishNeedsPetSetup=false;
     for(auto draw:{drawLoRaFishColorMenu,drawLoRaFishTimeMenu,drawLoRaFishTimeoutMenu,
                   drawLoRaFishResetConfirmation,drawLoRaFishAdvertMenu,drawLoRaFishGuessGame}) {
      output.clearBounds();draw(card);assert(!output.printed.empty());
     }
     for(uint8_t option=0;option<loRaFishDisplayOptionCount();++option) {
      loRaFishDisplayOption=option;output.clearBounds();drawLoRaFishDisplayMenu(card);
     }
#ifdef PIN_BUZZER
     output.clearBounds();drawLoRaFishSoundMenu(card);
#endif
    }
   }
  }
 }
 puts("PASS native production menu cards: 320x170, 320x240, 240x135, 128x64; glyph bounds/overlap, mono/colour, all selections, sound and stationary/advancing text");
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'menus.cpp').write_text(source)
 for edition in [[],['-DLORAGOTCHI_WATER_EDITION=1'],['-DLORAGOTCHI_AIR_EDITION=1']]:
  subprocess.run(['g++','-std=c++17','-DPIN_USER_BTN=0','-DPIN_BUZZER=6','-DLORAGOTCHI_NATIVE_UI=1',*edition,'-I'+str(ROOT),'-I'+str(ROOT/'src'),str(p/'menus.cpp'),'-o',str(p/'menus')],check=True)
  subprocess.run([str(p/'menus')],check=True)
