#!/usr/bin/env python3
"""Production scenery/bubbles/native layout raster, with explicit bounded scene.
Not the complete UITask aquarium: sprite/state integration is built separately.
"""
from pathlib import Path
import subprocess,tempfile,sys
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text()
def block(marker):
 a=s.index(marker);i=s.index('{',a);j=i+1;depth=1
 while depth:depth+=(s[j]=='{')-(s[j]=='}');j+=1
 return s[a:j]
code=r'''
#include <vector>
#include <cmath>
#include <cstdio>
#include <cassert>
#include "examples/companion_radio/ui-new/LoRaFishLayout.h"
ColorVal UIColor::primary_txt=0xffff,UIColor::secondary_txt=0x6db6;
static unsigned long tick=0;static unsigned long millis(){return tick;}
struct Memory:DisplayDriver {
 std::vector<uint16_t>pixels;uint16_t color=0;
 Memory(int w,int h):DisplayDriver(w,h),pixels(w*h){}
 bool isOn()override{return true;}void turnOn()override{}void turnOff()override{}void clear()override{}
 void startFrame(ColorVal b)override{std::fill(pixels.begin(),pixels.end(),b);}void endFrame()override{}
 void setTextSize(int)override{}void setColor(ColorVal c)override{color=c;}void setCursor(int,int)override{}void print(const char*)override{}
 uint16_t getTextWidth(const char*s)override{return strlen(s)*6;}
 void fillRect(int x,int y,int w,int h)override{for(int j=std::max(0,y);j<std::min(height(),y+h);++j)for(int i=std::max(0,x);i<std::min(width(),x+w);++i)pixels[j*width()+i]=color;}
 void drawRect(int x,int y,int w,int h)override{fillRect(x,y,w,1);fillRect(x,y+h-1,w,1);fillRect(x,y,1,h);fillRect(x+w-1,y,1,h);}
 void drawXbm(int,int,const uint8_t*,int,int)override{}
};
'''+block('static void drawLoRaFishBubbles(')+block('static void drawLoRaFishNativeScenery(')+r'''
int main(int argc,char** argv){
 for(auto dims:{std::pair<int,int>{320,170},{240,135}}){
  Memory d(dims.first,dims.second);LoRaFishLayout::Region habitat(d,0,24,d.width(),d.height()-24);
  int minY=999,maxY=0;
  for(tick=0;tick<50000;tick+=200){
   d.startFrame(0);drawLoRaFishNativeScenery(habitat);drawLoRaFishBubbles(habitat);
   int y=LoRaFishLayout::habitatY(30+(int)(11*sinf(tick/5100.0f)),habitat.height());
   minY=std::min(minY,y);maxY=std::max(maxY,y);
   for(int row=0;row<24;++row)for(int x=0;x<d.width();++x)assert(d.pixels[row*d.width()+x]==0);
  }
  assert(maxY-minY>(habitat.height()-68)*8/10);
  if(argc>1){char path[512];snprintf(path,sizeof(path),"%s/%dx%d-scenery.ppm",argv[1],d.width(),d.height());FILE*f=fopen(path,"wb");assert(f);fprintf(f,"P6\n%d %d\n255\n",d.width(),d.height());for(auto v:d.pixels){unsigned char rgb[]={(unsigned char)(((v>>11)&31)*255/31),(unsigned char)(((v>>5)&63)*255/63),(unsigned char)((v&31)*255/31)};fwrite(rgb,1,3,f);}fclose(f);}

 }
 puts("PASS production habitat scenery/bubbles: T190/T114, ribbon isolation, full-depth sweep; bounded raster, not complete aquarium simulation");
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'main.cpp').write_text(code)
 for edition in ['DX','WATER','AIR']:
  subprocess.run(['g++','-std=c++17','-DLORAGOTCHI_NATIVE_UI=1','-DLORAGOTCHI_'+edition+'_EDITION=1','-I'+str(ROOT),'-I'+str(ROOT/'src'),str(p/'main.cpp'),'-o',str(p/'check')],check=True)
  args=[]
  if len(sys.argv)>1:
   out=Path(sys.argv[1])/edition;out.mkdir(parents=True,exist_ok=True);args=[str(out)]
  subprocess.run([str(p/'check'),*args],check=True)
