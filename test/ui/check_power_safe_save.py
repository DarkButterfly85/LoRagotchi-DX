#!/usr/bin/env python3
"""Power-cut safety of the pet save (examples/companion_radio/ui-new/LoRaFishSafeSave.h).

python3 test/ui/check_power_safe_save.py (Python 3 and g++). A simulated file
system loses power before every single file operation, and part-way through
every write, for each storage style the firmware uses:
  atomic   - littlefs on nRF52/STM32: rename replaces the target in one step
  spiffs   - ESP32 SPIFFS: target removed, then renamed (two steps)
  keyvalue - T-Deck NVS: no rename; each key write is all-or-nothing
After every cut, "rebooting" must still load a complete, valid pet (the old one
or the new one, never garbage or nothing), and the next save must heal the files.
No real flash, no PlatformIO.
"""
from pathlib import Path
import subprocess, tempfile

root = Path(__file__).resolve().parents[2]
cpp = r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>
#include "examples/companion_radio/ui-new/LoRaFishSafeSave.h"
using namespace LoRaFishSafeSave;

struct Crash {};
enum Style { ATOMIC, SPIFFS, KEYVALUE };
typedef std::vector<uint8_t> Bytes;

struct Pet { uint32_t magic; uint32_t age; uint8_t pad[24]; };  // 32 bytes like LoRaFishState
static_assert(sizeof(Pet) == 32, "pet size");
static Bytes petBytes(uint32_t age) { Pet p; memset(&p, 0, sizeof p); p.magic = 0x4C464D32; p.age = age; return Bytes((uint8_t*)&p, (uint8_t*)&p + sizeof p); }
static bool validPet(const uint8_t* rec, size_t len) {
  uint32_t magic; if (len != sizeof(Pet)) return false; memcpy(&magic, rec, 4); return magic == 0x4C464D32;
}
static Bytes sealed(uint32_t age) { Bytes r = petBytes(age); Bytes out(r.size() + kTrailer); seal(r.data(), r.size(), out.data()); return out; }

struct Sim {
  Style style;
  std::map<std::string, Bytes> files;
  int op = 0, crashAt = -1; size_t tornLen = 0;
  explicit Sim(Style s) : style(s) {}
  bool hasRename() const { return style != KEYVALUE; }
  void tick() { if (op++ == crashAt) throw Crash(); }
  bool write(const char* path, const uint8_t* data, size_t len) {
    if (style == KEYVALUE) { tick(); files[path] = Bytes(data, data + len); return true; }
    if (files.count(path)) { tick(); files.erase(path); }       // append-mode FS: old file removed first
    if (op == crashAt) { files[path] = Bytes(data, data + (tornLen < len ? tornLen : len - 1)); ++op; throw Crash(); }
    ++op; files[path] = Bytes(data, data + len); return true;
  }
  int read(const char* path, uint8_t* buf, size_t cap) {
    auto it = files.find(path); if (it == files.end()) return -1;
    if (it->second.size() > cap) return -2;
    if (!it->second.empty()) memcpy(buf, it->second.data(), it->second.size());
    return (int)it->second.size();
  }
  bool exists(const char* path) { return files.count(path) != 0; }
  bool remove(const char* path) { tick(); return files.erase(path) != 0; }
  bool rename(const char* from, const char* to) {
    if (!files.count(from)) return false;
    if (style == SPIFFS && files.count(to)) { tick(); files.erase(to); }
    tick(); Bytes d = files[from]; files.erase(from); files[to] = d; return true;
  }
};

static int loadAge(Sim& s, Source* src = nullptr) {
  uint8_t rec[kMaxRecord]; size_t len = 0;
  Source got = load(s, validPet, rec, &len);
  if (src) *src = got;
  if (got == None) return -1;
  assert(len == sizeof(Pet)); uint32_t age; memcpy(&age, rec + 4, 4); return (int)age;
}
static bool saveAge(Sim& s, uint32_t age) { Bytes r = petBytes(age); return commit(s, r.data(), r.size()); }

enum Start { EMPTY, MAIN_ONLY, MAIN_AND_BAK, LEGACY_MAIN, CORRUPT_MAIN_GOOD_BAK };
static void setup(Sim& s, Start st) {
  s.files.clear();
  switch (st) {
    case EMPTY: break;
    case MAIN_ONLY: s.files[kMain] = sealed(100); break;
    case MAIN_AND_BAK: s.files[kMain] = sealed(100); s.files[kBak] = sealed(50); break;
    case LEGACY_MAIN: s.files[kMain] = petBytes(100); break;
    case CORRUPT_MAIN_GOOD_BAK: s.files[kMain] = sealed(100); s.files[kMain][5] ^= 0x10; s.files[kBak] = sealed(50); break;
  }
}

int main() {
  int cuts = 0;
  const char* styleName[] = {"atomic", "spiffs", "keyvalue"};
  const char* startName[] = {"empty", "main only", "main+backup", "older-firmware main", "corrupt main+backup"};
  for (int st = ATOMIC; st <= KEYVALUE; ++st) {
    for (int start = EMPTY; start <= CORRUPT_MAIN_GOOD_BAK; ++start) {
      // Pets that may legitimately be loaded after a cut during the save of age 200.
      int oldAge = start == EMPTY ? -1 : start == CORRUPT_MAIN_GOOD_BAK ? 50 : 100;
      Sim dry((Style)st); setup(dry, (Start)start);
      assert(saveAge(dry, 200)); const int totalOps = dry.op;
      assert(loadAge(dry) == 200);
      for (int cut = 0; cut <= totalOps; ++cut) {
        for (size_t torn : {(size_t)0, (size_t)1, (size_t)16, (size_t)39}) {
          Sim s((Style)st); setup(s, (Start)start); s.crashAt = cut; s.tornLen = torn;
          bool crashed = false;
          try { saveAge(s, 200); } catch (Crash&) { crashed = true; }
          s.crashAt = -1;
          Source src; const int age = loadAge(s, &src);
          const bool ok = age == 200 || age == oldAge;
          if (!ok) printf("FAIL style=%s start=%s cut=%d torn=%zu crashed=%d loaded=%d\n", styleName[st], startName[start], cut, torn, crashed, age);
          assert(ok);
          if (!crashed) assert(age == 200 && src == Main);
          ++cuts;
          // The next ordinary save must heal everything.
          if (age >= 0 && src != Main) {  // what the pet does: rewrite the loaded pet at the next save
            assert(saveAge(s, (uint32_t)age)); Source after; assert(loadAge(s, &after) == age && after == Main);
          }
          assert(saveAge(s, 300)); assert(loadAge(s, &src) == 300 && src == Main);
        }
      }
      // Third save in a row, cut anywhere: only the 2nd or 3rd pet may come back.
      Sim seq((Style)st); setup(seq, (Start)start); assert(saveAge(seq, 200)); Sim base = seq;
      Sim count = base; assert(saveAge(count, 300)); const int ops3 = count.op - base.op;
      for (int cut = 0; cut <= ops3; ++cut) {
        Sim s = base; s.op = 0; s.crashAt = cut; s.tornLen = 20;
        try { saveAge(s, 300); } catch (Crash&) {}
        s.crashAt = -1; const int age = loadAge(s); assert(age == 200 || age == 300);
        ++cuts;
      }
    }
  }
  printf("PASS %d simulated power cuts, every style/start state, always a valid pet\n", cuts);

  // Checksum: any single damaged byte in the main file falls back to the backup.
  for (int st = ATOMIC; st <= KEYVALUE; ++st) {
    for (size_t i = 0; i < 40; ++i) {
      Sim s((Style)st); setup(s, MAIN_AND_BAK); s.files[kMain][i] ^= 0x01;
      Source src; assert(loadAge(s, &src) == 50 && src == Bak);
    }
    for (size_t n = 0; n < 40; ++n) {   // main cut short at any length
      Sim s((Style)st); setup(s, MAIN_AND_BAK); s.files[kMain].resize(n);
      Source src; const int age = loadAge(s, &src);
      assert(age == 50 || (n == 32 && age == 100));  // 32 bytes is a whole old-format record
    }
    Sim none((Style)st); setup(none, MAIN_ONLY); none.files[kMain][7] ^= 0x01; assert(loadAge(none) == -1);  // both gone: new pet
    Sim both((Style)st); setup(both, MAIN_AND_BAK); both.files[kMain][7] ^= 1; both.files[kBak][9] ^= 1; assert(loadAge(both) == -1);
  }
  printf("PASS checksum rejects every damaged or short main file and falls back to the backup\n");

  // A bad main is never copied over the good backup.
  for (int st = ATOMIC; st <= KEYVALUE; ++st) {
    Sim s((Style)st); setup(s, CORRUPT_MAIN_GOOD_BAK); assert(saveAge(s, 200));
    Bytes bak = s.files[kBak]; Sim chk = s; (void)chk;
    assert(bak == sealed(50)); assert(loadAge(s) == 200);
  }
  printf("PASS a damaged main never replaces the good backup\n");

  // Older firmware's bare 32-byte file still loads and is upgraded on the next save.
  for (int st = ATOMIC; st <= KEYVALUE; ++st) {
    Sim s((Style)st); setup(s, LEGACY_MAIN); Source src; assert(loadAge(s, &src) == 100 && src == Legacy);
    assert(saveAge(s, 100)); assert(loadAge(s, &src) == 100 && src == Main && s.files[kMain].size() == 40);
  }
  printf("PASS older bare pet files still load and upgrade in place\n");

  // Each save keeps the previous good copy as the backup.
  for (int st = ATOMIC; st <= KEYVALUE; ++st) {
    Sim s((Style)st); setup(s, EMPTY);
    assert(saveAge(s, 10)); assert(!s.files.count(kBak));
    assert(saveAge(s, 20)); assert(s.files[kBak] == sealed(10) && s.files[kMain] == sealed(20));
    assert(saveAge(s, 30)); assert(s.files[kBak] == sealed(20) && s.files[kMain] == sealed(30));
    assert(!s.files.count(kTmp));
    s.files[kMain][3] ^= 0x40; Source src; assert(loadAge(s, &src) == 20 && src == Bak);
  }
  printf("PASS every save leaves the previous good pet as the backup\n");

  // A write that claims success but stored too little is caught before it replaces anything.
  for (int st = ATOMIC; st <= SPIFFS; ++st) {
    struct Liar : Sim {
      explicit Liar(Style s) : Sim(s) {}
      bool write(const char* path, const uint8_t* data, size_t len) { files[path] = Bytes(data, data + len / 2); return true; }
    };
    Liar s((Style)st); setup(s, MAIN_AND_BAK);
    Bytes before = s.files[kMain], bakBefore = s.files[kBak];
    Bytes r = petBytes(200); assert(!commit(s, r.data(), r.size()));
    assert(s.files[kMain] == before && s.files[kBak] == bakBefore && !s.files.count(kTmp));
  }
  printf("PASS a short write that reports success never replaces the good copy\n");

  // A genuine pet record is not mistaken for a bad one: wrong magic is refused.
  { Sim s(ATOMIC); Bytes bad = petBytes(5); bad[0] ^= 1; Bytes b(bad.size() + kTrailer); seal(bad.data(), bad.size(), b.data()); s.files[kMain] = b; assert(loadAge(s) == -1); }
  { Sim s(ATOMIC); assert(!commit(s, (const uint8_t*)"x", 0)); Bytes huge(kMaxRecord + 1); assert(!commit(s, huge.data(), huge.size())); }
  printf("PASS wrong-magic and out-of-range records refused\n");
  return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='lrx-powersave-') as tmp:
    src = Path(tmp) / 'powersave.cpp'; src.write_text(cpp); exe = Path(tmp) / 'powersave'
    subprocess.run(['g++', '-std=c++11', '-Wall', '-fsanitize=address,undefined', '-I', str(root), str(src), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
