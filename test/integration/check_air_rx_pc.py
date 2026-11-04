#!/usr/bin/env python3
"""Optional read-only sibling check: actual Air sender -> current RX -> PC store.
Not a standalone CI gate; pass RX and Aquarium checkouts explicitly.
"""
from pathlib import Path
import sys,subprocess,tempfile
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[2]
if len(sys.argv)!=3:raise SystemExit('Usage: check_air_rx_pc.py RX_CHECKOUT AQUARIUM_CHECKOUT')
rx=Path(sys.argv[1]).resolve();pc=Path(sys.argv[2]).resolve()
sys.path.insert(0,str(ROOT/'test/ui'));import check_dx_handlers as f
sys.path.insert(0,str(pc));from tank.protocol import decode_event
from tank.store import Store
code=f.pre+f.structs+f.globals+f.receive+f.methods+r'''
#include "RX-under-test.h"
#include <fstream>
struct IO:lrx::IO {
 std::vector<std::string> sent;
 bool save(const lrx::Journal& j){return lrx::valid(j);}
 bool send(const uint8_t*,const char* text,uint32_t& ack,uint32_t& timeout){sent.emplace_back(text);ack=1;timeout=10000;return true;}
};
int main(int argc,char** argv) {
 for(unsigned id=256;id<274;++id) {
  MyMesh m;ContactInfo dest;dest.id.pub_key[0]=9;m.contacts={dest};
  uint8_t owner[32]={1};IO io;lrx::Receiver r(io);assert(r.begin(nullptr,0));
  r.receive(owner,"LFG1|REQ|7|8|2|Air",0);assert(!io.sent.empty());
  loragotchiDXHome={};loragotchiDXHome.pending=true;loragotchiDXHome.destinationKnown=true;
  memcpy(loragotchiDXHome.destinationKey,dest.id.pub_key,32);loragotchiDXHome.txid=7;loragotchiDXHome.fishid=8;
  loragotchiDXLocalSpecies=id;loragotchiDXLocalHasColorGenes=true;
  loragotchiDXLocalColorIndex=220;loragotchiDXLocalScalesColorIndex=120;loragotchiDXLocalEyesColorIndex=6;
  loragotchiDXVisit={};now=100;m.estimate=30000;m.receive(dest,io.sent.back().c_str());
  const std::string first=m.sent.back();assert(first.find("|S1|0")!=std::string::npos);
  assert(loragotchiDXAirFallback && first.find("|H1|220|120|6")!=std::string::npos);
  loragotchiDXLocalSpecies=0;loragotchiDXLocalColorIndex=0;now=loragotchiDXVisit.due;
  m.serviceLoRaFishVisit();assert(m.sent.back()==first);r.receive(owner,m.sent.back().c_str(),now);
  assert(r.nextEvent());r.tick(now+4000);assert(r.data.slots[0].attempts==1);
  assert(io.sent.back()=="LFG1|RETURN|7|8|C|AQUARIUM1");
  uint8_t out[84];assert(r.event(r.nextEvent(),out,true)==84);
  std::ofstream(std::string(argv[1])+std::to_string(id),std::ios::binary).write((char*)out,84);
 }
}
'''
with tempfile.TemporaryDirectory(prefix='air-rx-pc-') as t:
 p=Path(t);(p/'RX-under-test.h').write_text('#include "'+str(rx/'examples/companion_radio/LoRagotchiRX.h')+'"\n')
 (p/'test.cpp').write_text(code)
 subprocess.run(['g++','-std=c++17','-DLORAGOTCHI_AIR_EDITION=1','-I',str(ROOT),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test'),str(p/'event-')],check=True)
 store=Store(p/'tank.sqlite')
 for id in range(256,274):
  event=decode_event('03'+'00'*31,(p/('event-'+str(id))).read_bytes())
  assert (event.species_id,event.body_gene,event.scales_gene,event.eyes_gene)==(0,220,120,6)
  store.save(replace(event,event_id=id,tx_id=id))
 assert len(store.roster())==1;store.close()
 print('PASS all 18 Air species: real RX S1-only negotiation -> lost first COMMIT/retry -> 84-byte fish fallback snapshot/return -> PC decoder and one SQLite fish; fine genes retained')
