#!/usr/bin/env python3
"""Compact menu layout: python3 test/ui/check_menu_compact.py

Menus take their row pitch from the driver (font height plus a pixel) and show as many rows as fit between the
header rule and the hint line, instead of a fixed 4 rows at a fixed gap. Three layers are checked:

 1. The layout rules (LoRaFishMenuLayout, pure integers) for every display geometry the firmware drives:
    visible rows = floor(usable height / pitch), the selected row always inside the window for every list length,
    pitch <= font height + 2, rows never run into the hint line, and the 128x64 reference keeps its old rows.
 2. The production Options and Display menu drawers (the real functions, extracted from UITask.cpp) drawn on a
    mock panel of each size: rows printed, their spacing, the marker, the order, nothing out of bounds/overlapping.
 3. Source guards: no list menu still carries a hard-coded 4/6 row count or a fixed 9/11/12 px row step.

It cannot see a real screen. It proves the geometry the firmware asks the driver for, not how a panel renders it.
"""
from pathlib import Path
import re,subprocess,tempfile
import check_menu_navigation as menus
ROOT=menus.root
SOURCE=menus.source

# (name, width, height, pitch in UI units, font px height, UI-unit-to-pixel scale, expected rows, expected hint y)
# Expected rows are written out by hand: floor((hint_y - 18) / pitch).
GEOMETRIES=[
 ('128x64 OLED (Heltec V3/V4)',128,64,9,8,1.0,4,56),
 ('170x320 portrait TFT',170,320,9,8,1.0,32,312),
 ('320x170 T190 landscape',320,170,9,8,1.0,16,162),
 ('240x135 Cardputer / T114',240,135,9,8,1.0,12,127),
 ('240x320 ST7789',240,320,9,8,1.0,32,312),
 ('T-Deck / V4 TFT 320x240 native',320,240,9,8,1.0,23,232),
 ('160x80 T096 / Wireless Tracker native',160,80,9,8,1.0,6,72),
 ('220x128 RC32 NV3001B native',220,128,9,8,1.0,11,120),
 ('320x240 ThinkNode M9 ST7789Display (10 pt Arial, 12 px pitch)',320,240,12,10,1.0,17,229),
]

LAYOUT_TEST=r'''
#include <cassert>
#include <cstdio>
#include "examples/companion_radio/ui-new/LoRaFishMenu.h"
namespace L=LoRaFishMenuLayout;
struct G{const char* name;int w,h,pitch,font;double scale;int rows,hint;};
int main(){
 const G g[]={@@GEOMETRIES@@};
 for(const G& d:g){
  // visible rows = floor(usable / pitch), computed here independently of the header's expression
  const int usable=d.hint-18;
  assert(L::hintY(d.h,d.pitch)==d.hint);
  assert(L::rows(d.h,d.pitch)==usable/d.pitch);
  assert(L::rows(d.h,d.pitch)==d.rows);
  // The last row ends above the hint line; the row after it would not.
  assert(L::kTop+L::rows(d.h,d.pitch)*d.pitch<=d.hint);
  assert(L::kTop+(L::rows(d.h,d.pitch)+1)*d.pitch>d.hint);
  // Pitch is tight: at least one pixel of clearance, at most font+2 on 1:1 panels. A scaled grid cannot hit a
  // fraction of a unit, so it may exceed that by less than one unit of its scale.
  const double pitchPx=d.pitch*d.scale;
  assert(pitchPx>=d.font+1-1e-9);
  assert(d.scale==1.0 ? d.pitch<=d.font+2 : pitchPx<d.font+2+d.scale);
  // Every list length and every selection: selected row inside [first, first+visible), window inside the list.
  for(int visible=1;visible<=40;++visible)for(int count=1;count<=60;++count)for(int sel=0;sel<count;++sel){
   const int f=L::first(sel,count,visible);
   assert(f>=0 && sel>=f && sel<f+visible);
   assert(count<=visible ? f==0 : f+visible<=count);
  }
  // Scrolling is monotone as the selection moves down (no flicker) and matches the old rule (selection on the
  // last row until the end of the list) for the old 4-row window.
  for(int count=1;count<=12;++count){int prev=0;for(int sel=0;sel<count;++sel){
   const int f=L::first(sel,count,d.rows);assert(f>=prev);prev=f;}}
  const int visible=L::rows(d.h,d.pitch);
  for(int row=0;row<visible;++row){const int y=L::rowY(d.h,d.pitch,row);assert(y>=L::kTop && y+d.pitch<=d.hint+d.pitch);}
  printf("  %-34s pitch %d  rows %d  hint y %d\n",d.name,d.pitch,visible,d.hint);
 }
 // The old rule, exactly: 4 rows, selection on the last row.
 for(int count=1;count<=12;++count)for(int sel=0;sel<count;++sel){
  const int old=count<=4?0:(sel>3?sel-3:0);
  assert(L::first(sel,count,4)==old);
 }
 // The 128x64 reference keeps every historic row so existing small-display layouts do not move.
 for(int row=0;row<4;++row){
  assert(L::rowY(64,9,row)==18+row*9);
  assert(L::rowY(64,9,row,22,11)==22+row*11);
  assert(L::rowY(64,9,row,22,12)==22+row*12);
  assert(L::rowY(64,9,row,18,11)==18+row*11);
 }
 // Tall panels pack at the driver pitch no matter what legacy spacing a menu asked for.
 for(int row=0;row<8;++row){assert(L::rowY(170,9,row,22,12)==18+row*9);assert(L::rowY(320,9,row,22,11)==18+row*9);}
 // Degenerate input never yields zero rows or a negative window start.
 assert(L::rows(64,0)==1 && L::rows(64,100)==1 && L::first(0,0,4)==0);
 // Cardputer size-2 options page: 17 px rows from y=22 with no hint line fill 135 px with 6 rows.
 assert(L::rows(135,17,22,false)==6);
 puts("PASS menu layout rules");
}
'''

DRAW_TEST=r'''
int main(){
 struct Case{int w,h,pitch,rows,glyph;};
 const Case cases[]={@@CASES@@};
 UITask task;
 for(const Case& c:cases){
  BoundsDisplay panel(c.w,c.h,c.pitch,c.glyph);
  // Option menu: every optional row present so the list is as long as it ever gets.
  canBreed=true;loragotchiDXGuest.present=true;
  const int count=loRaFishOptionCount();
  assert(count>=9);
  const int visible=LoRaFishMenuLayout::rowsFor(panel);
  assert(visible==c.rows);
  for(int sel=0;sel<count;++sel){
   loRaFishOption=LoRaFishOptions::at(sel,loRaFishHasSound,true,true);
   panel.clearBounds();drawLoRaFishOptions(panel,nullptr);
   int rows=0,marked=0,markedAt=-1,lastY=-1;std::vector<int> rowYs;std::vector<std::string> labels;
   for(size_t i=0;i<panel.printed.size();++i){
    const std::string& s=panel.printed[i];
    if(s.size()>2 && (s[0]=='>'||s[0]==' ') && s[1]==' '){
     labels.push_back(s.substr(2));rowYs.push_back(panel.ys[i]);
     if(s[0]=='>'){++marked;markedAt=rows;}
     ++rows;
    }
   }
   const int shown=std::min(count,visible);
   assert(rows==shown);                 // as many rows as fit, never more than the list has
   assert(marked==1);                   // exactly one selection marker, and it is visible
   assert(labels[markedAt]==loRaFishOptionLabel(loRaFishOption));
   for(size_t i=0;i<rowYs.size();++i){
    assert(rowYs[i]==LoRaFishMenuLayout::rowYFor(panel,(int)i));          // one shared row formula
    if(i)assert(rowYs[i]-rowYs[i-1]==c.pitch);                           // tight, constant pitch
   }
   // Order is the list order, contiguous, ending at or after the selection.
   const int firstShown=LoRaFishMenuLayout::first(sel,count,visible);
   for(size_t i=0;i<labels.size();++i)
    assert(labels[i]==loRaFishOptionLabel(LoRaFishOptions::at(firstShown+(int)i,loRaFishHasSound,true,true)));
   // Hint sits on the bottom edge line and below the last row.
   assert(panel.printed.back().find("NEXT")!=std::string::npos || panel.printed.back().find("OK")!=std::string::npos);
   assert(panel.ys.back()==LoRaFishMenuLayout::hintY(c.h,c.pitch));
   assert(rowYs.back()+c.glyph<=panel.ys.back());
  }
  // Display menu: same rules, its own list.
  loRaFishPartialSupported=true;loRaFishOrientationSupported=true;
  const int dcount=loRaFishDisplayOptionCount();
  for(int colour=0;colour<2;++colour){
   loRaFishColorDisplay=colour;
   for(int sel=0;sel<dcount;++sel){
    loRaFishDisplayOption=sel;panel.clearBounds();drawLoRaFishDisplayMenu(panel);
    int rows=0,marked=0;
    for(const std::string& s:panel.printed){
     if(s==">"||s=="DISPLAY")continue;
    }
    for(size_t i=0;i<panel.printed.size();++i){
     if(panel.printed[i]==">"){++marked;assert(panel.ys[i]>=18 && panel.ys[i]<LoRaFishMenuLayout::hintY(c.h,c.pitch));}
     if(panel.ys[i]>=18 && panel.ys[i]<LoRaFishMenuLayout::hintY(c.h,c.pitch) && panel.printed[i]!=">")++rows;
    }
    assert(rows==std::min(dcount,visible));
    assert(marked==1);
   }
  }
  // Fixed-length menus pack at the same pitch from the same top row on a tall panel.
  if(c.h>64){
   loRaFishColorDisplay=true;loRaFishNeedsAppearanceSetup=false;loRaFishNeedsPetSetup=false;
   panel.clearBounds();drawLoRaFishTimeMenu(panel);
   std::vector<int> ys;for(size_t i=0;i<panel.printed.size();++i)if(panel.printed[i]=="Sleep"||panel.printed[i]=="Wake"||panel.printed[i]=="Offset")ys.push_back(panel.ys[i]);
   assert(ys.size()==3 && ys[0]==18 && ys[1]-ys[0]==c.pitch && ys[2]-ys[1]==c.pitch);
  }
 }
 puts("PASS production Options/Display drawers on every panel size");
#if LORAGOTCHI_DXPRO
 // DX-Pro set picker and species list: the same compact rows, the draft candidate always on screen.
 for(const Case& c:cases){
  BoundsDisplay panel(c.w,c.h,c.pitch,c.glyph);
  const int visible=LoRaFishMenuLayout::rowsFor(panel);
  for(int step=0;step<2;++step){
   const bool sets=(step==0);
   loRaFishProSet=2; // Land: 39 animals, the longest list
   const int count=sets?LoRaFishSpecies::setCount+1:LoRaFishSpecies::setSize(2)+1;   // + Mystery egg: last of the environments, first of an environment's animals
   for(int cand=0;cand<count;++cand){
    loRaFishValuePicker.open(sets?LoRaFishSetting::SpeciesSet:LoRaFishSetting::Species,cand,count);
    panel.clearBounds();drawLoRaFishValuePicker(panel);
    std::vector<std::string> labels;std::vector<int> rowYs;int marked=0,markedAt=-1;
    for(size_t i=0;i<panel.printed.size();++i){
     const std::string& t=panel.printed[i];
     if(t.size()>2 && (t[0]=='>'||t[0]==' ') && t[1]==' '){
      if(t[0]=='>'){++marked;markedAt=(int)labels.size();}
      labels.push_back(t.substr(2));rowYs.push_back(panel.ys[i]);
     }
    }
    assert((int)labels.size()==std::min(count,visible));
    assert(marked==1);
    const int f=LoRaFishMenuLayout::first(cand,count,visible);
    assert(markedAt==cand-f);
    for(size_t i=0;i<labels.size();++i){
     const int item=f+(int)i;
     const std::string want=sets?(item>=LoRaFishSpecies::setCount?std::string("Mystery egg"):std::string(LoRaFishSpecies::setLabel(item))):(item==0?std::string("Mystery egg"):std::string(LoRaFishSpecies::label(LoRaFishSpecies::setSelectionId(2,item-1))));
     assert(labels[i]==want);                         // every item in order, none skipped or reordered
     assert(rowYs[i]==LoRaFishMenuLayout::rowYFor(panel,(int)i));
     if(i)assert(rowYs[i]-rowYs[i-1]==c.pitch);
    }
   }
  }
  loRaFishValuePicker.cancel();
 }
 puts("PASS DX-Pro set picker and species list use the compact rows, candidate always visible");
#endif
}
'''

def build_draw_source():
    src=chr(10).join(menus.parts)
    src=src[:src.index('int main(')]
    src=src.replace('BoundsDisplay():DisplayDriver(128,64){}',
        'int pitch=9,glyph=8;std::vector<int> ys;BoundsDisplay(int w=128,int h=64,int p=9,int g=8):DisplayDriver(w,h),pitch(p),glyph(g){}'
        ' int menuRowPitch() const override {return pitch;}')
    src=src.replace('int w=getTextWidth(t),h=8*size;','int w=getTextWidth(t),h=glyph*size;')
    src=src.replace('void clearBounds(){boxes.clear();printed.clear();','void clearBounds(){boxes.clear();printed.clear();ys.clear();')
    src=src.replace('printed.emplace_back(t);','printed.emplace_back(t);ys.push_back(y);')
    src=src.replace('#define LORAFISH_UI 1','#define LORAFISH_UI 1\nstatic uint8_t loRaFishProSet=0;',1)
    assert 'h=glyph*size' in src and 'ys.push_back(y)' in src and 'menuRowPitch' in src and 'ys.clear()' in src
    cases=','.join('{%d,%d,%d,%d,%d}'%(w,h,p,rows,int(f/sc)) for _,w,h,p,f,sc,rows,_ in GEOMETRIES)
    return src+DRAW_TEST.replace('@@CASES@@',cases)

def sources_guards():
    # Menu drawers no longer carry fixed row counts or fixed row steps.
    for name in ['static void drawLoRaFishOptions(','static void drawLoRaFishDisplayMenu(','static void drawLoRaFishWatchOptions(']:
        body=menus.block(name)
        assert not re.search(r'row\s*<\s*[46]\s*&&',body),name+' still hard-codes its row count'
        assert 'rowsFor(display)' in body or 'rows(display.height()' in body,name+' must derive its rows from the display'
        assert 'LoRaFishMenuLayout::first(' in body,name+' must use the shared scroll rule'
        assert not re.search(r'selected\s*>\s*[35]|DisplayOption\s*>\s*3',body),name+' still has the old fixed scroll window'
    for name in ['static void drawLoRaFishDisplayMenu(','static void drawLoRaFishPetSetup(','static void drawLoRaFishColorMenu(',
                 'static void drawLoRaFishTimeMenu(','static void drawLoRaFishTimeoutMenu(','static void drawLoRaFishSoundMenu(',
                 'static void drawLoRaFishAdvertMenu(']:
        body=menus.block(name)
        assert not re.search(r'\b1[0-9]\s*\+\s*(row|i)\s*\*\s*\d+|\b2[0-9]\s*\+\s*(row|i)\s*\*\s*\d+',body),name+' still uses a fixed row step'
        assert 'drawLoRaFishMenuHint(display, true)' in body,name+' hint must sit on the bottom edge'
    picker=menus.block('static void drawLoRaFishValuePicker(')
    assert 'SpeciesSet' in picker and 'rowsFor(display)' in picker,'DX-Pro set/species pickers must use the compact list'
    # Native panels draw list menus through the identity region, not the stretched 64 px page.
    assert 'loRaFishListPage()' in SOURCE and 'LoRaFishLayout::Region flow(display,0,0,w,h)' in SOURCE
    print('PASS source guards: no fixed row counts/steps in list menus; DX-Pro pickers and native flow use the shared layout')

def driver_pitch_check():
    """Every ST7789 LCD board is native 1:1 now, so the driver keeps the default 9 px row pitch (8 px glyph + 1)."""
    cpp=(ROOT/'src/helpers/ui/ST7789LCDDisplay.cpp').read_text()
    hdr=(ROOT/'src/helpers/ui/ST7789LCDDisplay.h').read_text()
    assert 'DISPLAY_SCALE' not in cpp and 'DISPLAY_SCALE' not in hdr, 'the LCD driver must not scale'
    assert 'menuRowPitch' not in cpp and 'menuRowPitch' not in hdr, 'native LCD panels use the default 9 px pitch'
    base=(ROOT/'src/helpers/ui/DisplayDriver.h').read_text()
    assert 'virtual int menuRowPitch() const { return 9; }' in base
    # The mono Arial driver draws a 13 px box for size-1 text, so it declares a taller pitch (see GEOMETRIES).
    assert 'int menuRowPitch() const override { return 12; }' in (ROOT/'src/helpers/ui/ST7789Display.h').read_text()
    print('PASS ST7789LCD pitch: native 1:1 on every board -> default 9 rows; ST7789Display (10 pt Arial) -> 12')

def run(cmd,**k): subprocess.run(cmd,check=True,**k)

if __name__=='__main__':
    sources_guards()
    driver_pitch_check()
    with tempfile.TemporaryDirectory() as t:
        p=Path(t)
        geoms=','.join('{"%s",%d,%d,%d,%d,%g,%d,%d}'%(n,w,h,pt,f,s,r,hy) for n,w,h,pt,f,s,r,hy in GEOMETRIES)
        (p/'layout.cpp').write_text(LAYOUT_TEST.replace('@@GEOMETRIES@@',geoms))
        run(['g++','-std=c++17','-I'+str(ROOT),str(p/'layout.cpp'),'-o',str(p/'layout')])
        run([str(p/'layout')])
        (p/'draw.cpp').write_text(build_draw_source())
        for sound in [False,True]:
          for pro in [False,True]:
            cmd=['g++','-std=c++17','-w','-DPIN_USER_BTN=0','-DLORAGOTCHI_TESTER_FIRMWARE=1','-I'+str(ROOT),'-I'+str(ROOT/'src'),str(p/'draw.cpp'),'-o',str(p/'draw')]
            if sound: cmd.append('-DPIN_BUZZER=6')
            if pro: cmd.append('-DLORAGOTCHI_DXPRO=1')
            run(cmd);run([str(p/'draw')])
