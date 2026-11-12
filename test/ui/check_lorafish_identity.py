#!/usr/bin/env python3
"""Static pet identity file /lorafish.id (examples/companion_radio/LoRaFishIdentity.h).

python3 test/ui/check_lorafish_identity.py      (Python 3 and g++; no firmware build, no hardware)

  a. a pet record with no /lorafish.id loads unchanged and the defaults are used; writing the identity
     never touches /lorafish.dat, .tmp or .bak (byte for byte), and an old bare record still loads
  b. name, species and colours written to /lorafish.id come back after a reload; the exact bytes on flash
     (27 byte record + 8 byte SafeSave trailer) match a Python reference built with zlib's CRC-32
  c. missing, truncated, bit-flipped, wrong magic/version, unknown species, bad genes: defaults, no crash;
     a bad name alone only loses the name
  d. names of 17 bytes or more, and non-ASCII names, are refused and nothing is written; 16 is fine
  e. LoRaFishState (cut out of UITask.cpp) is still 32 bytes with magic LFM2
  f. UITask.cpp wiring (UITask cannot be built on a PC, so the key pieces are cut out and checked): the
     T-Deck key/value names for the three identity files exist and differ from every other record's key
     (otherwise /lorafish.id would overwrite the pet record), and the load / save / display / reset /
     setter hooks are present in the right order
"""
from pathlib import Path
import re, subprocess, sys, tempfile, zlib

root = Path(__file__).resolve().parents[2]
CR = root / 'examples/companion_radio'


def check(cond, msg):
    if not cond:
        print('FAIL:', msg)
        sys.exit(1)


# ---- e. the pet record layout, taken from the real source ---------------------------------------------
src = (CR / 'ui-new/UITask.cpp').read_text()
m = re.search(r'struct LoRaFishState \{.*?\n\};', src, re.S)
check(m, 'LoRaFishState not found in UITask.cpp')
mg = re.search(r'LORAFISH_MAGIC = (0x[0-9A-Fa-f]+);', src)
check(mg and int(mg.group(1), 16) == 0x4C464D32, 'pet magic is no longer LFM2')

km = re.search(r'static const char\* loRaFishRecordKey\(const char\* path\) \{.*?\n\}', src, re.S)
check(km, 'loRaFishRecordKey not found in UITask.cpp')

cpp = r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>
#include "examples/companion_radio/LoRaFishIdentity.h"
using namespace LoRaFishIdentity;
namespace SS = LoRaFishSafeSave;

''' + m.group(0) + r'''
static_assert(sizeof(LoRaFishState) == 32, "the pet record must stay 32 bytes");

''' + km.group(0) + r'''
static void keysAreSeparate() {                       // f. T-Deck NVS keys
  const char* petMain = SS::kMain; const char* petBak = SS::kBak;
  const char* idMain = LoRaFishIdentity::kMain; const char* idBak = LoRaFishIdentity::kBak; const char* idTmp = LoRaFishIdentity::kTmp;
  const char* others[] = {petMain, petBak, "/lorafish.cfg", "/lfegg0.dat", "/lfegg1.dat"};
  const char* mine[] = {idMain, idBak, idTmp};
  for (const char* m : mine) {
    assert(strlen(loRaFishRecordKey(m)) <= 15);       // NVS key limit
    for (const char* o : others) assert(strcmp(loRaFishRecordKey(m), loRaFishRecordKey(o)) != 0);
  }
  assert(strcmp(loRaFishRecordKey(idMain), loRaFishRecordKey(idBak)) != 0);
  assert(strcmp(loRaFishRecordKey(idMain), loRaFishRecordKey(idTmp)) != 0);
  assert(strcmp(loRaFishRecordKey(idBak), loRaFishRecordKey(idTmp)) != 0);
  assert(!strcmp(loRaFishRecordKey(petMain), "state") && !strcmp(loRaFishRecordKey(petBak), "statebak"));   // pet keys unchanged
  assert(!strcmp(loRaFishRecordKey("/lorafish.cfg"), "cfg") && !strcmp(loRaFishRecordKey("/lfegg0.dat"), "egg0"));
  printf("F_OK\n");
}

typedef std::vector<uint8_t> Bytes;
struct Store {                       // littlefs style: rename replaces the target
  std::map<std::string, Bytes> files;
  bool failWrites = false;
  bool hasRename() const { return true; }
  bool write(const char* p, const uint8_t* d, size_t n) { if (failWrites) return false; files[p] = Bytes(d, d + n); return true; }
  int read(const char* p, uint8_t* b, size_t cap) {
    auto it = files.find(p); if (it == files.end()) return -1;
    if (it->second.size() > cap) return -2;
    if (!it->second.empty()) memcpy(b, it->second.data(), it->second.size());
    return (int)it->second.size();
  }
  bool exists(const char* p) { return files.count(p) != 0; }
  bool remove(const char* p) { return files.erase(p) != 0; }
  bool rename(const char* a, const char* b) { if (!files.count(a)) return false; Bytes d = files[a]; files.erase(a); files[b] = d; return true; }
};

static bool validPet(const uint8_t* rec, size_t len) {
  uint32_t magic; if (len < 4) return false; memcpy(&magic, rec, 4);
  return len == sizeof(LoRaFishState) && magic == 0x4C464D32;
}
static void hex(const char* tag, const Bytes& b) { printf("%s", tag); for (uint8_t c : b) printf(" %02x", c); printf("\n"); }
static Identity mk(const char* name, uint16_t sp, uint8_t b, uint8_t a, uint8_t e) {
  Identity i; memset(&i, 0, sizeof i); strncpy(i.name, name, kNameMax); i.species = sp; i.body = b; i.accent = a; i.eyes = e; return i;
}
static Identity defaults() { return mk("", LoRaFishSpecies::TropicalFish, 2, 3, 4); }
static void sealAndPut(Store& s, const char* path, const Bytes& rec) {
  Bytes out(rec.size() + SS::kTrailer); SS::seal(rec.data(), rec.size(), out.data()); s.files[path] = out;
}
static Bytes goodRecord() { uint8_t r[kRecord]; Identity i = mk("Bubbles", LoRaFishSpecies::Wolf, 8, 247, 6); assert(encode(i, r)); return Bytes(r, r + kRecord); }

int main() {
  static_assert(kRecord == 27 && kSealed == 35, "record size");
  keysAreSeparate();
  // ---- a. existing pet, no identity file
  { Store s; LoRaFishState pet; memset(&pet, 0, sizeof pet); pet.magic = 0x4C464D32; pet.ageMinutes = 1234; pet.happiness = 80;
    assert(SS::commit(s, (const uint8_t*)&pet, sizeof pet));
    assert(SS::commit(s, (const uint8_t*)&pet, sizeof pet));            // second save: main + bak both exist
    uint8_t rec[SS::kMaxRecord]; size_t len = 0;
    assert(SS::load(s, validPet, rec, &len) == SS::Main && len == 32 && !memcmp(rec, &pet, 32));
    Identity id = defaults(); const Identity before = id;
    assert(load(s, id) == SS::None && same(id, before));                // missing: defaults kept
    assert(!s.exists(kMain) && !s.exists(kTmp) && !s.exists(kBak));      // loading creates nothing
    std::map<std::string, Bytes> petFiles = s.files;
    assert(commit(s, mk("Rex", LoRaFishSpecies::Dog, 5, 6, 4)));        // first name: the file is created
    assert(s.exists(kMain) && s.files.size() == petFiles.size() + 1);
    for (auto& kv : petFiles) assert(s.files[kv.first] == kv.second);    // pet files byte for byte unchanged
    assert(SS::load(s, validPet, rec, &len) == SS::Main && !memcmp(rec, &pet, 32));
    // an older bare 32-byte record (no trailer) is still accepted through the unchanged default paths
    Store o; o.files[SS::kMain] = Bytes((uint8_t*)&pet, (uint8_t*)&pet + sizeof pet);
    assert(SS::load(o, validPet, rec, &len) == SS::Legacy && len == 32);
    printf("A_OK\n"); }

  // ---- b. round trip and exact bytes
  { Store s; const Identity want = mk("Bubbles", LoRaFishSpecies::Wolf, 8, 247, 6);
    assert(commit(s, want));
    assert(!s.exists(kTmp));                                              // tmp is renamed away
    hex("MAIN", s.files[kMain]);
    Identity got = defaults(); assert(load(s, got) == SS::Main && same(got, want));
    uint16_t sp[] = {0, 14, 256, 273, 512, 554};                          // first/last of Water, Air, Land
    uint8_t ge[] = {0, 5, 6, 8, 100, 247};
    for (uint16_t id : sp) for (uint8_t g : ge) {
      Store t; Identity w = mk("0123456789ABCDEF", id, g, ge[(g + 1) % 6], ge[(g + 2) % 6]);
      assert(commit(t, w)); Identity r = defaults(); assert(load(t, r) == SS::Main && same(r, w)); }
    { Store t; assert(commit(t, mk("", 3, 0, 0, 0))); Identity r = mk("zzz", 9, 9, 9, 9); assert(load(t, r) == SS::Main && r.name[0] == 0 && r.species == 3); }
    { Store t; assert(commit(t, mk("A", 1, 1, 1, 1))); assert(commit(t, mk("B", 2, 2, 2, 2)));   // second save keeps a backup
      assert(t.exists(kBak)); Identity r = defaults(); assert(load(t, r) == SS::Main && r.name[0] == 'B'); }
    printf("B_OK\n"); }

  // ---- c. missing and damaged
  { Store s; Identity id = defaults(); const Identity before = id;
    assert(load(s, id) == SS::None && same(id, before));
    const Bytes good = goodRecord();
    Bytes sealedGood(good.size() + SS::kTrailer); SS::seal(good.data(), good.size(), sealedGood.data());
    int cases = 0;
    for (size_t i = 0; i < sealedGood.size(); ++i) for (int bit = 0; bit < 8; ++bit) {   // every single bit flip
      Store t; Bytes b = sealedGood; b[i] ^= (uint8_t)(1 << bit); t.files[kMain] = b;
      Identity r = defaults(); assert(load(t, r) == SS::None && same(r, before)); ++cases; }
    for (size_t n = 0; n <= 70; ++n) if (n != sealedGood.size()) {                     // truncated / too long
      Store t; Bytes b(n, 0x5A); for (size_t i = 0; i < n && i < sealedGood.size(); ++i) b[i] = sealedGood[i]; t.files[kMain] = b;
      Identity r = defaults(); assert(load(t, r) == SS::None && same(r, before)); ++cases; }
    { Store t; t.files[kMain] = good; Identity r = defaults(); assert(load(t, r) == SS::None && same(r, before)); ++cases; }   // bare, no trailer
    { Store t; t.files[kMain] = Bytes(35, 0xFF); Identity r = defaults(); assert(load(t, r) == SS::None && same(r, before)); ++cases; }
    { Store t; t.files[kMain] = Bytes(35, 0x00); Identity r = defaults(); assert(load(t, r) == SS::None && same(r, before)); ++cases; }
    struct Edit { size_t at; uint8_t v; } bad[] = { {0,'X'}, {4,0}, {4,2}, {22,255}, {23,0x7F}, {23,1}, {24,7}, {24,248}, {25,255}, {26,250} };
    for (auto e : bad) {                                                               // valid seal, invalid content
      Bytes r = good; r[e.at] = e.v; Store t; sealAndPut(t, kMain, r);
      Identity x = defaults(); assert(load(t, x) == SS::None && same(x, before)); ++cases; }
    { Store t; sealAndPut(t, kMain, Bytes(good.begin(), good.begin() + 26)); Identity x = defaults(); assert(load(t, x) == SS::None && same(x, before)); ++cases; }
    // a bad name alone loses only the name: species and colours are still good
    std::vector<Bytes> names;
    for (uint8_t v : {0x01, 0x7F, 0xFF, 0xC3}) { Bytes r = good; r[7] = v; names.push_back(r); }
    { Bytes r = good; r[5 + 10] = 'Z'; names.push_back(r); }                                   // junk after the NUL
    { Bytes r = good; for (size_t i = 5; i < 5 + 17; ++i) r[i] = 'x'; names.push_back(r); }    // 17 letters, no NUL
    for (const Bytes& r : names) {
      Store t; sealAndPut(t, kMain, r); Identity x = defaults();
      assert(load(t, x) == SS::Main && x.name[0] == 0 && x.species == LoRaFishSpecies::Wolf && x.body == 8 && x.accent == 247 && x.eyes == 6); ++cases; }
    // main damaged, backup good: the previous good copy is used (this is what SafeSave is for)
    { Store t; assert(commit(t, mk("Old", 2, 2, 2, 2))); assert(commit(t, mk("New", 3, 3, 3, 3)));
      t.files[kMain][3] ^= 1; Identity x = defaults(); assert(load(t, x) == SS::Bak && !strcmp(x.name, "Old")); ++cases; }
    // main and backup both damaged: defaults
    { Store t; assert(commit(t, mk("Old", 2, 2, 2, 2))); assert(commit(t, mk("New", 3, 3, 3, 3)));
      t.files[kMain][3] ^= 1; t.files[kBak][5] ^= 1; Identity x = defaults(); assert(load(t, x) == SS::None && same(x, before)); ++cases; }
    printf("C_OK %d\n", cases); }

  // ---- d. names
  { Store s; assert(checkName("") == NameOk && checkName("0123456789ABCDEF") == NameOk && checkName(nullptr) == NameOk);
    assert(checkName("0123456789ABCDEFG") == NameTooLong && checkName("this name is far too long for sure") == NameTooLong);
    assert(checkName("caf\xC3\xA9") == NameBadChar && checkName("tab\t") == NameBadChar && checkName("\x7F") == NameBadChar);
    Identity live = mk("", LoRaFishSpecies::TropicalFish, 1, 2, 3), saved = live;
    assert(saveWithName(s, live, "0123456789ABCDEFG", &saved) == NameTooLong && s.files.empty());
    assert(saveWithName(s, live, "caf\xC3\xA9", &saved) == NameBadChar && s.files.empty());
    { Identity bad = live; bad.species = 15; uint8_t r[kRecord]; assert(!encode(bad, r)); assert(saveWithName(s, bad, "x", &saved) == NameSaveFailed && s.files.empty()); }
    { Identity longName; memset(&longName, 0, sizeof longName); memset(longName.name, 'a', kNameMax); longName.species = 0; uint8_t r[kRecord]; assert(encode(longName, r)); }
    assert(saveWithName(s, live, "0123456789ABCDEF", &saved) == NameOk && !strcmp(saved.name, "0123456789ABCDEF") && saved.body == 1);
    assert(saveWithName(s, live, "Fluffy", &saved) == NameOk);
    Identity r = defaults(); assert(load(s, r) == SS::Main && !strcmp(r.name, "Fluffy") && r.species == 0 && r.body == 1 && r.accent == 2 && r.eyes == 3);
    assert(saveWithName(s, r, "", &saved) == NameOk);                    // empty clears the name
    r = defaults(); assert(load(s, r) == SS::Main && r.name[0] == 0 && r.body == 1);
    s.failWrites = true; assert(saveWithName(s, live, "Nope", &saved) == NameSaveFailed);
    s.failWrites = false; r = defaults(); assert(load(s, r) == SS::Main && r.name[0] == 0);   // the failed save changed nothing
    assert(requestName("x") == NameNoPet);                                // no setter registered: no pet screen
    assert(requestName("0123456789ABCDEFG") == NameTooLong);
    printf("D_OK\n"); }
  return 0;
}
'''

work = Path(tempfile.mkdtemp(prefix='lfid_'))
(work / 't.cpp').write_text(cpp)
exe = work / 't'
cc = subprocess.run(['g++', '-std=c++17', '-O1', '-Wall', '-Wextra', '-Werror', '-I', str(root), '-I', str(root / 'src'), '-I', str(CR),
                     '-I', str(CR / 'ui-new'), str(work / 't.cpp'), '-o', str(exe)], capture_output=True, text=True, timeout=180)
check(cc.returncode == 0, 'did not compile:\n' + cc.stdout + cc.stderr)
run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=120)
check(run.returncode == 0, 'test program failed (%d): %s%s' % (run.returncode, run.stdout, run.stderr))
out = run.stdout
for tag in ('A_OK', 'B_OK', 'C_OK', 'D_OK', 'F_OK'):
    check(tag in out, tag + ' missing:\n' + out)

# ---- f. wiring in UITask.cpp (text checks: order and presence) ---------------------------------------------
def at(s, what):
    i = src.find(s)
    check(i >= 0, 'UITask.cpp: missing ' + what)
    return i


at('static_assert(sizeof(LoRaFishState) == 32', 'static_assert on the pet record size')
i_load = at('  loadLoRaFishIdentity();\n  LoRaFishIdentity::setterSlot() = setLoRaFishPetName;', 'identity load + setter registration in begin()')
check(i_load > at('  loadLoRaFish();\n  loadLoRaFishSettings();', 'pet and settings load in begin()'), 'identity must load after the pet record and settings')
check(i_load > at('LORAFISH_MONOCHROME_COLOR;\n  }\n  loadLoRaFishIdentity();', 'identity after the mono colour fallback'), 'identity after mono fallback')
check(src.count('syncLoRaFishIdentity();') == 2, 'settings save must sync the identity on both exits (changed / unchanged)')
body = src[at('static void saveLoRaFishSettings() {', 'saveLoRaFishSettings'):]
body = body[:body.index('\n}\n')]
check(body.count('syncLoRaFishIdentity();') == 2, 'both syncs belong to saveLoRaFishSettings')
check('loRaFishIdName[0]) {' in src[at('static const char* loRaFishDisplayName()', 'display name'):][:200], 'the header name prefers the pet name')
check('loRaFishIdName[0] = 0;' in src[at('static void resetLoRaFishPet() {', 'reset'):][:300], 'a reset pet does not keep the old name')
check('LoRaFishSafeSave::commit(loRaFishPetStore, (const uint8_t*)&fish, sizeof(fish))' in src, 'the pet record is still saved the old way, 32 bytes')
check('loRaFishProtocolName' in src and 'LoRaFishText::protocolName(name, sizeof(name), loRaFishMeshNodeName, 32)' in src, 'the radio/visit name still comes from the node name')
# the identity code never writes the pet files or the settings file
blk = src[at('// ---- static pet identity (/lorafish.id)', 'identity block'):at('static bool loRaFishPetRecordValid', 'pet record check')]
for banned in ('"/lorafish.dat"', '"/lorafish.cfg"', 'kMain', 'writeLoRaFishRecord', 'encodeLoRaFishSettings'):
    check(banned not in blk, 'identity block must not touch ' + banned)

# ---- b. exact bytes against a Python reference ---------------------------------------------------------
def ref(name, species, body, accent, eyes):
    rec = b'LFI1' + bytes([1]) + name.encode().ljust(17, b'\0') + species.to_bytes(2, 'little') + bytes([body, accent, eyes])
    check(len(rec) == 27, 'reference record size')
    return rec + b'LSV1' + zlib.crc32(rec).to_bytes(4, 'little')


line = [l for l in out.splitlines() if l.startswith('MAIN')][0]
main = bytes(int(x, 16) for x in line.split()[1:])
expect = ref('Bubbles', 551, 8, 247, 6)
check(main == expect, 'bytes on flash differ:\n  got    %s\n  expect %s' % (main.hex(), expect.hex()))
check(len(main) == 35, 'sealed size')
print('/lorafish.id (Bubbles, Wolf 551, genes 8/247/6) = ' + main.hex(' '))
print([l for l in out.splitlines() if l.startswith('C_OK')][0].replace('C_OK', 'damaged-file cases that fell back cleanly:'))
print('identity: ok (a existing pet unchanged, b round trip + exact bytes, c damaged files, d names, e LoRaFishState = 32 bytes, f UITask wiring + NVS keys)')
