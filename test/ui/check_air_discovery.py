#!/usr/bin/env python3
"""Real Air contact picker + exact UTF8 allowlist, no name-to-species guessing."""
import subprocess,tempfile
from pathlib import Path
import check_menu_navigation as f
code='\n'.join(f.parts[:-1])+f.parts[-1].split('int main(){')[0]+r'''
static ContactInfo contact(const char* name,unsigned type=1) {
 ContactInfo c={};snprintf(c.name,sizeof(c.name),"%s",name);c.type=type;return c;
}
int main() {
 UITask task;
 const char* markers[]={"🦅","🐦","🦉","🦆","🦢","🐧","🦜","🦩","🦚","🦃","🐓","🕊️","🦇","🐝","🦋","🪰","🪱","🐛"};
 for(unsigned i=0;i<18;++i) {
  char name[32];snprintf(name,sizeof(name),"Pet %s",markers[i]);
  auto c=contact(name);assert(loRaFishDXEligible(c));
  char ascii[32];LoRaFishText::display(ascii,sizeof(ascii),name,sizeof(name));assert(!strcmp(ascii,"Pet [A]"));
  assert(!loRaFishDXEligible(contact(name,2)) && !loRaFishDXEligible(contact(name,3)));
  the_mesh.useCustom=true;the_mesh.custom={contact("Plain"),c};
  loRaFishPage=0;task._alert_expiry=0;
  for(int n=0;n<4;++n)shortPress(KEY_NEXT);
  assert(loRaFishPage==4);task.handleLongPress(KEY_ENTER);
  assert(loRaFishPage==LORAFISH_DX_CONTACT_PAGE && loRaFishDXContactCount()==1);
  task.display.clearBounds();drawLoRaFishDX(task.display);assert(loRaFishDXContactIndex==1);
 }
 for(const char* bad:{"Eagle","Air","Penguin","Worm","wind 🌬️","cloud ☁️","🦄","🐸","turtle 🐢","\xf0\x9f\xa6"})
  assert(!LoRaFishText::hasFish(bad,strlen(bad)));
 for(unsigned id=0;id<65536;++id) {
  assert(LoRaFishSpecies::waterKnown(id)==(id<14));
  assert(LoRaFishSpecies::airKnown(id)==(id>=256 && id<=273));
  assert(LoRaFishSpecies::known(id)==(id<14 || (id>=256 && id<=273)));
 }
 for(unsigned i=0;i<18;++i) {
  assert(LoRaFishSpecies::selectionId(i)==256+i);
  assert(LoRaFishSpecies::selectionIndex(256+i)==i);
  loRaFishNeedsPetSetup=false;loRaFishPage=12;loRaFishDisplayOption=5;
  task.handleLongPress(KEY_ENTER);for(unsigned n=0;n<18;++n) {
    task.display.clearBounds();drawLoRaFishValuePicker(task.display);shortPress(KEY_NEXT);
  }
  task.handleDoubleClick(KEY_PREV);
 }
 the_mesh.useCustom=false;loragotchiDXHome.away=true;loRaFishPage=4;loragotchiDXAirFallback=true;
 task.display.clearBounds();drawLoRaFishDX(task.display);
 assert(std::find(task.display.printed.begin(),task.display.printed.end(),"FISH FALLBACK")!=task.display.printed.end());
 for(unsigned n=0;n<10000;++n) {
  assert(LoRaFishSpecies::airKnown(LoRaFishSpecies::mystery(n)));
  assert(LoRaFishSpecies::habitatY(LoRaFishSpecies::Penguin,38,n)==37);
  assert(LoRaFishSpecies::habitatY(LoRaFishSpecies::Worm,38,n)==37);
 }
 for(unsigned id=256;id<274;++id)for(unsigned stage=0;stage<4;++stage)
 for(unsigned tick=0;tick<40000;tick+=17) {
  int x=32,y=38;bool right=true;
  LoRaFishSpecies::habitatPosition(id,stage,128,tick,2700,x,y,right);
  assert(x>=20 && x<=108 && y>=29 && y<=37);
 }
 for(unsigned now:{0U,0x7fffffffU,0xffffffffU}) {
  int x=77,y=38;bool right=false;
  LoRaFishSpecies::habitatPosition(0,2,128,now,2700,x,y,right);
  assert(x==77 && y==38 && !right); // old fish path untouched
 }
 puts("PASS 18 exact Air markers through actual picker, malformed/name negatives, 65536 registry boundaries, menu bounds, mystery and ground paths");
}
'''
with tempfile.TemporaryDirectory(prefix='air-discovery-') as t:
 p=Path(t);(p/'test.cpp').write_text(code)
 subprocess.run(['g++','-std=c++17','-DLORAGOTCHI_AIR_EDITION=1','-I',str(f.root),'-I',str(f.root/'src'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
