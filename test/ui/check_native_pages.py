#!/usr/bin/env python3
"""Render actual production pages through native cards, including pairing branches."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text()
def block(marker):
 a=s.index(marker);i=s.index('{',a);j=i+1;depth=1
 while depth:depth+=(s[j]=='{')-(s[j]=='}');j+=1
 return s[a:j]
code=r'''
#ifndef LORAGOTCHI_SPECIES_EDITION
#define LORAGOTCHI_SPECIES_EDITION 0
#endif
#ifndef LORAGOTCHI_AIR_EDITION
#define LORAGOTCHI_AIR_EDITION 0
#endif
#include <cassert>
#include <cstdio>
#include <vector>
#include <string>
#include "examples/companion_radio/ui-new/LoRaFishLayout.h"
using std::min;using std::max;
template<class T>T constrain(T v,T a,T b){return std::max(a,std::min(v,b));}
ColorVal UIColor::primary_txt=1,UIColor::secondary_txt=2;
static unsigned long now=5000;static unsigned long millis(){return now;}
struct UITask {bool connected=false,gps=false;bool hasConnection(){return connected;}bool getGPSState(){return gps;}};
struct {uint32_t pin=0;uint32_t getBLEPin(){return pin;}}the_mesh;
struct {uint32_t ageMinutes=0xffffffff,rfEvents=0xffffffff,messages=0xffffffff,txAcks=0xffffffff;uint8_t happiness=100;}fish;
static uint16_t loRaFishGeneration=65535;
static uint16_t battery=4200;static uint16_t loRaFishDisplayBattery(UITask*){return battery;}
static bool clockValid=true;
static bool loRaFishClock(char*t,size_t tn,char*d,size_t dn){snprintf(t,tn,"23:59");snprintf(d,dn,"2026-11-07");return clockValid;}
static uint32_t lorafish_rf_sample_seq=0,loRaFishRfSeenSeq=0,lorafish_last_rf_ms=0;
static float lorafish_last_rssi=-127,lorafish_last_snr=-20;
static int8_t loRaFishRfHistory[48]={};static uint8_t loRaFishRfHistoryCount=0;
struct LocationProvider{
 bool valid=false;bool isValid(){return valid;}long satellitesCount(){return 99;}
 long getLatitude(){return -90000000;}long getLongitude(){return -180000000;}
}location;
struct {LocationProvider*current=nullptr;LocationProvider*getLocationProvider(){return current;}}sensors;
class Recorder:public DisplayDriver {
 int x=0,y=0,size=1;struct Box{int x,y,w,h;};std::vector<Box>boxes;
public:
 std::vector<std::string>printed;
 Recorder(int w,int h):DisplayDriver(w,h){}
 bool isOn()override{return true;}void turnOn()override{}void turnOff()override{}
 void clear()override{}void startFrame(ColorVal)override{}void endFrame()override{}
 void setTextSize(int s)override{size=s;}void setColor(ColorVal)override{}
 void setCursor(int a,int b)override{x=a;y=b;}uint16_t getTextWidth(const char*s)override{return strlen(s)*6*size;}
 void print(const char*s)override{
  if(!*s)return;int w=getTextWidth(s),h=8*size;
  assert(x>=0&&y>=0&&x+w<=width()&&y+h<=height());
  for(auto b:boxes)if(x<b.x+b.w&&x+w>b.x&&y<b.y+b.h&&y+h>b.y){fprintf(stderr,"overlap %s at %d,%d",s,x,y);abort();}
  boxes.push_back({x,y,w,h});printed.emplace_back(s);x+=w;
 }
 void fillRect(int x,int y,int w,int h)override{assert(x>=0&&y>=0&&x+w<=width()&&y+h<=height());}
 void drawRect(int x,int y,int w,int h)override{fillRect(x,y,w,h);}
 void drawXbm(int,int,const uint8_t*,int,int)override{}
 bool has(const char*s){return std::find(printed.begin(),printed.end(),s)!=printed.end();}
};
'''
for name in ['drawLoRaFishHeader','drawLoRaFishStats','drawLoRaFishClockPage','drawLoRaFishPairing','drawLoRaFishRFMonitor','drawLoRaFishGNSS','drawLoRaFishChannelNotice','drawLoRaFishNameNotice','drawLoRaFishMonoDisplayNotice']:
 code+=block('static void '+name+'(')+chr(10)
code+=r'''
int main(){
 UITask task;
 for(auto dims:{std::pair<int,int>{320,170},{320,240},{240,135}}){
  auto render=[&](auto draw){Recorder out(dims.first,dims.second);LoRaFishLayout::Region card(out,(dims.first-224)/2,(dims.second-64)/2,224,64);draw(card);return out;};
  for(uint32_t pin:{0u,123456u}){
   the_mesh.pin=pin;auto out=render([&](DisplayDriver&d){drawLoRaFishPairing(d);});
   assert(out.has("ENTER: next"));assert(out.has(pin?"123456":"No PIN configured"));
  }
  for(bool connected:{false,true}){
   task.connected=connected;render([&](DisplayDriver&d){drawLoRaFishStats(d,&task);});
   for(bool valid:{false,true}){clockValid=valid;render([&](DisplayDriver&d){drawLoRaFishClockPage(d,&task);});}
  }
  for(uint16_t mv:{uint16_t(0),uint16_t(3300),uint16_t(4200)}){
   battery=mv;for(unsigned age:{0u,1234u}){lorafish_last_rf_ms=age;++lorafish_rf_sample_seq;render([&](DisplayDriver&d){drawLoRaFishRFMonitor(d,&task);});}
  }
  for(bool receiver:{false,true})for(bool enabled:{false,true})for(bool fix:{false,true}){
   sensors.current=receiver?&location:nullptr;task.gps=enabled;location.valid=fix;
   auto out=render([&](DisplayDriver&d){drawLoRaFishGNSS(d,&task);});assert(out.has("LONG:TOGGLE"));
  }
  for(auto draw:{drawLoRaFishChannelNotice,drawLoRaFishNameNotice,drawLoRaFishMonoDisplayNotice}){
   auto out=render(draw);assert(out.has("CLICK TO DISMISS"));
  }
 }
 puts("PASS actual native pairing PIN/no-PIN, stats, clock valid/fallback, RF/battery/history, GNSS all states and notices: glyph bounds/overlap at 320x170/320x240/240x135");
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'test.cpp').write_text(code)
 for flags in [[],['-DLORAGOTCHI_SPECIES_EDITION=1'],['-DLORAGOTCHI_SPECIES_EDITION=1','-DLORAGOTCHI_AIR_EDITION=1']]:
  subprocess.run(['g++','-std=c++17','-DLORAGOTCHI_NATIVE_UI=1',*flags,'-I'+str(ROOT),'-I'+str(ROOT/'src'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
  subprocess.run([str(p/'test')],check=True)
