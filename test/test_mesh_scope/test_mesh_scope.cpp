// Host tests for helpers/MeshScope.h (LODESTAR ORION / NOVA lineage): the packet ring behind the
// dashboard's mesh analyzer, and the {"mesh":{...}} line it streams.
#include <gtest/gtest.h>

#include <stdint.h>
#include <string.h>
#include <string>

#include <helpers/MeshScope.h>

using meshscope::Rec;
using meshscope::Scope;

namespace {

Rec rec(uint32_t ms, uint8_t type, bool tx, int16_t rssi = -90) {
  Rec r;
  memset(&r, 0, sizeof(r));
  r.ms = ms;
  r.type = type;
  r.tx = tx ? 1 : 0;
  r.rssi = rssi;
  return r;
}

}  // namespace

TEST(MeshScopeRing, StartsEmpty) {
  Scope s;
  EXPECT_EQ(0u, s.head);
  EXPECT_EQ(0u, s.sent);
  EXPECT_EQ(0u, s.rx);
  EXPECT_EQ(0u, s.tx);
  for (int i = 0; i < 16; i++) EXPECT_EQ(0u, s.by_type[i]);
  EXPECT_EQ(64, (int)Scope::N);
}

TEST(MeshScopeRing, HeadAndCountersFollowEveryRecord) {
  Scope s;
  for (int i = 0; i < 5; i++) s.add(rec(100 + i, 4, false));
  for (int i = 0; i < 3; i++) s.add(rec(200 + i, 1, true));
  EXPECT_EQ(8u, s.head);
  EXPECT_EQ(5u, s.rx);
  EXPECT_EQ(3u, s.tx);
  EXPECT_EQ(5u, s.by_type[4]);
  EXPECT_EQ(3u, s.by_type[1]);
  EXPECT_EQ(100u, s.ring[0].ms);
  EXPECT_EQ(202u, s.ring[7].ms);
  s.add(rec(1, 0x1F, false));  // the type is masked to 0..15
  EXPECT_EQ(1u, s.by_type[15]);
}

TEST(MeshScopeRing, WrapsAtSixtyFour) {
  Scope s;
  for (uint32_t i = 0; i < 64; i++) s.add(rec(i, 2, i % 2));
  EXPECT_EQ(64u, s.head);
  EXPECT_EQ(0u, s.ring[0].ms);
  EXPECT_EQ(63u, s.ring[63].ms);

  s.add(rec(64, 2, false));  // record 64 overwrites slot 0
  EXPECT_EQ(65u, s.head);
  EXPECT_EQ(64u, s.ring[0].ms);
  EXPECT_EQ(1u, s.ring[1].ms);

  for (uint32_t i = 65; i < 70; i++) s.add(rec(i, 2, false));
  EXPECT_EQ(70u, s.head);
  for (uint32_t i = 0; i < 6; i++) EXPECT_EQ(64 + i, s.ring[i].ms) << i;
  for (uint32_t i = 6; i < 64; i++) EXPECT_EQ(i, s.ring[i].ms) << i;
  // the counters count everything ever added, not what is still in the ring
  EXPECT_EQ(70u, s.rx + s.tx);
  EXPECT_EQ(32u, s.tx);   // odd i in 0..63
  EXPECT_EQ(38u, s.rx);
  EXPECT_EQ(70u, s.by_type[2]);
}

TEST(MeshScopeRx, ReceivedPacketFieldsAreClampedAndPacked) {
  Scope s;
  uint8_t path[3] = {0xA1, 0xB2, 0xC3};
  uint8_t payload[2] = {0x11, 0x22};
  s.onRx(5000, -97.4f, -7.3f, 1, 2, 3, 1, path, payload, 2, 300);
  ASSERT_EQ(1u, s.head);
  EXPECT_EQ(1u, s.rx);
  const Rec& r = s.ring[0];
  EXPECT_EQ(5000u, r.ms);
  EXPECT_EQ(-97, r.rssi);
  EXPECT_EQ(-29, r.snr4);      // -7.3 dB * 4 = -29.2 -> -29
  EXPECT_EQ(1, r.type);
  EXPECT_EQ(2, r.rt);
  EXPECT_EQ(3, r.hops);
  EXPECT_EQ(255, r.len);       // capped
  EXPECT_EQ(0, r.tx);
  EXPECT_EQ(1, r.idn);
  EXPECT_EQ(0xC3, r.id[0]);    // last hop with 1-byte hashes: path[(3-1)*1]
  EXPECT_EQ(1, r.has_src);
  EXPECT_EQ(0x22, r.src);      // dest hash, then source hash
}

TEST(MeshScopeRx, AdvertAtZeroHopsNamesTheSenderKeyAndSource) {
  Scope s;
  uint8_t payload[40];
  for (int i = 0; i < 40; i++) payload[i] = (uint8_t)(0x70 + i);
  s.onRx(10, -80.0f, 5.0f, 4, 1, 0, 1, nullptr, payload, 40, 100);
  const Rec& r = s.ring[0];
  EXPECT_EQ(3, r.idn);
  EXPECT_EQ(0x70, r.id[0]);
  EXPECT_EQ(0x71, r.id[1]);
  EXPECT_EQ(0x72, r.id[2]);
  EXPECT_EQ(1, r.has_src);
  EXPECT_EQ(0x70, r.src);
  EXPECT_EQ(20, r.snr4);
}

TEST(MeshScopeRx, SaturatesRssiAndSnr) {
  Scope s;
  s.onRx(1, -99999.0f, 100.0f, 0, 0, 0, 1, nullptr, nullptr, 0, -4);
  EXPECT_EQ(-32000, s.ring[0].rssi);
  EXPECT_EQ(127, s.ring[0].snr4);
  EXPECT_EQ(0, s.ring[0].len);
  s.onRx(2, 99999.0f, -100.0f, 0, 0, 0, 1, nullptr, nullptr, 0, 10);
  EXPECT_EQ(32000, s.ring[1].rssi);
  EXPECT_EQ(-128, s.ring[1].snr4);
}

TEST(MeshScopeTx, SentPacketsCountAsTx) {
  Scope s;
  s.onTx(300, 0x12, 5, 64);
  ASSERT_EQ(1u, s.head);
  EXPECT_EQ(1u, s.tx);
  EXPECT_EQ(0u, s.rx);
  const Rec& r = s.ring[0];
  EXPECT_EQ(1, r.tx);
  EXPECT_EQ(2, r.type);  // masked
  EXPECT_EQ(1, r.rt);    // masked
  EXPECT_EQ(64, r.len);
  EXPECT_EQ(0, r.rssi);
}

TEST(MeshScopeLine, ShapeMatchesTheDashboardPlan) {
  Scope s;
  uint8_t path[1] = {0xAB};
  uint8_t payload[2] = {0x01, 0xCD};
  s.onRx(1000, -91.0f, 6.0f, 2, 1, 1, 1, path, payload, 2, 40);
  s.onTx(1500, 4, 1, 90);
  char out[2048];
  size_t n = s.line(2000, out, sizeof(out), -112, 8, 125.0f, 5, false);
  ASSERT_GT(n, 0u);
  EXPECT_EQ(strlen(out), n);
  EXPECT_STREQ("{\"mesh\":{\"nf\":-112,\"sf\":8,\"bw\":125.0,\"cr\":5,\"rx\":1,\"tx\":1,"
               "\"ty\":[0,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0],"
               "\"p\":[[1000,-91,24,2,1,40,1,0,\"ab\",\"cd\"],[500,0,0,4,0,90,1,1,\"\",\"\"]]}}",
               out);
  EXPECT_EQ(2u, s.sent);  // streamed
}

TEST(MeshScopeLine, OnlyUnsentRecordsGoOutAndForceSendsAnEmptyList) {
  Scope s;
  char out[2048];
  EXPECT_EQ(0u, s.line(10, out, sizeof(out), -100, 7, 250.0f, 5, false));  // nothing to say
  size_t n = s.line(10, out, sizeof(out), -100, 7, 250.0f, 5, true);
  ASSERT_GT(n, 0u);
  EXPECT_NE(nullptr, strstr(out, "\"p\":[]}}"));
  EXPECT_NE(nullptr, strstr(out, "\"bw\":250.0"));

  s.add(rec(5, 3, false));
  ASSERT_GT(s.line(20, out, sizeof(out), -100, 7, 250.0f, 5, false), 0u);
  EXPECT_EQ(0u, s.line(30, out, sizeof(out), -100, 7, 250.0f, 5, false));
  s.add(rec(25, 3, false));
  ASSERT_GT(s.line(40, out, sizeof(out), -100, 7, 250.0f, 5, false), 0u);
  EXPECT_NE(nullptr, strstr(out, "\"p\":[[15,"));  // only the new record, 15 ms old
}

TEST(MeshScopeLine, FallingBehindSkipsTheOldestAndStreamsTheWrappedRing) {
  Scope s;
  for (uint32_t i = 0; i < 70; i++) s.add(rec(i, 2, false));
  char out[8192];
  size_t n = s.line(1000, out, sizeof(out), -100, 7, 125.0f, 5, false);
  ASSERT_GT(n, 0u);
  EXPECT_EQ(70u, s.sent);
  std::string line(out);
  EXPECT_NE(std::string::npos, line.find("\"rx\":70,\"tx\":0"));
  // records 6..69 (age 994..931); 0..5 were overwritten
  EXPECT_NE(std::string::npos, line.find("\"p\":[[994,"));
  EXPECT_EQ(std::string::npos, line.find("[1000,"));
  size_t records = 0;
  for (size_t p = line.find("],["); p != std::string::npos; p = line.find("],[", p + 1)) records++;
  EXPECT_EQ(63u, records);  // 64 records = 63 separators
  EXPECT_EQ(0u, s.line(2000, out, sizeof(out), -100, 7, 125.0f, 5, false));
}

TEST(MeshScopeLine, TooSmallABufferGivesNothingAndASmallOneSplitsTheRecords) {
  Scope s;
  for (uint32_t i = 0; i < 10; i++) s.add(rec(i, 2, false));
  char tiny[20];
  EXPECT_EQ(0u, s.line(100, tiny, sizeof(tiny), -100, 7, 125.0f, 5, false));
  // room for only some records: the rest goes out in the next line
  char small[260];
  size_t n = s.line(100, small, sizeof(small), -100, 7, 125.0f, 5, false);
  ASSERT_GT(n, 0u);
  EXPECT_LT(s.sent, 10u);
  EXPECT_GT(s.sent, 0u);
  uint32_t first = s.sent;
  char big[2048];
  ASSERT_GT(s.line(100, big, sizeof(big), -100, 7, 125.0f, 5, false), 0u);
  EXPECT_EQ(10u, s.sent);
  EXPECT_LT(first, 10u);
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
