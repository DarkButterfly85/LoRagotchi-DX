#!/usr/bin/env python3
"""'nova contacts' serial command + the shared DX eligibility filter.

python3 test/ui/check_nova_contacts.py   (Python 3 and g++; no firmware build, no hardware)

Compiles the production examples/companion_radio/LoRaFishEligible.h (the filter the visit picker
uses and the JSON writer the serial command uses) against a fake contact table:
  - only eligible contacts are listed (chat with fish marker; 'LRX1 ' repeater with fish marker);
    chat without a marker, 'LRX1 ' repeater without a marker, other repeaters and rooms are not
  - at most 16 entries, in table order
  - quotes, backslashes and control characters are JSON-escaped
  - names are cut at 32 bytes on a UTF-8 character boundary
  - the output parses as JSON (checked by Python) and is a single line
Also checks the wiring in the sources: UITask.cpp no longer defines its own filter, MyMesh.cpp
only answers 'nova contacts' on the serial console, and no other 'nova ...' command exists.
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CPP = r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <string>
#include <vector>
#define LORAGOTCHI_DXPRO 1
static constexpr uint8_t ADV_TYPE_CHAT=1, ADV_TYPE_REPEATER=2, ADV_TYPE_ROOM=3;
static constexpr size_t PUB_KEY_SIZE=32;
struct ContactInfo {char name[32];uint8_t type=ADV_TYPE_CHAT;struct {uint8_t pub_key[PUB_KEY_SIZE]={};} id;};
#include "examples/companion_radio/LoRaFishEligible.h"

static const char FISH[]="\xF0\x9F\x90\x9F";
struct Sink { std::string out; void write(const char* p, size_t n){ out.append(p,n); } };
static ContactInfo mk(const char* name, uint8_t type, uint8_t key) {
  ContactInfo c;
  memset(c.name,0,sizeof(c.name));
  strncpy(c.name,name,sizeof(c.name)-1);
  c.type=type;
  for (int i=0;i<32;++i) c.id.pub_key[i]=(uint8_t)(key+i);
  return c;
}
static ContactInfo raw32(const std::string& bytes, uint8_t key) {   // exactly 32 bytes, no NUL
  assert(bytes.size()==32);
  ContactInfo c;
  memcpy(c.name,bytes.data(),32);
  c.type=ADV_TYPE_CHAT;
  memset(c.id.pub_key,key,32);
  return c;
}
static std::string run(const std::vector<ContactInfo>& table, unsigned* count) {
  Sink s;
  *count = NovaContacts::writeJson(s, [&](uint32_t i, ContactInfo& c){ if (i>=table.size()) return false; c=table[i]; return true; });
  return s.out;
}
int main() {
  unsigned n=0;
  // 1. Eligibility mix: indexes 0 and 2 are the only eligible ones.
  std::vector<ContactInfo> t = {
    mk((std::string("Chat Fish ")+FISH).c_str(), ADV_TYPE_CHAT, 0x10),
    mk("Chat No Marker", ADV_TYPE_CHAT, 0x20),
    mk((std::string("LRX1 Tank ")+FISH).c_str(), ADV_TYPE_REPEATER, 0x30),
    mk("LRX1 Plain Tank", ADV_TYPE_REPEATER, 0x40),
    mk((std::string("Other Repeater ")+FISH).c_str(), ADV_TYPE_REPEATER, 0x50),
    mk((std::string("LRX1 Room ")+FISH).c_str(), ADV_TYPE_ROOM, 0x60),
    mk((std::string("LRX1Tank ")+FISH).c_str(), ADV_TYPE_REPEATER, 0x70),
  };
  for (size_t i=0;i<t.size();++i) assert(loRaFishDXEligible(t[i]) == (i==0 || i==2));
  std::string j=run(t,&n);
  assert(n==2);
  printf("%s\n", j.c_str());
  // 2. Empty table / nothing eligible.
  assert(run({mk("nope",ADV_TYPE_CHAT,1)},&n)=="{\"contacts\":[]}" && n==0);
  assert(run({},&n)=="{\"contacts\":[]}" && n==0);
  // 3. Cap of 16: 40 eligible contacts, the first 16 in table order.
  std::vector<ContactInfo> many;
  for (int i=0;i<40;++i) {
    char nm[32];
    snprintf(nm,sizeof(nm),"F%02d %s",i,FISH);
    many.push_back(mk(nm,ADV_TYPE_CHAT,(uint8_t)i));
  }
  j=run(many,&n);
  assert(n==16);
  printf("%s\n", j.c_str());
  // 4. Escaping and full-width names.
  std::vector<ContactInfo> esc;
  esc.push_back(mk((std::string("a\"b\\c ")+FISH).c_str(),ADV_TYPE_CHAT,1));
  esc.push_back(mk((std::string("t\tn\nr\r\x01\x1f\x7f ")+FISH).c_str(),ADV_TYPE_CHAT,2));
  esc.push_back(raw32(FISH+std::string(28,'y'),0xAB));                           // full 32 bytes, no NUL
  esc.push_back(raw32(FISH+std::string(27,'z')+"\xC3",0xCD));                    // lead byte of a split character at the end
  esc.push_back(raw32(FISH+std::string(26,'w')+"\xC3\xA9",0xEF));                // 2-byte character fits exactly
  j=run(esc,&n);
  assert(n==5);
  printf("%s\n", j.c_str());
  // 5. Over-long names (longer buffer than the contact field): cut at 32 bytes on a character boundary.
  char o[6*32+1];
  std::string r;
  { std::string a(40,'q'); NovaContacts::escapeName(o,a.c_str(),64); r+=o; r+="|"; }                       // plain 40 -> 32
  { std::string a(28,'x'); a+=FISH; a+="tail"; NovaContacts::escapeName(o,a.c_str(),64); r+=o; r+="|"; }    // fish ends exactly at byte 32: kept
  { std::string a(29,'x'); a+=FISH; NovaContacts::escapeName(o,a.c_str(),64); r+=o; r+="|"; }               // fish spans bytes 30-33: dropped whole
  { std::string a(30,'x'); a+="\xC3\xA9\xC3\xA9"; NovaContacts::escapeName(o,a.c_str(),64); r+=o; r+="|"; } // one e-acute kept, one cut
  { std::string a(31,'x'); a+="\xC3\xA9"; NovaContacts::escapeName(o,a.c_str(),64); r+=o; r+="|"; }        // e-acute spans 32-33: dropped
  { std::string a(40,'"'); NovaContacts::escapeName(o,a.c_str(),64); assert(strlen(o)==64); r+=o; }        // escapes expand the output, not the 32 bytes
  printf("%s\n", r.c_str());
  return 0;
}
'''
with tempfile.TemporaryDirectory() as d:
    src = Path(d) / 'nova_contacts.cpp'
    exe = Path(d) / 'nova_contacts'
    src.write_text(CPP)
    subprocess.run(['g++', '-std=c++17', '-Wall', '-Werror', '-I', str(ROOT), '-I', str(ROOT / 'src'), str(src), '-o', str(exe)], check=True, timeout=120)
    out = subprocess.run([str(exe)], check=True, capture_output=True, text=True, timeout=30).stdout.splitlines()
assert len(out) == 4, out
FISH = '\U0001F41F'

# Mixed table: exactly the two eligible contacts, with their 12-hex short ids.
assert json.loads(out[0]) == {'contacts': [{'n': 'Chat Fish ' + FISH, 'id': '101112131415'},
                                           {'n': 'LRX1 Tank ' + FISH, 'id': '303132333435'}]}, out[0]

# Cap: 16 entries, table order F00..F15, no F16+.
many = json.loads(out[1])['contacts']
assert [c['n'] for c in many] == ['F%02d %s' % (i, FISH) for i in range(16)], many
assert all(re.fullmatch(r'[0-9a-f]{12}', c['id']) for c in many)

# Escaping: the raw line has no control characters; the parsed names round-trip exactly.
raw = out[2]
assert all(ord(ch) >= 0x20 and ord(ch) != 0x7F for ch in raw), 'control character leaked into the line'
for needle in ('\\"', '\\\\', '\\u0009', '\\u000a', '\\u000d', '\\u0001', '\\u001f', '\\u007f'):
    assert needle in raw, needle
esc = json.loads(raw)['contacts']
assert len(esc) == 5, esc
assert esc[0]['n'] == 'a"b\\c ' + FISH
assert esc[1]['n'] == 't\tn\nr\r\x01\x1f\x7f ' + FISH
assert esc[2] == {'n': FISH + 'y' * 28, 'id': 'abababababab'}                    # 32 bytes, unterminated
assert esc[3] == {'n': FISH + 'z' * 27, 'id': 'cdcdcdcdcdcd'}                    # split character dropped, never half of one
assert esc[4] == {'n': FISH + 'w' * 26 + '\u00e9', 'id': 'efefefefefef'}
assert all(len(c['n'].encode()) <= 32 for c in esc)

# Over-long names are cut at 32 bytes on a character boundary.
cuts = [json.loads('"' + piece + '"') for piece in out[3].split('|')]
assert cuts[0] == 'q' * 32
assert cuts[1] == 'x' * 28 + FISH and len(cuts[1].encode()) == 32
assert cuts[2] == 'x' * 29
assert cuts[3] == 'x' * 30 + '\u00e9' and len(cuts[3].encode()) == 32
assert cuts[4] == 'x' * 31
assert cuts[5] == '"' * 32

# Source wiring.
ui = (ROOT / 'examples/companion_radio/ui-new/UITask.cpp').read_text()
mesh = (ROOT / 'examples/companion_radio/MyMesh.cpp').read_text()
assert 'static bool loRaFishDXEligible' not in ui and '#include "../LoRaFishEligible.h"' in ui
assert 'loRaFishDXEligible(c)' in ui                                    # the picker still calls the shared filter
assert '#include "LoRaFishEligible.h"' in mesh
# (the quoted "nova petname" is a comment on an include; the other nova commands are matched by word in the serial block)
assert sorted(set(re.findall(r'"nova [a-z]+"', mesh))) == ['"nova contacts"', '"nova petname"'], 'unexpected quoted nova command'
blk = mesh[mesh.index('#ifdef LORAGOTCHI_NOVA_LINK\n// ---- LORAGOTCHI NOVA serial link'):]
assert 'n == 8 && strncmp(w, "contacts", 8) == 0' in blk and 'NovaContacts::writeJson(sink, getContact)' in blk   # normal mode too
assert 'strcmp(command, "nova contacts") == 0 && _cli_from_serial' in mesh
hdr = (ROOT / 'examples/companion_radio/LoRaFishEligible.h').read_text()
assert '!strncmp(c.name, "LRX1 ", 5)' in hdr and 'c.type == ADV_TYPE_CHAT' in hdr
print('PASS: nova contacts (eligibility, cap 16, escaping, 32-byte cut, wiring)')
