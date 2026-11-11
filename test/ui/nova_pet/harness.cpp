// Host harness for test/ui/check_nova_pet_frame.py. Not firmware. Built with g++ on the PC.
// Reads commands on stdin, drives the real NovaPetLink.h / NovaPetTee.h code, prints results.
#include <helpers/ui/DisplayDriver.h>
#include "NovaPetLink.h"
#include "NovaPetTee.h"
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

ColorVal UIColor::window_bkg = 0, UIColor::title_bkg = 0, UIColor::title_txt = 1, UIColor::primary_txt = 1,
         UIColor::secondary_txt = 1, UIColor::warning_txt = 1, UIColor::popup_bkg = 0, UIColor::popup_txt = 1,
         UIColor::corp_blue = 1;

// A stand-in for the SSD1306 OLED: it only writes every call it gets into a log.
class FakeMono : public DisplayDriver {
public:
  std::vector<std::string> log;
  FakeMono(int w = 128, int h = 64) : DisplayDriver(w, h) {}
  bool isOn() override { return true; }
  void turnOn() override { log.push_back("turnOn"); }
  void turnOff() override { log.push_back("turnOff"); }
  void clear() override { log.push_back("clear"); }
  void startFrame(ColorVal b = UIColor::window_bkg) override { log.push_back("startFrame " + std::to_string(b)); }
  void endFrame() override { log.push_back("endFrame"); }
  void setTextSize(int s) override { log.push_back("size " + std::to_string(s)); }
  void setColor(ColorVal c) override { log.push_back("color " + std::to_string(c)); }
  void setCursor(int x, int y) override { log.push_back("cursor " + std::to_string(x) + " " + std::to_string(y)); }
  void print(const char* s) override { log.push_back(std::string("print ") + s); }
  void fillRect(int x, int y, int w, int h) override { log.push_back("fill " + std::to_string(x) + " " + std::to_string(y) + " " + std::to_string(w) + " " + std::to_string(h)); }
  void drawRect(int x, int y, int w, int h) override { log.push_back("box " + std::to_string(x) + " " + std::to_string(y) + " " + std::to_string(w) + " " + std::to_string(h)); }
  void drawXbm(int x, int y, const uint8_t* b, int w, int h) override {
    std::string s = "xbm " + std::to_string(x) + " " + std::to_string(y) + " " + std::to_string(w) + " " + std::to_string(h) + " ";
    char t[4]; for (int i = 0; i < ((w + 7) / 8) * h; i++) { snprintf(t, sizeof t, "%02x", b[i]); s += t; }
    log.push_back(s);
  }
  uint16_t getTextWidth(const char* s) override { return (uint16_t)(strlen(s) * 6 - 1); }
};

static std::vector<uint8_t> unhex(const std::string& h) {
  std::vector<uint8_t> v;
  for (size_t i = 0; i + 1 < h.size(); i += 2) v.push_back((uint8_t)strtol(h.substr(i, 2).c_str(), nullptr, 16));
  return v;
}

// one drawing command, applied to whichever driver we are given
static void apply(DisplayDriver& d, const std::string& op, std::istringstream& in) {
  int a = 0, b = 0, c = 0, e = 0;
  if (op == "color") { in >> a; d.setColor((ColorVal)a); }
  else if (op == "size") { in >> a; d.setTextSize(a); }
  else if (op == "cursor") { in >> a >> b; d.setCursor(a, b); }
  else if (op == "print") { std::string t; in.get(); std::getline(in, t); d.print(t.c_str()); }
  else if (op == "center") { in >> a >> b; std::string t; in.get(); std::getline(in, t); d.drawTextCentered(a, b, t.c_str()); }
  else if (op == "rect") { in >> a >> b >> c >> e; d.fillRect(a, b, c, e); }
  else if (op == "box") { in >> a >> b >> c >> e; d.drawRect(a, b, c, e); }
  else if (op == "xbm") { std::string hex; in >> a >> b >> c >> e >> hex; auto v = unhex(hex); d.drawXbm(a, b, v.data(), c, e); }
  else if (op == "clear") { d.clear(); }
}

int main() {
  FakeMono real, direct;           // real = behind the tee, direct = the same commands with no tee
  NovaPetLink::Link* link = new NovaPetLink::Link();
  NovaPetTee* tee = nullptr;
  uint32_t now = 0;
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    std::string op; in >> op;
    if (op.empty() || op[0] == '#') continue;
    if (op == "REQ") { in >> now; link->request(now); }
    else if (op == "F") {           // begin a frame at time now
      in >> now; delete tee; tee = new NovaPetTee(real, *link, now);
      tee->startFrame(); direct.startFrame();
    }
    else if (op == "E") {           // end the frame; print any line that is waiting, as the serial code would
      tee->endFrame(); direct.endFrame(); delete tee; tee = nullptr;
      while (link->pending()) {
        size_t n = link->pending();
        printf("LINE %.*s", (int)n, (const char*)link->pendingData());   // ends with its own newline
        link->consumed(n);
      }
      printf("ACTIVE %d SEQ %u\n", link->active(now) ? 1 : 0, (unsigned)link->sequence());
    }
    else if (op == "ENC") {         // ENC <seq> <hexfb> [<hexprev>]: the bare encoder
      unsigned seq; std::string fb, pv; in >> seq >> fb >> pv;
      auto f = unhex(fb), p = unhex(pv);
      static char buf[NovaPetLink::MAX_LINE];
      size_t n = NovaPetLink::encodeLine(f.data(), pv.empty() ? nullptr : p.data(), seq, buf, sizeof buf);
      printf("ENC %zu %s", n, n ? buf : "\n");
    }
    else if (op == "ENCSMALL") {    // a buffer below MAX_LINE must be refused, not overrun
      std::vector<uint8_t> f(NovaPetLink::BYTES, 0x55); char buf[NovaPetLink::MAX_LINE - 1];
      printf("ENCSMALL %zu\n", NovaPetLink::encodeLine(f.data(), nullptr, 1, buf, sizeof buf));
    }
    else if (op == "DUMP") {        // the picture the tee drew so far, as hex
      for (int i = 0; i < NovaPetLink::BYTES; i++) printf("%02x", link->canvas.px[i]);
      printf("\n");
    }
    else if (op == "PRESS" ) { /* reserved */ }
    else {                         // the same command, parsed afresh for each driver
      if (tee) apply(*tee, op, in);
      std::istringstream in2(line); std::string op2; in2 >> op2;
      apply(direct, op2, in2);
    }
  }
  printf("PASSTHROUGH %s %zu\n", real.log == direct.log ? "same" : "DIFFERENT", real.log.size());
  printf("SIZEOF_LINK %zu\n", sizeof(NovaPetLink::Link));
  return 0;
}
