// Host tests for the Nova pet picture on every screen (NovaPetLink.h + NovaPetTee.h) and for the frame name
// fallback (NovaPetName::frameName): /lorafish.id name, else the radio's node name.
//   - mono 128x64 (the OLED) must stay byte for byte what the first version sent (golden lines made with the
//     encoder of commit a5f0e04), and a line without "c" is what an old dashboard reads
//   - colour screens (non-square, odd width) go in the "c" field: 16-colour palette, 4 bits a pixel
//   - e-ink: still pictures, black ink on white, no deltas
// The decoder below is written separately from the encoder, from the format description at the top of NovaPetLink.h.
#include <gtest/gtest.h>

#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include <vector>

#include "../../examples/companion_radio/NovaPetLink.h"
#include "../../examples/companion_radio/ui-new/NovaPetTee.h"

ColorVal UIColor::window_bkg = 0, UIColor::title_bkg = 0, UIColor::title_txt = 1, UIColor::primary_txt = 1,
         UIColor::secondary_txt = 1, UIColor::warning_txt = 1, UIColor::popup_bkg = 0, UIColor::popup_txt = 1,
         UIColor::corp_blue = 1;

using NovaPetLink::Format;
using NovaPetLink::Link;

namespace {

// ---- a screen that draws nothing: only its size and kind matter ---------------------------------------
class FakeScreen : public DisplayDriver {
  bool _color, _eink;
public:
  int calls = 0;
  FakeScreen(int w, int h, bool color = false, bool eink = false) : DisplayDriver(w, h), _color(color), _eink(eink) {}
  bool supportsColor() const override { return _color; }
  bool isEink() override { return _eink; }
  bool isOn() override { return true; }
  void turnOn() override {}
  void turnOff() override {}
  void clear() override { calls++; }
  void startFrame(ColorVal = 0) override { calls++; }
  void endFrame() override { calls++; }
  void setTextSize(int) override { calls++; }
  void setColor(ColorVal) override { calls++; }
  void setCursor(int, int) override { calls++; }
  void print(const char*) override { calls++; }
  void fillRect(int, int, int, int) override { calls++; }
  void drawRect(int, int, int, int) override { calls++; }
  void drawXbm(int, int, const uint8_t*, int, int) override { calls++; }
  uint16_t getTextWidth(const char* s) override { return (uint16_t)(strlen(s) * 6); }
};

// ---- the dashboard side: base64, run-length, one line at a time ---------------------------------------
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
    else break;
    acc = (acc << 6) | (uint32_t)v;
    bits += 6;
    if (bits >= 8) { bits -= 8; out.push_back((uint8_t)((acc >> bits) & 0xFF)); }
  }
  return out;
}

Bytes rleDecode(const Bytes& in) {
  Bytes out;
  for (size_t i = 0; i < in.size(); i++) {
    if (in[i]) { out.push_back(in[i]); continue; }
    EXPECT_LT(i + 1, in.size());
    if (i + 1 >= in.size()) break;
    EXPECT_GE(in[i + 1], 1);
    out.insert(out.end(), in[++i], 0);
  }
  return out;
}

// the top-level keys of {"pet":{...}} in order, and the text of each value
struct Fields {
  std::vector<std::string> keys;
  std::vector<std::string> vals;
  std::string get(const char* k) const { for (size_t i = 0; i < keys.size(); i++) if (keys[i] == k) return vals[i]; return ""; }
  bool has(const char* k) const { for (auto& x : keys) if (x == k) return true; return false; }
  std::string joined() const { std::string r; for (auto& k : keys) { if (!r.empty()) r += ","; r += k; } return r; }
};

Fields parseFields(const std::string& line) {
  Fields f;
  EXPECT_EQ(0u, line.find("{\"pet\":{")) << line.substr(0, 30);
  EXPECT_EQ("\"}}\n", line.substr(line.size() - 4));
  size_t i = 8;                                         // just after {"pet":{
  while (i < line.size()) {
    if (line[i] != '"') break;
    const size_t q = line.find('"', i + 1);
    f.keys.push_back(line.substr(i + 1, q - i - 1));
    EXPECT_EQ(':', line[q + 1]);
    const size_t v = q + 2;
    size_t e;
    if (line[v] == '"') { e = line.find('"', v + 1); f.vals.push_back(line.substr(v + 1, e - v - 1)); e++; }
    else if (line[v] == '{') {
      int depth = 0; bool inStr = false; e = v;
      for (; e < line.size(); e++) {
        const char c = line[e];
        if (c == '"') inStr = !inStr;
        if (!inStr) { if (c == '{') depth++; if (c == '}' && --depth == 0) { e++; break; } }
      }
      f.vals.push_back(line.substr(v, e - v));
    } else { e = v; while (e < line.size() && line[e] != ',' && line[e] != '}') e++; f.vals.push_back(line.substr(v, e - v)); }
    i = e;
    if (i < line.size() && line[i] == ',') i++; else break;
  }
  return f;
}

// what the dashboard keeps between lines
struct Pic {
  int w = 128, h = 64;
  bool colour = false, eink = false;
  uint16_t pal[16] = {};
  Bytes raw;
  long seq = -1;
  std::string name;
  Fields last;

  size_t rowBytes() const { return colour ? (size_t)(w + 1) / 2 : (size_t)(w + 7) / 8; }

  // returns false when the line is not usable (a delta after a gap)
  bool apply(const std::string& line) {
    Fields f = parseFields(line);
    last = f;
    const long s = atol(f.get("s").c_str());
    const bool key = f.get("k") == "1";
    Bytes d = rleDecode(b64decode(f.get("d")));
    if (key) {
      w = f.has("w") ? atoi(f.get("w").c_str()) : 128;
      h = f.has("h") ? atoi(f.get("h").c_str()) : 64;
      eink = f.has("e");
      colour = f.has("c");
      name = f.get("n");
      if (colour) {
        const std::string c = f.get("c");
        EXPECT_EQ(0u, c.find("{\"b\":4,\"p\":\""));
        Bytes p = b64decode(c.substr(12, c.size() - 12 - 2));
        EXPECT_EQ(32u, p.size());
        for (int i = 0; i < 16 && (size_t)i * 2 + 1 < p.size(); i++) pal[i] = (uint16_t)(p[i * 2] << 8 | p[i * 2 + 1]);
      }
    } else if (seq < 0 || s != seq + 1) {
      seq = -1;
      return false;
    }
    if (colour) for (size_t i = 1; i < d.size(); i++) d[i] ^= d[i - 1];      // undo "XOR with the byte before"
    if (key) raw = d;
    else { EXPECT_EQ(raw.size(), d.size()); for (size_t i = 0; i < raw.size() && i < d.size(); i++) raw[i] ^= d[i]; }
    EXPECT_EQ(rowBytes() * (size_t)h, raw.size()) << line.substr(0, 80);
    seq = s;
    return true;
  }

  // mono: 1 = ink; colour: the RGB565 of the pixel
  uint32_t pixel(int x, int y) const {
    if (colour) { const uint8_t b = raw[(size_t)y * rowBytes() + x / 2]; return pal[(x & 1) ? (b & 15) : (b >> 4)]; }
    return (raw[(size_t)y * rowBytes() + x / 8] >> (7 - (x & 7))) & 1;
  }
};

// ---- what the picture should be, worked out per pixel, separately from the canvas -------------------
struct Model {
  int w, h;
  std::vector<uint32_t> g;
  uint32_t ink = 1;
  Model(int w_, int h_, uint32_t bg) : w(w_), h(h_), g((size_t)w_ * h_, bg) {}
  void pix(int x, int y) { if (x >= 0 && x < w && y >= 0 && y < h) g[(size_t)y * w + x] = ink; }
  void fill(int x, int y, int ww, int hh) { for (int j = y; j < y + hh; j++) for (int i = x; i < x + ww; i++) pix(i, j); }
  void box(int x, int y, int ww, int hh) { fill(x, y, ww, 1); fill(x, y + hh - 1, ww, 1); fill(x, y, 1, hh); fill(x + ww - 1, y, 1, hh); }
  void glyphA(int x, int y, int sz) {                    // 'A' of the 5x7 font, bit 0 = top row
    static const uint8_t A[5] = {0x7C, 0x12, 0x11, 0x12, 0x7C};
    for (int c = 0; c < 5; c++) for (int r = 0; r < 8; r++) if (A[c] >> r & 1) fill(x + c * sz, y + r * sz, sz, sz);
  }
  void xbm(int x, int y, const uint8_t* b, int ww, int hh) {
    const int st = (ww + 7) / 8;
    for (int j = 0; j < hh; j++) for (int i = 0; i < ww; i++) if (b[j * st + i / 8] & (0x80 >> (i % 8))) pix(x + i, y + j);
  }
};

void expectSame(const Pic& p, const Model& m, const char* what) {
  ASSERT_EQ(m.w, p.w) << what;
  ASSERT_EQ(m.h, p.h) << what;
  int bad = 0;
  for (int y = 0; y < m.h; y++) for (int x = 0; x < m.w; x++)
    if (p.pixel(x, y) != m.g[(size_t)y * m.w + x]) {
      if (bad++ < 3) ADD_FAILURE() << what << ": pixel " << x << "," << y << " is " << p.pixel(x, y) << ", expected " << m.g[(size_t)y * m.w + x];
    }
  EXPECT_EQ(0, bad) << what;
}

// one frame through the tee; returns the line the link made ("" if none) and takes it off the link
std::string frame(Link& l, DisplayDriver& real, uint32_t now, void (*draw)(DisplayDriver&, void*), void* arg = nullptr) {
  NovaPetTee tee(real, l, now);
  tee.startFrame();
  draw(tee, arg);
  tee.endFrame();
  std::string out;
  while (l.pending()) { const size_t n = l.pending(); out.append((const char*)l.pendingData(), n); l.consumed(n); }
  return out;
}

const uint8_t kXbm[] = {0x80, 0x40, 0xFF, 0xC0, 0x01, 0x00};   // 10 x 3

std::string fname(const char* pet, const char* radio) {
  char out[NovaPetName::kMax + 1];
  memset(out, '!', sizeof(out));
  NovaPetName::frameName(pet, radio, out, sizeof(out));
  return std::string(out);
}

void drawDot(DisplayDriver& d, void*) { d.fillRect(10, 10, 3, 3); }
void drawDot2(DisplayDriver& d, void* a) { const int x = *(int*)a; d.fillRect(x, 20, 6, 4); d.drawRect(0, 0, 128, 64); }

std::vector<std::string> streamOf(const char* pet, const char* radio, bool useSetName = false) {
  FakeScreen scr(128, 64);
  Link l;
  EXPECT_TRUE(l.ok());
  if (useSetName) l.setName(pet); else l.setNames(pet, radio);
  std::vector<std::string> lines;
  uint32_t t = 1000;
  for (int i = 0; i < 6; i++, t += 300) {
    l.request(t);
    int x = 10 + i * 3;
    std::string s = frame(l, scr, t, drawDot2, &x);
    if (!s.empty()) lines.push_back(s);
  }
  return lines;
}

void monoPattern(uint8_t* a, uint8_t* b) {
  for (int i = 0; i < 1024; i++) { a[i] = (i % 37 == 0 || (i > 300 && i < 340)) ? (uint8_t)(i * 7 + 1) : 0; b[i] = a[i]; }
  for (int i = 500; i < 540; i++) b[i] ^= (uint8_t)(0x81 + i);
  b[1023] ^= 1;
}

}  // namespace

// =============================================================================================
// 1. The frame name: /lorafish.id, else the radio's name
// =============================================================================================
TEST(NovaFrameName, PetNameSetIsUsed) {
  EXPECT_EQ("Fluffy", fname("Fluffy", "MeshNode-7"));
  EXPECT_EQ("Mr Bubbles", fname("Mr Bubbles", ""));
}

TEST(NovaFrameName, UnsetFallsBackToTheRadioName) {
  EXPECT_EQ("MeshNode-7", fname("", "MeshNode-7"));
  EXPECT_EQ("MeshNode-7", fname(nullptr, "MeshNode-7"));
  EXPECT_EQ("MeshNode-7", fname("   ", "MeshNode-7")) << "a name of only spaces is no name";
  EXPECT_EQ("Hi", fname("", "  Hi  ")) << "the radio name loses its edge spaces";
  EXPECT_EQ("0123456789ABCDEF", fname("", "0123456789ABCDEFGHIJ")) << "16 characters at most";
  EXPECT_EQ("caf", fname("", "caf\xC3\xA9")) << "not ASCII: removed";
  EXPECT_EQ("", fname("", ""));
  EXPECT_EQ("", fname(nullptr, nullptr));
  EXPECT_EQ("", fname("", "   ")) << "nothing visible anywhere: no name";
}

TEST(NovaFrameName, QuoteCharactersAreStrippedFromBothNames) {
  EXPECT_EQ("ab", fname("a\"b", "Radio"));
  EXPECT_EQ("ab", fname("a\\b", "Radio"));
  EXPECT_EQ("Radio", fname("", "Ra\"d\\io")) << "the radio name is cleaned the same way";
  EXPECT_EQ("Radio", fname("\"\\\"\\", "Radio")) << "a pet name that is nothing but quotes counts as not set";
  const std::string evil = fname("\"}},{\"pet\":{\"s\":9", "");
  EXPECT_EQ(std::string::npos, evil.find('"'));
  EXPECT_EQ(std::string::npos, evil.find('\\'));
  const std::string evil2 = fname("", "\"}},{\"pet\":{\"s\":9");
  EXPECT_EQ(std::string::npos, evil2.find('"'));
  EXPECT_EQ(std::string::npos, evil2.find('\\'));
}

TEST(NovaFrameName, NeverWritesPastTheBuffer) {
  char small[8];
  memset(small, 'x', sizeof(small));
  NovaPetName::frameName("Fluffy", "Radio", small, sizeof(small));
  EXPECT_EQ(0, small[0]) << "a buffer under 17 bytes gets an empty name";
  NovaPetName::frameName("Fluffy", "Radio", nullptr, 0);
}

TEST(NovaFrameName, KeyFramesCarryNOnlyAndDeltasNever) {
  auto lines = streamOf("Fluffy", "Radio");
  ASSERT_GE(lines.size(), 3u);
  Fields k = parseFields(lines[0]);
  EXPECT_EQ("s,k,n,d", k.joined());
  EXPECT_EQ("Fluffy", k.get("n"));
  for (size_t i = 1; i < lines.size(); i++) {
    Fields d = parseFields(lines[i]);
    EXPECT_EQ("0", d.get("k"));
    EXPECT_EQ("s,k,d", d.joined()) << "delta " << i << " carries only s, k, d";
  }
}

TEST(NovaFrameName, LinkFallsBackToTheRadioNameOnKeyFrames) {
  auto lines = streamOf("", "MeshNode-7");
  ASSERT_GE(lines.size(), 2u);
  EXPECT_EQ("MeshNode-7", parseFields(lines[0]).get("n"));
  EXPECT_FALSE(parseFields(lines[1]).has("n"));
  lines = streamOf("Fluffy", "MeshNode-7");
  EXPECT_EQ("Fluffy", parseFields(lines[0]).get("n")) << "a set pet name wins over the radio name";
  lines = streamOf("", "");
  EXPECT_FALSE(parseFields(lines[0]).has("n")) << "no name anywhere: no n field at all";
  lines = streamOf("", "Ra\"di\\o");
  EXPECT_EQ("Radio", parseFields(lines[0]).get("n"));
  EXPECT_EQ(std::string::npos, lines[0].find("\\"));
  lines = streamOf("", "MeshNode-7", true);
  EXPECT_FALSE(parseFields(lines[0]).has("n")) << "setName(pet) alone has no fallback";
}

// =============================================================================================
// 2. Formats from the screen
// =============================================================================================
TEST(NovaScreenFormat, TakenFromTheDriver) {
  FakeScreen oled(128, 64);
  Format f = NovaPetTee::formatOf(oled);
  EXPECT_TRUE(f.isDefault());
  EXPECT_EQ(128, f.w); EXPECT_EQ(64, f.h); EXPECT_EQ(1, f.bpp); EXPECT_FALSE(f.eink);
  EXPECT_EQ(1024u, f.bytes());
  EXPECT_EQ(NovaPetLink::MAX_LINE, f.maxLine());

  FakeScreen lcd(135, 240, true);
  f = NovaPetTee::formatOf(lcd);
  EXPECT_FALSE(f.isDefault());
  EXPECT_TRUE(f.colour());
  EXPECT_EQ(68u, f.rowBytes()) << "135 pixels of 4 bits: 68 bytes, the last nibble unused";
  EXPECT_EQ(68u * 240u, f.bytes());

  FakeScreen colour128(128, 64, true);
  EXPECT_FALSE(NovaPetTee::formatOf(colour128).isDefault()) << "a 128x64 colour screen is not the mono OLED";

  FakeScreen ink(296, 128, false, true);
  f = NovaPetTee::formatOf(ink);
  EXPECT_TRUE(f.eink); EXPECT_EQ(1, f.bpp);
  EXPECT_EQ(37u * 128u, f.bytes());

  FakeScreen both(250, 122, true, true);
  EXPECT_FALSE(NovaPetTee::formatOf(both).colour()) << "e-ink wins: a still black and white picture";

  FakeScreen sq(128, 128);
  EXPECT_TRUE(NovaPetTee::suitable(sq));
  FakeScreen deck(320, 240, true);
  EXPECT_TRUE(NovaPetTee::suitable(deck));
  FakeScreen huge(480, 480, true);
  EXPECT_FALSE(NovaPetTee::suitable(huge));
  FakeScreen none(0, 0);
  EXPECT_FALSE(NovaPetTee::suitable(none));
  FakeScreen wide(700, 20);
  EXPECT_FALSE(NovaPetTee::suitable(wide));
}

TEST(NovaScreenFormat, SupportedFollowsSetFormat) {
  EXPECT_FALSE(NovaPetLink::supported());
  EXPECT_FALSE(NovaPetLink::setFormat(Format(0, 0, false, false)));
  EXPECT_FALSE(NovaPetLink::supported());
  EXPECT_TRUE(NovaPetLink::setFormat(Format(240, 135, true, false)));
  EXPECT_TRUE(NovaPetLink::supported());
  Link* l = NovaPetLink::link(true);
  ASSERT_NE(nullptr, l);
  EXPECT_TRUE(l->format() == Format(240, 135, true, false));
  EXPECT_NE(NovaPetLink::MAX_LINE, l->lineCapacity());
  NovaPetLink::setSupported(false);
  EXPECT_FALSE(NovaPetLink::supported());
}

// =============================================================================================
// 3. Mono 128x64: byte for byte what the first version sent
// =============================================================================================
TEST(NovaMonoRegression, LinesAreByteIdenticalToTheFirstEncoder) {
  // made with NovaPetLink::encodeLine of commit a5f0e04
  const std::string KEY_NONAME = "{\"pet\":{\"s\":1,\"k\":1,\"d\":\"AQAkBAAkBwAkCgAkDQAkEAAkEwAkFgAkGQAEPENKUVhfZm10e4KJkJeepayzusHIz9bd5Ovy+QABBw4VHCMqMTg/RgAeHwAkIgAkJQAkKAAkKwAkLgAkMQAkNAAkNwAkOgAkPQAkQAAkQwAkRgAkSQAkTAAkTwAkUgAY\"}}\n";
  const std::string KEY_NAME = "{\"pet\":{\"s\":2,\"k\":1,\"n\":\"Fluffy\",\"d\":\"AQAkBAAkBwAkCgAkDQAkEAAkEwAkFgAkGQAEPENKUVhfZm10e4KJkJeepayzusHIz9bd5Ovy+QABBw4VHCMqMTg/RgAeHwAkIgAkJQAkKAAkKwAkLgAkMQAkNAAkNwAkOgAkPQAkQAAkQwAkRgAkSQAkTAAkTwAkUgAY\"}}\n";
  const std::string DELTA = "{\"pet\":{\"s\":3,\"k\":0,\"d\":\"AP8A9XV2d3h5ent8fX5/gIGCg4SFhoeIiYqLjI2Oj5CRkpOUlZaXmJmam5wA/wDkAQ==\"}}\n";
  uint8_t a[1024], b[1024];
  monoPattern(a, b);
  static char buf[NovaPetLink::MAX_LINE];
  ASSERT_GT(NovaPetLink::encodeLine(a, nullptr, 1, buf, sizeof buf, nullptr), 0u);
  EXPECT_EQ(KEY_NONAME, std::string(buf));
  ASSERT_GT(NovaPetLink::encodeLine(a, nullptr, 2, buf, sizeof buf, "Fluffy"), 0u);
  EXPECT_EQ(KEY_NAME, std::string(buf));
  ASSERT_GT(NovaPetLink::encodeLine(b, a, 3, buf, sizeof buf, "Fluffy"), 0u);
  EXPECT_EQ(DELTA, std::string(buf)) << "a delta never carries the name";
  // the general encoder, given the 128x64 mono format, writes the same bytes
  ASSERT_GT(NovaPetLink::encodeFrame(Format(128, 64, false, false), a, nullptr, 2, buf, sizeof buf, "Fluffy"), 0u);
  EXPECT_EQ(KEY_NAME, std::string(buf));
  ASSERT_GT(NovaPetLink::encodeFrame(Format(128, 64, false, false), b, a, 3, buf, sizeof buf, "Fluffy"), 0u);
  EXPECT_EQ(DELTA, std::string(buf));
}

TEST(NovaMonoRegression, BufferBelowMaxLineIsStillRefused) {
  uint8_t a[1024];
  memset(a, 0x55, sizeof(a));
  char small[NovaPetLink::MAX_LINE - 1];
  EXPECT_EQ(0u, NovaPetLink::encodeLine(a, nullptr, 1, small, sizeof small));
  static char ok[NovaPetLink::MAX_LINE];
  EXPECT_GT(NovaPetLink::encodeLine(a, nullptr, 1, ok, sizeof ok), 0u);
}

TEST(NovaMonoRegression, WorstCasePictureFitsTheOriginalLineSize) {
  uint8_t a[1024];
  for (int i = 0; i < 1024; i++) a[i] = (i % 2) ? 0 : 0x55;      // every other byte set: the longest coding
  static char buf[NovaPetLink::MAX_LINE];
  const size_t n = NovaPetLink::encodeLine(a, nullptr, 4294967295u, buf, sizeof buf, "0123456789ABCDEF");
  ASSERT_GT(n, 0u);
  EXPECT_LT(n, NovaPetLink::MAX_LINE);
}

TEST(NovaMonoRegression, TeeStreamOnAnOledCarriesNoScreenFields) {
  FakeScreen scr(128, 64);
  Link l(NovaPetTee::formatOf(scr));
  ASSERT_TRUE(l.ok());
  EXPECT_EQ(NovaPetLink::MAX_LINE, l.lineCapacity());
  l.setNames("Fluffy", "Radio");
  l.request(1000);
  Model m(128, 64, 0);
  m.fill(10, 10, 3, 3);
  std::string s = frame(l, scr, 1000, drawDot);
  ASSERT_FALSE(s.empty());
  Fields f = parseFields(s);
  EXPECT_EQ("s,k,n,d", f.joined()) << "no w, h, e or c on a 128x64 mono screen";
  Pic p;
  ASSERT_TRUE(p.apply(s));
  EXPECT_FALSE(p.colour);
  expectSame(p, m, "oled");
}

TEST(NovaMonoRegression, AFrameWithoutCIsReadAsMono128x64) {
  // the lines of the first encoder: no w, h, e or c. A reader that knows nothing of colour reads them as it always did.
  uint8_t a[1024], b[1024];
  monoPattern(a, b);
  Pic p;
  ASSERT_TRUE(p.apply("{\"pet\":{\"s\":2,\"k\":1,\"n\":\"Fluffy\",\"d\":\"AQAkBAAkBwAkCgAkDQAkEAAkEwAkFgAkGQAEPENKUVhfZm10e4KJkJeepayzusHIz9bd5Ovy+QABBw4VHCMqMTg/RgAeHwAkIgAkJQAkKAAkKwAkLgAkMQAkNAAkNwAkOgAkPQAkQAAkQwAkRgAkSQAkTAAkTwAkUgAY\"}}\n"));                        // number 2, a key picture
  EXPECT_FALSE(p.last.has("c"));
  EXPECT_FALSE(p.colour);
  EXPECT_FALSE(p.eink);
  EXPECT_EQ(128, p.w);
  EXPECT_EQ(64, p.h);
  EXPECT_EQ("Fluffy", p.name);
  EXPECT_EQ(Bytes(a, a + 1024), p.raw);
  ASSERT_TRUE(p.apply("{\"pet\":{\"s\":3,\"k\":0,\"d\":\"AP8A9XV2d3h5ent8fX5/gIGCg4SFhoeIiYqLjI2Oj5CRkpOUlZaXmJmam5wA/wDkAQ==\"}}\n"));                           // number 3, the change that follows
  EXPECT_EQ(Bytes(b, b + 1024), p.raw);
}

// =============================================================================================
// 4. Colour screens: 4 bits a pixel, 16 colours, in "c"
// =============================================================================================
namespace {
struct Scene { Model* m; int dx; uint16_t extra; };

// The scene is drawn twice: into the tee, and into the model. A colour is RGB565.
void drawColourScene(DisplayDriver& d, void* arg) {
  Scene& sc = *(Scene*)arg;
  Model& m = *sc.m;
  d.setColor(0xF800); m.ink = 0xF800;
  d.fillRect(3 + sc.dx, 5, 51, 20); m.fill(3 + sc.dx, 5, 51, 20);       // odd start, odd width
  d.setColor(0x001F); m.ink = 0x001F;
  d.drawRect(100, 100, 31, 21); m.box(100, 100, 31, 21);
  d.setColor(0x07E0); m.ink = 0x07E0;
  d.setCursor(7, 60); d.print("A"); m.glyphA(7, 60, 1);
  d.setTextSize(2); d.setCursor(40, 60); d.print("A"); m.glyphA(40, 60, 2);
  d.setTextSize(1);
  d.setColor(0xFFE0); m.ink = 0xFFE0;
  d.drawXbm(21, 90, kXbm, 10, 3); m.xbm(21, 90, kXbm, 10, 3);
  d.fillRect(-5, -5, 10, 10); m.fill(-5, -5, 10, 10);                    // off the screen at the top left
  d.fillRect(d.width() - 3, 0, 20, 4); m.fill(d.width() - 3, 0, 20, 4);  // off the right edge
  d.fillRect(0, d.height() - 2, d.width(), 9); m.fill(0, d.height() - 2, d.width(), 9);   // off the bottom
  if (sc.extra) { d.setColor(sc.extra); m.ink = sc.extra; d.fillRect(70, 30, 9, 9); m.fill(70, 30, 9, 9); }
}

void drawFlatBlue(DisplayDriver& d, void*) { d.setColor(0x001F); d.fillRect(0, 0, d.width(), d.height()); }

void drawNoise(DisplayDriver& d, void*) {
  uint32_t r = 12345;
  for (int y = 0; y < d.height(); y++) for (int x = 0; x < d.width(); x++) {
    r = r * 1664525u + 1013904223u;
    d.setColor((ColorVal)(0x0821u * (1 + ((r >> 24) % 15))));
    d.fillRect(x, y, 1, 1);
  }
}

void drawStrips(DisplayDriver& d, void*) {                  // 20 different colours: more than the palette holds
  for (int i = 0; i < 20; i++) { d.setColor((ColorVal)(0x0841u * (i + 1))); d.fillRect(i * 4, 0, 4, 10); }
}

void drawBlack(DisplayDriver& d, void*) { d.setColor(0); d.fillRect(1, 1, 5, 5); }
}  // namespace

class NovaColourScreen : public ::testing::TestWithParam<std::pair<int, int>> {
protected:
  void SetUp() override { UIColor::window_bkg = 0xFFFF; }
  void TearDown() override { UIColor::window_bkg = 0; }
};

TEST_P(NovaColourScreen, KeyAndDeltaMatchThePictureDrawn) {
  const int W = GetParam().first, H = GetParam().second;
  FakeScreen scr(W, H, true);
  Link l(NovaPetTee::formatOf(scr));
  ASSERT_TRUE(l.ok());
  l.setNames("", "Radio");
  Pic p;

  Model m1(W, H, 0xFFFF);
  Scene s1{&m1, 0, 0};
  l.request(1000);
  std::string k = frame(l, scr, 1000, drawColourScene, &s1);
  ASSERT_FALSE(k.empty());
  Fields f = parseFields(k);
  EXPECT_EQ("s,k,n,w,h,c,d", f.joined());
  EXPECT_EQ("1", f.get("k"));
  EXPECT_EQ("Radio", f.get("n"));
  EXPECT_EQ(std::to_string(W), f.get("w"));
  EXPECT_EQ(std::to_string(H), f.get("h"));
  ASSERT_TRUE(p.apply(k));
  EXPECT_TRUE(p.colour);
  EXPECT_FALSE(p.eink);
  EXPECT_EQ(0xFFFF, p.pal[0]) << "the window background is palette colour 0";
  expectSame(p, m1, "key");

  Model m2(W, H, 0xFFFF);
  Scene s2{&m2, 11, 0};
  l.request(1300);
  std::string d = frame(l, scr, 1300, drawColourScene, &s2);
  ASSERT_FALSE(d.empty());
  f = parseFields(d);
  EXPECT_EQ("0", f.get("k"));
  EXPECT_EQ("s,k,d", f.joined()) << "a delta carries no name, size or palette";
  ASSERT_TRUE(p.apply(d));
  expectSame(p, m2, "delta");
  if (W * H > 10000) EXPECT_LT(d.size(), k.size()) << "a small change costs less than the whole picture (a key also carries name, size and palette)";
  EXPECT_LE(d.size() + 1, l.lineCapacity());
  EXPECT_LE(k.size() + 1, l.lineCapacity());
}

TEST_P(NovaColourScreen, ANewColourForcesAKeyPictureWithTheNewPalette) {
  const int W = GetParam().first, H = GetParam().second;
  FakeScreen scr(W, H, true);
  Link l(NovaPetTee::formatOf(scr));
  ASSERT_TRUE(l.ok());
  Pic p;
  Model m1(W, H, 0xFFFF), m2(W, H, 0xFFFF), m3(W, H, 0xFFFF), m4(W, H, 0xFFFF);
  Scene s1{&m1, 0, 0}, s2{&m2, 5, 0}, s3{&m3, 9, 0x8410}, s4{&m4, 12, 0x8410};
  l.request(1000);
  ASSERT_TRUE(p.apply(frame(l, scr, 1000, drawColourScene, &s1)));
  l.request(1300);
  std::string d = frame(l, scr, 1300, drawColourScene, &s2);
  EXPECT_EQ("0", parseFields(d).get("k"));
  ASSERT_TRUE(p.apply(d));
  l.request(1600);
  std::string k = frame(l, scr, 1600, drawColourScene, &s3);      // 0x8410 (grey) has not been used so far
  ASSERT_FALSE(k.empty());
  EXPECT_EQ("1", parseFields(k).get("k")) << "a colour that is not in the palette the dashboard has: a key picture";
  EXPECT_TRUE(parseFields(k).has("c"));
  ASSERT_TRUE(p.apply(k));
  bool inPal = false;
  for (int i = 0; i < 16; i++) inPal |= p.pal[i] == 0x8410;
  EXPECT_TRUE(inPal);
  expectSame(p, m3, "after the new colour");
  l.request(1900);
  d = frame(l, scr, 1900, drawColourScene, &s4);
  EXPECT_EQ("0", parseFields(d).get("k")) << "and back to deltas";
  ASSERT_TRUE(p.apply(d));
  expectSame(p, m4, "delta after the key");
}

INSTANTIATE_TEST_SUITE_P(Sizes, NovaColourScreen,
  ::testing::Values(std::make_pair(135, 240),      // portrait, odd width (T114-style TFT)
                    std::make_pair(240, 135),      // landscape (Cardputer)
                    std::make_pair(320, 240),      // T-Deck
                    std::make_pair(128, 64)));     // a colour screen of the OLED size is still a colour picture

TEST(NovaColourScreen, PaletteHoldsSixteenAndTheRestAreNearest) {
  UIColor::window_bkg = 0xFFFF;
  FakeScreen scr(100, 12, true);
  Link l(NovaPetTee::formatOf(scr));
  ASSERT_TRUE(l.ok());
  l.request(1000);
  std::string k = frame(l, scr, 1000, drawStrips);
  ASSERT_FALSE(k.empty());
  EXPECT_GT(l.canvas.overflowed(), 0u);
  Pic p;
  ASSERT_TRUE(p.apply(k));
  EXPECT_EQ(16, l.canvas.paletteCount());
  for (int i = 0; i < 15; i++)                              // palette 0 = background, then the first 15 strips, exactly
    EXPECT_EQ((uint32_t)(0x0841u * (i + 1)), p.pixel(i * 4 + 1, 2)) << "strip " << i;
  for (int i = 15; i < 20; i++) {                           // the rest: some colour of the palette
    bool found = false;
    for (int c = 0; c < 16; c++) found |= p.pal[c] == p.pixel(i * 4 + 1, 2);
    EXPECT_TRUE(found) << "strip " << i;
  }
  UIColor::window_bkg = 0;
}

TEST(NovaColourScreen, FlatAreaOfAnyColourCostsLittle) {
  UIColor::window_bkg = 0xFFFF;
  FakeScreen scr(240, 135, true);
  Link l(NovaPetTee::formatOf(scr));
  ASSERT_TRUE(l.ok());
  l.request(1000);
  std::string k = frame(l, scr, 1000, drawFlatBlue);
  ASSERT_FALSE(k.empty());
  EXPECT_LT(k.size(), 800u) << "16200 bytes of one non-zero colour, coded";
  Pic p;
  ASSERT_TRUE(p.apply(k));
  Model m(240, 135, 0x001F);
  expectSame(p, m, "flat");
  UIColor::window_bkg = 0;
}

TEST(NovaColourScreen, APictureTooBusyForTheLineIsSkippedNotCut) {
  UIColor::window_bkg = 0xFFFF;
  FakeScreen scr(240, 135, true);
  Link l(NovaPetTee::formatOf(scr));
  ASSERT_TRUE(l.ok());
  l.request(1000);
  std::string k = frame(l, scr, 1000, drawNoise);
  EXPECT_TRUE(k.empty()) << "noise in every pixel does not fit the line buffer: nothing goes out";
  EXPECT_EQ(0u, l.sequence()) << "and the line number does not move";
  l.request(1300);
  Model m(240, 135, 0xFFFF);
  Scene sc{&m, 0, 0};
  k = frame(l, scr, 1300, drawColourScene, &sc);
  ASSERT_FALSE(k.empty()) << "the next ordinary picture still starts the stream with a key picture";
  EXPECT_EQ("1", parseFields(k).get("k"));
  EXPECT_EQ(1u, l.sequence());
  UIColor::window_bkg = 0;
}

TEST(NovaColourScreen, ABlackPictureOnABlackWindowIsStillAColourPicture) {
  UIColor::window_bkg = 0;                                  // dark themes: window background 0x0000
  FakeScreen scr(135, 240, true);
  Link l(NovaPetTee::formatOf(scr));
  l.request(1000);
  std::string k = frame(l, scr, 1000, drawBlack);
  Pic p;
  ASSERT_TRUE(p.apply(k));
  EXPECT_EQ(0u, p.pixel(2, 2));
  EXPECT_EQ(0u, p.pal[0]);
}

TEST(NovaColourScreen, TeeSendsTheRealScreenTheSameCallsAsWithoutIt) {
  UIColor::window_bkg = 0xFFFF;
  FakeScreen a(240, 135, true), b(240, 135, true);
  Link l(NovaPetTee::formatOf(a));
  l.request(1000);
  Model m1(240, 135, 0xFFFF), m2(240, 135, 0xFFFF);
  Scene s1{&m1, 0, 0}, s2{&m2, 0, 0};
  frame(l, a, 1000, drawColourScene, &s1);
  b.startFrame(0xFFFF);
  drawColourScene(b, &s2);
  b.endFrame();
  EXPECT_EQ(b.calls, a.calls);
  UIColor::window_bkg = 0;
}

TEST(NovaColourScreen, StreamRestartsWithAFreshPalette) {
  UIColor::window_bkg = 0xFFFF;
  FakeScreen scr(135, 240, true);
  Link l(NovaPetTee::formatOf(scr));
  Model m1(135, 240, 0xFFFF);
  Scene s1{&m1, 0, 0x8410};
  l.request(1000);
  frame(l, scr, 1000, drawColourScene, &s1);
  const int before = l.canvas.paletteCount();
  EXPECT_GT(before, 4);
  l.request(20000);                                          // the window had lapsed: a new stream
  EXPECT_EQ(0, l.canvas.paletteCount());
  UIColor::window_bkg = 0;
}

// =============================================================================================
// 4b. Palette seed: which colours get the first slots, and that every key picture starts the same way
// =============================================================================================
namespace {
// 20 strips drawn background-first, then the strips the picture cares about LAST (sprite colours): without a seed
// they would be the ones that overflow.
const uint16_t kPrio[4] = {0xF81F, 0x07E0, 0xFFE0, 0x2104};              // seeded, in this order
void drawLateSprite(DisplayDriver& d, void*) {
  for (int i = 0; i < 18; i++) { d.setColor((ColorVal)(0x0841u * (i + 1))); d.fillRect(i * 4, 0, 4, 10); }   // 18 background shades
  for (int i = 3; i >= 0; i--) { d.setColor(kPrio[i]); d.fillRect(i * 4, 20, 4, 4); }                      // drawn in the reverse order
}
}  // namespace

TEST(NovaPaletteSeed, SeededColoursTakeTheLowestSlotsInOrderAndNeverSnap) {
  UIColor::window_bkg = 0xFFFF;
  FakeScreen scr(100, 30, true);
  Link l(NovaPetTee::formatOf(scr));
  ASSERT_TRUE(l.ok());
  l.setPaletteSeed(kPrio, 4);
  l.request(1000);
  Pic p;
  ASSERT_TRUE(p.apply(frame(l, scr, 1000, drawLateSprite)));
  EXPECT_EQ(0xFFFF, p.pal[0]) << "the window background is still slot 0";
  for (int i = 0; i < 4; i++) EXPECT_EQ(kPrio[i], p.pal[1 + i]) << "seed slot " << i;
  for (int i = 0; i < 4; i++) EXPECT_EQ((uint32_t)kPrio[i], p.pixel(i * 4 + 1, 21)) << "strip " << i << " is exact";
  EXPECT_GT(l.canvas.overflowed(), 0u) << "18 shades do not all fit: the shades overflow";
  UIColor::window_bkg = 0;
}

TEST(NovaPaletteSeed, WithoutASeedTheLateColoursAreTheOnesThatSnap) {   // what the seed fixes
  UIColor::window_bkg = 0xFFFF;
  FakeScreen scr(100, 30, true);
  Link l(NovaPetTee::formatOf(scr));
  l.request(1000);
  Pic p;
  ASSERT_TRUE(p.apply(frame(l, scr, 1000, drawLateSprite)));
  int exact = 0;
  for (int i = 0; i < 4; i++) exact += p.pixel(i * 4 + 1, 21) == (uint32_t)kPrio[i];
  EXPECT_LT(exact, 4);
  UIColor::window_bkg = 0;
}

TEST(NovaPaletteSeed, DuplicatesAndTheBackgroundTakeOneSlot) {
  UIColor::window_bkg = 0xFFFF;
  FakeScreen scr(100, 30, true);
  Link l(NovaPetTee::formatOf(scr));
  const uint16_t seed[] = {0xFFFF, 0xF81F, 0xF81F, 0x07E0, 0xFFFF};
  l.setPaletteSeed(seed, 5);
  l.request(1000);
  Pic p;
  ASSERT_TRUE(p.apply(frame(l, scr, 1000, drawDot)));
  EXPECT_EQ(0xFFFF, p.pal[0]);
  EXPECT_EQ(0xF81F, p.pal[1]);
  EXPECT_EQ(0x07E0, p.pal[2]);
  EXPECT_EQ(3, l.canvas.paletteCount());
  UIColor::window_bkg = 0;
}

TEST(NovaPaletteSeed, EveryKeyPictureStartsFromTheSameSeedWhateverTheDrawingOrder) {
  UIColor::window_bkg = 0xFFFF;
  FakeScreen scr(100, 30, true);
  Link l(NovaPetTee::formatOf(scr));
  l.setPaletteSeed(kPrio, 4);
  l.request(1000);
  Pic p1;
  ASSERT_TRUE(p1.apply(frame(l, scr, 1000, drawLateSprite)));
  uint16_t first[16];
  memcpy(first, l.canvas.palette(), sizeof(first));
  l.dropPending();                                           // the next picture is a key picture again
  l.request(1300);
  Pic p2;
  ASSERT_TRUE(p2.apply(frame(l, scr, 1300, drawStrips)));    // a different picture, other colours, other order
  EXPECT_EQ(0xFFFF, p2.pal[0]);
  for (int i = 0; i < 4; i++) EXPECT_EQ(first[1 + i], p2.pal[1 + i]) << "seed slot " << i;
  l.dropPending();
  l.request(1600);
  Pic p3;
  ASSERT_TRUE(p3.apply(frame(l, scr, 1600, drawLateSprite)));   // the first scene again: the same palette as the first time
  EXPECT_EQ(0, memcmp(first, p3.pal, sizeof(first)));
  UIColor::window_bkg = 0;
}

TEST(NovaPaletteSeed, DeltaPicturesKeepTheirKeyPicturesPalette) {
  UIColor::window_bkg = 0xFFFF;
  FakeScreen scr(100, 30, true);
  Link l(NovaPetTee::formatOf(scr));
  l.setPaletteSeed(kPrio, 4);
  l.request(1000);
  Pic p;
  ASSERT_TRUE(p.apply(frame(l, scr, 1000, drawLateSprite)));
  uint16_t before[16];
  memcpy(before, l.canvas.palette(), sizeof(before));
  l.request(1300);
  const std::string d = frame(l, scr, 1300, drawLateSprite);
  EXPECT_TRUE(d.empty()) << "nothing moved: nothing to say";
  int x = 4;
  l.request(1600);
  const std::string d2 = frame(l, scr, 1600, drawDot2, &x);
  if (!d2.empty()) EXPECT_EQ("0", parseFields(d2).get("k"));
  EXPECT_EQ(0, memcmp(before, l.canvas.palette(), 5 * sizeof(uint16_t))) << "the seeded slots do not move";
  UIColor::window_bkg = 0;
}

// =============================================================================================
// 5. E-ink: a still picture, black on white, no animation
// =============================================================================================
namespace {
struct InkScene { Model* m; int x; };
void drawInk(DisplayDriver& d, void* arg) {
  InkScene& sc = *(InkScene*)arg;
  Model& m = *sc.m;
  d.setColor(0); m.ink = 1;                                  // black ink on the white window (window_bkg = 1)
  d.setCursor(sc.x, 20); d.print("A"); m.glyphA(sc.x, 20, 1);
  d.setTextSize(3); d.setCursor(40, 60); d.print("A"); m.glyphA(40, 60, 3);
  d.setTextSize(1);
  d.drawRect(0, 0, d.width(), d.height()); m.box(0, 0, d.width(), d.height());
  d.drawXbm(200, 90, kXbm, 10, 3); m.xbm(200, 90, kXbm, 10, 3);
}
}  // namespace

class NovaEinkScreen : public ::testing::Test {
protected:
  void SetUp() override { UIColor::window_bkg = 1; }        // WHITE
  void TearDown() override { UIColor::window_bkg = 0; }
};

TEST_F(NovaEinkScreen, FirstPictureIsAKeyWithSizeAndTheEinkFlagAndNoColour) {
  FakeScreen scr(296, 128, false, true);
  Link l(NovaPetTee::formatOf(scr));
  ASSERT_TRUE(l.ok());
  l.setNames("", "Radio");
  Model m(296, 128, 0);
  InkScene sc{&m, 10};
  l.request(1000);
  std::string k = frame(l, scr, 1000, drawInk, &sc);
  ASSERT_FALSE(k.empty());
  Fields f = parseFields(k);
  EXPECT_EQ("s,k,n,w,h,e,d", f.joined());
  EXPECT_EQ("1", f.get("e"));
  EXPECT_EQ("296", f.get("w"));
  EXPECT_EQ("128", f.get("h"));
  EXPECT_FALSE(f.has("c")) << "one bit a pixel: ink or paper";
  Pic p;
  ASSERT_TRUE(p.apply(k));
  EXPECT_TRUE(p.eink);
  EXPECT_FALSE(p.colour);
  expectSame(p, m, "e-ink");
  EXPECT_EQ(1u, p.pixel(0, 0)) << "black ink (the box) is a set pixel; the paper is 0";
  EXPECT_EQ(0u, p.pixel(150, 64));
}

TEST_F(NovaEinkScreen, NeverADeltaAndNotMoreOftenThanEveryTwoSeconds) {
  FakeScreen scr(250, 122, false, true);
  Link l(NovaPetTee::formatOf(scr));
  ASSERT_TRUE(l.ok());
  l.setNames("Fluffy", "Radio");
  Pic p;
  int lines = 0;
  uint32_t lastAt = 0;
  for (int i = 0; i < 40; i++) {                            // something changes every 300 ms for 12 s
    const uint32_t t = 1000 + i * 300;
    Model m(250, 122, 0);
    InkScene sc{&m, 10 + i};
    l.request(t);
    std::string s = frame(l, scr, t, drawInk, &sc);
    if (s.empty()) continue;
    Fields f = parseFields(s);
    EXPECT_EQ("1", f.get("k")) << "e-ink pictures are whole pictures, never a change";
    EXPECT_TRUE(f.has("e"));
    EXPECT_EQ("Fluffy", f.get("n")) << "every picture is a key picture, so every one has the name";
    ASSERT_TRUE(p.apply(s));
    expectSame(p, m, "e-ink frame");
    if (lines) EXPECT_GE(t - lastAt, 2000u);
    lastAt = t;
    lines++;
  }
  EXPECT_GE(lines, 5);
  EXPECT_LE(lines, 7) << "12 s of changes: at most one picture every 2 s";
}

TEST_F(NovaEinkScreen, UnchangedScreenStaysQuietThenKeepsAlive) {
  FakeScreen scr(250, 122, false, true);
  Link l(NovaPetTee::formatOf(scr));
  Model m(250, 122, 0);
  InkScene sc{&m, 10};
  l.request(1000);
  EXPECT_FALSE(frame(l, scr, 1000, drawInk, &sc).empty());
  l.request(2500); EXPECT_TRUE(frame(l, scr, 2500, drawInk, &sc).empty());
  l.request(4000); EXPECT_TRUE(frame(l, scr, 4000, drawInk, &sc).empty());
  l.request(6100);
  std::string s = frame(l, scr, 6100, drawInk, &sc);        // 5 s since the last key: the same picture again, for a page that joined late
  ASSERT_FALSE(s.empty());
  EXPECT_EQ("1", parseFields(s).get("k"));
  EXPECT_EQ(2u, l.sequence());
}

TEST(NovaMonoOtherSizes, SquareOledGetsItsSizeAndKeepsDeltas) {
  UIColor::window_bkg = 0;
  FakeScreen scr(128, 128);
  Link l(NovaPetTee::formatOf(scr));
  ASSERT_TRUE(l.ok());
  Pic p;
  l.request(1000);
  Model m1(128, 128, 0), m2(128, 128, 0);
  auto draw = [](DisplayDriver& d, void* a) { Model& m = *(Model*)a; d.setColor(1); m.ink = 1; d.fillRect(3, 100, 13, 7); m.fill(3, 100, 13, 7); };
  std::string k = frame(l, scr, 1000, +draw, &m1);
  Fields f = parseFields(k);
  EXPECT_EQ("s,k,w,h,d", f.joined());
  EXPECT_EQ("128", f.get("h"));
  ASSERT_TRUE(p.apply(k));
  expectSame(p, m1, "128x128");
  auto draw2 = [](DisplayDriver& d, void* a) { Model& m = *(Model*)a; d.setColor(1); m.ink = 1; d.fillRect(3, 100, 13, 7); m.fill(3, 100, 13, 7); d.fillRect(60, 60, 5, 5); m.fill(60, 60, 5, 5); };
  l.request(1300);
  std::string d = frame(l, scr, 1300, +draw2, &m2);
  EXPECT_EQ("s,k,d", parseFields(d).joined());
  ASSERT_TRUE(p.apply(d));
  expectSame(p, m2, "128x128 delta");
}

TEST(NovaMonoOtherSizes, OddWidthOledPadsEachRow) {
  UIColor::window_bkg = 0;
  FakeScreen scr(132, 64);                                  // 132 wide: 17 bytes a row, the last 4 bits unused
  Link l(NovaPetTee::formatOf(scr));
  ASSERT_TRUE(l.ok());
  l.request(1000);
  Model m(132, 64, 0);
  auto draw = [](DisplayDriver& d, void* a) { Model& m = *(Model*)a; d.setColor(1); m.ink = 1; d.fillRect(126, 1, 20, 3); m.fill(126, 1, 20, 3); d.drawRect(0, 0, 132, 64); m.box(0, 0, 132, 64); };
  Pic p;
  ASSERT_TRUE(p.apply(frame(l, scr, 1000, +draw, &m)));
  EXPECT_EQ(17u, p.rowBytes());
  expectSame(p, m, "132x64");
}

TEST(NovaScreenLink, UnusableFormatsMakeNoLink) {
  Link bad(Format(0, 0, false, false));
  EXPECT_FALSE(bad.ok());
  bad.request(1000);
  bad.frameDone(1000);                                        // must not crash
  EXPECT_EQ(0u, bad.pending());
  Link huge(Format(480, 480, true, false));
  EXPECT_FALSE(huge.ok());
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
