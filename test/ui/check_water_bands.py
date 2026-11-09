#!/usr/bin/env python3
"""Water tank bands: exact species-to-band table, band rows, bounds for every path.

Compiles the production LoRaFishSpecies.h (band table, fit) and checks the UITask hooks as text.
No panel is involved: this proves rows, not how it looks on a screen.
"""
from pathlib import Path
import subprocess, tempfile, re
ROOT=Path(__file__).resolve().parents[2]
source=r'''
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <initializer_list>
#include "examples/companion_radio/LoRaFishSpecies.h"
#ifdef WITH_LAYOUT
#include "examples/companion_radio/ui-new/LoRaFishLayout.h"
#endif
using namespace LoRaFishSpecies;
static bool isSurface(uint16_t id){return band(id)==Surface;}
int main() {
 // Exact table: 15 Water species plus the three Air-set swimmers; nothing else is listed.
 const uint16_t surface[]={Dolphin,Whale,Seal,Jellyfish,Duck,Swan};
 const uint16_t under[]={TropicalFish,Blowfish,Shark,Shrimp,Squid,Lobster,Crab,Octopus,ShellDweller,SeaStar,Anglerfish,Penguin};
 assert(sizeof(bandTable)/sizeof(bandTable[0])==sizeof(surface)/2+sizeof(under)/2);
 for(uint16_t id:surface)assert(band(id)==Surface);
 for(uint16_t id:under)assert(band(id)==Underwater);
 for(uint16_t id=0;id<count;++id){ // every Water species has an explicit table row
  int rows=0;for(auto&e:bandTable)rows+=e.id==id;assert(rows==1);
 }
 // Unlisted, reserved, Air-other, Land and future IDs use the fish row.
 for(uint32_t id=0;id<65536;++id){
  bool listed=false;for(auto&e:bandTable)listed|=e.id==id;
  if(!listed)assert(band((uint16_t)id)==Underwater);
 }
 // Band rows: fixed boundary, each band on its own side, no overlap, in every layout.
 for(BandLayout l:{BandCompact,BandTall,BandWander}){
  BandRows s=bandRows(Surface,l),u=bandRows(Underwater,l);
  assert(s.top<=s.bottom && u.top<=u.bottom);
  assert(s.bottom<bandBoundary(l) && u.top>=bandBoundary(l));
  assert(s.bottom<u.top);
 }
 assert(bandBoundary(BandCompact)==34 && bandBoundary(BandTall)==30 && bandBoundary(BandWander)==39);
 assert(bandRows(Surface,BandCompact).top==28 && bandRows(Surface,BandCompact).bottom==32);
 assert(bandRows(Underwater,BandCompact).top==36 && bandRows(Underwater,BandCompact).bottom==40);
 assert(bandRows(Surface,BandTall).top==18 && bandRows(Surface,BandTall).bottom==29);
 assert(bandRows(Underwater,BandTall).top==30 && bandRows(Underwater,BandTall).bottom==42);
 // 64 px panel, generic fish path: y=38+int(2*sin). Underwater is the identity (old saves unchanged).
 for(uint32_t t=0;t<200000;t+=7){
  int y=38+(int)(2.0f*sinf(t/650.0f));
  assert(y>=36 && y<=40);
  for(uint16_t id=0;id<count;++id){
   if(waterMotion(id))continue;
   int b=bandFit(id,BandCompact,y,36,40);
   if(isSurface(id)){assert(b>=28 && b<=32);assert(b==y-8);}
   else assert(b==y);
  }
 }
 // 64 px panel, jellyfish bell stroke from the production habitatPosition: stays in the surface band.
 int lo=999,hi=0;
 for(uint8_t stage=0;stage<4;++stage)for(uint32_t t=0;t<80000;t+=11){
  int x=71,y=39;bool r=false;habitatPosition(Jellyfish,stage,128,t,2700,x,y,r);
  int b=bandFit(Jellyfish,BandCompact,y,30,36);
  assert(b>=28 && b<=32);lo=lo<b?lo:b;hi=hi>b?hi:b;
 }
 assert(lo==28 && hi==32);
 // Crab and snail are pinned at row 37 and the band helper leaves them to the floor path (underwater).
 for(uint16_t id:{(uint16_t)Crab,(uint16_t)ShellDweller}){assert(band(id)==Underwater);assert(bandFit(id,BandCompact,37,37,37)==37);}
 // Tall native path: y=30+int(11*sin) over its full range lands in each band, in the y order of the bands.
 for(uint32_t t=0;t<400000;t+=13){
  int y=30+(int)(11.0f*sinf(t/5100.0f));
  assert(y>=19 && y<=41);
  for(uint16_t id:{(uint16_t)Dolphin,(uint16_t)Jellyfish,(uint16_t)Whale,(uint16_t)Seal,(uint16_t)Duck,(uint16_t)Swan}){
   int b=bandFit(id,BandTall,y,19,41);assert(b>=18 && b<=29);}
  for(uint16_t id:{(uint16_t)TropicalFish,(uint16_t)Shark,(uint16_t)Squid,(uint16_t)Anglerfish,(uint16_t)Penguin}){
   int b=bandFit(id,BandTall,y,19,41);assert(b>=30 && b<=42);}
 }
 assert(bandFit(Dolphin,BandTall,19,19,41)==18 && bandFit(Dolphin,BandTall,41,19,41)==29);
 assert(bandFit(Shark,BandTall,19,19,41)==30 && bandFit(Shark,BandTall,41,19,41)==42);
 // T-Watch wander path: rows 29..49.
 for(int y=29;y<=49;++y){
  int s=bandFit(Whale,BandWander,y,29,49),u=bandFit(Octopus,BandWander,y,29,49);
  assert(s>=29 && s<=38 && u>=39 && u<=49);
 }
 // Out-of-range inputs are clamped, never extrapolated.
 assert(bandFit(Dolphin,BandCompact,-1000,36,40)==28 && bandFit(Dolphin,BandCompact,1000,36,40)==32);
 assert(bandFit(Shark,BandCompact,-1000,36,40)==36 && bandFit(Shark,BandCompact,1000,36,40)==40);
#ifdef WITH_LAYOUT
 // After habitatY on real native panels the surface band is above the underwater band.
 for(int h:{135,170,240}){
  int sTop=LoRaFishLayout::habitatY(bandRows(Surface,BandTall).top,h),sBot=LoRaFishLayout::habitatY(bandRows(Surface,BandTall).bottom,h);
  int uTop=LoRaFishLayout::habitatY(bandRows(Underwater,BandTall).top,h),uBot=LoRaFishLayout::habitatY(bandRows(Underwater,BandTall).bottom,h);
  assert(sTop==34 && sTop<sBot && sBot<uTop && uTop<uBot && uBot<=h-26);
  printf("h=%d surface %d..%d underwater %d..%d\n",h,sTop,sBot,uTop,uBot);
 }
#endif
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='dx-bands-') as tmp:
    cpp=Path(tmp)/'bands.cpp';cpp.write_text(source)
    for edition,extra in (('DX',[]),('WATER',[]),('AIR',[]),('LAND',[]),('WATER',['-DWITH_LAYOUT','-DLORAGOTCHI_NATIVE_UI=1','-I'+str(ROOT/'src'),'-Wno-unused-parameter'])):
        exe=Path(tmp)/('b-'+edition+str(len(extra)))
        flags=[] if edition=='DX' else [f'-DLORAGOTCHI_{edition}_EDITION=1']
        subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=undefined','-I',str(ROOT),*flags,*extra,str(cpp),'-o',str(exe)],check=True)
        out=subprocess.run([str(exe)],check=True,capture_output=True,text=True).stdout
        print('PASS Water bands',edition,'native layout' if extra else '');print(out,end='')

# Production hooks (text): Water build only, applied before habitatY for home and visitor.
ui=(ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text()
a=ui.index('#if LORAGOTCHI_WATER_EDITION\n// Bands need room')
helper=ui[a:ui.index('static void drawLoRaFishAquarium(')]
assert 'LORAGOTCHI_AIR_EDITION' not in helper and 'LORAGOTCHI_LAND_EDITION' not in helper and 'ANIMAL' not in helper
assert helper.rstrip().endswith('#endif')
assert 'species!=Jellyfish' in helper and 'waterMotion(species)' in helper  # same floor-walker rule as habitatY
assert not re.search(r'Duck|Swan|Penguin|Dolphin|Shark',helper)  # no species names in the hook: the band is data
home='#if LORAGOTCHI_WATER_EDITION\n  y=loRaFishBandY(loRaFishSpecies,y,h);\n#endif\n  y=LoRaFishLayout::habitatY(y,h,'
guest='#if LORAGOTCHI_WATER_EDITION\n  gy=loRaFishBandY(guestMotionSpecies,gy,h);\n#endif\n  gy=LoRaFishLayout::habitatY(gy,h,'
assert ui.count(home)==1 and ui.count(guest)==1
assert ui.index('habitatPosition(loRaFishSpecies')<ui.index(home)<ui.index('const int foodX=w/2+18;')
assert ui.index('habitatPosition(guestMotionSpecies')<ui.index(guest)
# Save/load path is untouched by the bands: band(...) is never referenced near persistence or the wire.
for name in ('examples/companion_radio/MyMesh.cpp','examples/companion_radio/DataStore.cpp','examples/companion_radio/LoRaFishCommit.h','examples/companion_radio/LoRaFishVisit.h'):
    t=(ROOT/name).read_text();assert 'bandFit' not in t and 'LoRaFishSpecies::band' not in t,name
print('PASS Water band hooks: Water-only, before habitatY, home and visitor, no wire/save use')
