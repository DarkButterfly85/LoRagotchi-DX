#!/usr/bin/env python3
"""Fault-inject the production DX handlers/service and the sibling RX core.

RF, clock and storage are mocked. No reconstructed sender protocol or UI ticks.
"""
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

fixture = runpy.run_path(str(Path(__file__).with_name('check_dx_handlers.py')))
root = fixture['root']
rx = Path(sys.argv[1] if len(sys.argv) > 1 else root.parent / 'loragotchi-rx-busy-mesh').resolve()
assert (root/'examples/companion_radio/LoRaFishTiming.h').read_bytes() == (rx/'examples/companion_radio/LoRaFishTiming.h').read_bytes()
queue_probe = r"""
class QueueProbe {
 public:
 struct Manager {int pending=0;int getOutboundTotal(){return pending;}} mgr;
 struct Radio {bool receiveMode=true,receiving=false;bool isInRecvMode(){return receiveMode;}bool isReceiving(){return receiving;}} radio;
 Manager* _mgr=&mgr;Radio* _radio=&radio;
 bool loRaFishQueueReady() const;
};
""".replace('\n+', '\n') + fixture['block']('bool MyMesh::loRaFishQueueReady()').replace('MyMesh::','QueueProbe::')
main = r'''
#include "RX-under-test.h"
struct IO:lrx::IO {
 std::vector<std::string> sent;
 bool save(const lrx::Journal&){return true;}
 bool send(const uint8_t*,const char* text,uint32_t& ack,uint32_t& timeout){sent.emplace_back(text);ack=1;timeout=10000;return true;}
};
static void reset(MyMesh& m,ContactInfo peer,uint32_t time=100) {
 now=time;m=MyMesh{};m.contacts={peer};saves=0;
 loragotchiDXHome=LoRaGotchiDXHomeState{};loragotchiDXGuest=LoRaGotchiDXGuestState{};
 loragotchiDXVisit=LoRaFishVisit{};loragotchiDXReservation=LoRaFishReservation{};
 loragotchiDXGuestReturn=LoRaFishGuestReturn{};loRaFishCommitFrame=LoRaFishCommitFrame{};
 loRaFishArrival=LoRaFishArrival{};
 loragotchiDXHome.fishid=8;loragotchiDXHome.txid=7;loragotchiDXHome.destinationKnown=true;
 memcpy(loragotchiDXHome.destinationKey,peer.id.pub_key,32);
 loragotchiDXHome.pending=true;
 m.trackLoRaFishRequest("LFG1|REQ|7|8|2|Fish",m.estimate);
}
int main() {
 QueueProbe queue;assert(queue.loRaFishQueueReady());
 queue.mgr.pending=1;assert(!queue.loRaFishQueueReady());queue.mgr.pending=0;
 queue.radio.receiveMode=false;assert(!queue.loRaFishQueueReady());queue.radio.receiveMode=true;
 queue.radio.receiving=true;assert(!queue.loRaFishQueueReady());
 puts("PASS actual local queue/radio gate refuses queued, transmitting/standby and mid-receive states");
 ContactInfo peer,wrong;peer.id.pub_key[0]=9;wrong=peer;wrong.id.pub_key[31]=1;
 uint8_t owner[32]={1};MyMesh m;
 reset(m,peer);m.receive(peer,"LFG1|ACK|7|8");
 const std::string commit=m.sent.back();const uint32_t deadline=loragotchiDXVisit.deadline;
 // Old three-second retries would have sent three copies during this wait.
 now=10100;m.serviceLoRaFishVisit();assert(m.sent.size()==1);
 m.receive(peer,"LFG1|ACK|7|8");assert(m.sent.size()==1 && loragotchiDXVisit.deadline==deadline);
 now=loragotchiDXVisit.due;m.queueReady=false;m.txPending=true;
 m.serviceLoRaFishVisit();assert(m.sent.size()==1 && loragotchiDXVisit.attempts==1);
 // Later unrelated TX blocks enqueue, but cannot restart the response window.
 m.queueReady=true;m.txPending=false;m.serviceLoRaFishVisit();
 assert(m.sent.size()==2 && m.sent.back()==commit);
 m.estimate=40000;now=loragotchiDXVisit.due;m.serviceLoRaFishVisit();
 assert(loragotchiDXVisit.due-now>=82000);
 now=deadline;m.serviceLoRaFishVisit();
 assert(loragotchiDXVisit.phase==LoRaFishVisit::Unconfirmed && loragotchiDXHome.committing && !loragotchiDXHome.away);
 auto sends=m.sent.size();now+=600000;m.serviceLoRaFishVisit();assert(m.sent.size()==sends);
 m.receive(wrong,"LFG1|ARRIVED|7|8");assert(loragotchiDXHome.committing);
 m.receive(peer,"LFG1|ARRIVED|7|8");assert(loragotchiDXHome.away && !loragotchiDXHome.committing);
 puts("PASS no 3s retry, queued-copy backpressure, updated route estimate, bounded uncertainty, late ARRIVED/full key");

 reset(m,peer);m.random=1234;
 m.receive(peer,"LFG1|ACK|7|8");assert(loragotchiDXVisit.due-now==23234);
 m.contacts.clear();now=loragotchiDXVisit.due;m.serviceLoRaFishVisit();assert(m.sent.size()==1);
 now=loragotchiDXVisit.deadline;m.serviceLoRaFishVisit();assert(loragotchiDXVisit.phase==LoRaFishVisit::Unconfirmed);
 m.contacts={wrong,peer};snprintf(m.contacts[1].name,32,"Renamed host");
 assert(m.recallLoRaFish() && m.sent.back()=="LFG1|RECALL|7|8" && m.destinations.back()==9);
 auto recallDue=loragotchiDXVisit.due;auto recallDeadline=loragotchiDXVisit.deadline;
 sends=m.sent.size();assert(m.recallLoRaFish() && m.sent.size()==sends && loragotchiDXVisit.deadline==recallDeadline);
 m.receive(peer,"LFG1|ARRIVED|7|8");assert(loragotchiDXVisit.phase==LoRaFishVisit::Recall && loragotchiDXHome.away);
 now=recallDue;m.serviceLoRaFishVisit();assert(m.sent.back()=="LFG1|RECALL|7|8");
 m.receive(peer,"LFG1|RETURN|7|8|C|AQUARIUM1");assert(!loragotchiDXHome.away && loragotchiDXHome.completedVisit);
 m.receive(peer,"LFG1|ARRIVED|7|8");assert(!loragotchiDXHome.away && !loragotchiDXVisit.running());
 puts("PASS jitter, deleted/reordered/renamed contact, manual recall cannot reset budget, ARRIVED/RETURN reordering");

 reset(m,peer);m.failure=true;m.receive(peer,"LFG1|ACK|7|8");
 assert(loragotchiDXHome.pending && !loragotchiDXHome.committing && loragotchiDXVisit.attempts==0);
 sends=m.sent.size();now+=9999;m.serviceLoRaFishVisit();assert(m.sent.size()==sends);
 now=loragotchiDXVisit.deadline;m.serviceLoRaFishVisit();
 assert(!loragotchiDXHome.pending && !loragotchiDXHome.committing && loragotchiDXVisit.phase==LoRaFishVisit::NoReply);
 assert(!loragotchiDXHome.completedVisit);
 puts("PASS failed enqueue has bounded pacing but no queued-attempt credit or invented completed visit");

 reset(m,peer);const std::string req=loragotchiDXVisit.request;
 for(unsigned i=0;i<3;++i){now=loragotchiDXVisit.due;m.serviceLoRaFishVisit();assert(m.sent.back()==req);}
 now=loragotchiDXVisit.deadline;m.serviceLoRaFishVisit();
 assert(m.sent.size()==3 && !loragotchiDXHome.pending && loragotchiDXVisit.phase==LoRaFishVisit::NoReply);
 m.receive(peer,"LFG1|ACK|7|8");assert(!loragotchiDXHome.committing && m.sent.size()==3);
 reset(m,peer);now=loragotchiDXVisit.deadline;
 m.receive(peer,"LFG1|ACK|7|8");assert(!loragotchiDXHome.committing && m.sent.empty());
 m.serviceLoRaFishVisit();assert(!loragotchiDXHome.pending);
 puts("PASS lost REQ/acceptance retries same identity and payload, stops without UI, rejects obsolete acceptance");

 reset(m,peer,0xfffffff0UL);m.receive(peer,"LFG1|ACK|7|8");
 now=uint32_t(0xfffffff0UL+21999);m.serviceLoRaFishVisit();assert(m.sent.size()==1);
 ++now;m.serviceLoRaFishVisit();assert(m.sent.size()==2);
 assert(LoRaFishTiming::retryMs(UINT32_MAX,255,UINT32_MAX)==0x7fffffffUL);
 now=loragotchiDXVisit.deadline;m.serviceLoRaFishVisit();assert(loragotchiDXVisit.phase==LoRaFishVisit::Unconfirmed);
 puts("PASS millis wrap and saturated route estimates never overflow into immediate retry");

 reset(m,peer,100);loragotchiDXHome.pending=false;m.receive(peer,"LFG1|REQ|1|2|2|Guest");
 const uint32_t lease=loragotchiDXReservation.due;auto writes=saves;
 now=lease-1;m.receive(peer,"LFG1|REQ|1|2|2|Guest");assert(loragotchiDXReservation.due==lease && saves==writes);
 now=lease;m.serviceLoRaFishVisit();assert(!loragotchiDXGuest.reserved && loragotchiDXReservation.expired);
 m.receive(peer,"LFG1|COMMIT|1|2|C|1|2|3|65535");assert(!loragotchiDXGuest.present && m.sent.back()=="LFG1|RETURN|1|2|M|CANCEL1");
 m.receive(peer,"LFG1|REQ|1|2|2|Guest");assert(!loragotchiDXGuest.reserved);
 m.receive(wrong,"LFG1|REQ|1|2|2|New guest");assert(loragotchiDXGuest.reserved && !loragotchiDXReservation.expired);
 m.receive(peer,"LFG1|COMMIT|1|2");assert(!loragotchiDXGuest.present);
 m.receive(wrong,"LFG1|COMMIT|1|2|C|1|2|3|65535");assert(loragotchiDXGuest.present);
 now+=600000;m.serviceLoRaFishVisit();assert(loragotchiDXGuest.present);
 puts("PASS exact reservation expiry, duplicate REQ cannot extend, cancelled COMMIT cannot revive, actual guest never expires");

 reset(m,peer);m.receive(peer,"LFG1|ACK|7|8");
 m.receive(peer,"LFG1|RETURN|7|8|M|CANCEL1");
 assert(loragotchiDXHome.returned && !loragotchiDXHome.committing && !loragotchiDXHome.completedVisit && !loragotchiDXHome.communityVisit && !loragotchiDXReturnedFromMonochrome);
 puts("PASS cancellation confirmation returns HOME without a visit count, community reward or monochrome colour effect");

 // Lost ACK first; then ACK arrives 110s after RX reserved. The first COMMIT
 // is lost too. The production retry arrives well beyond the old 30s lease.
 reset(m,peer);IO io;lrx::Receiver rx(io);rx.begin(nullptr,now);
 rx.receive(owner,loragotchiDXVisit.request,now);assert(io.sent.back()=="LFG1|ACK|7|8");
 now+=110000;m.receive(peer,io.sent.back().c_str());
 const auto lostCommit=m.sent.back();now=loragotchiDXVisit.due;m.serviceLoRaFishVisit();
 assert(m.sent.back()==lostCommit);rx.receive(owner,m.sent.back().c_str(),now);
 assert(rx.data.slots[0].state==lrx::Captured && io.sent.back()=="LFG1|ARRIVED|7|8");
 // Lose ARRIVED; RX's early return can still finish the visit before render.
 rx.tick(now+4000);assert(io.sent.back()=="LFG1|RETURN|7|8|C|AQUARIUM1");
 m.receive(peer,io.sent.back().c_str());assert(loragotchiDXHome.returned && loragotchiDXHome.completedVisit && loragotchiDXHome.communityVisit);
 m.receive(peer,"LFG1|ARRIVED|7|8");assert(!loragotchiDXHome.away);
 puts("PASS production DX/RX exchange: 110s acceptance delay, lost first COMMIT/ARRIVED, coordinated lease, fast return");

 reset(m,peer);IO expiredIO;lrx::Receiver expiredRX(expiredIO);expiredRX.begin(nullptr,now);
 expiredRX.receive(owner,loragotchiDXVisit.request,now);m.receive(peer,expiredIO.sent.back().c_str());
 now+=lrx::RESERVE_MS;expiredRX.receive(owner,m.sent.back().c_str(),now);
 assert(expiredIO.sent.back()=="LFG1|RETURN|7|8|C|CANCEL1" && !expiredRX.nextEvent());
 m.receive(peer,expiredIO.sent.back().c_str());assert(loragotchiDXHome.returned && !loragotchiDXHome.completedVisit);
 puts("PASS COMMIT delivered after RX lease gets positive cancellation, no captured event and no phantom visit");
}
'''
with tempfile.TemporaryDirectory(prefix='dx-busy-mesh-') as directory:
    temp = Path(directory)
    (temp/'RX-under-test.h').write_text('#include "'+str(rx/'examples/companion_radio/LoRagotchiRX.h')+'"\n')
    cpp = temp/'busy.cpp'
    cpp.write_text(''.join(fixture[key] for key in ('pre', 'structs', 'globals', 'receive', 'methods'))+queue_probe+main)
    exe = temp/'busy'
    subprocess.run(['g++', '-std=c++17', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    '-I', str(root), str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
