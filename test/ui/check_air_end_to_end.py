#!/usr/bin/env python3
"""One linked executable: actual CFG/DAT -> LFG1 handlers -> production pixels.
Separate translation units retain real globals without replacing state machines.
RAM files and mocked radio/display only. No attached-device claims.
"""
from pathlib import Path
import subprocess,tempfile
import check_fish_lifecycle as state
import check_dx_handlers as mesh
from check_juvenile_rendering import run,ROOT
state_cpp='\n'.join(state.parts[:-1])+state.parts[-1].split('int main() {')[0]+r'''
extern "C" void savedPet(unsigned id,unsigned* out) {
 resetAt(5000);loRaFishSpecies=id;loRaFishEggSpecies=id;
 loRaFishColor=220;loRaFishScaleColor=120;loRaFishEyeColor=6;
 saveLoRaFishSettings();saveLoRaFish();reboot();
 assert(loRaFishSpecies==id && fish.ageMinutes==5000);
 out[0]=loRaFishSpecies;out[1]=fish.evolution;out[2]=loRaFishColor;out[3]=loRaFishScaleColor;out[4]=loRaFishEyeColor;
}
'''
mesh_cpp=mesh.pre.replace('unsigned long millis()', 'static unsigned long millis()')+mesh.structs+mesh.globals+mesh.receive+mesh.methods+r'''
extern "C" void visitPet(const unsigned* input,unsigned* output,unsigned peer) {
 MyMesh m;ContactInfo owner;owner.id.pub_key[0]=9;m.contacts={owner};now=100;
 loragotchiDXHome={};loragotchiDXHome.pending=true;loragotchiDXHome.destinationKnown=true;
 memcpy(loragotchiDXHome.destinationKey,owner.id.pub_key,32);loragotchiDXHome.txid=7;loragotchiDXHome.fishid=8;
 loragotchiDXLocalSpecies=input[0];loragotchiDXLocalColorIndex=input[2];
 loragotchiDXLocalScalesColorIndex=input[3];loragotchiDXLocalEyesColorIndex=input[4];
 loragotchiDXVisit={};m.receive(owner,peer==2?"LFG1|ACK|7|8|S1|A1":peer==1?"LFG1|ACK|7|8|S1":"LFG1|ACK|7|8");
 const std::string first=m.sent.back();now=loragotchiDXVisit.due;m.serviceLoRaFishVisit();assert(m.sent.back()==first);
 loragotchiDXGuest={};loragotchiDXReservation={};loragotchiDXGuestReturn={};loRaFishArrival={};
 char req[80];snprintf(req,sizeof(req),"LFG1|REQ|7|8|%u|Pet",input[1]);m.receive(owner,req);
 m.receive(owner,first.c_str());assert(loragotchiDXGuest.present);
 output[0]=loragotchiDXGuest.species;output[1]=loragotchiDXGuest.stage;
 output[2]=loragotchiDXGuest.color;output[3]=loragotchiDXGuest.scalesColor;output[4]=loragotchiDXGuest.eyesColor;
 assert(output[0]==(peer==2?input[0]:0));
 m.receive(owner,"LFG1|RECALL|7|8");assert(loragotchiDXGuestReturn.status!=LoRaFishGuestReturn::Idle);
}
'''
render_cpp=run((ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text(),'plain',None,False,air=True,source_only=True)
render_cpp=render_cpp.split('int main(')[0]+r'''
extern "C" void savedPet(unsigned,unsigned*);
extern "C" void visitPet(const unsigned*,unsigned*,unsigned);
int main() {
 for(unsigned id=256;id<274;++id)for(unsigned peer=0;peer<3;++peer) {
  unsigned saved[5]={},received[5]={};savedPet(id,saved);visitPet(saved,received,peer);
  for(bool colour:{false,true}) {
   loRaFishColorDisplay=colour;UIColor::window_bkg=0;UIColor::primary_txt=colour?0xffff:1;
   DisplayDriver guest,expected;const LoRaFishAppearance genes={uint8_t(received[3]),uint8_t(received[2]),uint8_t(received[4])};
   drawFishSpriteForStage(guest,32,20,true,received[1],genes,received[0]);
   drawFishSpriteForStage(expected,32,20,true,saved[1],genes,peer==2?id:0);
   assert(guest.pixels==expected.pixels);unsigned pixels=0;
   for(auto pixel:guest.pixels)pixels+=pixel!=0;assert(pixels>15);
  }
 }
 puts("PASS linked production save/reboot -> negotiated Air/Water/legacy retry -> receiver/recall -> mono/colour pixels for all 18 species");
}
'''
with tempfile.TemporaryDirectory(prefix='air-e2e-') as t:
 p=Path(t)
 for name,cpp in [('state',state_cpp),('mesh',mesh_cpp),('render',render_cpp)]:
  (p/(name+'.cpp')).write_text(cpp)
 for platform in ('ESP32','NRF52_PLATFORM'):
  exe=p/platform
  subprocess.run(['g++','-std=c++17','-DLORAGOTCHI_AIR_EDITION=1','-D'+platform,'-I',str(ROOT),
     *[str(p/(n+'.cpp')) for n in ('state','mesh','render')],'-o',str(exe)],check=True)
  subprocess.run([str(exe)],check=True)
