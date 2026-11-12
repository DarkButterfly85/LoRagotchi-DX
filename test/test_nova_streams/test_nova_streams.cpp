// Host tests for helpers/NovaStreams.h: the lines the Nova dashboard's Mesh analyzer, Best uplink, Repeaters, Speed, Battery and
// Messages-you-sent panels read, how often they may go out, and that the hello only claims what works.
#include <gtest/gtest.h>

#include <stdint.h>
#include <string.h>
#include <string>

#include <helpers/NovaCli.h>
#include <helpers/NovaStreams.h>

using namespace NovaStreams;

namespace {

// a one-line JSON text is balanced, has no raw line end and no control bytes
bool oneLineJson(const std::string& s) {
  int depth = 0; bool str = false;
  for (size_t i = 0; i < s.size(); i++) {
    unsigned char c = (unsigned char)s[i];
    if (c < 32) return false;
    if (str) { if (c == '\\') i++; else if (c == '"') str = false; continue; }
    if (c == '"') str = true;
    else if (c == '{' || c == '[') depth++;
    else if (c == '}' || c == ']') { if (--depth < 0) return false; }
  }
  return depth == 0 && !str;
}
bool has(const std::string& s, const char* t) { return s.find(t) != std::string::npos; }

std::string takeLine(Hub& h) {                  // what the next write to the port would be: one whole line, then the outbox is empty
  std::string s((const char*)h.out.data(), h.out.pending());
  h.out.consumed(h.out.pending());
  return s;
}

const uint8_t kPath[3] = {0xA1, 0xB2, 0xC3};
int curve(uint16_t mv) { return mv >= 4200 ? 100 : mv <= 3300 ? 0 : (mv - 3300) / 9; }

void heardRepeater(Hub& h, uint32_t now, uint8_t id, float snr, float rssi = -90) {
  uint8_t path[1] = {id};
  h.onRx(now, rssi, snr, 2, 1, 1, 1, path, kPath, 3, 40);          // a flood text relayed by repeater id
}

}  // namespace

// ---- mesh line ---------------------------------------------------------------------------------------------

TEST(NovaStreamsMesh, LineHasTheFieldsTheDashboardReads) {
  Hub h; h.nf = -112; h.sf = 10; h.bw = 250.0f; h.cr = 5;
  uint8_t path[2] = {0x11, 0x22};
  h.onRx(1000, -97.4f, 6.25f, 2, 1, 2, 1, path, kPath, 3, 55);
  h.onTx(1200, 4, 1, 60);
  ASSERT_TRUE(h.askMesh(2000));
  std::string s = takeLine(h);
  ASSERT_EQ(s.back(), '\n');
  s.pop_back();
  EXPECT_TRUE(oneLineJson(s)) << s;
  EXPECT_EQ(s.rfind("{\"mesh\":{\"nf\":-112,\"sf\":10,\"bw\":250.0,\"cr\":5,\"rx\":1,\"tx\":1,\"ty\":[", 0), 0u) << s;     // the order the page's decoder expects
  EXPECT_TRUE(has(s, "\"p\":[[1000,-97,25,2,2,55,1,0,\"22\",\"")) << s;           // age, rssi, snr in quarter dB, type, hops, len, route, tx, last hop
  EXPECT_TRUE(has(s, "[800,0,0,4,0,60,1,1,\"\",\"\"]")) << s;                      // the packet we sent
  EXPECT_EQ(s.find('\n'), std::string::npos);
}

TEST(NovaStreamsMesh, AtMostOneLineASecondAndOnlyWhenAsked) {
  Hub h;
  EXPECT_EQ(h.out.pending(), 0u);                       // nothing is ever produced by feeding alone
  for (int i = 0; i < 10; i++) heardRepeater(h, 100 + i * 10, 0x21, 5);
  EXPECT_EQ(h.out.pending(), 0u);
  ASSERT_TRUE(h.askMesh(1000));
  takeLine(h);
  heardRepeater(h, 1100, 0x21, 5);
  EXPECT_FALSE(h.askMesh(1500)) << "a second request inside a second is not answered";
  EXPECT_EQ(h.out.pending(), 0u);
  EXPECT_TRUE(h.askMesh(2000));                         // a second later: the new packet goes
  std::string s = takeLine(h);
  EXPECT_TRUE(has(s, "\"rx\":11")) << s;
}

TEST(NovaStreamsMesh, QuietRadioGetsAnEmptyLineEveryTenSecondsNotMore) {
  Hub h;
  ASSERT_TRUE(h.askMesh(5000));                         // the first ask: an empty line, so the page knows we are here
  std::string s = takeLine(h);
  EXPECT_TRUE(has(s, "\"p\":[]")) << s;
  for (uint32_t t = 6000; t < 15000; t += 1000) EXPECT_FALSE(h.askMesh(t)) << t;   // nothing new, no beat due
  EXPECT_TRUE(h.askMesh(15000));                        // the beat
  EXPECT_TRUE(has(takeLine(h), "\"p\":[]"));
  EXPECT_FALSE(h.askMesh(16000));
}

TEST(NovaStreamsMesh, RecordsAreSentOnceAndHeavyTrafficFitsTheLineCap) {
  Hub h;
  for (int i = 0; i < 64; i++) heardRepeater(h, 100 + i, (uint8_t)i, 4);
  ASSERT_TRUE(h.askMesh(1000));
  std::string a = takeLine(h);
  EXPECT_LE(a.size(), MESH_CAP + 1);
  EXPECT_TRUE(oneLineJson(a.substr(0, a.size() - 1)));
  ASSERT_TRUE(h.askMesh(2000));                         // the rest, not the same ones again
  std::string b = takeLine(h);
  EXPECT_NE(a, b);
  size_t recs = 0;
  for (const std::string* t : {&a, &b}) for (size_t p = 0; (p = t->find("],[", p)) != std::string::npos; p += 3) recs++;
  EXPECT_FALSE(h.askMesh(3000)) << "everything was sent once; nothing new, no heartbeat due";
  EXPECT_GE(recs, 60u);                                  // 64 records over the two lines (the commas between records)
}

TEST(NovaStreamsMesh, OutboxHoldsOneWholeLineAtATime) {
  Hub h;
  ASSERT_TRUE(h.askMesh(1000));
  size_t total = h.out.pending();
  EXPECT_FALSE(h.out.midLine());
  h.out.consumed(10);
  EXPECT_TRUE(h.out.midLine());                         // part of the line is out: nobody else may write
  EXPECT_EQ(h.out.pending(), total - 10);
  h.out.consumed(h.out.pending());
  EXPECT_FALSE(h.out.midLine());
  EXPECT_EQ(h.out.pending(), 0u);
  EXPECT_TRUE(h.out.append("{\"nova_ok\":\"battery\"}"));
  EXPECT_TRUE(h.out.append("{\"x\":1}"));
  EXPECT_EQ(std::string((const char*)h.out.data(), h.out.pending()), "{\"nova_ok\":\"battery\"}\n{\"x\":1}\n");
  h.out.consumed(22);                                   // exactly the first line: at a line end, so not mid-line
  EXPECT_FALSE(h.out.midLine());
}

// ---- battery -----------------------------------------------------------------------------------------------

TEST(NovaStreamsBattery, ReplyShapeAndNoReading) {
  Hub h; char o[96];
  ASSERT_GT(h.batteryReply(o, sizeof(o)), 0u);
  EXPECT_STREQ(o, "{\"nova_error\":\"battery_no_reading\"}");
  h.bat.pctOf = curve;
  h.bat.sample(0, 3900, false);
  ASSERT_GT(h.batteryReply(o, sizeof(o)), 0u);
  EXPECT_STREQ(o, "{\"nova_ok\":\"battery\",\"mv\":3900,\"pct\":66,\"chg\":0}");
  h.bat.sample(1000, 4150, true);
  h.batteryReply(o, sizeof(o));
  EXPECT_STREQ(o, "{\"nova_ok\":\"battery\",\"mv\":4150,\"pct\":94,\"chg\":1}");
  EXPECT_EQ(h.batteryReply(o, 10), 0u);                // too small: nothing half-written
  EXPECT_STREQ(o, "");
}

TEST(NovaStreamsBattery, HistoryIsOneSampleEvery150sAndRestartsWhenChargingChanges) {
  Battery b; b.pctOf = curve;
  b.sample(0, 4000, false);
  b.sample(60000, 3990, false);                         // too soon for a history sample, but the reading is current
  EXPECT_EQ(b.n, 1); EXPECT_EQ(b.mv, 3990);
  b.sample(150000, 3980, false);
  EXPECT_EQ(b.n, 2); EXPECT_EQ(b.hist[1], 3980);
  b.sample(151000, 4200, true);                         // plugged in: the discharge history is forgotten
  EXPECT_EQ(b.n, 1); EXPECT_TRUE(b.chg);
  b.sample(152000, 0, true);                            // a failed read changes nothing
  EXPECT_EQ(b.mv, 4200);
  Battery full;
  for (int i = 0; i < 200; i++) full.sample((uint32_t)i * 150000u, (uint16_t)(4100 - i), false);
  EXPECT_EQ(full.n, Battery::N);                        // 96 at most; the oldest drop off
  EXPECT_EQ(full.hist[Battery::N - 1], 4100 - 199);
}

TEST(NovaStreamsBattery, TrendAndTimeLeftNeedHalfAnHourOfDischarge) {
  Battery b; b.pctOf = curve;
  float t, hl;
  for (int i = 0; i < 12; i++) b.sample((uint32_t)i * 150000u, (uint16_t)(4000 - i * 9), false);
  EXPECT_FALSE(b.trendPerHour(t)) << "under 30 minutes of history: no trend";
  EXPECT_FALSE(b.hoursLeft(hl));
  for (int i = 12; i < 24; i++) b.sample((uint32_t)i * 150000u, (uint16_t)(4000 - i * 9), false);
  ASSERT_TRUE(b.trendPerHour(t));
  EXPECT_NEAR(t, -1.0f * 24.0f, 1.5f);                  // 9 mV = 1% per 150 s = 24% an hour
  ASSERT_TRUE(b.hoursLeft(hl));
  EXPECT_GT(hl, 1.0f); EXPECT_LT(hl, 3.0f);
  b.sample(24 * 150000u, 4100, true);                   // charging: no estimate
  EXPECT_FALSE(b.hoursLeft(hl));
}

// ---- repeaters and best uplink ----------------------------------------------------------------------------

TEST(NovaStreamsLinks, LastHopOfFloodPacketsOnly) {
  Hub h;
  uint8_t path[3] = {0x01, 0x02, 0x03};
  h.onRx(1000, -80, 8, 2, 1, 3, 1, path, kPath, 3, 50);            // flood: the last hop is 03
  h.onRx(1100, -80, 8, 2, 2, 3, 1, path, kPath, 3, 50);            // direct route: the path is the way still to go, ignored
  h.onRx(1200, -80, 8, 2, 1, 0, 1, path, kPath, 3, 50);            // zero hops, not an advert: nobody to name
  EXPECT_EQ(h.links.count(1300), 1);
  const Links::E* hit = nullptr;
  for (auto& e : h.links.e) if (e.used) hit = &e;
  ASSERT_NE(hit, nullptr);
  EXPECT_EQ(hit->key[0], 0x03); EXPECT_EQ(hit->len, 1);
}

TEST(NovaStreamsLinks, ZeroHopAdvertFromARepeaterCounts) {
  Hub h;
  uint8_t adv[110]; memset(adv, 0x55, sizeof(adv)); adv[0] = 0xAB; adv[1] = 0xCD; adv[2] = 0xEF; adv[100] = 0x02;   // appdata flags: type 2 = repeater
  h.onRx(1000, -70, 9, 4, 1, 0, 3, nullptr, adv, 110, 120);
  adv[100] = 0x01;                                                  // a chat node's advert is not a repeater
  adv[0] = 0x77;
  h.onRx(1100, -70, 9, 4, 1, 0, 3, nullptr, adv, 110, 120);
  ASSERT_EQ(h.links.count(1200), 1);
  for (auto& e : h.links.e) if (e.used) { EXPECT_EQ(e.len, 3); EXPECT_EQ(e.key[0], 0xAB); EXPECT_EQ(e.key[2], 0xEF); }
}

TEST(NovaStreamsLinks, ScoreFollowsSnrAndFreshnessAndBestNeedsAGoodOne) {
  Hub h;
  heardRepeater(h, 1000, 0x10, 8);     // good
  heardRepeater(h, 1000, 0x20, -14);   // barely
  ASSERT_TRUE(h.askStatus(1000, STATUS_GAP_MS));
  std::string s = takeLine(h);
  size_t a = s.find("{\"id\":\"10\""), b = s.find("{\"id\":\"20\"");
  ASSERT_NE(a, std::string::npos) << s; ASSERT_NE(b, std::string::npos) << s;
  EXPECT_LT(a, b) << "best first";
  EXPECT_TRUE(has(s, "\"id\":\"10\",\"name\":\"\",\"best\":1,")) << s;
  EXPECT_TRUE(has(s, "\"id\":\"20\",\"name\":\"\",\"best\":0,")) << s;
  EXPECT_TRUE(has(s, ",\"best\":16,\"dl\"")) << s;                // the original "best" key: the key's first byte
  // ten minutes on, nothing refreshed it: the freshness part is zero and the score is the SNR part alone
  EXPECT_EQ(Links::rel(h.links.e[0], 1000 + 700000u), 0);
  EXPECT_LT(Links::score(h.links.e[0], 1000 + 700000u), Links::score(h.links.e[0], 1000));
  Hub poor; heardRepeater(poor, 1000, 0x30, -14);
  ASSERT_TRUE(poor.askStatus(1000, STATUS_GAP_MS));
  std::string p = takeLine(poor);
  EXPECT_TRUE(has(p, "\"best\":0,")) << p;
  EXPECT_TRUE(has(p, ",\"best\":-1,\"dl\"")) << p;                // nothing is good enough: no uplink
  EXPECT_FALSE(poor.links.hasBest(1000));
}

TEST(NovaStreamsLinks, ForgottenAfterHalfAnHourAndTableReplacesTheStalest) {
  Hub h;
  heardRepeater(h, 1000, 0x10, 5);
  EXPECT_EQ(h.links.count(1000 + Links::FORGET_MS - 1), 1);
  EXPECT_EQ(h.links.count(1000 + Links::FORGET_MS), 0);
  Hub t;
  for (int i = 0; i < Links::N; i++) heardRepeater(t, 1000 + i, (uint8_t)(i + 1), 5);
  heardRepeater(t, 5000, 0x99, 5);                                  // the 13th: replaces the one heard longest ago
  EXPECT_EQ(t.links.count(5001), Links::N);
  bool have1 = false, have99 = false;
  for (auto& e : t.links.e) { if (e.used && e.key[0] == 1) have1 = true; if (e.used && e.key[0] == 0x99) have99 = true; }
  EXPECT_FALSE(have1); EXPECT_TRUE(have99);
}

TEST(NovaStreamsLinks, NamesAreFilledInAndStayPrintableJson) {
  Hub h;
  heardRepeater(h, 1000, 0x10, 5);
  int u = h.links.nextUnnamed(1000);
  ASSERT_GE(u, 0);
  h.links.triedName(u, 1000);
  EXPECT_EQ(h.links.nextUnnamed(2000), -1) << "not asked again within 30 s";
  EXPECT_EQ(h.links.nextUnnamed(32000), u);
  h.links.setName(u, "Hill \"Top\"\\\x01 \xC3\xA9");
  EXPECT_EQ(h.links.nextUnnamed(99999), -1);
  ASSERT_TRUE(h.askStatus(1000, STATUS_GAP_MS));
  std::string s = takeLine(h); s.pop_back();
  EXPECT_TRUE(oneLineJson(s)) << s;
  EXPECT_TRUE(has(s, "\"name\":\"Hill ?Top??? ??\"")) << s;        // quote, backslash and non-ASCII bytes become '?'
}

// ---- messages you sent ------------------------------------------------------------------------------------

TEST(NovaStreamsDeliveries, DeliveredWhenTheAckComesFailedWhenItDoesNot) {
  Hub h;
  h.dl.onSent(1000, "Alice", 0x11223344, 4000, true, false);
  h.dl.onSent(2000, "Bob", 0x55667788, 4000, false, true);
  EXPECT_TRUE(h.dl.onAck(3500, 0x11223344));
  EXPECT_FALSE(h.dl.onAck(3600, 0xDEADBEEF));                       // not ours
  h.tick(2000 + 4000 + Deliveries::GRACE_MS);                       // at the limit: still on its way
  EXPECT_EQ(h.dl.fail, 0u);
  h.tick(2000 + 4000 + Deliveries::GRACE_MS + 1);
  EXPECT_EQ(h.dl.sent, 2u); EXPECT_EQ(h.dl.ok, 1u); EXPECT_EQ(h.dl.fail, 1u);
  ASSERT_TRUE(h.askStatus(9000, STATUS_GAP_MS));
  std::string s = takeLine(h); s.pop_back();
  EXPECT_TRUE(oneLineJson(s)) << s;
  EXPECT_TRUE(has(s, "\"dl\":{\"sent\":2,\"rep\":0,\"ok\":1,\"fail\":1,\"list\":[{\"who\":\"Bob\",\"st\":\"failed\",\"via\":-1,\"rtt\":0,\"age\":7,\"flood\":0,\"link\":1,\"chan\":0},"
                "{\"who\":\"Alice\",\"st\":\"delivered\",\"via\":-1,\"rtt\":2500,\"age\":8,\"flood\":1,\"link\":0,\"chan\":0}]}")) << s;   // newest first
  EXPECT_TRUE(h.dl.onAck(9500, 0x55667788));                        // a late ack still turns it to delivered
  EXPECT_EQ(h.dl.ok, 2u); EXPECT_EQ(h.dl.fail, 0u);
  EXPECT_FALSE(h.dl.onAck(9600, 0x55667788));                       // the same ack twice counts once
  EXPECT_EQ(h.dl.ok, 2u);
}

// ---- gps / speed -------------------------------------------------------------------------------------------

TEST(NovaStreamsGps, SpeedFromSuccessiveFixesAndNoFixMeansNoSpeed) {
  Gps g;
  g.update(0, true, 51500000, -100000, 8);
  EXPECT_TRUE(g.fix); EXPECT_FLOAT_EQ(g.kmh, 0.0f); EXPECT_FALSE(g.moving);
  g.update(1000, true, 51500100, -100000, 8);                       // under 2 s: no speed yet
  EXPECT_FLOAT_EQ(g.kmh, 0.0f);
  // 100 m north in 10 s = 36 km/h; 0.111195 m per 1e-6 deg of latitude
  g.update(10000, true, 51500000 + 899, -100000, 8);
  EXPECT_NEAR(g.kmh, 36.0f, 1.0f); EXPECT_TRUE(g.moving);
  EXPECT_NEAR((float)g.course, 0.0f, 1.0f);
  g.update(20000, true, 51500000 + 899, -100000 + 1, 8);            // standing still (jitter under 2 m)
  EXPECT_LT(g.kmh, 20.0f);
  g.update(30000, true, 51500000 + 899, -100000, 8);
  g.update(40000, true, 51500000 + 899, -100000, 8);
  g.update(50000, true, 51500000 + 899, -100000, 8);
  EXPECT_FALSE(g.moving); EXPECT_EQ(g.course, -1);
  g.update(60000, false, 0, 0, 0);
  EXPECT_FALSE(g.fix);
}

// ---- the status frame --------------------------------------------------------------------------------------

TEST(NovaStreamsStatus, FrameShapeMatchesWhatThePageReads) {
  Hub h; h.nf = -110; h.bat.pctOf = curve;
  h.bat.sample(0, 3900, false); h.bat.sample(150000, 3890, false);
  h.gps.update(0, true, 51500000, -100000, 9);
  h.gps.update(10000, true, 51500899, -100000, 9);
  heardRepeater(h, 5000, 0x42, 7.5f, -88);
  h.dl.onSent(6000, "Carol", 1, 5000, false, true);
  ASSERT_TRUE(h.askStatus(20000, STATUS_GAP_MS));
  std::string s = takeLine(h); ASSERT_EQ(s.back(), '\n'); s.pop_back();
  EXPECT_TRUE(oneLineJson(s)) << s;
  EXPECT_EQ(s.rfind("{\"nova\":1,\"t\":20000,\"bat\":{\"mv\":3890,\"pct\":65,\"chg\":0,\"trend\":null,\"hrs\":null,\"hist\":[3900,3890]},\"gps\":{\"fix\":1,\"lat\":51.500899,\"lon\":-0.100000,\"sats\":9,\"spd\":", 0), 0u) << s;
  EXPECT_EQ(s.find("\"ed\""), std::string::npos) << "an ed key would make the page read the frame as a hello";
  for (const char* k : {"\"links\":[{\"id\":\"42\"", "\"best\":", "\"dl\":{\"sent\":1,", "\"diag\":{\"rx\":1,\"tx\":0,\"snr\":7.5,\"last_rx_s\":15,\"up_s\":20}}"}) EXPECT_TRUE(has(s, k)) << k << " in " << s;
  EXPECT_EQ(s.find("\"nova\""), 1u) << "the page's router needs the \"nova\" key after index 0";
  EXPECT_EQ(s.find("\"mesh\""), std::string::npos);
  EXPECT_EQ(s.find("\"pet\""), std::string::npos);
  EXPECT_EQ(s.find("\"contacts\""), std::string::npos);
}

TEST(NovaStreamsStatus, EmptyRadioStillGivesAFullFrame) {
  Hub h;                                                            // no battery reading, no fix, nothing heard, nothing sent
  ASSERT_TRUE(h.askStatus(1000, STATUS_GAP_MS));
  std::string s = takeLine(h); s.pop_back();
  EXPECT_TRUE(oneLineJson(s)) << s;
  EXPECT_EQ(s, "{\"nova\":1,\"t\":1000,\"bat\":{\"mv\":0,\"pct\":-1,\"chg\":0,\"trend\":null,\"hrs\":null,\"hist\":[]},\"gps\":{\"fix\":0},"
               "\"links\":[],\"best\":-1,\"dl\":{\"sent\":0,\"rep\":0,\"ok\":0,\"fail\":0,\"list\":[]},"
               "\"diag\":{\"rx\":0,\"tx\":0,\"snr\":null,\"last_rx_s\":0,\"up_s\":1}}");
}

TEST(NovaStreamsStatus, AtMostOneEvery5sAndOnDemandOnceASecond) {
  Hub h;
  ASSERT_TRUE(h.askStatus(1000, STATUS_GAP_MS));
  takeLine(h);
  for (uint32_t t = 1001; t < 6000; t += 500) EXPECT_FALSE(h.askStatus(t, STATUS_GAP_MS)) << t;
  EXPECT_EQ(h.out.pending(), 0u);
  EXPECT_TRUE(h.askStatus(6000, STATUS_GAP_MS));
  takeLine(h);
  EXPECT_FALSE(h.askStatus(6500, STATUS_CMD_GAP_MS));    // inside a second of the last frame, even for the explicit command
  EXPECT_TRUE(h.askStatus(7000, STATUS_CMD_GAP_MS));     // the explicit command is not held to the 5 s of the piggyback
}

TEST(NovaStreamsStatus, WorstCaseFrameFitsItsCapAndStaysValid) {
  Hub h; h.bat.pctOf = curve;
  for (int i = 0; i < 300; i++) h.bat.sample((uint32_t)i * 150000u, (uint16_t)(4199 - i % 800), false);
  h.gps.update(0, true, -51500000, -179999999, 14); h.gps.update(10000, true, -51500899, -179999999, 14);
  for (int i = 0; i < Links::N; i++) {
    uint8_t path[3] = {(uint8_t)(0xF0 + i), 0xFE, 0xFD};
    h.onRx(1000, -120.0f, -19.75f, 2, 1, 1, 3, path, kPath, 3, 250);
    h.links.setName(i, "abcdefghijklmnopqrstuvw");
  }
  for (int i = 0; i < 20; i++) h.dl.onSent(1000 + i, "abcdefghijklmnopqrstuvw", (uint32_t)i + 1, 1, true, true);
  h.tick(900000);
  ASSERT_TRUE(h.askStatus(1000000, STATUS_GAP_MS));
  std::string s = takeLine(h);
  EXPECT_LT(s.size(), STATUS_CAP) << s.size();
  s.pop_back();
  EXPECT_TRUE(oneLineJson(s));
  size_t n = 0; for (size_t p = 0; (p = s.find("{\"id\":", p)) != std::string::npos; p++) n++;
  EXPECT_EQ(n, (size_t)Links::SHOWN);
}

TEST(NovaStreamsStatus, TooSmallABufferGivesNothingNotHalfALine) {
  Hub h; heardRepeater(h, 1000, 1, 5);
  char small[100];
  EXPECT_EQ(h.statusLine(1000, small, sizeof(small)), 0u);
  EXPECT_EQ(h.statusLine(1000, nullptr, 0), 0u);
}

// ---- the commands and the hello ----------------------------------------------------------------------------

TEST(NovaStreamsCli, StatusAndBatteryAreParsedAndAnsweredByTheCaller) {
  EXPECT_EQ(NovaCli::parse("nova status").cmd, NovaCli::Cmd::Status);
  EXPECT_EQ(NovaCli::parse("nova battery").cmd, NovaCli::Cmd::Battery);
  EXPECT_EQ(NovaCli::parse("nova batteryx").cmd, NovaCli::Cmd::Unknown);
  EXPECT_EQ(NovaCli::parse("nova statuses").cmd, NovaCli::Cmd::Unknown);
  char o[64] = "x";
  EXPECT_EQ(NovaCli::reply(NovaCli::parse("nova status"), "dx-pro", NovaCli::Caps(), o, sizeof(o)), 0u);
  EXPECT_EQ(NovaCli::reply(NovaCli::parse("nova battery"), "dx-pro", NovaCli::Caps(), o, sizeof(o)), 0u);
}

TEST(NovaStreamsCli, HelloSaysMeshOnlyWhenTheBuildHasTheStream) {
  char o[400];
  NovaCli::Caps without;                                            // a build without the feeds
  NovaCli::reply(NovaCli::parse("nova hello"), "dx-pro", without, o, sizeof(o));
  EXPECT_TRUE(has(o, "\"mesh\":0")) << o;
  NovaCli::Caps with; with.mesh = 1;
  NovaCli::reply(NovaCli::parse("nova hello"), "dx-pro", with, o, sizeof(o));
  EXPECT_TRUE(has(o, "\"pet\":0,\"mesh\":1,\"contacts\":0")) << o;
  EXPECT_TRUE(has(o, "\"lg\":{\"hello\":1,\"pet\":0,\"mesh\":1}")) << o;
  EXPECT_EQ(std::string(o).find("\"ed\":\"dx-pro\",\"nova\":{"), 1u);
  // the other caps stay 0: nothing here claims keys, clean, feed, guess, ping or sendpet
  EXPECT_TRUE(has(o, "\"keys\":0,\"clean\":0,\"feed\":0,\"guess\":0,\"ping\":0,\"sendpet\":0")) << o;
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
