#!/usr/bin/env python3
"""Compile actual reset/load, wire receive and splash bodies for both editions.
RAM mocks only, no physical flash, panel, BLE or RF acceptance.
"""
from pathlib import Path
import subprocess,tempfile
import check_fish_lifecycle as lifecycle
import check_dx_handlers as wire
ROOT=lifecycle.ROOT
state=chr(10).join(lifecycle.parts[:-1])+lifecycle.parts[-1].split('int main() {',1)[0]+r'''
int main() {
 resetAt(5000);resetLoRaFishPet();assert(loRaFishSpecies==LoRaFishSpecies::freshSpecies);
 assert(loRaFishNeedsPetSetup==bool(LORAGOTCHI_SPECIES_EDITION));
 for(unsigned id:{9U,256U,273U,65535U}) {
 loRaFishSpecies=id;loRaFishEggSpecies=id;loRaFishMysterySeed=42;
 loRaFishNeedsPetSetup=true;saveLoRaFishSettings();saveLoRaFish();reboot();
 assert(loRaFishSpecies==id && loRaFishEggSpecies==id && loRaFishMysterySeed==42);
 assert(loRaFishNeedsPetSetup==bool(LORAGOTCHI_SPECIES_EDITION));
 if(LORAGOTCHI_SPECIES_EDITION)assert(loRaFishPage==LORAFISH_PET_SETUP_PAGE);
 }
 puts("PASS reset/load gate, stored Water identity preserved across DX fallback");
}
'''
protocol=wire.pre+wire.structs+wire.globals+wire.receive+wire.methods+r'''
int main() {
 MyMesh m;ContactInfo owner;owner.id.pub_key[0]=9;m.contacts={owner};
 m.receive(owner,"LFG1|REQ|1|2|2|Pet");
 assert((m.sent.back().find("|S1")!=std::string::npos)==bool(LORAGOTCHI_SPECIES_EDITION));
 loragotchiDXHome={};loragotchiDXHome.pending=true;loragotchiDXHome.destinationKnown=true;
 memcpy(loragotchiDXHome.destinationKey,owner.id.pub_key,32);
 loragotchiDXHome.txid=7;loragotchiDXHome.fishid=8;loragotchiDXLocalSpecies=13;
 m.receive(owner,"LFG1|ACK|7|8|S1");
 assert(m.sent.back().find(LORAGOTCHI_SPECIES_EDITION ? "|S1|13" : "|S1|0")!=std::string::npos);
 puts("PASS DX does not advertise S1; negotiated outgoing identity follows edition");
}
'''
source=(ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text()
splash=source[source.index('class SplashScreen'):source.index('class HomeScreen')]
splash=splash[splash.index('  int render('):splash.index('  void poll(')]
splash=splash.replace(' override','')
boot=r'''
#include <cassert>
#include <cstring>
#include <string>
#include <vector>
#include "examples/companion_radio/LoRaGotchiVersion.h"
namespace UIColor { enum {primary_txt,secondary_txt}; }
struct DisplayDriver {
 int scale=1;std::vector<std::string> rows;
 int width(){return 128;}
 void setColor(int){}
 void setTextSize(int n){scale=n;}
 void drawTextCentered(int,int y,const char* text){
  assert(strlen(text)*6*scale<=128 && y+8*scale<=64);rows.push_back(text);
 }
};
'''+splash+r'''
int main() {
 DisplayDriver display;render(display);
 assert(display.rows.at(2)==std::string(LORAGOTCHI_EDITION_NAME)+" "+LORAGOTCHI_PRODUCT_VERSION);
 assert(display.rows.at(2).find("v1.0")==std::string::npos);
 puts(display.rows.at(2).c_str());puts("PASS actual splash product/edition and 128x64 text bounds");
}
'''
with tempfile.TemporaryDirectory(prefix='dx-editions-') as directory:
 p=Path(directory)
 for edition in (0,1,2):
  for name,code in [('wire',protocol),('boot',boot),('state-esp32',state),('state-nrf52',state)]:
   cpp=p/(name+'.cpp');cpp.write_text(code);exe=p/(name+str(edition))
   flags=['-DESP32'] if name=='state-esp32' else ['-DNRF52_PLATFORM'] if name=='state-nrf52' else []
   subprocess.run(['g++','-std=c++17','-I',str(ROOT),'-DLORAGOTCHI_WATER_EDITION='+str(int(edition==1)),'-DLORAGOTCHI_AIR_EDITION='+str(int(edition==2)),*flags,str(cpp),'-o',str(exe)],check=True)
   print('edition',edition,name,flush=True);subprocess.run([str(exe)],check=True)
