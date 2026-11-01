#!/usr/bin/env python3
"""Production adoption/serializers with fault-injected files, clock and radio.
Host evidence only; no physical flash, display, receiver app or RF validation.
"""
from pathlib import Path
import runpy, subprocess, tempfile
fixture=runpy.run_path(str(Path(__file__).with_name('check_fish_lifecycle.py')))
root=fixture['ROOT']
source='\n'.join(fixture['parts'][:-1])+fixture['parts'][-1].split('int main() {',1)[0]
source=source.replace('static int settingsWrites = 0;', 'static int settingsWrites = 0;\nstatic std::string shortPath, badReadPath;')
source=source.replace('auto& data = files[path];','if(path==shortPath) count/=2;\n    auto& data = files[path];')
source=source.replace('const auto& data = files.at(path);','if(path==badReadPath) return 0;\n    const auto& data = files.at(path);')
source=source.replace('} SPIFFS, InternalFS;', r''' } SPIFFS, InternalFS;
#if defined(LORAFISH_TDECK_NVS)
struct LoRaFishNVSFile {
 File f;
 LoRaFishNVSFile(const char* key,bool write):f(SPIFFS.open(!strcmp(key,"cfg")?"/lorafish.cfg":
     !strcmp(key,"state")?"/lorafish.dat":!strcmp(key,"egg0")?"/lfegg0.dat":"/lfegg1.dat",write?FILE_WRITE:FILE_READ)){}
 explicit operator bool() const{return (bool)f;}
 bool recordExists(){return files.count(f.path);}
 size_t size()const{return f.size();}
 size_t read(uint8_t* p,size_t n){return f.read(p,n);}
 size_t write(const uint8_t* p,size_t n){return f.write(p,n);}
 bool close(){f.close();return true;}
};
#endif
''')
source+=r'''
#include "examples/companion_radio/ui-new/LoRaFishText.h"
#include "examples/companion_radio/LoRaFishCommit.h"
#define MAX_ANON_CONTACTS 4
#define ADV_TYPE_CHAT 1
struct ContactInfo { struct {uint8_t pub_key[32]={};} id; uint8_t type=1; char name[32]="🥚 Nursery"; };
struct Mesh {
 std::vector<ContactInfo> contacts;std::vector<std::string> sent;std::vector<std::vector<uint8_t>> recipients;
 uint32_t rng=100; bool failure=false,ready=true;
 struct RTC{uint32_t getCurrentTime(){return clockMs/1000;}}rtc;
 RTC* getRTCClock(){return &rtc;}
 int getNumContacts(){return contacts.size();}
 bool getContactByIdx(int i,ContactInfo& c){i-=MAX_ANON_CONTACTS;if(i<0 || (unsigned)i>=contacts.size())return false;c=contacts[i];return true;}
 ContactInfo* lookupContactByPubKey(const uint8_t* k,int n){for(auto& c:contacts)if(!memcmp(c.id.pub_key,k,n))return &c;return nullptr;}
 uint32_t loRaFishRandom(){return ++rng;}
 bool loRaFishQueueReady(){return ready;}
 int sendMessage(const ContactInfo& c,uint32_t,int,const char* p,uint32_t& hash,uint32_t& timeout){hash=0;timeout=30000;if(failure)return -1;sent.emplace_back(p);recipients.emplace_back(c.id.pub_key,c.id.pub_key+32);return 0;}
}the_mesh;
#include "examples/companion_radio/ui-new/LoRaFishAdoption.h"
static void init() {
 resetAt(0);files.clear();shortPath.clear();badReadPath.clear();clockMs=10000;
 loRaFishAdoptionEligible=true;loRaFishNeedsAppearanceSetup=true;loRaFishColorDisplay=true;
 loRaFishEggSession={};loRaFishEggReceipt={};loRaFishEggBank=-1;loRaFishEggStorageHealthy=true;
 loRaFishEggApplying=false;loRaFishEggWindowStarted=false;loRaFishEggSaveDue=0;loRaFishEggSaveScheduled=false;
 the_mesh={};ContactInfo c;c.id.pub_key[0]=9;the_mesh.contacts={c};loadLoRaFishEggReceipt();
 serviceLoRaFishAdoption(true);assert(loRaFishEggSession.phase==LoRaFishEgg::Probe);
 assert(the_mesh.sent.size()==1);
}
static std::string packet(const char* op,const char* tail) {
 char p[180];snprintf(p,sizeof(p),"LEG1|%s|%lu|%lu|%s",op,
   (unsigned long)loRaFishEggSession.nonce[0],(unsigned long)loRaFishEggSession.nonce[1],tail);return p;
}
static bool receive(const std::string& p,std::string* result=nullptr,const uint8_t* key=nullptr) {
 char reply[80]={};bool ok=loragotchiEggMessage(key?key:the_mesh.contacts[0].id.pub_key,p.c_str(),reply,sizeof(reply));
 if(result)*result=reply;return ok;
}
static std::string offer() {
 assert(receive(packet("READY","H1")));
 auto p=packet("EGG","77|12|H1|220|120|6");assert(receive(p));return p;
}
int main() {
 init(); auto e=loRaFishEggSession;
 uint8_t impostor[32];memcpy(impostor,e.peer,32);impostor[31]=1;
 assert(!receive(packet("READY","H1"),nullptr,impostor));
 assert(!receive(packet("EGG","77|1|H1|1|2|3")));
 assert(!receive("LEG1|READY|4294967296|2|H1"));
 assert(receive(packet("READY","H1")));
 for(const char* tail:{"0|1|H1|1|2|3","77|65536|H1|1|2|3","77|1|H1|7|2|3","77|1|H1|255|2|3","77|1|H1|1|2|3|junk","77|1|H1|-1|2|3","9999999999999999999999|1|H1|1|2|3"})assert(!receive(packet("EGG",tail)));
 closeLoRaFishAdoption();assert(!receive(packet("EGG","77|1|H1|1|2|3")));
 pass("capability required, full-key/nonce binding, strict MCU-width numeric grammar and skip closure");
 init();auto p=offer();auto sends=the_mesh.sent.size();serviceLoRaFishAdoption(true);
 assert(!loRaFishAdoptionEligible && !loRaFishNeedsAppearanceSetup && fish.ageMinutes==0);
 assert(loRaFishColor==220 && loRaFishScaleColor==120 && loRaFishEyeColor==6 && loRaFishGeneration==12);
 assert(loRaFishEggReceipt.valid() && loRaFishEggReceipt.bytes[8]==2 && the_mesh.sent.size()==sends+1);
 assert(the_mesh.recipients.back()[0]==9 && files["/lorafish.cfg"].size()==54);
 auto saved=files;std::string reply;fish.ageMinutes=45;
 assert(receive(p,&reply) && reply.find("LEG1|SAVED|")==0 && files==saved && fish.ageMinutes==45);
 loRaFishEggReceipt={};loRaFishEggBank=-1;loadLoRaFishEggReceipt();assert(receive(p,&reply));
 assert(fish.ageMinutes==45);assert(!receive(p,nullptr,impostor));
 pass("save/readback precedes SAVED; duplicate and reboot replay acknowledge without replacing pet");
 init();p=offer();shortPath="/lfegg0.dat";sends=the_mesh.sent.size();serviceLoRaFishAdoption(true);
 assert(!loRaFishEggApplying && the_mesh.sent.size()==sends && loRaFishGeneration==7);
 shortPath.clear();clockMs+=5000;shortPath="/lorafish.cfg";serviceLoRaFishAdoption(true);
 assert(loRaFishEggApplying && loRaFishEggReceipt.bytes[8]==1 && the_mesh.sent.size()==sends);
 closeLoRaFishAdoption();assert(loRaFishAdoptionEligible); // intent cannot be abandoned
 shortPath.clear();loRaFishEggSession={};loRaFishEggReceipt={};loRaFishEggApplying=false;loRaFishEggBank=-1;
 loadLoRaFish();loadLoRaFishSettings();loadLoRaFishEggReceipt();assert(loRaFishEggApplying);
 clockMs+=5000;serviceLoRaFishAdoption(false);
 assert(!loRaFishAdoptionEligible && loRaFishGeneration==12 && loRaFishColor==220);
 assert(receive(p,&reply));
 pass("torn intent/config saves do not ACK; pending journal resumes through real boot serializers");
 init();p=offer();badReadPath="/lorafish.dat";sends=the_mesh.sent.size();serviceLoRaFishAdoption(true);
 assert(loRaFishEggApplying && the_mesh.sent.size()==sends);
 badReadPath.clear();shortPath="/lfegg1.dat";clockMs+=5000;serviceLoRaFishAdoption(true);
 assert(loRaFishEggApplying && loRaFishEggReceipt.bytes[8]==1 && the_mesh.sent.size()==sends);
 shortPath.clear();clockMs+=5000;serviceLoRaFishAdoption(true);assert(receive(p,&reply));
 pass("failed pet readback and torn completion receipt keep pending intent and suppress ACK");
 init();clockMs+=120000;assert(!receive(packet("READY","H1")));serviceLoRaFishAdoption(false);
 assert(!loRaFishAdoptionEligible && loRaFishNeedsAppearanceSetup);
 init();auto first=loRaFishEggSession;selectLoRaFishEggTank(true);
 assert(first.nonce[0]!=loRaFishEggSession.nonce[0]);
 char old[80];snprintf(old,sizeof(old),"LEG1|READY|%lu|%lu|H1",(unsigned long)first.nonce[0],(unsigned long)first.nonce[1]);assert(!receive(old));
 the_mesh.contacts.clear();serviceLoRaFishAdoption(true);assert(!loRaFishAdoptionEligible);
 init();loRaFishAdoptionEligible=false;assert(!receive(packet("READY","H1")));
 pass("timeout, reselection and deleted contacts close old requests; existing fish cannot adopt");
 init();clockMs=0xFFFFFFF0UL;loRaFishEggWindowStarted=false;serviceLoRaFishAdoption(true);
 clockMs=(uint32_t)(clockMs+119999);serviceLoRaFishAdoption(true);assert(loRaFishAdoptionEligible);
 clockMs=(uint32_t)(clockMs+1);serviceLoRaFishAdoption(true);assert(!loRaFishAdoptionEligible);
 init();the_mesh.failure=true;selectLoRaFishEggTank(true);
 for(int i=0;i<4;++i) {
   serviceLoRaFishAdoption(true);assert(loRaFishEggSession.attempts==i+1);
   for(int repeat=0;repeat<100;++repeat)serviceLoRaFishAdoption(true);
   assert(loRaFishEggSession.attempts==i+1);clockMs+=5000;
 }
 serviceLoRaFishAdoption(true);assert(loRaFishEggSession.attempts==4);
 init();clockMs=0xFFFFFFF0UL;loRaFishEggWindowStarted=false;serviceLoRaFishAdoption(true);
 p=offer();shortPath="/lfegg0.dat";serviceLoRaFishAdoption(true);
 assert(loRaFishEggSaveScheduled && !loRaFishEggApplying);
 clockMs=(uint32_t)(clockMs+4999);shortPath.clear();serviceLoRaFishAdoption(true);assert(loRaFishAdoptionEligible);
 clockMs=(uint32_t)(clockMs+1);serviceLoRaFishAdoption(true);assert(!loRaFishAdoptionEligible && receive(p,&reply));
 pass("millis rollover, fixed deadline and bounded failed-enqueue/save backoff");
 init();loRaFishEggSession={};loRaFishEggWindowStarted=false;the_mesh.contacts[0].type=2;
 serviceLoRaFishAdoption(true);assert(loRaFishEggSession.phase==LoRaFishEgg::Closed);
 clockMs+=10000;serviceLoRaFishAdoption(true);assert(!loRaFishAdoptionEligible);
 init();files["/lfegg0.dat"]={};files["/lfegg1.dat"]={4};loRaFishEggBank=-1;loRaFishEggReceipt={};
 loadLoRaFishEggReceipt();assert(!loRaFishEggStorageHealthy);serviceLoRaFishAdoption(true);assert(!loRaFishAdoptionEligible);
 pass("marker/type filter, no-candidate fallback and corrupt-journal adoption fail-closed");
 // Actual codec migration: old prefix remains palette-only; complete HUE1 restores all six alleles.
 init();loRaFishAdoptionEligible=false;loRaFishColor=220;loRaFishScaleColor=120;loRaFishEyeColor=6;
 loRaFishEggAppearance={50,80,110};saveLoRaFishSettings();auto cfg=files["/lorafish.cfg"];
 assert(cfg[3]<=6 && cfg[14]<=6 && cfg[19]<=6);loadLoRaFishSettings();assert(loRaFishColor==220 && loRaFishEggAppearance.eyes==110);
 files["/lorafish.cfg"].resize(44);loadLoRaFishSettings();assert(loRaFishColor==LoRaFishColour::fallback(220));
 files["/lorafish.cfg"]=cfg;files["/lorafish.cfg"][50]=7;loadLoRaFishSettings();assert(loRaFishColor<=6);
 pass("HUE1 round trip, palette-compatible old saves, invalid extension fallback");
}
'''
mesh_source=(root/'examples/companion_radio/MyMesh.cpp').read_text()
a=mesh_source.index('  if (text && strncmp(text,"LEG1|",5)==0) {')
b=mesh_source.index('  if (text && strncmp(text,"LFG1|",5)==0)',a)
route=mesh_source[a:b].replace('sendMessage(', 'the_mesh.sendMessage(').replace('getRTCClock()', 'the_mesh.getRTCClock()')
source=source.replace('static void init() {','static void radioReceive(const ContactInfo& from,const char* text) {\n'+route+'}\nstatic void init() {')
source=source.replace('assert(fish.ageMinutes==45);assert(!receive(p,nullptr,impostor));',
    'assert(fish.ageMinutes==45);assert(!receive(p,nullptr,impostor));\n  auto sentBefore=the_mesh.sent.size();radioReceive(the_mesh.contacts[0],p.c_str());assert(the_mesh.sent.size()==sentBefore+1 && fish.ageMinutes==45);')
with tempfile.TemporaryDirectory(prefix='dx-egg-') as directory:
    cpp=Path(directory)/'egg.cpp';cpp.write_text(source)
    for platform in ('ESP32','NRF52_PLATFORM','TDECK_NVS'):
        exe=Path(directory)/platform
        subprocess.run(['g++','-std=c++17','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(root),'-I',str(root/'src'),*(['-DESP32','-DLORAFISH_TDECK_NVS'] if platform=='TDECK_NVS' else ['-D'+platform]),str(cpp),'-o',str(exe)],check=True)
        print(platform,flush=True);subprocess.run([str(exe)],check=True)
