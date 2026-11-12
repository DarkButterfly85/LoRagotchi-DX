// Host tests for the Nova link serial speed (examples/companion_radio/NovaBaud.h): the list, rejection of
// unlisted rates, the reply JSON, the saved record, the "nova baud" end to end, and the output pacing.
#define NOVA_BAUD_APPLIES 1   // a UART build: the apply() path is compiled in
#include <gtest/gtest.h>
#include <stdint.h>
#include <string.h>
#include <map>
#include <string>
#include <vector>
#include <helpers/NovaCli.h>
#include "../../examples/companion_radio/NovaBaud.h"
#include "../../examples/companion_radio/NovaPetLink.h"   // sendChunk: the pet sender's pacing

using namespace NovaBaud;

// The same duck-typed store LoRaFishSafeSave takes (flash with rename).
struct MemStore {
  std::map<std::string, std::vector<uint8_t>> f;
  bool failWrites = false;
  bool hasRename() const { return true; }
  bool write(const char* p, const uint8_t* d, size_t n) { if (failWrites) return false; f[p].assign(d, d + n); return true; }
  int read(const char* p, uint8_t* b, size_t cap) {
    auto it = f.find(p);
    if (it == f.end()) return -1;
    if (it->second.size() > cap) return -2;
    memcpy(b, it->second.data(), it->second.size());
    return (int)it->second.size();
  }
  bool exists(const char* p) { return f.count(p) != 0; }
  bool remove(const char* p) { return f.erase(p) != 0; }
  bool rename(const char* a, const char* b) {
    auto it = f.find(a);
    if (it == f.end()) return false;
    f[b] = it->second;
    f.erase(a);
    return true;
  }
};

static std::string say(Status st, uint32_t rate = 0) {
  char out[96];
  size_t n = reply(st, rate, out, sizeof(out));
  EXPECT_EQ(n, strlen(out));
  return out;
}

TEST(NovaBaud, TheListIsShortFixedAndStartsAtTheOldSpeed) {
  ASSERT_EQ(kCount, 4);
  EXPECT_EQ(kRates[0], 115200u);
  EXPECT_EQ(kRates[1], 230400u);
  EXPECT_EQ(kRates[2], 460800u);
  EXPECT_EQ(kRates[3], 921600u);
  EXPECT_EQ(kDefault, 115200u);              // nothing changes for existing users
  EXPECT_EQ(indexOf(kDefault), 0);
  for (uint8_t i = 0; i < kCount; ++i) EXPECT_EQ(indexOf(kRates[i]), i);
  for (uint32_t bad : {0u, 1u, 9600u, 57600u, 115201u, 1000000u, 2000000u, 4294967295u}) {
    EXPECT_FALSE(listed(bad)) << bad;
    EXPECT_EQ(indexOf(bad), -1) << bad;
  }
}

TEST(NovaBaud, ParseAcceptsOnlyListedRates) {
  uint32_t r = 0;
  for (uint8_t i = 0; i < kCount; ++i) {
    char a[16];
    snprintf(a, sizeof(a), "%lu", (unsigned long)kRates[i]);
    r = 0;
    EXPECT_EQ(parse(a, &r), Status::Ok) << a;
    EXPECT_EQ(r, kRates[i]);
  }
  r = 0;
  EXPECT_EQ(parse("  921600  ", &r), Status::Ok);   // spaces around are fine
  EXPECT_EQ(r, 921600u);
}

TEST(NovaBaud, ParseRejectsEverythingElseAndLeavesTheRateAlone) {
  for (const char* bad : {"", " ", "-", "0", "9600", "57600", "115201", "1000000", "3000000", "921601", "0115200", "-115200", "+115200",
                          "115200.0", "115200 x", "x 115200", "1152OO", "0x1C200", "115,200", "115200k", "921600921600",
                          "99999999999999999999", "4294967296", "4294967295", "\t115200"}) {
    uint32_t r = 777;
    EXPECT_EQ(parse(bad, &r), Status::Unsupported) << "[" << bad << "]";
    EXPECT_EQ(r, 777u) << "[" << bad << "]";
  }
  uint32_t r = 777;
  EXPECT_EQ(parse(nullptr, &r), Status::Unsupported);
  EXPECT_EQ(r, 777u);
  EXPECT_EQ(parse("115200", nullptr), Status::Ok);   // a null out is fine
}

TEST(NovaBaud, ReplyLinesAreExact) {
  EXPECT_EQ(say(Status::Ok, 115200), "{\"nova_ok\":\"baud\",\"rate\":115200}");
  EXPECT_EQ(say(Status::Ok, 921600), "{\"nova_ok\":\"baud\",\"rate\":921600}");
  EXPECT_EQ(say(Status::Unsupported), "{\"nova_error\":\"baud_unsupported\"}");
  EXPECT_EQ(say(Status::SaveFailed), "{\"nova_error\":\"baud_save_failed\"}");
  EXPECT_EQ(say(Status::Unavailable), "{\"nova_unavailable\":\"baud\"}");
  // A reply never repeats what was typed, and a line that does not fit becomes "" (never half a line).
  char tiny[8];
  EXPECT_EQ(reply(Status::Ok, 921600, tiny, sizeof(tiny)), 0u);
  EXPECT_STREQ(tiny, "");
  EXPECT_EQ(reply(Status::Ok, 1, nullptr, 10), 0u);
  EXPECT_EQ(reply(Status::Ok, 1, tiny, 0), 0u);
}

TEST(NovaBaud, RecordIsNineBytesAndSealedTo17) {
  uint8_t rec[kRecord];
  ASSERT_TRUE(encode(230400, rec));
  const uint8_t want[kRecord] = { 'N', 'B', 'D', '1', 1, 0x00, 0x84, 0x03, 0x00 };   // 230400 = 0x00038400
  EXPECT_EQ(memcmp(rec, want, sizeof(want)), 0);
  EXPECT_EQ(kSealed, 17u);
  EXPECT_LE(kRecord, LoRaFishSafeSave::kMaxRecord);
  EXPECT_FALSE(encode(9600, rec));      // an unlisted rate is never written
  for (uint8_t i = 0; i < kCount; ++i) {
    ASSERT_TRUE(encode(kRates[i], rec));
    EXPECT_TRUE(recordValid(rec, kRecord));
    EXPECT_EQ(decode(rec, kRecord), kRates[i]);
  }
}

TEST(NovaBaud, SaveThenLoadComesBackAndOtherFilesAreUntouched) {
  MemStore s;
  const std::vector<uint8_t> pet(40, 0xA5), cfg(112, 0x5A), id(35, 0x3C);
  s.f["/lorafish.dat"] = pet; s.f["/lorafish.cfg"] = cfg; s.f["/lorafish.id"] = id;
  EXPECT_EQ(load(s), kDefault);          // no file: the default
  for (uint8_t i = 0; i < kCount; ++i) {
    ASSERT_TRUE(commit(s, kRates[i]));
    EXPECT_EQ(load(s), kRates[i]);
  }
  EXPECT_EQ(s.f["/lorafish.dat"], pet);  // byte for byte
  EXPECT_EQ(s.f["/lorafish.cfg"], cfg);
  EXPECT_EQ(s.f["/lorafish.id"], id);
  EXPECT_EQ(s.f["/lorafish.bd"].size(), kSealed);
  for (auto& kv : s.f) {                 // nothing else was created except our own three names
    const std::string& n = kv.first;
    EXPECT_TRUE(n == "/lorafish.dat" || n == "/lorafish.cfg" || n == "/lorafish.id" || n == "/lorafish.bd" ||
                n == "/lorafish.bdb" || n == "/lorafish.bdt") << n;
  }
}

TEST(NovaBaud, UnlistedRateWritesNothing) {
  MemStore s;
  EXPECT_FALSE(commit(s, 9600));
  EXPECT_TRUE(s.f.empty());
  ASSERT_TRUE(commit(s, 460800));
  const auto before = s.f;
  EXPECT_FALSE(commit(s, 12345));
  EXPECT_EQ(s.f, before);
  EXPECT_EQ(load(s), 460800u);
}

TEST(NovaBaud, DamagedFileFallsBackToTheBackupThenTheDefault) {
  MemStore s;
  ASSERT_TRUE(commit(s, 230400));
  ASSERT_TRUE(commit(s, 921600));        // main = 921600, bak = 230400
  s.f["/lorafish.bd"][6] ^= 0x10;        // bit flip in the main copy
  EXPECT_EQ(load(s), 230400u);
  s.f["/lorafish.bdb"][0] = 'X';         // backup damaged too
  EXPECT_EQ(load(s), kDefault);
  MemStore t;
  t.f["/lorafish.bd"] = std::vector<uint8_t>(9, 0);     // bare record, no trailer: never accepted
  EXPECT_EQ(load(t), kDefault);
  MemStore u;                            // a well sealed record whose rate is no longer in the list
  uint8_t rec[kRecord] = { 'N', 'B', 'D', '1', 1, 0x80, 0x25, 0x00, 0x00 };   // 9600
  uint8_t blob[kSealed];
  LoRaFishSafeSave::seal(rec, kRecord, blob);
  u.f["/lorafish.bd"].assign(blob, blob + sizeof(blob));
  EXPECT_EQ(load(u), kDefault);
}

TEST(NovaBaud, SaveFailureKeepsTheOldChoice) {
  MemStore s;
  ASSERT_TRUE(commit(s, 230400));
  s.failWrites = true;
  EXPECT_FALSE(commit(s, 921600));
  s.failWrites = false;
  EXPECT_EQ(load(s), 230400u);
}

static MemStore* gStore = nullptr;
static uint32_t gLive = kDefault;
static Status testSetter(uint32_t rate) {
  if (!listed(rate)) return Status::Unsupported;
  if (!commit(*gStore, rate)) return Status::SaveFailed;
  gLive = rate;
  return Status::Ok;
}
static std::string nova(const char* line) {
  const NovaCli::Parsed p = NovaCli::parse(line);
  EXPECT_EQ(p.cmd, NovaCli::Cmd::Baud) << line;
  uint32_t rate = 0;
  const Status st = request(p.arg, &rate);
  return say(st, rate);
}

TEST(NovaBaud, NovaBaudWithoutASetterIsUnavailable) {
  setterSlot() = nullptr;
  EXPECT_EQ(nova("nova baud 460800"), "{\"nova_unavailable\":\"baud\"}");
  // and so is NovaCli's own answer (a build that never registered one)
  char out[96];
  reply(NovaCli::parse("nova baud 460800"), "DX-PRO", NovaCli::Caps(), out, sizeof(out));
  EXPECT_STREQ(out, "{\"nova_unavailable\":\"baud\"}");
}

TEST(NovaBaud, NovaBaudEndToEnd) {
  MemStore s; gStore = &s; gLive = kDefault;
  setterSlot() = testSetter;
  EXPECT_EQ(nova("nova baud 230400"), "{\"nova_ok\":\"baud\",\"rate\":230400}");
  EXPECT_EQ(gLive, 230400u);
  EXPECT_EQ(load(s), 230400u);                          // saved
  EXPECT_EQ(nova("nova   baud   921600  "), "{\"nova_ok\":\"baud\",\"rate\":921600}");
  EXPECT_EQ(load(s), 921600u);
  const auto saved = s.f;
  for (const char* bad : {"nova baud", "nova baud 9600", "nova baud 1000000", "nova baud fast", "nova baud -115200", "nova baud 115200 460800",
                          "nova baud 0", "nova baud 921600x", "nova baud 0x1C200"}) {
    EXPECT_EQ(nova(bad), "{\"nova_error\":\"baud_unsupported\"}") << bad;
    EXPECT_EQ(s.f, saved) << bad;                        // nothing written
    EXPECT_EQ(gLive, 921600u) << bad;
  }
  s.failWrites = true;
  EXPECT_EQ(nova("nova baud 115200"), "{\"nova_error\":\"baud_save_failed\"}");
  s.failWrites = false;
  EXPECT_EQ(load(s), 921600u);
  setterSlot() = nullptr;
}

struct FakePort {
  int flushes = 0, updates = 0; uint32_t last = 0;
  void flush() { flushes++; }
  void updateBaudRate(unsigned long r) { updates++; last = (uint32_t)r; }
};

TEST(NovaBaud, ApplyMovesThePortOnceAndOnlyToListedRates) {
  activeRate() = kDefault;
  FakePort p;
  EXPECT_FALSE(apply(p, kDefault));                      // the default: the port is not touched
  EXPECT_FALSE(apply(p, 9600));
  EXPECT_FALSE(apply(p, 0));
  EXPECT_EQ(p.updates, 0);
  EXPECT_TRUE(apply(p, 460800));
  EXPECT_EQ(p.last, 460800u);
  EXPECT_EQ(p.flushes, 1);
  EXPECT_EQ(activeRate(), 460800u);
  EXPECT_FALSE(apply(p, 460800));                        // once
  EXPECT_EQ(p.updates, 1);
  activeRate() = kDefault;
}

TEST(NovaBaud, HelloListsBaudOnlyWhenItWorks) {
  char out[400];
  NovaCli::Caps none;
  NovaCli::reply(NovaCli::parse("nova hello"), "DX-PRO", none, out, sizeof(out));
  EXPECT_EQ(std::string(out).find("baud"), std::string::npos);          // byte for byte what it always said
  NovaCli::Caps c; c.baud = 1;
  size_t n = NovaCli::reply(NovaCli::parse("nova hello"), "DX-PRO", c, out, sizeof(out));
  EXPECT_EQ(n, strlen(out));
  EXPECT_NE(std::string(out).find("\"sendpet\":0,\"baud\":1}}"), std::string::npos) << out;
  EXPECT_LT(n, 320u);                                                   // MyMesh.cpp's msg[320]
}

TEST(NovaBaud, PetSenderPacingFollowsTheSpeed) {
  using namespace NovaPetLink;
  EXPECT_EQ(sendChunk(115200), 96u);     // exactly what the link always sent (96 bytes / 10 ms)
  EXPECT_EQ(sendChunk(230400), 192u);
  EXPECT_EQ(sendChunk(460800), 384u);
  EXPECT_EQ(sendChunk(921600), 512u);    // capped
  EXPECT_EQ(sendChunk(0), 96u);
  EXPECT_EQ(SEND_GAP_MS, 10u);
  for (uint8_t i = 0; i < kCount; ++i) {
    // never more than 85 percent of what the port carries: baud/10 bytes a second
    const double carried = kRates[i] / 10.0 * (SEND_GAP_MS / 1000.0);
    EXPECT_LE((double)sendChunk(kRates[i]), carried * 0.85) << kRates[i];
  }
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
