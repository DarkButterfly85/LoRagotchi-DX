// Host tests for helpers/PetMirror.h (LODESTAR ORION / NOVA lineage): the pet frame lines the Nova
// dashboard decodes. Line shape (notes/nova-dashboard-plan.md): {"pet":{"s":SEQ,"k":KEY,"d":"BASE64"}}
// with n/u/x/m/c/i added on key frames. The tests decode base64 and RLE themselves.
#include <gtest/gtest.h>

#include <stdint.h>
#include <string.h>
#include <string>
#include <vector>

#include <helpers/PetMirror.h>

namespace {

typedef std::vector<uint8_t> Bytes;

Bytes b64decode(const std::string& s) {
  Bytes out;
  uint32_t acc = 0;
  int bits = 0;
  for (char ch : s) {
    int v;
    if (ch >= 'A' && ch <= 'Z') v = ch - 'A';
    else if (ch >= 'a' && ch <= 'z') v = ch - 'a' + 26;
    else if (ch >= '0' && ch <= '9') v = ch - '0' + 52;
    else if (ch == '+') v = 62;
    else if (ch == '/') v = 63;
    else break;  // '=' padding
    acc = (acc << 6) | (uint32_t)v;
    bits += 6;
    if (bits >= 8) { bits -= 8; out.push_back((uint8_t)((acc >> bits) & 0xFF)); }
  }
  return out;
}

// 0x00 is followed by a count (1..255) of zero bytes; every other byte stands for itself.
Bytes rleDecode(const Bytes& in) {
  Bytes out;
  for (size_t i = 0; i < in.size(); i++) {
    if (in[i] != 0) { out.push_back(in[i]); continue; }
    EXPECT_LT(i + 1, in.size()) << "run marker without a count";
    if (i + 1 >= in.size()) break;
    uint8_t run = in[++i];
    EXPECT_GE(run, 1);
    out.insert(out.end(), run, 0);
  }
  return out;
}

struct Line {
  long s = -1;
  int k = -1;
  std::string d;
  std::string raw;
};

// The line is {"pet":{"s":N,"k":N,...,"d":"B64"}}: pull out what the tests need.
Line parse(const char* text) {
  Line l;
  l.raw = text;
  EXPECT_EQ(0u, l.raw.find("{\"pet\":{\"s\":")) << l.raw.substr(0, 40);
  EXPECT_EQ("\"}}", l.raw.substr(l.raw.size() - 3));
  size_t p = l.raw.find("\"s\":");
  l.s = strtol(l.raw.c_str() + p + 4, nullptr, 10);
  p = l.raw.find("\"k\":");
  l.k = (int)strtol(l.raw.c_str() + p + 4, nullptr, 10);
  p = l.raw.find("\"d\":\"");
  l.d = l.raw.substr(p + 5, l.raw.size() - 3 - (p + 5));
  return l;
}

Bytes frameBytes(const Line& l) { return rleDecode(b64decode(l.d)); }

void fillPattern(uint8_t* fb, uint32_t salt) {
  for (int i = 0; i < PM_BYTES; i++) fb[i] = (uint8_t)((i * 37 + salt * 11) % 251 < 90 ? 0 : (i * 13 + salt));
}

size_t encode(PetMirrorEncoder& e, const uint8_t* fb, uint32_t now, char* out, const char* name = "Bubbles",
              int sex = 1, int months = 14, int count = 3, int index = 2, const char* uname = "") {
  return e.line(fb, now, out, 4096, name, sex, months, count, index, uname);
}

}  // namespace

TEST(PetMirrorFrame, SizeConstantsMatchThe128x64Frame) {
  EXPECT_EQ(128, PM_W);
  EXPECT_EQ(64, PM_H);
  EXPECT_EQ(1024, PM_BYTES);
  PetMirror m;
  EXPECT_EQ(128, m.width());
  EXPECT_EQ(64, m.height());
  EXPECT_EQ(sizeof(m.fb), (size_t)PM_BYTES);
}

TEST(PetMirrorFrame, PixelsAreTopRowFirstLeftmostPixelIsTopBit) {
  PetMirror m;
  m.startFrame();
  m.fillRect(0, 0, 1, 1);      // top left
  m.fillRect(127, 63, 1, 1);   // bottom right
  m.fillRect(9, 1, 1, 1);      // row 1, byte 1 of that row, bit 6
  EXPECT_EQ(0x80, m.fb[0]);
  EXPECT_EQ(0x01, m.fb[1023]);
  EXPECT_EQ(0x40, m.fb[16 + 1]);
  m.fillRect(-5, -5, 3, 3);    // off screen draws are ignored
  m.fillRect(200, 10, 4, 4);
  int lit = 0;
  for (int i = 0; i < PM_BYTES; i++) for (int b = 0; b < 8; b++) lit += (m.fb[i] >> b) & 1;
  EXPECT_EQ(3, lit);
}

TEST(PetMirrorFrame, BlankFrameIsFourFullRunsAndOneShortRun) {
  PetMirror m;
  PetMirrorEncoder e;
  char out[4096];
  ASSERT_GT(encode(e, m.fb, 1000, out), 0u);
  Line l = parse(out);
  Bytes rle = b64decode(l.d);
  // 1024 zero bytes = 255 + 255 + 255 + 255 + 4
  const Bytes want = {0, 255, 0, 255, 0, 255, 0, 255, 0, 4};
  EXPECT_EQ(want, rle);
  EXPECT_EQ(1, l.k);
  EXPECT_EQ(1, l.s);
}

TEST(PetMirrorFrame, KnownFrameRoundTripsThroughBase64AndRle) {
  PetMirror m;
  m.startFrame();
  m.setTextSize(1);
  m.setCursor(4, 4);
  m.print("LoRaFish 123");
  m.drawRect(0, 0, 128, 64);
  m.setTextSize(2);
  m.setCursor(10, 30);
  m.print("Hi");
  static const uint8_t xbm[] = {0xAA, 0x55, 0xAA, 0x55, 0xF0, 0x0F, 0xFF, 0x00};  // 8x8 checker/bars
  m.drawXbm(100, 40, xbm, 8, 8);
  bool any = false;
  for (int i = 0; i < PM_BYTES; i++) any = any || m.fb[i];
  ASSERT_TRUE(any);

  PetMirrorEncoder e;
  char out[4096];
  size_t n = encode(e, m.fb, 5000, out);
  ASSERT_GT(n, 0u);
  EXPECT_EQ(strlen(out), n);

  Line l = parse(out);
  EXPECT_EQ(1, l.k);
  Bytes got = frameBytes(l);
  ASSERT_EQ((size_t)PM_BYTES, got.size());
  EXPECT_EQ(0, memcmp(got.data(), m.fb, PM_BYTES));
  EXPECT_EQ(0u, l.d.size() % 4u);  // padded base64
  // the border and the font landed where the format says
  EXPECT_EQ(0xFF, got[0]);         // top border row, all 16 bytes lit
  EXPECT_EQ(0xFF, got[15]);
  EXPECT_EQ(0x80, got[16] & 0x80); // left border pixel on row 1
  EXPECT_EQ(0x01, got[16 + 15] & 0x01);
}

TEST(PetMirrorFrame, DenseFrameStillFitsTheLineBufferAndRoundTrips) {
  uint8_t fb[PM_BYTES];
  for (int i = 0; i < PM_BYTES; i++) fb[i] = (uint8_t)(i % 255 + 1);  // no zero bytes: no compression
  PetMirrorEncoder e;
  char out[4096];
  size_t n = encode(e, fb, 100, out);
  ASSERT_GT(n, 0u);
  EXPECT_LT(n, 2000u);  // the encoder asks for at least 2000 bytes of line buffer
  Bytes got = frameBytes(parse(out));
  ASSERT_EQ((size_t)PM_BYTES, got.size());
  EXPECT_EQ(0, memcmp(got.data(), fb, PM_BYTES));
}

TEST(PetMirrorFrame, RefusesASmallLineBuffer) {
  PetMirror m;
  PetMirrorEncoder e;
  char out[1999];
  EXPECT_EQ(0u, e.line(m.fb, 0, out, sizeof(out), "x", 0, 0, 0, 0));
}

TEST(PetMirrorFrame, Base64MatchesKnownVectors) {
  char o[16];
  size_t n = PetMirrorEncoder::b64((const uint8_t*)"Man", 3, o); o[n] = 0; EXPECT_STREQ("TWFu", o);
  n = PetMirrorEncoder::b64((const uint8_t*)"Ma", 2, o); o[n] = 0; EXPECT_STREQ("TWE=", o);
  n = PetMirrorEncoder::b64((const uint8_t*)"M", 1, o); o[n] = 0; EXPECT_STREQ("TQ==", o);
  const uint8_t hi[] = {0xFB, 0xFF, 0xBF};
  n = PetMirrorEncoder::b64(hi, 3, o); o[n] = 0; EXPECT_STREQ("+/+/", o);
}

TEST(PetMirrorKeyDelta, SecondFrameIsAXorDeltaAgainstTheFirst) {
  uint8_t a[PM_BYTES], b[PM_BYTES];
  fillPattern(a, 1);
  memcpy(b, a, sizeof(b));
  b[5] ^= 0x3C;
  b[700] ^= 0x81;
  b[1023] ^= 0x01;

  PetMirrorEncoder e;
  char out[4096];
  ASSERT_GT(encode(e, a, 1000, out), 0u);
  Line first = parse(out);
  EXPECT_EQ(1, first.k);
  Bytes k = frameBytes(first);
  ASSERT_EQ(0, memcmp(k.data(), a, PM_BYTES));  // key frame carries the picture itself

  ASSERT_GT(encode(e, b, 1100, out), 0u);
  Line second = parse(out);
  EXPECT_EQ(0, second.k);
  EXPECT_EQ(2, second.s);
  Bytes dlt = frameBytes(second);
  ASSERT_EQ((size_t)PM_BYTES, dlt.size());
  for (int i = 0; i < PM_BYTES; i++) EXPECT_EQ((uint8_t)(a[i] ^ b[i]), dlt[i]) << i;
  EXPECT_EQ(0x3C, dlt[5]);
  EXPECT_EQ(0x81, dlt[700]);
  EXPECT_EQ(0x01, dlt[1023]);
  // a receiver applying the delta to its copy of the key frame rebuilds the new picture
  for (int i = 0; i < PM_BYTES; i++) k[i] ^= dlt[i];
  EXPECT_EQ(0, memcmp(k.data(), b, PM_BYTES));
  // and the delta is a lot shorter than the key frame
  EXPECT_LT(second.raw.size(), first.raw.size());
}

TEST(PetMirrorKeyDelta, DeltasChainAgainstThePreviousFrameNotTheKey) {
  uint8_t f[3][PM_BYTES];
  fillPattern(f[0], 1);
  memcpy(f[1], f[0], PM_BYTES); f[1][10] ^= 0xFF;
  memcpy(f[2], f[1], PM_BYTES); f[2][20] ^= 0x0F;
  PetMirrorEncoder e;
  char out[4096];
  Bytes shown;
  for (int i = 0; i < 3; i++) {
    ASSERT_GT(encode(e, f[i], 1000 + 100 * i, out), 0u);
    Line l = parse(out);
    Bytes d = frameBytes(l);
    if (l.k) shown = d;
    else for (int j = 0; j < PM_BYTES; j++) shown[j] ^= d[j];
    ASSERT_EQ(0, memcmp(shown.data(), f[i], PM_BYTES)) << "frame " << i;
  }
}

TEST(PetMirrorKeyDelta, UnchangedPictureIsSkippedUntilASecondHasPassed) {
  uint8_t a[PM_BYTES];
  fillPattern(a, 3);
  PetMirrorEncoder e;
  char out[4096];
  ASSERT_GT(encode(e, a, 1000, out), 0u);       // key
  EXPECT_EQ(0u, encode(e, a, 1200, out));       // same picture, 200 ms later: nothing to say
  EXPECT_EQ(0u, encode(e, a, 1900, out));       // still under 1000 ms since the last sent line
  ASSERT_GT(encode(e, a, 2100, out), 0u);       // >= 1000 ms: an all-zero delta goes out as a heartbeat
  Line l = parse(out);
  EXPECT_EQ(0, l.k);
  Bytes d = frameBytes(l);
  ASSERT_EQ((size_t)PM_BYTES, d.size());
  for (uint8_t v : d) ASSERT_EQ(0, v);
  EXPECT_EQ(2, l.s);  // skipped frames do not use up sequence numbers
}

TEST(PetMirrorKeyDelta, KeyFrameEveryFortyDeltasAndAfterAPause) {
  uint8_t a[PM_BYTES];
  fillPattern(a, 4);
  PetMirrorEncoder e;
  char out[4096];
  uint32_t now = 1000;
  std::vector<int> keys;
  for (int i = 0; i < 90; i++) {
    a[i % PM_BYTES] ^= 0x01;  // every frame differs
    ASSERT_GT(encode(e, a, now, out), 0u);
    keys.push_back(parse(out).k);
    now += 100;
  }
  EXPECT_EQ(1, keys[0]);
  for (int i = 1; i <= 40; i++) EXPECT_EQ(0, keys[i]) << i;
  EXPECT_EQ(1, keys[41]);
  for (int i = 42; i <= 81; i++) EXPECT_EQ(0, keys[i]) << i;
  EXPECT_EQ(1, keys[82]);

  // a gap over 1500 ms (the dashboard stopped asking) forces a key frame
  a[0] ^= 0x80;
  now += 1501;
  ASSERT_GT(encode(e, a, now, out), 0u);
  EXPECT_EQ(1, parse(out).k);
  // exactly 1500 ms is not a pause
  a[1] ^= 0x80;
  now += 1500;
  ASSERT_GT(encode(e, a, now, out), 0u);
  EXPECT_EQ(0, parse(out).k);
}

TEST(PetMirrorMeta, KeyFramesCarryNameSexMonthsCountIndexAndEmptyOwner) {
  PetMirror m;
  PetMirrorEncoder e;
  char out[4096];
  ASSERT_GT(encode(e, m.fb, 1000, out, "Bubbles", 1, 14, 3, 2), 0u);
  const char* want = "{\"pet\":{\"s\":1,\"k\":1,\"n\":\"Bubbles\",\"u\":\"\",\"x\":1,\"m\":14,\"c\":3,\"i\":2,\"d\":\"";
  EXPECT_EQ(0, strncmp(out, want, strlen(want)));
  EXPECT_NE(nullptr, strstr(out, "\"n\":\"Bubbles\""));
  EXPECT_NE(nullptr, strstr(out, "\"u\":\"\""));
  EXPECT_NE(nullptr, strstr(out, "\"x\":1"));
  EXPECT_NE(nullptr, strstr(out, "\"m\":14"));
  EXPECT_NE(nullptr, strstr(out, "\"c\":3"));
  EXPECT_NE(nullptr, strstr(out, "\"i\":2"));
}

TEST(PetMirrorMeta, OwnerNameGoesOutInUWhenGiven) {
  PetMirror m;
  PetMirrorEncoder e;
  char out[4096];
  ASSERT_GT(encode(e, m.fb, 1000, out, "Bubbles", 0, 0, 1, 0, "Sam"), 0u);
  EXPECT_NE(nullptr, strstr(out, "\"n\":\"Bubbles\",\"u\":\"Sam\",\"x\":0,\"m\":0,\"c\":1,\"i\":0,"));
  // a null owner is treated as empty
  PetMirrorEncoder e2;
  ASSERT_GT(e2.line(m.fb, 1000, out, sizeof(out), "Bubbles", 0, 0, 1, 0, nullptr), 0u);
  EXPECT_NE(nullptr, strstr(out, "\"u\":\"\""));
}

TEST(PetMirrorMeta, DeltaFramesHaveNoMetaFields) {
  uint8_t a[PM_BYTES];
  fillPattern(a, 5);
  PetMirrorEncoder e;
  char out[4096];
  ASSERT_GT(encode(e, a, 1000, out), 0u);
  a[3] ^= 0x10;
  ASSERT_GT(encode(e, a, 1100, out), 0u);
  EXPECT_EQ(0u, strncmp(out, "{\"pet\":{\"s\":2,\"k\":0,\"d\":\"", 24));
  for (const char* f : {"\"n\":", "\"u\":", "\"x\":", "\"m\":", "\"c\":", "\"i\":"})
    EXPECT_EQ(nullptr, strstr(out, f)) << f;
  EXPECT_EQ(0, strcmp(out + strlen(out) - 3, "\"}}"));
}

TEST(PetMirrorMeta, KeyFrameAfterAPauseCarriesTheMetaAgain) {
  uint8_t a[PM_BYTES];
  fillPattern(a, 6);
  PetMirrorEncoder e;
  char out[4096];
  ASSERT_GT(encode(e, a, 1000, out), 0u);
  a[9] ^= 1;
  ASSERT_GT(encode(e, a, 1100, out, "Bubbles", 1, 15, 3, 2), 0u);
  a[9] ^= 1;
  ASSERT_GT(encode(e, a, 5000, out, "Bubbles", 1, 15, 3, 2), 0u);  // after a pause
  Line l = parse(out);
  EXPECT_EQ(1, l.k);
  EXPECT_NE(nullptr, strstr(out, "\"n\":\"Bubbles\",\"u\":\"\",\"x\":1,\"m\":15,\"c\":3,\"i\":2,"));
  EXPECT_EQ(3, l.s);
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
