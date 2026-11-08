#!/usr/bin/env python3
"""Actual DX receive/send/retry code with peer-bound mocked radio.
Also executes preserved pre-Water parser source and its original colour codec.
"""
import subprocess,tempfile
from pathlib import Path
import check_dx_handlers as f
code=f.pre+f.structs+f.globals+f.receive+f.methods+r'''
int main() {
 MyMesh m;ContactInfo owner,impostor;owner.id.pub_key[0]=9;impostor=owner;impostor.id.pub_key[31]=1;
 m.contacts={owner,impostor};
 for(unsigned id=0;id<15;++id) {
   loragotchiDXGuest={};loragotchiDXReservation={};loragotchiDXGuestReturn={};loRaFishArrival={};
   char req[128],commit[128];snprintf(req,sizeof(req),"LFG1|REQ|%u|2|2|Water",id+1);
   snprintf(commit,sizeof(commit),"LFG1|COMMIT|%u|2|C|0|4|6|944|H1|220|120|6|P1|2|S1|%u",id+1,id);
   m.receive(owner,req);assert(m.sent.back().find("|S1")!=std::string::npos);m.receive(impostor,commit);assert(!loragotchiDXGuest.present);
   m.receive(owner,commit);assert(loragotchiDXGuest.present && loragotchiDXGuest.species==id);
   assert(loragotchiDXGuest.color==220 && loragotchiDXGuest.scalesColor==120 && loragotchiDXGuest.monoPanel==2);
   snprintf(commit,sizeof(commit),"LFG1|COMMIT|%u|2",id+1);m.receive(owner,commit);assert(loragotchiDXGuest.species==id);
   snprintf(commit,sizeof(commit),"LFG1|COMMIT|%u|2|C|0|4|6|944|S1|65535",id+1);m.receive(owner,commit);assert(loragotchiDXGuest.species==id);
 }
 puts("PASS all 15 species, full-key binding, composable H1/P1/S1 and short/full duplicates preserve identity");
 for(const char* tail:{"65536","-1","+1","1x","9999999999999999999999","1|S1|2",""}) {
   loragotchiDXGuest={};loragotchiDXReservation={};loragotchiDXGuestReturn={};
   m.receive(owner,"LFG1|REQ|77|2|2|Water");char p[160];snprintf(p,sizeof(p),"LFG1|COMMIT|77|2|C|0|4|6|944|S1|%s",tail);
   auto sent=m.sent.size();m.receive(owner,p);assert(!loragotchiDXGuest.present && loragotchiDXGuest.reserved && m.sent.size()==sent);
 }
 m.receive(owner,"LFG1|COMMIT|77|2|C|0|4|6|944|S1|65535");assert(loragotchiDXGuest.species==0);
 loragotchiDXGuest={};loragotchiDXReservation={};loragotchiDXGuestReturn={};
 m.receive(owner,"LFG1|REQ|78|2|2|Legacy");m.receive(owner,"LFG1|COMMIT|78|2|M|6|6|6|65535");assert(loragotchiDXGuest.species==0);
 puts("PASS malformed/overflow metadata rejected without consuming reservation; unknown wire ID stored as fish; legacy defaults fish");
 loragotchiDXHome={};loragotchiDXHome.pending=true;loragotchiDXHome.destinationKnown=true;
 memcpy(loragotchiDXHome.destinationKey,owner.id.pub_key,32);loragotchiDXHome.txid=7;loragotchiDXHome.fishid=8;
 loragotchiDXLocalSpecies=14;loragotchiDXVisit={};now=100;m.estimate=30000;
 m.receive(owner,"LFG1|ACK|7|8|S1");const std::string first=m.sent.back();assert(first.find("|S1|14")!=std::string::npos);
 // First complete packet is dropped. Deliver the actual retry first to a fresh guest.
 loragotchiDXLocalSpecies=1;loragotchiDXLocalColorIndex=0;
 auto count=m.sent.size();now=loragotchiDXVisit.due-1;m.serviceLoRaFishVisit();assert(m.sent.size()==count);
 now=loragotchiDXVisit.due;m.serviceLoRaFishVisit();assert(m.sent.back()==first);
 loragotchiDXGuest={};loragotchiDXReservation={};loragotchiDXGuestReturn={};
 const std::string retry=m.sent.back();m.receive(owner,"LFG1|REQ|7|8|2|Retry");m.receive(owner,retry.c_str());assert(loragotchiDXGuest.species==14);
 assert(!loRaFishCommitFrame.forVisit(impostor.id.pub_key,7,8));
 puts("PASS lost first COMMIT: production retry preserves frozen species/genes and full identity; deadline unchanged");
}
'''
with tempfile.TemporaryDirectory(prefix='water-wire-') as tmp:
    p=Path(tmp);(p/'test.cpp').write_text(code)
    subprocess.run(['g++','-std=c++17','-DLORAGOTCHI_WATER_EDITION=1','-I',str(f.root),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
legacy_main=r'''
int main() {
 MyMesh m;ContactInfo owner;owner.id.pub_key[0]=9;m.contacts={owner};
 for(unsigned id=0;id<15;++id) {
  loragotchiDXGuest={};loragotchiDXReservation={};loragotchiDXGuestReturn={};loRaFishArrival={};
  LoRaFishCommitFrame frame;frame.prepare(owner.id.pub_key,7,8,true,220,120,6,944,2,id);
  m.receive(owner,"LFG1|REQ|7|8|2|Water visitor");
  m.receive(owner,frame.forVisit(owner.id.pub_key,7,8));
  assert(loragotchiDXGuest.present && loragotchiDXGuest.species==0);
  assert(loragotchiDXGuest.color<=6 && loragotchiDXGuest.scalesColor<=6);
  m.receive(owner,"LFG1|RECALL|7|8");assert(loragotchiDXGuestReturn.status!=LoRaFishGuestReturn::Idle);
 }
 puts("PASS pre-Water f310240 production parser accepts every species as a legacy fish and permits recall");
}
'''
with tempfile.TemporaryDirectory(prefix='water-legacy-') as tmp:
    p=Path(tmp);(p/'test.cpp').write_text(f.pre+f.structs+f.globals+'\n#define LoRaFishColour LegacyLoRaFishColour\n'+(f.root/'test/ui/legacy_lorafish_colour.inc').read_text().replace('#pragma once','')+'\n#undef LoRaFishColour\n'+(f.root/'test/ui/legacy_lfg1_receive.inc').read_text().replace('LoRaFishColour::','LegacyLoRaFishColour::')+f.methods+legacy_main)
    subprocess.run(['g++','-std=c++17','-DLORAGOTCHI_WATER_EDITION=1','-I',str(f.root),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
