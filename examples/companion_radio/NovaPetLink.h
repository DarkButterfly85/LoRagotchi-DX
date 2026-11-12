#pragma once
// LORAGOTCHI NOVA serial link: the pet picture for the Nova dashboard (pure C++, no Arduino calls).
//
// The picture format and the dashboard page that reads it come from LODESTAR ORION / LODESTAR NOVA
// (Aries Thorne, Todd Steinhauer, FEAR REACTIVE), used with the authors' permission; see NOTICE and
// docs/CREDITS.md. This file is a separate LoRaGotchi implementation of that format. The pixels are
// taken from the pet's own screen drawing by NovaPetTee.h (ui-new), so nothing here changes pet logic,
// saves or radio traffic. Nothing is sent unless the Nova page (or a person) types "nova pet".
//
// One line per picture, only while asked (see Link::request):
//   {"pet":{"s":SEQ,"k":KEY,"d":"BASE64"}}
// d is the picture, coded as below; k is 1 for a whole picture ("key"), 0 for a change ("delta").
//
// ---- screens: one encoder for every screen -------------------------------------------------------
// The size and colour depth come from the active DisplayDriver (NovaPetTee::formatOf): width(), height(),
// supportsColor(), isEink(). A key picture says what it is, only when it is not the original case:
//   mono 128x64 (the OLEDs)   nothing extra: {"pet":{"s":1,"k":1,"d":"..."}}  (byte for byte what it always was)
//   any other size            "w":WIDTH,"h":HEIGHT before d
//   e-ink                     "e":1 before d: a still picture, black ink on white paper, no animation
//   colour                    "c":{"b":4,"p":"BASE64"} before d, see below
// A frame with no "c" is a one-colour (mono) picture: the dashboard draws it as it always did, so a
// dashboard (or a radio) that knows nothing of colour keeps working. No "w"/"h" means 128x64.
// w, h, e and c are only on key pictures (like the name n); a delta picture continues the last key picture.
//
// Mono picture (1 bit a pixel): rows padded to whole bytes, (w+7)/8 bytes a row, top row first, leftmost pixel =
// the top bit (0x80). A set bit is "ink" (anything but the window background colour).
//
// Colour picture ("c" present, 4 bits a pixel): (w+1)/2 bytes a row, top row first, leftmost pixel = the high
// nibble. A pixel is an index into the palette p: 16 colours, each 2 bytes of RGB565 (big endian, as the
// screen takes them), base64 of 32 bytes. The palette is built as the screen draws (the first colour is the
// window background), is the same in every delta that follows its key picture, and a colour that is new
// forces a new key picture. More than 16 distinct colours: the extras are drawn in the nearest palette colour.
// Colour d is coded one more way than mono, so flat areas of any colour cost little: after the XOR with the
// previous picture (key: none), every byte is XORed with the byte before it (h[0] = t[0], h[i] = t[i] ^ t[i-1]).
// Decode: run-length decode, then t[i] = h[i] ^ t[i-1], then (delta) XOR with the previous picture.
//
// When KEY is 1, d is the whole picture; otherwise d is the XOR with the previous picture and SEQ is
// exactly one more than the last line. d is run-length coded: a 0x00 byte is followed by a count
// (1..255) of zero bytes; every other byte stands for itself. Then base64 (standard alphabet, padded).
// E-ink: every picture is a key picture (no deltas), sent only when the screen changed (at most one
// every 2 s) and now and then as a keep-alive.
//
// A key picture also carries the pet's name as "n" (before w/h/e/c/d), only when there is one:
//   {"pet":{"s":SEQ,"k":1,"n":"Fluffy","d":"BASE64"}}
// The name is the pet's own name from /lorafish.id; when the pet has none, the radio's node name
// (NovaPetName::frameName). Printable ASCII without '"' and '\', 16 characters at most. Same field as
// PetMirror.h's key frames. (PetMirror.h's key frames also use "c" for a pet count; there it is a number, here it
// is an object, and the two encoders are never in one build: only this one is in the firmware.)

#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <new>
#include <helpers/NovaPetName.h>   // the pet's name, made safe for a JSON line

// The link needs the pet UI and a free USB serial port (the phone talks over Bluetooth). Builds that
// carry the phone protocol on USB, RP2040 WiFi builds that use USB for the rescue CLI, and the
// LORAFISH_SERIAL_TEST builds (they read USB serial for button commands) leave it out.
// Add -D LORAGOTCHI_NO_NOVA_LINK to leave it out of any other build.
#if defined(LORAFISH_UI) && !defined(ENABLE_USB_INTERFACE) && !defined(LORAGOTCHI_NO_NOVA_LINK) && \
    !defined(LORAFISH_SERIAL_TEST) && !(defined(ENABLE_WIFI_INTERFACE) && defined(RP2040_PLATFORM))
#define LORAGOTCHI_NOVA_LINK 1
#endif

namespace NovaPetLink {

static constexpr int W = 128, H = 64, ROW = W / 8;    // the original screen: 128x64, one bit a pixel
static constexpr int BYTES = ROW * H;                 // 1024
// Longest possible line of the original screen: prefix 34 + name field 23 + base64 of at most 1536 coded bytes (2048) + '"}}' + newline + NUL.
static constexpr size_t MAX_LINE = 2112;
static constexpr uint32_t WINDOW_MS = 4000;           // a "nova pet" keeps the stream going this long
static constexpr uint32_t MIN_GAP_MS = 250;           // at most four changed pictures a second
static constexpr uint32_t EINK_MIN_GAP_MS = 2000;     // e-ink: a still picture at most every 2 s
static constexpr uint32_t KEY_EVERY_FRAMES = 40;      // and a whole picture now and then, so a page
static constexpr uint32_t KEY_EVERY_MS = 5000;        // that joins late or misses a line recovers
static constexpr int MAX_DIM = 512;                   // widest/tallest screen the link copies
static constexpr size_t MAX_FRAME_BYTES = 40000;      // 320x240 in 4 bits is 38400; bigger is refused
static constexpr size_t MAX_LINE_CAP = 16384;         // the line buffer never grows past this (a rare picture that
                                                      // codes bigger is skipped, not cut)
static constexpr int PALETTE_SIZE = 16;               // colour pictures: 4 bits a pixel

// Output pacing (MyMesh.cpp checkNovaSerial): at most sendChunk(baud) bytes every SEND_GAP_MS, written without waiting
// for the port. A byte on the wire is 10 bits (8N1), so the port carries baud/10 bytes a second = baud/1000 bytes per
// 10 ms. baud/1200 of them is about 83 percent of that: 96 bytes at 115200 (what the link always sent), 192 at 230400,
// 384 at 460800, and 512 at 921600 and above (the cap keeps one step small). Frame format unchanged.
static constexpr uint32_t SEND_GAP_MS = 10;
static constexpr size_t SEND_CHUNK_MIN = 96, SEND_CHUNK_MAX = 512;
static constexpr size_t sendChunk(uint32_t baud) {
  return baud / 1200u < SEND_CHUNK_MIN ? SEND_CHUNK_MIN : baud / 1200u > SEND_CHUNK_MAX ? SEND_CHUNK_MAX : (size_t)(baud / 1200u);
}

// What one screen looks like to the link. Built from the DisplayDriver (NovaPetTee::formatOf).
struct Format {
  uint16_t w, h;
  uint8_t bpp;        // 1 = mono (one ink), 4 = colour (16-entry palette)
  bool eink;          // a still picture, black on white, no animation (always 1 bit)
  Format() : w(W), h(H), bpp(1), eink(false) {}
  Format(int w_, int h_, bool color, bool eink_)
    : w((uint16_t)(w_ < 0 ? 0 : w_ > 65535 ? 65535 : w_)), h((uint16_t)(h_ < 0 ? 0 : h_ > 65535 ? 65535 : h_)),
      bpp((color && !eink_) ? 4 : 1), eink(eink_) {}
  bool colour() const { return bpp == 4; }
  size_t rowBytes() const { return bpp == 4 ? (size_t)(w + 1) / 2 : (size_t)(w + 7) / 8; }
  size_t bytes() const { return rowBytes() * h; }
  bool valid() const { return w > 0 && h > 0 && w <= MAX_DIM && h <= MAX_DIM && bytes() <= MAX_FRAME_BYTES; }
  bool isDefault() const { return w == W && h == H && bpp == 1 && !eink; }   // the original 128x64 mono OLED
  // The longest line this format can make: run-length coding grows a picture by half at worst.
  size_t maxLine() const {
    const size_t n = bytes(), coded = n + (n + 1) / 2;
    return (coded + 2) / 3 * 4 + (isDefault() ? 64 : 64 + 112);
  }
  bool operator==(const Format& o) const { return w == o.w && h == o.h && bpp == o.bpp && eink == o.eink; }
};

// The classic 5x7 font (characters 32..126), five columns each, bit 0 = top row. Same glyphs as the
// OLED text, so names and clocks look the same on the dashboard. 475 bytes of read-only data.
inline const uint8_t* font5x7() {
  static const uint8_t t[] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x5F, 0x00, 0x00, 0x00, 0x07, 0x00, 0x07, 0x00,
    0x14, 0x7F, 0x14, 0x7F, 0x14, 0x24, 0x2A, 0x7F, 0x2A, 0x12, 0x23, 0x13, 0x08, 0x64, 0x62,
    0x36, 0x49, 0x56, 0x20, 0x50, 0x00, 0x08, 0x07, 0x03, 0x00, 0x00, 0x1C, 0x22, 0x41, 0x00,
    0x00, 0x41, 0x22, 0x1C, 0x00, 0x2A, 0x1C, 0x7F, 0x1C, 0x2A, 0x08, 0x08, 0x3E, 0x08, 0x08,
    0x00, 0x80, 0x70, 0x30, 0x00, 0x08, 0x08, 0x08, 0x08, 0x08, 0x00, 0x00, 0x60, 0x60, 0x00,
    0x20, 0x10, 0x08, 0x04, 0x02, 0x3E, 0x51, 0x49, 0x45, 0x3E, 0x00, 0x42, 0x7F, 0x40, 0x00,
    0x72, 0x49, 0x49, 0x49, 0x46, 0x21, 0x41, 0x49, 0x4D, 0x33, 0x18, 0x14, 0x12, 0x7F, 0x10,
    0x27, 0x45, 0x45, 0x45, 0x39, 0x3C, 0x4A, 0x49, 0x49, 0x31, 0x41, 0x21, 0x11, 0x09, 0x07,
    0x36, 0x49, 0x49, 0x49, 0x36, 0x46, 0x49, 0x49, 0x29, 0x1E, 0x00, 0x00, 0x14, 0x00, 0x00,
    0x00, 0x40, 0x34, 0x00, 0x00, 0x00, 0x08, 0x14, 0x22, 0x41, 0x14, 0x14, 0x14, 0x14, 0x14,
    0x00, 0x41, 0x22, 0x14, 0x08, 0x02, 0x01, 0x59, 0x09, 0x06, 0x3E, 0x41, 0x5D, 0x59, 0x4E,
    0x7C, 0x12, 0x11, 0x12, 0x7C, 0x7F, 0x49, 0x49, 0x49, 0x36, 0x3E, 0x41, 0x41, 0x41, 0x22,
    0x7F, 0x41, 0x41, 0x41, 0x3E, 0x7F, 0x49, 0x49, 0x49, 0x41, 0x7F, 0x09, 0x09, 0x09, 0x01,
    0x3E, 0x41, 0x41, 0x51, 0x73, 0x7F, 0x08, 0x08, 0x08, 0x7F, 0x00, 0x41, 0x7F, 0x41, 0x00,
    0x20, 0x40, 0x41, 0x3F, 0x01, 0x7F, 0x08, 0x14, 0x22, 0x41, 0x7F, 0x40, 0x40, 0x40, 0x40,
    0x7F, 0x02, 0x1C, 0x02, 0x7F, 0x7F, 0x04, 0x08, 0x10, 0x7F, 0x3E, 0x41, 0x41, 0x41, 0x3E,
    0x7F, 0x09, 0x09, 0x09, 0x06, 0x3E, 0x41, 0x51, 0x21, 0x5E, 0x7F, 0x09, 0x19, 0x29, 0x46,
    0x26, 0x49, 0x49, 0x49, 0x32, 0x03, 0x01, 0x7F, 0x01, 0x03, 0x3F, 0x40, 0x40, 0x40, 0x3F,
    0x1F, 0x20, 0x40, 0x20, 0x1F, 0x3F, 0x40, 0x38, 0x40, 0x3F, 0x63, 0x14, 0x08, 0x14, 0x63,
    0x03, 0x04, 0x78, 0x04, 0x03, 0x61, 0x59, 0x49, 0x4D, 0x43, 0x00, 0x7F, 0x41, 0x41, 0x41,
    0x02, 0x04, 0x08, 0x10, 0x20, 0x00, 0x41, 0x41, 0x41, 0x7F, 0x04, 0x02, 0x01, 0x02, 0x04,
    0x40, 0x40, 0x40, 0x40, 0x40, 0x00, 0x03, 0x07, 0x08, 0x00, 0x20, 0x54, 0x54, 0x78, 0x40,
    0x7F, 0x28, 0x44, 0x44, 0x38, 0x38, 0x44, 0x44, 0x44, 0x28, 0x38, 0x44, 0x44, 0x28, 0x7F,
    0x38, 0x54, 0x54, 0x54, 0x18, 0x00, 0x08, 0x7E, 0x09, 0x02, 0x18, 0xA4, 0xA4, 0x9C, 0x78,
    0x7F, 0x08, 0x04, 0x04, 0x78, 0x00, 0x44, 0x7D, 0x40, 0x00, 0x20, 0x40, 0x40, 0x3D, 0x00,
    0x7F, 0x10, 0x28, 0x44, 0x00, 0x00, 0x41, 0x7F, 0x40, 0x00, 0x7C, 0x04, 0x78, 0x04, 0x78,
    0x7C, 0x08, 0x04, 0x04, 0x78, 0x38, 0x44, 0x44, 0x44, 0x38, 0xFC, 0x18, 0x24, 0x24, 0x18,
    0x18, 0x24, 0x24, 0x18, 0xFC, 0x7C, 0x08, 0x04, 0x04, 0x08, 0x48, 0x54, 0x54, 0x54, 0x24,
    0x04, 0x04, 0x3F, 0x44, 0x24, 0x3C, 0x40, 0x40, 0x20, 0x7C, 0x1C, 0x20, 0x40, 0x20, 0x1C,
    0x3C, 0x40, 0x30, 0x40, 0x3C, 0x44, 0x28, 0x10, 0x28, 0x44, 0x4C, 0x90, 0x90, 0x90, 0x7C,
    0x44, 0x64, 0x54, 0x4C, 0x44, 0x00, 0x08, 0x36, 0x41, 0x00, 0x00, 0x00, 0x77, 0x00, 0x00,
    0x00, 0x41, 0x36, 0x08, 0x00, 0x02, 0x01, 0x02, 0x04, 0x02
  };
  return t;
}

// ---- a one-bit or 16-colour picture with the few drawing calls the pet screens use --------------------
class Canvas {
public:
  uint8_t* px;                   // the picture, Format::bytes() long (NULL when memory was short)
  Canvas() : px(NULL), cx_(0), cy_(0), size_(1), on_(true), cur_(0xFFFF), idx_(0xFF), npal_(0), dirty_(false), overflow_(0) {
    memset(pal_, 0, sizeof(pal_));
  }
  ~Canvas() { free(px); }
  Canvas(const Canvas&) = delete;
  Canvas& operator=(const Canvas&) = delete;

  bool init(const Format& f) {
    fmt_ = f;
    free(px);
    px = f.valid() ? (uint8_t*)calloc(1, f.bytes()) : NULL;
    return px != NULL;
  }
  const Format& format() const { return fmt_; }
  size_t bytes() const { return fmt_.bytes(); }

  void clear() { if (px) memset(px, 0, bytes()); }
  // mono
  void beginFrame(bool fillAll) { if (px) memset(px, fillAll ? 0xFF : 0, bytes()); cx_ = cy_ = 0; size_ = 1; on_ = true; }
  void setOn(bool on) { on_ = on; }
  // colour: the frame background (RGB565) is the first palette colour, and fills the picture
  void beginFrameColor(uint16_t bkg) {
    if (npal_ == 0) { pal_[0] = bkg; npal_ = 1; dirty_ = true; }
    const uint8_t b = indexFor(bkg);
    if (px) memset(px, (uint8_t)(b << 4 | b), bytes());
    cx_ = cy_ = 0; size_ = 1; cur_ = 0xFFFF; idx_ = 0xFF;
  }
  void setColor565(uint16_t c) { cur_ = c; idx_ = 0xFF; }     // resolved to a palette index when something is drawn
  void setTextSize(int s) { size_ = s < 1 ? 1 : s; }
  void setCursor(int x, int y) { cx_ = x; cy_ = y; }

  // palette (colour pictures)
  const uint16_t* palette() const { return pal_; }
  int paletteCount() const { return npal_; }
  bool paletteDirty() const { return dirty_; }          // a colour was added since the last key picture went out
  void clearPaletteDirty() { dirty_ = false; }
  void resetPalette() { npal_ = 0; dirty_ = false; overflow_ = 0; idx_ = 0xFF; memset(pal_, 0, sizeof(pal_)); }
  uint32_t overflowed() const { return overflow_; }     // pixels drawn in a "nearest" colour because the palette was full

  void set(int x, int y) {
    if (!px || x < 0 || x >= fmt_.w || y < 0 || y >= fmt_.h) return;
    if (fmt_.bpp == 4) {
      const uint8_t v = ink();
      uint8_t* b = px + (size_t)y * fmt_.rowBytes() + (x >> 1);
      *b = (x & 1) ? (uint8_t)((*b & 0xF0) | v) : (uint8_t)((*b & 0x0F) | (v << 4));
      return;
    }
    const uint8_t m = (uint8_t)(0x80 >> (x & 7));
    uint8_t* b = px + (size_t)y * fmt_.rowBytes() + (x >> 3);
    if (on_) *b |= m; else *b &= (uint8_t)~m;
  }
  void fillRect(int x, int y, int w, int h) {
    if (w <= 0 || h <= 0) return;
    const int x0 = x < 0 ? 0 : x, y0 = y < 0 ? 0 : y;
    const int x1 = x + w > fmt_.w ? fmt_.w : x + w, y1 = y + h > fmt_.h ? fmt_.h : y + h;
    if (x0 >= x1 || y0 >= y1) return;
    if (fmt_.bpp == 4 && px) {                          // colour: whole bytes where it can
      const uint8_t v = ink();
      for (int j = y0; j < y1; j++) {
        uint8_t* row = px + (size_t)j * fmt_.rowBytes();
        int i = x0;
        if (i & 1) { set(i, j); i++; }
        if (i + 1 < x1) { memset(row + (i >> 1), (uint8_t)(v << 4 | v), (size_t)((x1 - i) >> 1)); i += ((x1 - i) >> 1) * 2; }
        if (i < x1) set(i, j);
      }
      return;
    }
    for (int j = y0; j < y1; j++) for (int i = x0; i < x1; i++) set(i, j);
  }
  void drawRect(int x, int y, int w, int h) {
    if (w <= 0 || h <= 0) return;
    fillRect(x, y, w, 1); fillRect(x, y + h - 1, w, 1); fillRect(x, y, 1, h); fillRect(x + w - 1, y, 1, h);
  }
  // 1-bit bitmap, rows padded to whole bytes, leftmost pixel = top bit; only the set bits are drawn
  void drawXbm(int x, int y, const uint8_t* bits, int w, int h) {
    if (!bits || w <= 0 || h <= 0) return;
    const int stride = (w + 7) / 8;
    for (int j = 0; j < h; j++) for (int i = 0; i < w; i++)
      if (bits[j * stride + (i >> 3)] & (0x80 >> (i & 7))) set(x + i, y + j);
  }
  // Same rules as the Adafruit text the OLED uses: 6 columns a character, wrap at the right edge,
  // newline goes back to column 0. Characters outside 32..126 leave a blank cell.
  void print(const char* s) {
    for (; *s; s++) {
      const unsigned char ch = (unsigned char)*s;
      if (ch == '\n') { cx_ = 0; cy_ += 8 * size_; continue; }
      if (ch == '\r') continue;
      if (cx_ + 6 * size_ > fmt_.w) { cx_ = 0; cy_ += 8 * size_; }
      glyph(ch, cx_, cy_);
      cx_ += 6 * size_;
    }
  }
  // One character with its left edge at x: no wrapping, the cursor does not move. For a copy of a screen
  // whose own text is narrower than 6 columns a character (NovaPetTee places each one where the real screen does).
  void glyph(unsigned char ch, int x, int y) {
    if (ch < 32 || ch > 126) return;
    const uint8_t* g = font5x7() + (ch - 32) * 5;
    for (int col = 0; col < 5; col++)
      for (int row = 0; row < 8; row++)
        if (g[col] & (1 << row)) fillRect(x + col * size_, y + row * size_, size_, size_);
  }
  int cursorX() const { return cx_; }
  int cursorY() const { return cy_; }
  int textSize() const { return size_; }

private:
  Format fmt_;
  int cx_, cy_, size_;
  bool on_;
  uint16_t cur_;
  uint8_t idx_;                  // palette index of cur_, 0xFF = not looked up yet
  uint16_t pal_[PALETTE_SIZE];
  uint8_t npal_;
  bool dirty_;
  uint32_t overflow_;

  uint8_t ink() { if (idx_ == 0xFF) idx_ = indexFor(cur_); return idx_; }
  static int dist(uint16_t a, uint16_t b) {
    const int ar = a >> 11, ag = (a >> 5) & 63, ab = a & 31, br = b >> 11, bg = (b >> 5) & 63, bb = b & 31;
    const int dr = (ar - br) * 8, dg = (ag - bg) * 4, db = (ab - bb) * 8;      // about the same scale per channel
    return dr * dr + dg * dg + db * db;
  }
  uint8_t indexFor(uint16_t c) {
    for (uint8_t i = 0; i < npal_; i++) if (pal_[i] == c) return i;
    if (npal_ < PALETTE_SIZE) { pal_[npal_] = c; dirty_ = true; return npal_++; }
    uint8_t best = 0; int bd = dist(c, pal_[0]);
    for (uint8_t i = 1; i < npal_; i++) { const int d = dist(c, pal_[i]); if (d < bd) { bd = d; best = i; } }
    overflow_++;
    return best;
  }
};

// ---- base64, written straight into the output line --------------------------------------------
class B64Out {
public:
  size_t n;
  bool over;
  B64Out(char* out, size_t cap) : n(0), over(false), out_(out), cap_(cap), na_(0) {}
  void put(uint8_t b) { a_[na_++] = b; if (na_ == 3) emit(); }
  void finish() { if (na_) emit(); }
private:
  char* out_; size_t cap_; uint8_t a_[3]; uint8_t na_;
  void emit() {
    static const char T[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    const uint32_t v = ((uint32_t)a_[0] << 16) | (na_ > 1 ? (uint32_t)a_[1] << 8 : 0) | (na_ > 2 ? a_[2] : 0);
    if (n + 4 > cap_) { over = true; na_ = 0; return; }
    out_[n++] = T[(v >> 18) & 63];
    out_[n++] = T[(v >> 12) & 63];
    out_[n++] = na_ > 1 ? T[(v >> 6) & 63] : '=';
    out_[n++] = na_ > 2 ? T[v & 63] : '=';
    na_ = 0;
  }
};

// Builds one line for any screen format, newline included, NUL after it. prev == NULL makes a key picture
// (the whole thing). Returns the length (without the NUL), or 0 if it does not fit in cap (nothing is cut).
// name (key pictures only, "" or NULL = no field) is made JSON safe here, whatever the caller passes.
// pal (colour key pictures): the 16 palette colours (RGB565) that go in "c"; NULL writes a black palette.
// Formats that are not the original 128x64 mono carry w/h (and e / c) on key pictures, see the top of this file.
inline size_t encodeFrame(const Format& f, const uint8_t* fb, const uint8_t* prev, uint32_t seq, char* out, size_t cap,
                          const char* name = NULL, const uint16_t* pal = NULL) {
  if (!f.valid() || !fb || cap < 192) return 0;
  const bool key = prev == NULL;
  char safe[NovaPetName::kMax + 1];
  NovaPetName::jsonSafe(key ? name : NULL, safe, sizeof(safe));
  int w = snprintf(out, cap, "{\"pet\":{\"s\":%lu,\"k\":%d,", (unsigned long)seq, key ? 1 : 0);
  if (w <= 0) return 0;
  if (key && safe[0]) w += snprintf(out + w, cap - (size_t)w, "\"n\":\"%s\",", safe);
  if (key && !f.isDefault()) {
    w += snprintf(out + w, cap - (size_t)w, "\"w\":%u,\"h\":%u,", (unsigned)f.w, (unsigned)f.h);
    if (f.eink) w += snprintf(out + w, cap - (size_t)w, "\"e\":1,");
    if (f.colour()) {
      uint8_t pb[PALETTE_SIZE * 2];
      for (int i = 0; i < PALETTE_SIZE; i++) { const uint16_t c = pal ? pal[i] : 0; pb[i * 2] = (uint8_t)(c >> 8); pb[i * 2 + 1] = (uint8_t)c; }
      static const char T[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
      w += snprintf(out + w, cap - (size_t)w, "\"c\":{\"b\":4,\"p\":\"");
      if ((size_t)w + 44 + 8 >= cap) return 0;
      for (size_t i = 0; i < sizeof(pb); i += 3) {                 // 32 bytes: 10 groups of 3 and a padded one of 2
        const uint32_t v = (uint32_t)pb[i] << 16 | (i + 1 < sizeof(pb) ? (uint32_t)pb[i + 1] << 8 : 0) | (i + 2 < sizeof(pb) ? pb[i + 2] : 0);
        out[w++] = T[(v >> 18) & 63]; out[w++] = T[(v >> 12) & 63];
        out[w++] = i + 1 < sizeof(pb) ? T[(v >> 6) & 63] : '=';
        out[w++] = i + 2 < sizeof(pb) ? T[v & 63] : '=';
      }
      w += snprintf(out + w, cap - (size_t)w, "\"},");
    }
  }
  if (w <= 0 || (size_t)w >= cap) return 0;
  w += snprintf(out + w, cap - (size_t)w, "\"d\":\"");
  if (w <= 0 || (size_t)w + 5 >= cap) return 0;
  B64Out b(out + w, cap - (size_t)w - 5);              // room for  "}}  newline  NUL
  const size_t N = f.bytes();
  const bool hx = f.colour();                          // colour: also XOR each byte with the one before it
  auto t = [&](size_t i) -> uint8_t { return prev ? (uint8_t)(fb[i] ^ prev[i]) : fb[i]; };
  auto v = [&](size_t i) -> uint8_t { return hx && i ? (uint8_t)(t(i) ^ t(i - 1)) : t(i); };
  for (size_t i = 0; i < N;) {
    const uint8_t x = v(i);
    if (x) { b.put(x); i++; continue; }
    int run = 0;
    while (i < N && run < 255 && !v(i)) { run++; i++; }
    b.put(0); b.put((uint8_t)run);
  }
  b.finish();
  if (b.over) return 0;
  size_t n = (size_t)w + b.n;
  out[n++] = '"'; out[n++] = '}'; out[n++] = '}'; out[n++] = '\n'; out[n] = 0;
  return n;
}

// The original 128x64 mono line (kept for callers and tests that only know that screen). Returns 0 if cap < MAX_LINE.
inline size_t encodeLine(const uint8_t* fb, const uint8_t* prev, uint32_t seq, char* out, size_t cap, const char* name = NULL) {
  if (cap < MAX_LINE) return 0;
  return encodeFrame(Format(), fb, prev, seq, out, cap, name, NULL);
}

// ---- the link: the picture being drawn, the previous one, and the line waiting to go out ---------
// Allocated with malloc on the first "nova pet", so a radio nobody asks costs a few bytes of RAM. The
// picture, the previous picture and the line buffer are sized for this radio's screen (see ok()).
class Link {
public:
  Canvas canvas;                 // the tee draws into this while a page is asking
  explicit Link(const Format& f = Format())
    : fmt_(f), prev_(NULL), line_(NULL), cap_(0), seq_(0), since_key_(0), last_key_(0), last_sent_(0), until_(0), started_(0),
      want_key_(true), got_frame_(false), len_(0), off_(0) {
    name_[0] = 0;
    if (!f.valid() || !canvas.init(f)) return;
    cap_ = f.maxLine() < MAX_LINE_CAP ? f.maxLine() : MAX_LINE_CAP;
    prev_ = (uint8_t*)calloc(1, f.bytes());
    line_ = (char*)malloc(cap_);
    if (!prev_ || !line_) { free(prev_); free(line_); prev_ = NULL; line_ = NULL; cap_ = 0; }
    else line_[0] = 0;
  }
  ~Link() { free(prev_); free(line_); }
  Link(const Link&) = delete;
  Link& operator=(const Link&) = delete;

  bool ok() const { return canvas.px && prev_ && line_; }   // false: the format was refused or memory was short
  const Format& format() const { return fmt_; }

  // "nova pet": keep the stream going for WINDOW_MS. A stream that lapsed starts again with a key picture.
  void request(uint32_t now) {
    if (!active(now)) { want_key_ = true; len_ = off_ = 0; started_ = now; got_frame_ = false; canvas.resetPalette(); }
    until_ = now + WINDOW_MS;
  }
  // Asked for more than 3 s ago and the screen has not drawn once: it is off or asleep. The caller says so.
  bool waiting(uint32_t now) const { return active(now) && !got_frame_ && (uint32_t)(now - started_) > 3000; }
  bool active(uint32_t now) const { return until_ != 0 && (int32_t)(until_ - now) > 0; }

  // The name for the next key picture: the pet's own name (/lorafish.id; "" = none), else the radio's node
  // name (node_prefs->node_name). UITask calls this with loRaFishPetNameForNova() and the node name; nothing
  // else may feed it. Both are made JSON safe, see NovaPetName::frameName().
  void setNames(const char* pet, const char* radio) { NovaPetName::frameName(pet, radio, name_, sizeof(name_)); }
  void setName(const char* name) { setNames(name, NULL); }   // the pet's name only, no fallback

  // A finished screen picture is in canvas. Builds the next line unless one is still going out.
  void frameDone(uint32_t now) {
    if (!active(now) || !ok()) return;
    got_frame_ = true;
    if (off_ < len_) return;
    bool key = want_key_ || since_key_ >= KEY_EVERY_FRAMES || (uint32_t)(now - last_key_) >= KEY_EVERY_MS || canvas.paletteDirty();
    if (!key) {
      if ((uint32_t)(now - last_sent_) < (fmt_.eink ? EINK_MIN_GAP_MS : MIN_GAP_MS)) return;
      if (memcmp(canvas.px, prev_, fmt_.bytes()) == 0) return;       // nothing moved: nothing to say
      if (fmt_.eink) key = true;                                      // e-ink: still pictures only, never a delta
    }
    const size_t n = encodeFrame(fmt_, canvas.px, key ? (const uint8_t*)NULL : prev_, seq_ + 1, line_, cap_, name_,
                                 fmt_.colour() ? canvas.palette() : NULL);
    if (!n) return;
    seq_++;
    memcpy(prev_, canvas.px, fmt_.bytes());
    since_key_ = key ? 0 : since_key_ + 1;
    if (key) { last_key_ = now; canvas.clearPaletteDirty(); }
    want_key_ = false;
    last_sent_ = now;
    len_ = n; off_ = 0;
  }

  // output side: the serial code writes what the port can take and tells us how much went
  size_t pending() const { return len_ - off_; }
  const uint8_t* pendingData() const { return (const uint8_t*)line_ + off_; }
  void consumed(size_t n) { off_ += n > pending() ? pending() : n; }
  void dropPending() { len_ = off_ = 0; want_key_ = true; }   // stream lapsed mid-line: start clean next time

  uint32_t sequence() const { return seq_; }
  size_t lineCapacity() const { return cap_; }

private:
  Format fmt_;
  uint8_t* prev_;
  char* line_;
  size_t cap_;
  char name_[NovaPetName::kMax + 1];
  uint32_t seq_, since_key_, last_key_, last_sent_, until_, started_;
  bool want_key_, got_frame_;
  size_t len_, off_;
};

// ---- which screen this radio has, and the one shared Link ------------------------------------------
// Set once at start-up from the display (NovaPetTee::formatOf); supported() is false until then.
inline bool& supportedSlot() { static bool s = false; return s; }
inline Format& formatSlot() { static Format f; return f; }
inline bool supported() { return supportedSlot(); }
inline const Format& format() { return formatSlot(); }
inline bool setFormat(const Format& f) {
  supportedSlot() = f.valid();
  if (f.valid()) formatSlot() = f;
  return f.valid();
}
inline void setSupported(bool s) { supportedSlot() = s; if (s) formatSlot() = Format(); }   // s = the original 128x64 mono screen

inline Link*& linkSlot() { static Link* l = NULL; return l; }
// make = true allocates it on first use (for the screen set by setFormat); NULL means it does not exist (or no memory).
inline Link* link(bool make = false) {
  Link*& l = linkSlot();
  if (!l && make && supported()) {
    void* m = malloc(sizeof(Link));                       // not new: a full heap must not abort the radio
    if (m) {
      Link* n = new (m) Link(formatSlot());
      if (n->ok()) l = n; else { n->~Link(); free(m); }
    }
  }
  return l;
}

}  // namespace NovaPetLink
