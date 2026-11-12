#!/usr/bin/env python3
"""Production composition boundary checks; scene dispatch is recorded, not simulated."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text()
start=s.index('static void drawLoRaFishNative(');op=s.index('{',start);end=op+1;depth=1
while depth:
 depth+=(s[end]=='{')-(s[end]=='}');end+=1
ls=s.index('static bool loRaFishListPage(');lop=s.index('{',ls);lend=lop+1;ldepth=1
while ldepth:
 ldepth+=(s[lend]=='{')-(s[lend]=='}');lend+=1
listpage=s[ls:lend]
code=r'''
#include <cassert>
#include <cstdio>
#include <vector>
#include "examples/companion_radio/ui-new/LoRaFishLayout.h"
ColorVal UIColor::primary_txt=1,UIColor::secondary_txt=2;
struct UITask { bool hasConnection(){return true;} };
static bool loRaFishNovaNotice=false,loRaFishChannelNotice=false,loRaFishNameNotice=false,loRaFishMonoDisplayNotice=false,
 loRaFishAdoptionEligible=false,loRaFishNeedsPetSetup=false;
static int loRaFishPage=0,loRaFishGeneration=65535;
enum class LoRaFishSetting{Species,SpeciesSet,Theme};
static constexpr uint8_t LORAFISH_PET_SETUP_PAGE=20,LORAFISH_ADVERT_PAGE=18;
struct {bool active(){return false;} LoRaFishSetting key(){return LoRaFishSetting::Theme;}} loRaFishValuePicker;
struct {uint32_t ageMinutes=0xffffffff,rfEvents=0xffffffff,messages=0xffffffff,txAcks=0xffffffff;int happiness=100;} fish;
static int sceneW,sceneH;
static void drawLoRaFish(DisplayDriver& d,UITask*){sceneW=d.width();sceneH=d.height();}
class Recorder:public DisplayDriver {
 int x=0,y=0,size=1;
 struct Box{int x,y,w,h;}; std::vector<Box> boxes;
public:
 Recorder(int w,int h):DisplayDriver(w,h){}
 bool isOn()override{return true;}void turnOn()override{}void turnOff()override{}
 void clear()override{}void startFrame(ColorVal)override{}void endFrame()override{}
 void setTextSize(int s)override{size=s;}void setColor(ColorVal)override{}
 void setCursor(int a,int b)override{x=a;y=b;}
 uint16_t getTextWidth(const char*s)override{return strlen(s)*6*size;}
 void print(const char*s)override{
  int w=getTextWidth(s),h=8*size;if(!w)return;
  assert(x>=0 && y>=0 && x+w<=width() && y+h<=height());
  for(auto b:boxes)assert(!(x<b.x+b.w && x+w>b.x && y<b.y+b.h && y+h>b.y));
  boxes.push_back({x,y,w,h});x+=w;
 }
 void fillRect(int x,int y,int w,int h)override{assert(x>=0&&y>=0&&x+w<=width()&&y+h<=height());}
 void drawRect(int,int,int,int)override{}void drawXbm(int,int,const uint8_t*,int,int)override{}
};
'''+listpage+chr(10)+s[start:end]+r'''
int main(){
 UITask task;
 for(auto dims:{std::pair<int,int>{320,170},{320,240},{240,135}}){
  Recorder r(dims.first,dims.second);drawLoRaFishNative(r,&task);
  assert(sceneW==dims.first-LoRaFishLayout::sidebarWidth(dims.first) && sceneH==dims.second-24);
  loRaFishPage=8;Recorder m(dims.first,dims.second);drawLoRaFishNative(m,&task);
  assert(sceneW==dims.first && sceneH==dims.second);loRaFishPage=0;
  for(bool* notice:{&loRaFishNovaNotice,&loRaFishChannelNotice,&loRaFishNameNotice,&loRaFishMonoDisplayNotice,
                  &loRaFishAdoptionEligible,&loRaFishNeedsPetSetup}){
   *notice=true;Recorder n(dims.first,dims.second);drawLoRaFishNative(n,&task);
   assert(sceneW==dims.first && sceneH==dims.second);*notice=false;
  }
 }
 puts("PASS production native compositor: full-width habitat/top ribbon, full-area pages, all notice/setup routes, maximum counters no glyph overlap");
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'test.cpp').write_text(code)
 subprocess.run(['g++','-std=c++17','-DLORAGOTCHI_NATIVE_UI=1','-I'+str(ROOT),'-I'+str(ROOT/'src'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
