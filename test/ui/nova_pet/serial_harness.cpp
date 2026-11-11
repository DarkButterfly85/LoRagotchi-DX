// Host harness for the "nova" serial commands in MyMesh.cpp. Not firmware.
// check_nova_pet_frame.py cuts the real block out of examples/companion_radio/MyMesh.cpp (the part between
// "#ifdef LORAGOTCHI_NOVA_LINK" and "#endif  // LORAGOTCHI_NOVA_LINK") into nova_block.inc and compiles it here
// against a fake Serial port, so the production command handler and output pump are what runs.
#define LORAGOTCHI_NOVA_LINK 1
#include "fake_mono.h"
#include "NovaPetLink.h"
#include "NovaPetTee.h"
#include "LoRaFishIdentity.h"
#include <cstdio>
#include <cstring>
#include <deque>
#include <map>
#include <vector>

static uint32_t g_now = 0;
static uint32_t millis() { return g_now; }

struct MockSerial {
  std::deque<char> in;
  std::string out;
  size_t writes = 0, biggest = 0;
  int available() { return (int)in.size(); }
  int read() { int c = (unsigned char)in.front(); in.pop_front(); return c; }
  size_t print(const char* s) { out += s; return strlen(s); }
  size_t print(char c) { out += c; return 1; }
  size_t write(const uint8_t* p, size_t n) { out.append((const char*)p, n); writes++; if (n > biggest) biggest = n; return n; }
} Serial;

// A fake flash (littlefs style) and the same glue UITask.cpp has: "nova petname" reaches the real
// LoRaFishIdentity::saveWithName(), which writes /lorafish.id through the real LoRaFishSafeSave.
struct FakeFlash {
  std::map<std::string, std::vector<uint8_t>> files;
  bool failWrites = false;
  bool hasRename() const { return true; }
  bool write(const char* p, const uint8_t* d, size_t n) { if (failWrites) return false; files[p] = std::vector<uint8_t>(d, d + n); return true; }
  int read(const char* p, uint8_t* b, size_t cap) {
    auto it = files.find(p); if (it == files.end()) return -1;
    if (it->second.size() > cap) return -2;
    if (!it->second.empty()) memcpy(b, it->second.data(), it->second.size());
    return (int)it->second.size();
  }
  bool exists(const char* p) { return files.count(p) != 0; }
  bool remove(const char* p) { return files.erase(p) != 0; }
  bool rename(const char* a, const char* b) { if (!files.count(a)) return false; auto d = files[a]; files.erase(a); files[b] = d; return true; }
} flash;
static LoRaFishIdentity::Identity liveId;               // what the UI would have in its variables
static LoRaFishIdentity::NameResult setPetName(const char* name) {
  LoRaFishIdentity::Identity saved;
  const LoRaFishIdentity::NameResult r = LoRaFishIdentity::saveWithName(flash, liveId, name, &saved);
  if (r == LoRaFishIdentity::NameOk) liveId = saved;
  return r;
}

class MyMesh { public: void checkNovaSerial(); };
#include "nova_block.inc"

static std::string esc(const std::string& s) {
  std::string r;
  for (char c : s) { if (c == '\n') r += "\\n"; else if (c == '\r') r += "\\r"; else r += c; }
  return r;
}

int main() {
  FakeMono real;
  MyMesh mesh;
  NovaPetTee* tee = nullptr;
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    std::string op; in >> op;
    if (op.empty() || op[0] == '#') continue;
    if (op == "SUP") { int v; in >> v; NovaPetLink::setSupported(v != 0); }
    else if (op == "SETTER") { int v; in >> v; LoRaFishIdentity::setterSlot() = v ? setPetName : nullptr; }   // pet screen present?
    else if (op == "LIVE") { unsigned sp, b, a, e; in >> sp >> b >> a >> e; memset(&liveId, 0, sizeof liveId); liveId.species = (uint16_t)sp; liveId.body = (uint8_t)b; liveId.accent = (uint8_t)a; liveId.eyes = (uint8_t)e; }
    else if (op == "FAIL") { int v; in >> v; flash.failWrites = v != 0; }
    else if (op == "ID") {                       // files on the fake flash, then the identity as a restart would load it
      std::string names;
      for (auto& kv : flash.files) names += (names.empty() ? "" : ",") + kv.first;
      LoRaFishIdentity::Identity got = liveId; memset(got.name, 0, sizeof got.name); strcpy(got.name, "?");
      const LoRaFishSafeSave::Source s = LoRaFishIdentity::load(flash, got);
      printf("ID files=%s src=%d name=[%s] sp=%u genes=%u,%u,%u\n", names.empty() ? "-" : names.c_str(), (int)s, got.name, got.species, got.body, got.accent, got.eyes);
    }
    else if (op == "RX") {                       // RX <text>: \n and \r are written as backslash-n, backslash-r
      std::string t; in.get(); std::getline(in, t);
      for (size_t i = 0; i < t.size(); i++) {
        if (t[i] == '\\' && i + 1 < t.size() && t[i + 1] == 'n') { Serial.in.push_back('\n'); i++; }
        else if (t[i] == '\\' && i + 1 < t.size() && t[i + 1] == 'r') { Serial.in.push_back('\r'); i++; }
        else Serial.in.push_back(t[i]);
      }
    }
    else if (op == "RXLONG") { int n; in >> n; std::string t = "nova pet "; while ((int)t.size() < n) t += 'x'; for (char c : t) Serial.in.push_back(c); Serial.in.push_back('\n'); }
    else if (op == "T") {                        // T <ms>: the radio loop runs once at this time
      in >> g_now; Serial.out.clear(); Serial.writes = 0; mesh.checkNovaSerial();
      printf("OUT %zu %zu %s\n", Serial.out.size(), Serial.writes, esc(Serial.out).c_str());
    }
    else if (op == "F") {                        // F <ms>: the UI draws a frame, through the tee if the stream is on
      in >> g_now;
      NovaPetLink::Link* l = NovaPetLink::supported() ? NovaPetLink::link() : nullptr;
      if (l && l->active(g_now)) { tee = new NovaPetTee(real, *l, g_now); tee->startFrame(); }
      else { real.startFrame(); }
    }
    else if (op == "E") {
      if (tee) { tee->endFrame(); delete tee; tee = nullptr; } else real.endFrame();
    }
    else {
      std::istringstream in2(line); std::string o2; in2 >> o2;
      apply(tee ? (DisplayDriver&)*tee : (DisplayDriver&)real, o2, in2);
    }
  }
  return 0;
}
