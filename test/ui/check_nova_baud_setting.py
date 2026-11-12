#!/usr/bin/env python3
"""Nova link serial speed setting: wiring in UITask.cpp / MyMesh.cpp / main.cpp, and the real save + apply code.

python3 test/ui/check_nova_baud_setting.py     (Python 3 and g++; no firmware build, no hardware)

  a. menu: the Serial speed row is the LAST Display row, hidden unless the build has a UART (kApplies), its value
     picker has one entry per listed speed, and its text fits the narrowest screen (mono 128 px, 6 px a character)
  b. storage: the speed is NOT in /lorafish.cfg (still 112 bytes, same tails), /lorafish.dat / LoRaFishState are
     untouched, the T-Deck key/value names for /lorafish.bd* exist and differ from every other record's key
  c. the real loadLoRaFishSerialSpeed() / setLoRaFishSerialSpeed() cut out of UITask.cpp and run on a memory store:
     default with no file, save + reload, unlisted rate refused and nothing written, port moved once at start-up
     (UART build) and never on a build without a UART
  d. MyMesh.cpp: "nova baud" goes through NovaBaud::request, hello lists baud only when the setter is registered,
     the pet sender paces by the active speed; main.cpp still opens the port at 115200 (default unchanged)
"""
from pathlib import Path
import re, subprocess, sys, tempfile

ROOT = Path(__file__).resolve().parents[2]
CR = ROOT / 'examples/companion_radio'
UI = (CR / 'ui-new/UITask.cpp').read_text()
MENU = (CR / 'ui-new/LoRaFishMenu.h').read_text()
MESH = (CR / 'MyMesh.cpp').read_text()
MAIN = (CR / 'main.cpp').read_text()
BAUD = (CR / 'NovaBaud.h').read_text()


def check(cond, msg):
    if not cond:
        print('FAIL:', msg)
        sys.exit(1)


def between(text, start, end, include_end=False):
    a = text.index(start)
    b = text.index(end, a)
    return text[a:b + (len(end) if include_end else 0)]


# ---- a. menu ----------------------------------------------------------------------------------------------
check(re.search(r'DimSlow,\s*SerialSpeed,\s*Count', MENU), 'SerialSpeed must be appended after DimSlow, before Count')
check(re.search(r'DimSlow,[^\n]*\n\s*SerialSpeed[^\n]*\n\};', MENU), 'LoRaFishSetting::SerialSpeed must be the last setting')
check('case LoRaFishDisplayRow::SerialSpeed: return serialSpeed;' in MENU, 'row available only when serialSpeed is set')
check('bool serialSpeed = false;' in MENU, 'hidden by default')
check('rows.serialSpeed = NovaBaud::shown();' in UI, 'row flag comes from the build')
check('NovaBaud::shown() = NovaBaud::kApplies;' in UI, 'supported only where Serial is a UART')
check('static uint32_t v = kDefault; return v;' in BAUD and 'static bool v = false; return v;' in BAUD, 'default speed unchanged, row hidden by default')
check('count = NovaBaud::shown() ? NovaBaud::kCount : 0;' in UI, 'one picker entry per listed speed; none when unsupported')
check('NovaBaud::kRates[value]' in UI and 'value < NovaBaud::kCount' in UI, 'picker value is bounds checked')
check('"SERIAL SPEED"}' in UI.replace('\n', ''), 'picker title appended last (titles are indexed by setting)')
check('case LoRaFishSetting::SerialSpeed: row = LoRaFishDisplayRow::SerialSpeed; break;' in UI, 'Back returns to the Serial speed row')
check('openLoRaFishValue(LoRaFishSetting::SerialSpeed)' in UI, 'row opens the picker')
check('key != LoRaFishSetting::SerialSpeed) loRaFishSettingsPending = true;' in UI, 'the speed does not trigger a /lorafish.cfg save')
for s in ('Serial speed', 'Hold: save, reboot', 'SERIAL SPEED', '115200', '230400', '460800', '921600'):
    check(len(s) * 6 <= 128, s + ' is wider than the 128 px mono screen')

# ---- b. storage ------------------------------------------------------------------------------------------
check('LORAFISH_SETTINGS_SIZE = 112;' in UI, '/lorafish.cfg size unchanged')
enc = between(UI, 'static void encodeLoRaFishSettings(uint8_t* data) {', '\n}\n', True)
check('NovaBaud' not in enc and 'SerialSpeed' not in enc, 'the speed must not be written into /lorafish.cfg')
check('memcpy(data+106,"DIM1",4); data[110]=loRaFishDimSlow ? 1 : 0; data[111]=0;' in enc, 'cfg tail unchanged')
km = between(UI, 'static const char* loRaFishRecordKey(const char* path) {', '\n}\n', True)
keys = re.findall(r'return "([a-z0-9]+)";', km)
check(len(keys) == len(set(keys)), 'record keys must be distinct: ' + str(keys))
for name, path, key in (('kMain', '/lorafish.bd', 'bd'), ('kBak', '/lorafish.bdb', 'bdbak'), ('kTmp', '/lorafish.bdt', 'bdtmp')):
    check('strcmp(path,"%s")) return "%s";' % (path, key) in km, 'T-Deck key ' + key)
    check('%s = "%s";' % (name, path) in BAUD, 'NovaBaud.h and loRaFishRecordKey must name the same file: ' + path)
check(km.index('"/lorafish.bd"') < km.index('return "state";'), 'bd keys come before the "state" fallback')
for fn in ('/lorafish.bd"', '/lorafish.bdt"', '/lorafish.bdb"'):
    check(fn in BAUD, fn)
check(BAUD.count('"/lorafish.') == 3, 'NovaBaud touches only its own three names')
m = re.search(r'struct LoRaFishState \{.*?\n\};', UI, re.S)
check(m, 'LoRaFishState not found')
check('LORAFISH_MAGIC = 0x4C464D32' in UI, 'pet magic LFM2 unchanged')

# ---- c. the real functions on a memory store --------------------------------------------------------------
load_fn = between(UI, 'static void loadLoRaFishSerialSpeed() {', '\n}\n', True)
set_fn = between(UI, 'static NovaBaud::Status setLoRaFishSerialSpeed(uint32_t rate) {', '\n}\n', True)
cpp = r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>
#include "examples/companion_radio/NovaBaud.h"

struct MemStore {
  std::map<std::string, std::vector<uint8_t>> f;
  bool hasRename() const { return true; }
  bool write(const char* p, const uint8_t* d, size_t n) { f[p].assign(d, d + n); return true; }
  int read(const char* p, uint8_t* b, size_t cap) {
    auto it = f.find(p); if (it == f.end()) return -1;
    if (it->second.size() > cap) return -2;
    memcpy(b, it->second.data(), it->second.size()); return (int)it->second.size();
  }
  bool exists(const char* p) { return f.count(p) != 0; }
  bool remove(const char* p) { return f.erase(p) != 0; }
  bool rename(const char* a, const char* b) {
    auto it = f.find(a); if (it == f.end()) return false;
    f[b] = it->second; f.erase(a); return true;
  }
};
struct FakeSerial { int updates = 0; uint32_t last = 0; void flush() {} void updateBaudRate(unsigned long r) { updates++; last = (uint32_t)r; } };
static MemStore loRaFishPetStore;
static FakeSerial Serial;
''' + load_fn + set_fn + r'''
int main() {
  NovaBaud::shown() = true;
  // no file: default, nothing moves
  loadLoRaFishSerialSpeed();
  assert(NovaBaud::choice() == 115200 && Serial.updates == 0);
  // another file of the pet is never touched by a save
  loRaFishPetStore.f["/lorafish.dat"] = std::vector<uint8_t>(40, 0xA5);
  loRaFishPetStore.f["/lorafish.cfg"] = std::vector<uint8_t>(112, 0x5A);
  const auto dat = loRaFishPetStore.f["/lorafish.dat"], cfg = loRaFishPetStore.f["/lorafish.cfg"];
  assert(setLoRaFishSerialSpeed(460800) == NovaBaud::Status::Ok);
  assert(NovaBaud::choice() == 460800);
  assert(loRaFishPetStore.f["/lorafish.dat"] == dat && loRaFishPetStore.f["/lorafish.cfg"] == cfg);
  assert(Serial.updates == 0);                      // choosing never moves the running port
  // unlisted: refused, nothing written, nothing changed
  const auto before = loRaFishPetStore.f;
  assert(setLoRaFishSerialSpeed(9600) == NovaBaud::Status::Unsupported);
  assert(setLoRaFishSerialSpeed(0) == NovaBaud::Status::Unsupported);
  assert(loRaFishPetStore.f == before && NovaBaud::choice() == 460800);
  // restart: the saved speed is read and the port moves once
  NovaBaud::choice() = NovaBaud::kDefault;
  loadLoRaFishSerialSpeed();
  assert(NovaBaud::choice() == 460800);
#if NOVA_BAUD_APPLIES
  assert(Serial.updates == 1 && Serial.last == 460800 && NovaBaud::activeRate() == 460800);
  loadLoRaFishSerialSpeed();                         // a second call does not move it again
  assert(Serial.updates == 1);
#else
  assert(Serial.updates == 0);
#endif
  // a build without a UART: the setter refuses
  NovaBaud::shown() = false;
  assert(setLoRaFishSerialSpeed(230400) == NovaBaud::Status::Unsupported);
  puts("ok");
  return 0;
}
'''
for applies in (1, 0):
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / 'h.cpp'
        src.write_text(cpp)
        exe = Path(td) / 'h'
        # with NOVA_BAUD_APPLIES=0 the preprocessor cuts the apply() lines out, as on a native USB build
        check('#if NOVA_BAUD_APPLIES' in load_fn, 'apply() is guarded by the preprocessor (native USB ports have no updateBaudRate)')
        r = subprocess.run(['g++', '-std=c++17', '-Wall', '-Werror', '-I', str(ROOT), '-I', str(ROOT / 'src'),
                            '-DNOVA_BAUD_APPLIES=%d' % applies, str(src), '-o', str(exe)], capture_output=True, text=True)
        check(r.returncode == 0, 'harness (applies=%d) did not compile:\n%s' % (applies, r.stderr))
        r = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30)
        check(r.returncode == 0 and r.stdout.strip() == 'ok', 'harness (applies=%d) failed: %s %s' % (applies, r.stdout, r.stderr))

# ---- d. MyMesh.cpp / main.cpp -------------------------------------------------------------------------------
check('caps.baud = NovaBaud::setterSlot() ? 1 : 0;' in MESH, 'hello lists baud only when the UI registered the setter')
check('p.cmd == NovaCli::Cmd::Baud' in MESH and 'NovaBaud::request(p.arg, &rate)' in MESH, 'nova baud goes through the validating path')
check('NovaBaud::reply(st, rate, msg, sizeof(msg))' in MESH, 'one JSON line answers it')
check('NovaPetLink::sendChunk(NovaBaud::activeRate())' in MESH and 'NovaPetLink::SEND_GAP_MS' in MESH, 'pet sender paces by the active speed')
check('NovaBaud::setterSlot() = setLoRaFishSerialSpeed;' in UI, 'setter registered')
check(UI.index('loadLoRaFishSerialSpeed();   ') < UI.index('NovaBaud::setterSlot() = setLoRaFishSerialSpeed;'), 'load before the setter is registered')
check('  Serial.begin(115200);' in MAIN and 'NOVA_SERIAL_BAUD' not in MAIN, 'main.cpp still opens the port at the old speed')
check('#if NOVA_BAUD_APPLIES' in UI, 'apply is compiled only where Serial has updateBaudRate')
print('check_nova_baud_setting: all checks passed')
