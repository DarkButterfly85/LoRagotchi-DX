#!/usr/bin/env python3
"""Production DX save/load migration with in-memory Preferences, not flash proof."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'examples/companion_radio/MyMesh.cpp').read_text()
header = (root / 'examples/companion_radio/MyMesh.h').read_text()


def block(marker):
    start = source.index(marker)
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


structs = header[header.index('struct LoRaGotchiDXHomeState'):header.index('extern LoRaGotchiDXHomeState')]
globals_ = source[source.index('LoRaGotchiDXHomeState loragotchiDXHome;'):source.index('static void loragotchiDXResetTravelStateForMigration')]
pre = r'''
#include <cassert>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>
#include "examples/companion_radio/LoRaFishGuestReturn.h"
#include "examples/companion_radio/LoRaFishVisit.h"
#include "examples/companion_radio/LoRaFishArrival.h"
static std::map<std::string,std::vector<uint8_t>> records;
struct Preferences {
  bool begin(const char*,bool){return true;}
  void end(){}
  void putUInt(const char*,uint32_t){}
  void putUShort(const char*,uint16_t){}
  size_t getBytesLength(const char* key){return records[key].size();}
  size_t getBytes(const char* key,void* out,size_t n){assert(records[key].size()<=n);memcpy(out,records[key].data(),records[key].size());return records[key].size();}
  size_t putBytes(const char* key,const void* bytes,size_t n){const auto* p=(const uint8_t*)bytes;records[key]={p,p+n};return n;}
};
struct {void println(const char*){}} Serial;
'''
main = r'''
int main(){
  LoRaGotchiDXHomeState old;
  old.fishid=0xCAFE1234;old.away=true;old.txid=567;old.destinationKnown=true;
  const auto* bytes=reinterpret_cast<const uint8_t*>(&old);
  static_assert(offsetof(LoRaGotchiDXHomeState,destinationKey)==48,"legacy home layout");
  records["home"]={bytes,bytes+48};
  loragotchiDXGuest.present=true;loragotchiDXGuestReturn.start(42);
  uint8_t owner[32]={1};loRaFishArrival.start(owner,7,8,42);
  loragotchiDXLoad();
#ifdef ESP32
  assert(loragotchiDXHome.fishid==0xCAFE1234);
#else
  assert(loragotchiDXHome.fishid==0); // nRF52 has never persisted DX session identity here
#endif
  assert(!loragotchiDXHome.away && !loragotchiDXHome.destinationKnown && !loragotchiDXHome.completedVisit);
  assert(!loragotchiDXGuest.present && !loragotchiDXGuest.ownerKnown && loragotchiDXGuestReturn.status==LoRaFishGuestReturn::Idle);
  assert(!loRaFishArrival.active);
  puts("PASS legacy identity retained where supported; reboot clears sessions and retry jobs");
#ifdef ESP32
  loragotchiDXHome.fishid=99;loragotchiDXHome.away=true;loragotchiDXHome.completedVisit=true;
  loragotchiDXGuest.present=true;loragotchiDXSave();loragotchiDXLoad();
  assert(loragotchiDXHome.fishid==99 && !loragotchiDXHome.away && !loragotchiDXHome.completedVisit && !loragotchiDXGuest.present);
  puts("PASS new record round trip keeps identity, never stale travel/completion state");
  for(size_t length=0;length<=sizeof(old)+4;length++) {
    if(length==48 || length==sizeof(old))continue;
    records["home"]=std::vector<uint8_t>(length,0xFF);
    loragotchiDXLoad();assert(loragotchiDXHome.fishid==0 && !loragotchiDXHome.away);
  }
  puts("PASS absent, truncated and unknown-sized home records use safe defaults");
#endif
}
'''
with tempfile.TemporaryDirectory(prefix='dx-storage-') as tmp:
    path = Path(tmp)
    cpp = path / 'storage.cpp'
    cpp.write_text(pre + structs + globals_ + block('void loragotchiDXSave()') +
                   block('void loragotchiDXLoad()') + main)
    for platform in ('ESP32', 'NRF52_PLATFORM'):
        exe = path / platform
        subprocess.run(['g++', '-std=c++17', '-I', str(root), '-D' + platform,
                        str(cpp), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
