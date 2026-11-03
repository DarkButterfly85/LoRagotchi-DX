#!/usr/bin/env python3
"""Execute preserved pre-Air Water handlers against actual Air fallback frames.
Old Water ACK's exact S1 grammar is intentionally NOT retroactively changed.
"""
from pathlib import Path
import subprocess,tempfile
import check_dx_handlers as f
preserved='\n#define LoRaFishSpecies PreAirSpecies\n'+(f.root/'test/ui/pre_air_species.inc').read_text()+'\n#undef LoRaFishSpecies\n'
receive=(f.root/'test/ui/pre_air_lfg1_receive.inc').read_text().replace('LoRaFishSpecies::','PreAirSpecies::')
code=f.pre+preserved+f.structs+f.globals+receive+f.methods+r'''
int main() {
 MyMesh m;ContactInfo owner;owner.id.pub_key[0]=9;m.contacts={owner};
 // Old Water -> Air A1 ACK: the old exact capability checker must fall back.
 loragotchiDXHome.pending=true;loragotchiDXHome.destinationKnown=true;
 memcpy(loragotchiDXHome.destinationKey,owner.id.pub_key,32);
 loragotchiDXHome.txid=7;loragotchiDXHome.fishid=8;loragotchiDXLocalSpecies=13;
 m.receive(owner,"LFG1|ACK|7|8|S1|A1");
 const std::string oldToAir=m.sent.back();assert(oldToAir.find("|S1")==std::string::npos);
 assert(!PreAirSpecies::acknowledged("LFG1|ACK|7|8|S1|A1"));
 for(unsigned id=256;id<274;++id) {
  loragotchiDXGuest={};loragotchiDXReservation={};loragotchiDXGuestReturn={};loRaFishArrival={};
  m.receive(owner,"LFG1|REQ|7|8|2|Air");assert(m.sent.back()=="LFG1|ACK|7|8|S1");
  // Use new sender's exact negotiated codec, not a hand-written COMMIT.
  LoRaFishCommitFrame frame;frame.prepare(owner.id.pub_key,7,8,true,220,120,6,944,2,
    LoRaFishSpecies::wireSpecies(id,m.sent.back().c_str()),LoRaFishSpecies::acknowledged(m.sent.back().c_str()));
  m.receive(owner,frame.forVisit(owner.id.pub_key,7,8));
  assert(loragotchiDXGuest.present && loragotchiDXGuest.species==0);
  assert(loragotchiDXGuest.color==220 && loragotchiDXGuest.scalesColor==120);
  m.receive(owner,"LFG1|RECALL|7|8");assert(loragotchiDXGuestReturn.status!=LoRaFishGuestReturn::Idle);
 }
 puts("PASS preserved pre-Air Water production: exact S1 ACK, all Air visitors fish fallback with genes/recall; old Water-to-Air conservatively legacy");
}
'''
with tempfile.TemporaryDirectory(prefix='air-old-water-') as t:
 p=Path(t);(p/'test.cpp').write_text(code)
 subprocess.run(['g++','-std=c++17','-DLORAGOTCHI_WATER_EDITION=1','-I',str(f.root),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
