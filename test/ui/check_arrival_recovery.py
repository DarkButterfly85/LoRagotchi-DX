#!/usr/bin/env python3
"""Fault-inject production DX handlers, queue gates, ACK dispatch and schedulers.

No RF or physical display claim: only radio/clock/contact/storage boundaries are
mocked. The two-endpoint trace swaps the real session globals between endpoints.
"""
from pathlib import Path
import runpy
import subprocess
import tempfile

f = runpy.run_path(str(Path(__file__).with_name('check_dx_handlers.py')))
root = f['root']
globals_ = f['globals'].replace(
    'bool queueReady=true,txPending=false;uint32_t random=0;\n'
    ' bool loRaFishQueueReady() const{return queueReady;}\n'
    ' bool loRaFishTxPending() const{return txPending;}',
    '''uint32_t random=0;
 struct Manager {int pending=0;int getOutboundTotal(){return pending;}} mgr;
 struct Radio {bool receiveMode=true,receiving=false;bool isInRecvMode(){return receiveMode;}bool isReceiving(){return receiving;}} radio;
 Manager* _mgr=&mgr;Radio* _radio=&radio;
 bool loRaFishQueueReady() const;
 bool loRaFishTxPending() const;
 ContactInfo* receiveTransportAck(uint32_t);''')
assert globals_ != f['globals']
ack = f['block']('ContactInfo*  MyMesh::processAck(')
ack = ack[ack.index('#ifdef LORAFISH_UI')+len('#ifdef LORAFISH_UI'):ack.index('#endif')]
methods = f['methods'] + '\n' + '\n'.join(f['block'](name) for name in (
    'bool MyMesh::loRaFishQueueReady()', 'bool MyMesh::loRaFishTxPending()'))
methods += '\nContactInfo* MyMesh::receiveTransportAck(uint32_t hash){const uint8_t* data=(uint8_t*)&hash;' + ack + '\nreturn nullptr;}'
assert 'serviceLoRaFishArrival();' in f['block']('void MyMesh::loop()')
main = r'''
static ContactInfo owner,host,impostor;
static void reset(MyMesh& m, uint32_t time=100) {
 now=time;m=MyMesh{};m._mgr=&m.mgr;m._radio=&m.radio;m.contacts={owner};
 loragotchiDXHome=LoRaGotchiDXHomeState{};loragotchiDXGuest=LoRaGotchiDXGuestState{};
 loragotchiDXVisit=LoRaFishVisit{};loragotchiDXReservation=LoRaFishReservation{};
 loragotchiDXGuestReturn=LoRaFishGuestReturn{};loRaFishCommitFrame=LoRaFishCommitFrame{};
 loRaFishArrival=LoRaFishArrival{};saves=0;
}
static void sending(MyMesh& m, LoRaFishVisit::Phase phase=LoRaFishVisit::Commit) {
 reset(m);m.contacts={host};
 loragotchiDXHome.txid=7;loragotchiDXHome.fishid=8;loragotchiDXHome.pending=true;
 loragotchiDXHome.destinationKnown=true;memcpy(loragotchiDXHome.destinationKey,host.id.pub_key,32);
 m.trackLoRaFishRequest("LFG1|REQ|7|8|2|Fish",m.estimate);
 if(phase==LoRaFishVisit::Commit) m.receive(host,"LFG1|ACK|7|8");
 else if(phase==LoRaFishVisit::Recall){loragotchiDXHome.pending=false;loragotchiDXHome.away=true;assert(m.recallLoRaFish());}
 else m.sent.emplace_back("LFG1|REQ|7|8|2|Fish"); // initial UI send precedes track
 m.serviceLoRaFishVisit(); // observe the initial send drained
}
static void arrive(MyMesh& m) {
 m.receive(owner,"LFG1|REQ|1|2|2|Guest");
 m.receive(owner,"LFG1|COMMIT|1|2|C|1|2|3|65535");
 assert(loragotchiDXGuest.present);
}
struct Endpoint {
 MyMesh mesh;
 LoRaGotchiDXHomeState home;
 LoRaGotchiDXGuestState guest;
 LoRaFishVisit visit;
 LoRaFishReservation reservation;
 LoRaFishGuestReturn returning;
 LoRaFishCommitFrame commit;
 LoRaFishArrival arrival;
 void enter(){loragotchiDXHome=home;loragotchiDXGuest=guest;loragotchiDXVisit=visit;
   loragotchiDXReservation=reservation;loragotchiDXGuestReturn=returning;
   loRaFishCommitFrame=commit;loRaFishArrival=arrival;}
 void leave(){home=loragotchiDXHome;guest=loragotchiDXGuest;visit=loragotchiDXVisit;
   reservation=loragotchiDXReservation;returning=loragotchiDXGuestReturn;
   commit=loRaFishCommitFrame;arrival=loRaFishArrival;}
};
int main() {
 owner.id.pub_key[0]=1;host.id.pub_key[0]=9;impostor=owner;impostor.id.pub_key[31]=99;
 MyMesh m;
 for(auto phase:{LoRaFishVisit::Request,LoRaFishVisit::Commit,LoRaFishVisit::Recall}) {
   sending(m,phase);auto initialDue=loragotchiDXVisit.due;
   for(uint32_t t=5100;t<initialDue;t+=5000){now=t;m.radio.receiving=true;m.serviceLoRaFishVisit();
     now=t+100;m.radio.receiving=false;m.serviceLoRaFishVisit();assert(loragotchiDXVisit.due==initialDue);}
   now=initialDue;m.radio.receiving=true;m.serviceLoRaFishVisit();assert(m.sent.size()==1);
   now+=100;m.radio.receiving=false;m.serviceLoRaFishVisit();assert(m.sent.size()==2);
 }
 puts("PASS REQ/COMMIT/RECALL: unrelated RX cannot restart response timer; due send waits only for idle radio");
 sending(m);loragotchiDXVisit.awaitingTxDrain=true;m.mgr.pending=1;
 now=1000;m.serviceLoRaFishVisit();auto wait=loragotchiDXVisit.wait;
 now=5000;m.mgr.pending=0;m.radio.receiving=true;m.serviceLoRaFishVisit();
 assert(loragotchiDXVisit.due==now+wait && !loragotchiDXVisit.awaitingTxDrain);
 auto due=loragotchiDXVisit.due;m.radio.receiving=false;
 now+=1000;m.mgr.pending=1;m.serviceLoRaFishVisit();
 now+=1000;m.mgr.pending=0;m.serviceLoRaFishVisit();assert(loragotchiDXVisit.due==due);
 now=due;m.serviceLoRaFishVisit();assert(m.sent.size()==2);
 puts("PASS queued-send drain extends response window once; subsequent unrelated TX does not extend it");

 reset(m);arrive(m);assert(m.sent.back()=="LFG1|ARRIVED|1|2");
 auto firstHash=m.hash;auto deadline=loRaFishArrival.retry.deadline;auto writes=saves;
 for(int i=0;i<10;++i)m.receive(owner,"LFG1|COMMIT|1|2");
 assert(m.sent.size()==2 && loRaFishArrival.retry.deadline==deadline);
 m.serviceLoRaFishArrival();now=loRaFishArrival.retry.due;m.serviceLoRaFishArrival();
 assert(m.sent.size()==3 && m.sent.back()=="LFG1|ARRIVED|1|2");
 assert(!m.receiveTransportAck(firstHash+1000));writes=saves;
 assert(m.receiveTransportAck(firstHash)==&m.contacts[0]);
 assert(loRaFishArrival.confirmed && loragotchiDXGuest.present && saves==writes);
 auto sends=m.sent.size();now+=600000;m.serviceLoRaFishArrival();m.receive(owner,"LFG1|COMMIT|1|2");
 assert(m.sent.size()==sends && !m.receiveTransportAck(firstHash));
 puts("PASS lost ARRIVED retries autonomously; earlier-attempt ACK stops once, retains guest, duplicates cannot reset budget");

 reset(m);m.failure=true;arrive(m);auto failedHash=m.hash;
 assert(loRaFishArrival.retry.attempts==0 && !m.receiveTransportAck(failedHash));
 sends=m.sent.size();now+=9999;m.serviceLoRaFishArrival();assert(m.sent.size()==sends);
 m.failure=false;m.hash=UINT32_MAX;now=loRaFishArrival.retry.due;m.serviceLoRaFishArrival();
 assert(loRaFishArrival.retry.attempts==1 && m.hash==0 && m.receiveTransportAck(0));
 assert(loragotchiDXGuest.present);
 puts("PASS enqueue failure is paced without attempt credit; failed hash rejected and zero-valued successful ACK accepted");

 reset(m);arrive(m);firstHash=m.hash;deadline=loRaFishArrival.retry.deadline;
 for(int i=1;i<4;++i){now=loRaFishArrival.retry.due;m.serviceLoRaFishArrival();assert(loRaFishArrival.retry.attempts==i+1);}
 now=deadline;m.serviceLoRaFishArrival();assert(loRaFishArrival.retry.phase==LoRaFishVisit::Unconfirmed);
 sends=m.sent.size();for(int i=0;i<10;++i){now+=10000;m.receive(owner,"LFG1|COMMIT|1|2");m.serviceLoRaFishArrival();}
 assert(m.sent.size()==sends && loRaFishArrival.retry.attempts==4 && loragotchiDXGuest.present);
 assert(m.receiveTransportAck(firstHash));
 puts("PASS four queued confirmations and 120s bound; lost ACKs/duplicate COMMIT cannot create endless sends; late ACK valid");

 reset(m);m.radio.receiving=true;arrive(m);assert(loRaFishArrival.retry.attempts==0);
 deadline=loRaFishArrival.retry.deadline;now=deadline;m.serviceLoRaFishArrival();
 m.radio.receiving=false;m.serviceLoRaFishArrival();assert(loRaFishArrival.retry.attempts==0);
 assert(loragotchiDXGuest.present);
 reset(m);m.failure=true;arrive(m);deadline=loRaFishArrival.retry.deadline;
 for(now=100;now<deadline;now+=1000)m.serviceLoRaFishArrival();
 now=deadline;m.serviceLoRaFishArrival();sends=m.sent.size();m.failure=false;now+=10000;m.serviceLoRaFishArrival();
 assert(m.sent.size()==sends && loRaFishArrival.retry.attempts==0);
 puts("PASS permanent receive-busy and enqueue failure terminate at deadline without deleting guest");

 reset(m);arrive(m);m.serviceLoRaFishArrival();due=loRaFishArrival.retry.due;
 m.contacts={impostor};now=due;m.serviceLoRaFishArrival();assert(loRaFishArrival.retry.attempts==1);
 m.contacts={impostor,owner};snprintf(m.contacts[1].name,32,"Renamed owner");
 m.serviceLoRaFishArrival();assert(loRaFishArrival.retry.attempts==2 && m.destinations.back()==1);
 assert(m.receiveTransportAck(m.hash)==&m.contacts[1]);
 puts("PASS missing/same-prefix/reordered/renamed owner never redirects confirmation; restored full-key contact works");

 reset(m);arrive(m);firstHash=m.hash;m.receive(owner,"LFG1|RECALL|1|2");
 assert(!loRaFishArrival.active && !m.receiveTransportAck(firstHash));
 m.serviceLoRaFishGuestReturn();assert(m.sent.back()=="LFG1|RETURN|1|2|M");
 assert(m.receiveTransportAck(m.hash) && !loragotchiDXGuest.present);
 m.receive(impostor,"LFG1|REQ|3|4|2|Next");m.contacts={impostor};
 m.receive(impostor,"LFG1|COMMIT|3|4|C|2|3|4|65535");
 assert(loragotchiDXGuest.present && !m.receiveTransportAck(firstHash));
 assert(m.receiveTransportAck(m.hash) && loragotchiDXGuest.present);
 puts("PASS recall cancels ARRIVED job, RETURN ACK removes guest, old ACK cannot confirm a new visitor");

 reset(m,0xfffffff0UL);arrive(m);m.serviceLoRaFishArrival();
 due=loRaFishArrival.retry.due;now=due-1;m.serviceLoRaFishArrival();assert(loRaFishArrival.retry.attempts==1);
 now=due;m.serviceLoRaFishArrival();assert(loRaFishArrival.retry.attempts==2);
 now=loRaFishArrival.retry.deadline;m.serviceLoRaFishArrival();
 assert(loRaFishArrival.retry.phase==LoRaFishVisit::Unconfirmed);
 puts("PASS arrival retry and phase deadlines survive millis rollover");

 reset(m);arrive(m);m.serviceLoRaFishArrival();due=loRaFishArrival.retry.due;
 for(uint32_t t=5100;t<due;t+=5000){now=t;m.radio.receiving=true;m.serviceLoRaFishArrival();
   now=t+100;m.radio.receiving=false;m.serviceLoRaFishArrival();assert(loRaFishArrival.retry.due==due);}
 now=due;m.serviceLoRaFishArrival();assert(loRaFishArrival.retry.attempts==2);
 puts("PASS ARRIVED itself survives unrelated RX traffic without response-timer starvation");

 reset(m);arrive(m);firstHash=m.hash;loragotchiDXGuest.ownerKey[31]=77;
 assert(!m.receiveTransportAck(firstHash));m.serviceLoRaFishArrival();assert(!loRaFishArrival.active);
 reset(m);arrive(m);loragotchiDXGuest=LoRaGotchiDXGuestState{};m.serviceLoRaFishArrival();assert(!loRaFishArrival.active);
 puts("PASS changed/cleared guest identity cancels stale confirmation jobs");

 // Full production DX-to-DX exchange, with the first ARRIVED deliberately lost.
 Endpoint a,b;now=100;a.mesh.contacts={host};b.mesh.contacts={owner};
 a.home.txid=7;a.home.fishid=8;a.home.pending=true;a.home.destinationKnown=true;
 memcpy(a.home.destinationKey,host.id.pub_key,32);
 a.enter();a.mesh.trackLoRaFishRequest("LFG1|REQ|7|8|2|Fish",10000);a.leave();
 b.enter();b.mesh.receive(owner,"LFG1|REQ|7|8|2|Fish");b.leave();
 a.enter();a.mesh.receive(host,b.mesh.sent.back().c_str());
 auto commit=a.mesh.sent.back();assert(loragotchiDXHome.committing);
 assert(!a.mesh.receiveTransportAck(a.mesh.hash) && loragotchiDXHome.committing);a.leave();
 b.enter();b.mesh.receive(owner,commit.c_str());assert(loragotchiDXGuest.present);
 assert(b.mesh.sent.back()=="LFG1|ARRIVED|7|8"); // drop this first reply
 b.mesh.serviceLoRaFishArrival();now=loRaFishArrival.retry.due;b.mesh.serviceLoRaFishArrival();
 auto reply=b.mesh.sent.back();auto arrivalHash=b.mesh.hash;b.leave();
 a.enter();a.mesh.receive(host,reply.c_str());assert(loragotchiDXHome.away && !loragotchiDXHome.committing);a.leave();
 b.enter();assert(b.mesh.receiveTransportAck(arrivalHash));sends=b.mesh.sent.size();now+=300000;
 b.mesh.serviceLoRaFishArrival();assert(b.mesh.sent.size()==sends && loragotchiDXGuest.present);b.leave();
 assert(a.mesh.sent.size()==1); // home sent no additional COMMIT to rescue the lost reply
 puts("PASS actual two-DX handshake: COMMIT transport ACK is not acceptance; lost ARRIVED recovers without another COMMIT");
}
'''
with tempfile.TemporaryDirectory(prefix='dx-arrival-recovery-') as directory:
    temp = Path(directory)
    cpp, exe = temp/'arrival.cpp', temp/'arrival'
    cpp.write_text(f['pre']+f['structs']+globals_+f['receive']+methods+main)
    subprocess.run(['g++', '-std=c++17', '-fsanitize=address,undefined',
                    '-fno-omit-frame-pointer', '-I', str(root), str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
