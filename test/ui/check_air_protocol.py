#!/usr/bin/env python3
"""Actual DX receive/send/retry code with peer-bound mocked radio.
Also executes preserved pre-Water parser source and its original colour codec.
"""
import subprocess,tempfile
from pathlib import Path
import check_dx_handlers as f
code='#include <algorithm>\n'+f.pre+f.structs+f.globals+f.receive+f.methods+r'''
int main() {
 MyMesh m;ContactInfo owner,impostor;owner.id.pub_key[0]=9;impostor=owner;impostor.id.pub_key[31]=1;
 m.contacts={owner,impostor};
 for(unsigned id=256;id<274;++id) {
   loragotchiDXGuest={};loragotchiDXReservation={};loragotchiDXGuestReturn={};loRaFishArrival={};
   char req[128],commit[128];snprintf(req,sizeof(req),"LFG1|REQ|%u|2|2|Water",id+1);
   snprintf(commit,sizeof(commit),"LFG1|COMMIT|%u|2|C|0|4|6|944|H1|220|120|6|P1|2|S1|%u",id+1,id);
   m.receive(owner,req);assert(m.sent.back().find("|S1")!=std::string::npos);m.receive(impostor,commit);assert(!loragotchiDXGuest.present);
   m.receive(owner,commit);assert(loragotchiDXGuest.present && loragotchiDXGuest.species==id);
   assert(loragotchiDXGuest.color==220 && loragotchiDXGuest.scalesColor==120 && loragotchiDXGuest.monoPanel==2);
   snprintf(commit,sizeof(commit),"LFG1|COMMIT|%u|2",id+1);m.receive(owner,commit);assert(loragotchiDXGuest.species==id);
   snprintf(commit,sizeof(commit),"LFG1|COMMIT|%u|2|C|0|4|6|944|S1|65535",id+1);m.receive(owner,commit);assert(loragotchiDXGuest.species==id);
 }
 puts("PASS all 18 Air species, full-key binding, composable H1/P1/S1 and short/full duplicates preserve identity");
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
 loragotchiDXLocalSpecies=273;loragotchiDXVisit={};now=100;m.estimate=30000;
 m.receive(owner,"LFG1|ACK|7|8|S1|A1");const std::string first=m.sent.back();assert(first.find("|S1|273")!=std::string::npos);
 // First complete packet is dropped. Deliver the actual retry first to a fresh guest.
 loragotchiDXLocalSpecies=1;loragotchiDXLocalColorIndex=0;
 auto count=m.sent.size();now=loragotchiDXVisit.due-1;m.serviceLoRaFishVisit();assert(m.sent.size()==count);
 now=loragotchiDXVisit.due;m.serviceLoRaFishVisit();assert(m.sent.back()==first);
 loragotchiDXGuest={};loragotchiDXReservation={};loragotchiDXGuestReturn={};
 const std::string retry=m.sent.back();m.receive(owner,"LFG1|REQ|7|8|2|Retry");m.receive(owner,retry.c_str());assert(loragotchiDXGuest.species==273);
 assert(!loRaFishCommitFrame.forVisit(impostor.id.pub_key,7,8));
 puts("PASS lost first COMMIT: production retry preserves frozen species/genes and full identity; deadline unchanged");
 for(unsigned id=256;id<274;++id)for(const char* suffix:{"","|S1","|S1|A1","|S1|A1|junk","|A1"}) {
   loragotchiDXHome={};loragotchiDXHome.pending=true;loragotchiDXHome.destinationKnown=true;
   memcpy(loragotchiDXHome.destinationKey,owner.id.pub_key,32);
   loragotchiDXHome.txid=7;loragotchiDXHome.fishid=8;loragotchiDXLocalSpecies=id;loragotchiDXVisit={};
   char ack[128];snprintf(ack,sizeof(ack),"LFG1|ACK|7|8%s",suffix);
   auto sent=m.sent.size();m.receive(impostor,ack);assert(m.sent.size()==sent);
   m.receive(owner,ack);std::string payload=m.sent.back();
   uint16_t wireId=65535;bool present=false;assert(LoRaFishSpecies::extension(payload.c_str(),wireId,present));
   const bool air=!strcmp(suffix,"|S1|A1"),s1=!strcmp(suffix,"|S1");
   assert(loragotchiDXAirFallback==!air);
   assert(wireId==(air?id:0) && present==(air||s1));
   if(!air&&!s1)assert(std::count(payload.begin(),payload.end(),'|')==8);
   loragotchiDXLocalSpecies=256;now=loragotchiDXVisit.due;m.serviceLoRaFishVisit();assert(m.sent.back()==payload);
   assert(loRaFishCommitFrame.forVisit(impostor.id.pub_key,7,8)==nullptr);
 }
 puts("PASS every Air ID: exact A1, S1-only fish, strict nine-field legacy/RX, malformed capabilities, spoofing and frozen retry");
 for(const char* ack:{"LFG1|ACK|4294967295|4294967295|S1|A1"})assert(LoRaFishSpecies::airAcknowledged(ack));
 for(const char* ack:{"LFG1|ACK|4294967296|1|S1|A1","LFG1|ACK|1|99999999999999999999|S1|A1",
    "LFG1|ACK|1|2|S1|A1|", "LFG1|ACK|+1|2|S1|A1","LFG1|ACK|1|2|A1"})
   assert(!LoRaFishSpecies::airAcknowledged(ack));
 assert(LoRaFishSpecies::wireSpecies(65535,"LFG1|ACK|1|2|S1")==65535);

}
'''
with tempfile.TemporaryDirectory(prefix='water-wire-') as tmp:
    p=Path(tmp);(p/'test.cpp').write_text(code)
    subprocess.run(['g++','-std=c++17','-DLORAGOTCHI_AIR_EDITION=1','-I',str(f.root),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
