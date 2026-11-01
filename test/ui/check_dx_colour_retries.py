#!/usr/bin/env python3
"""Drop first production DX COMMIT, deliver real retry to production RX + Aquarium.

The independent sibling checkouts are read-only inputs. No radio/flash/UI objects
are replaced with reconstructed protocol implementations: only the boundaries
(clock, contacts, RF delivery and flash write) are mocks.
"""
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
fixture=runpy.run_path(str(Path(__file__).with_name('check_dx_handlers.py')))
root=fixture['root']
rx=Path(sys.argv[1] if len(sys.argv)>1 else root.parent/'loragotchi-rx-firmware').resolve()
aquarium=Path(sys.argv[2] if len(sys.argv)>2 else root.parent/'loragotchi-community-tank').resolve()
if not (rx/'examples/companion_radio/LoRagotchiRX.h').exists():raise SystemExit('Production RX checkout required')
if not (aquarium/'tank/protocol.py').exists():raise SystemExit('Aquarium checkout required')
block=fixture['block'];ui=fixture['ui_source']
methods=fixture['methods']
source=fixture['pre']+fixture['structs']+fixture['globals']+fixture['receive']+methods+r'''
#include <fstream>
#include "RX-under-test.h"
MyMesh the_mesh;
struct IO:lrx::IO {
 std::vector<std::string> sent;unsigned writes=0;
 bool save(const lrx::Journal&){++writes;return true;}
 bool send(const uint8_t*,const char* text,uint32_t& ack,uint32_t& timeout){sent.emplace_back(text);ack=1;timeout=10000;return true;}
};
'''+r'''
int main(int argc,char** argv) {
 ContactInfo dest,impostor;dest.id.pub_key[0]=9;impostor=dest;impostor.id.pub_key[31]=1;
 the_mesh.contacts={dest};uint8_t owner[32]={1};
 // First colour packet is lost. All three retries must carry the exact original
 // genes even if local display preferences change after the initial send.
 now=100;loragotchiDXHome.pending=true;loragotchiDXHome.destinationKnown=true;
 memcpy(loragotchiDXHome.destinationKey,dest.id.pub_key,32);
 loragotchiDXHome.txid=7;loragotchiDXHome.fishid=8;
 loragotchiDXLocalHasColorGenes=true;loragotchiDXLocalColorIndex=5;
 loragotchiDXLocalScalesColorIndex=4;loragotchiDXLocalEyesColorIndex=2;
 the_mesh.receive(dest,"LFG1|ACK|7|8");
 const std::string first=the_mesh.sent.back();assert(first=="LFG1|COMMIT|7|8|C|5|4|2|65535");
 assert(loragotchiDXHome.committing && !loragotchiDXHome.pending);
 IO io;lrx::Receiver r(io);r.begin(nullptr,0);r.receive(owner,"LFG1|REQ|7|8|2|Colour Fish",0);
 the_mesh.serviceLoRaFishVisit();now=loragotchiDXVisit.due-1;the_mesh.serviceLoRaFishVisit();assert(the_mesh.sent.size()==1);
 loragotchiDXLocalColorIndex=loragotchiDXLocalScalesColorIndex=loragotchiDXLocalEyesColorIndex=0;
 loragotchiDXLocalHasColorGenes=false;
 for(int i=1;i<=3;++i){
  now=loragotchiDXVisit.due;the_mesh.serviceLoRaFishVisit();assert(the_mesh.sent.size()==size_t(i+1));
  assert(the_mesh.sent.back()==first);r.receive(owner,the_mesh.sent.back().c_str(),now);
  if(i==1) {
    r.tick(now+3999);assert(io.sent.back().find("ARRIVED")!=std::string::npos);
    r.tick(now+4000);assert(io.sent.back()=="LFG1|RETURN|7|8|C|AQUARIUM1");
  }
 }
 assert(r.data.slots[0].body==5 && r.data.slots[0].scales==4 && r.data.slots[0].eyes==2 && r.data.slots[0].appearance);
 assert(r.data.nextId==2); // retries don't create more snapshots or mutate one
 uint8_t data[80];auto len=r.event(r.data.slots[0].id,data);assert(len==77);
 std::ofstream(argv[1],std::ios::binary).write((char*)data,len);
 puts("PASS first packet lost: all three production retries preserve original purple/turquoise/yellow genes");
 now=loragotchiDXVisit.deadline;the_mesh.serviceLoRaFishVisit();assert(the_mesh.sent.size()==4 && loragotchiDXHome.committing && loragotchiDXVisit.phase==LoRaFishVisit::Unconfirmed);
 puts("PASS bounded retry budget and four-second RX hold; duplicates keep one immutable snapshot");

 loragotchiDXHome.committing=true;auto sends=the_mesh.sent.size();
 assert(the_mesh.sendLoRaFishCommit(impostor)==MSG_SEND_FAILED);
 ++loragotchiDXHome.txid;assert(the_mesh.sendLoRaFishCommit(dest)==MSG_SEND_FAILED);--loragotchiDXHome.txid;
 ++loragotchiDXHome.fishid;assert(the_mesh.sendLoRaFishCommit(dest)==MSG_SEND_FAILED);--loragotchiDXHome.fishid;
 loragotchiDXHome.committing=false;assert(the_mesh.sendLoRaFishCommit(dest)==MSG_SEND_FAILED);
 assert(the_mesh.sent.size()==sends);
 puts("PASS cached payload requires active visit, exact transaction/fish and full destination key");

 // Monochrome tint must not be guessed or silently upgraded to a colour fish.
 loragotchiDXHome.committing=false;loragotchiDXVisit.stop();
 loragotchiDXHome.pending=true;loragotchiDXHome.txid=9;loragotchiDXHome.fishid=10;
 loragotchiDXLocalHasColorGenes=false;loragotchiDXLocalColorIndex=6;
 loragotchiDXLocalScalesColorIndex=6;loragotchiDXLocalEyesColorIndex=6;
 the_mesh.receive(dest,"LFG1|ACK|9|10");
 assert(the_mesh.sent.back()=="LFG1|COMMIT|9|10|M|6|6|6|65535");
 r.receive(owner,"LFG1|REQ|9|10|2|Mono Fish",now);r.receive(owner,the_mesh.sent.back().c_str(),now+1);
 assert(r.data.slots[1].mode=='M' && r.data.slots[1].body==6 && r.data.slots[1].tint==65535);
 puts("PASS next visit replaces cache; genuine monochrome appearance remains monochrome");

 LoRaFishCommitFrame frame;assert(!frame.forVisit(dest.id.pub_key,0,0));
 frame.prepare(dest.id.pub_key,UINT32_MAX,UINT32_MAX,true,0,6,5,65535);
 assert(std::string(frame.forVisit(dest.id.pub_key,UINT32_MAX,UINT32_MAX))=="LFG1|COMMIT|4294967295|4294967295|C|0|6|5|65535");
 frame.prepare(dest.id.pub_key,0,0,false,6,6,6,0x03B0);
 assert(std::string(frame.forVisit(dest.id.pub_key,0,0))=="LFG1|COMMIT|0|0|M|6|6|6|944");
 puts("PASS maximum IDs, mixed mono alleles and V4 OLED tint fit complete frame without truncation");

 // No local packet is invented for a retry after a fresh process boot.
 loRaFishCommitFrame=LoRaFishCommitFrame{};sends=the_mesh.sent.size();
 assert(the_mesh.sendLoRaFishCommit(dest)==MSG_SEND_FAILED);assert(the_mesh.sent.size()==sends);
 puts("PASS empty session cache never fabricates an incomplete retry");
}
'''
with tempfile.TemporaryDirectory(prefix='dx-colour-retry-') as directory:
    temp=Path(directory);cpp=temp/'retry.cpp';binary=temp/'retry';event_file=temp/'event.bin'
    # Forward to the unchanged production RX header; avoid a dependency copy.
    (temp/'RX-under-test.h').write_text('#include "'+str(rx/'examples/companion_radio/LoRagotchiRX.h')+'"\n')
    cpp.write_text(source)
    subprocess.run(['g++','-std=c++17','-I',str(root),str(cpp),'-o',str(binary)],check=True)
    subprocess.run([str(binary),str(event_file)],check=True)
    sys.path.insert(0,str(aquarium))
    from tank.protocol import decode_event, encode_event
    from tank.store import Store
    from dataclasses import replace
    event=decode_event('03'+'00'*31,event_file.read_bytes())
    assert (event.body,event.scales,event.eyes,event.mode,event.appearance)==(5,4,2,'C',True)
    assert encode_event(event)==event_file.read_bytes()
    store=Store(temp/'aquarium.sqlite')
    # A new correctly coloured visit repairs the earlier white copy in place.
    store.save(replace(event,event_id=1,appearance=False,mode='M',body=6,scales=6,eyes=6))
    store.save(replace(event,event_id=3,tx_id=9));roster=store.roster()
    assert len(roster)==1 and (roster[0].body,roster[0].scales,roster[0].eyes)==(5,4,2)
    store.close()
    print('PASS actual Aquarium decoder/SQLite receives colours and a new visit replaces the white copy without cloning')
