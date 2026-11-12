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
// The picture is 128x64 pixels, 16 bytes a row, top row first, leftmost pixel = the top bit (0x80).
// When KEY is 1, d is the whole picture; otherwise d is the XOR with the previous picture and SEQ is
// exactly one more than the last line. d is run-length coded: a 0x00 byte is followed by a count
// (1..255) of zero bytes; every other byte stands for itself. Then base64 (standard alphabet, padded).
// No colour field is sent, so the dashboard draws the picture in one colour.

#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <new>

// The link needs the pet UI and a free USB serial port (the phone talks over Bluetooth). Builds that
// carry the phone protocol on USB, RP2040 WiFi builds that use USB for the rescue CLI, and the
// LORAFISH_SERIAL_TEST builds (they read USB serial for button commands) leave it out.
// Add -D LORAGOTCHI_NO_NOVA_LINK to leave it out of any other build.
#if defined(LORAFISH_UI) && !defined(ENABLE_USB_INTERFACE) && !defined(LORAGOTCHI_NO_NOVA_LINK) && \
    !defined(LORAFISH_SERIAL_TEST) && !(defined(ENABLE_WIFI_INTERFACE) && defined(RP2040_PLATFORM))
#define LORAGOTCHI_NOVA_LINK 1
#endif

namespace NovaPetLink {

static constexpr int W = 128, H = 64, ROW = W / 8;
static constexpr int BYTES = ROW * H;                 // 1024
// Longest possible line: prefix 34 + base64 of at most 1536 coded bytes (2048) + '"}}' + newline + NUL.
static constexpr size_t MAX_LINE = 2112;
static constexpr uint32_t WINDOW_MS = 4000;           // a "nova pet" keeps the stream going this long
static constexpr uint32_t MIN_GAP_MS = 250;           // at most four changed pictures a second
static constexpr uint32_t KEY_EVERY_FRAMES = 40;      // and a whole picture now and then, so a page
static constexpr uint32_t KEY_EVERY_MS = 5000;        // that joins late or misses a line recovers

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

// ---- a 128x64 one-bit picture with the few drawing calls the pet screens use -------------------
class Canvas {
public:
  uint8_t px[BYTES];
  Canvas() : cx_(0), cy_(0), size_(1), on_(true) { memset(px, 0, sizeof(px)); }

  void clear() { memset(px, 0, sizeof(px)); }
  void beginFrame(bool fillAll) { memset(px, fillAll ? 0xFF : 0, sizeof(px)); cx_ = cy_ = 0; size_ = 1; on_ = true; }
  void setOn(bool on) { on_ = on; }
  void setTextSize(int s) { size_ = s < 1 ? 1 : s; }
  void setCursor(int x, int y) { cx_ = x; cy_ = y; }

  void set(int x, int y) {
    if (x < 0 || x >= W || y < 0 || y >= H) return;
    const uint8_t m = (uint8_t)(0x80 >> (x & 7));
    if (on_) px[y * ROW + (x >> 3)] |= m; else px[y * ROW + (x >> 3)] &= (uint8_t)~m;
  }
  void fillRect(int x, int y, int w, int h) {
    if (w <= 0 || h <= 0) return;
    const int x0 = x < 0 ? 0 : x, y0 = y < 0 ? 0 : y;
    const int x1 = x + w > W ? W : x + w, y1 = y + h > H ? H : y + h;
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
    const uint8_t* f = font5x7();
    for (; *s; s++) {
      const unsigned char ch = (unsigned char)*s;
      if (ch == '\n') { cx_ = 0; cy_ += 8 * size_; continue; }
      if (ch == '\r') continue;
      if (cx_ + 6 * size_ > W) { cx_ = 0; cy_ += 8 * size_; }
      if (ch >= 32 && ch <= 126) {
        const uint8_t* g = f + (ch - 32) * 5;
        for (int col = 0; col < 5; col++)
          for (int row = 0; row < 8; row++)
            if (g[col] & (1 << row)) fillRect(cx_ + col * size_, cy_ + row * size_, size_, size_);
      }
      cx_ += 6 * size_;
    }
  }

private:
  int cx_, cy_, size_;
  bool on_;
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

// Builds one line, newline included, NUL after it. prev == NULL makes a key picture (the whole thing).
// Returns the length (without the NUL), or 0 if cap < MAX_LINE.
inline size_t encodeLine(const uint8_t* fb, const uint8_t* prev, uint32_t seq, char* out, size_t cap) {
  if (cap < MAX_LINE) return 0;
  const int w = snprintf(out, cap, "{\"pet\":{\"s\":%lu,\"k\":%d,\"d\":\"", (unsigned long)seq, prev ? 0 : 1);
  if (w <= 0) return 0;
  B64Out b(out + w, cap - (size_t)w - 5);              // room for  "}}  newline  NUL
  for (int i = 0; i < BYTES;) {
    const uint8_t v = prev ? (uint8_t)(fb[i] ^ prev[i]) : fb[i];
    if (v) { b.put(v); i++; continue; }
    int run = 0;
    while (i < BYTES && run < 255 && !(prev ? (uint8_t)(fb[i] ^ prev[i]) : fb[i])) { run++; i++; }
    b.put(0); b.put((uint8_t)run);
  }
  b.finish();
  if (b.over) return 0;
  size_t n = (size_t)w + b.n;
  out[n++] = '"'; out[n++] = '}'; out[n++] = '}'; out[n++] = '\n'; out[n] = 0;
  return n;
}

// ---- the link: the picture being drawn, the previous one, and the line waiting to go out ---------
// Allocated with new on the first "nova pet", so a radio nobody asks costs a few bytes of RAM.
class Link {
public:
  Canvas canvas;                 // the tee draws into this while a page is asking
  Link() : seq_(0), since_key_(0), last_key_(0), last_sent_(0), until_(0), started_(0), want_key_(true),
           got_frame_(false), len_(0), off_(0) { memset(prev_, 0, sizeof(prev_)); line_[0] = 0; }

  // "nova pet": keep the stream going for WINDOW_MS. A stream that lapsed starts again with a key picture.
  void request(uint32_t now) {
    if (!active(now)) { want_key_ = true; len_ = off_ = 0; started_ = now; got_frame_ = false; }
    until_ = now + WINDOW_MS;
  }
  // Asked for more than 3 s ago and the screen has not drawn once: it is off or asleep. The caller says so.
  bool waiting(uint32_t now) const { return active(now) && !got_frame_ && (uint32_t)(now - started_) > 3000; }
  bool active(uint32_t now) const { return until_ != 0 && (int32_t)(until_ - now) > 0; }

  // A finished screen picture is in canvas. Builds the next line unless one is still going out.
  void frameDone(uint32_t now) {
    if (!active(now)) return;
    got_frame_ = true;
    if (off_ < len_) return;
    bool key = want_key_ || since_key_ >= KEY_EVERY_FRAMES || (uint32_t)(now - last_key_) >= KEY_EVERY_MS;
    if (!key) {
      if ((uint32_t)(now - last_sent_) < MIN_GAP_MS) return;
      if (memcmp(canvas.px, prev_, sizeof(prev_)) == 0) return;       // nothing moved: nothing to say
    }
    const size_t n = encodeLine(canvas.px, key ? (const uint8_t*)NULL : prev_, seq_ + 1, line_, sizeof(line_));
    if (!n) return;
    seq_++;
    memcpy(prev_, canvas.px, sizeof(prev_));
    since_key_ = key ? 0 : since_key_ + 1;
    if (key) last_key_ = now;
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

private:
  uint8_t prev_[BYTES];
  char line_[MAX_LINE];
  uint32_t seq_, since_key_, last_key_, last_sent_, until_, started_;
  bool want_key_, got_frame_;
  size_t len_, off_;
};

// One shared Link. make = true allocates it on first use; NULL means it does not exist (or no memory).
inline Link*& linkSlot() { static Link* l = NULL; return l; }
inline Link* link(bool make = false) {
  Link*& l = linkSlot();
  if (!l && make) {
    void* m = malloc(sizeof(Link));                       // not new: a full heap must not abort the radio
    if (m) l = new (m) Link();
  }
  return l;
}
// Set once at start-up: does this radio have a screen the link can copy (128x64, black and white)?
inline bool& supportedSlot() { static bool s = false; return s; }
inline bool supported() { return supportedSlot(); }
inline void setSupported(bool s) { supportedSlot() = s; }

}  // namespace NovaPetLink
