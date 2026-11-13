// Test helper. Not firmware. A stand-in for the SSD1306 OLED and a tiny drawing-command interpreter.
#pragma once
#include <helpers/ui/DisplayDriver.h>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

ColorVal UIColor::window_bkg = 0, UIColor::title_bkg = 0, UIColor::title_txt = 1, UIColor::primary_txt = 1,
         UIColor::secondary_txt = 1, UIColor::warning_txt = 1, UIColor::popup_bkg = 0, UIColor::popup_txt = 1,
         UIColor::corp_blue = 1;

// A stand-in for the SSD1306 OLED (or, with the flags, a colour LCD or an e-ink panel of any size): it only
// writes every call it gets into a log.
class FakeMono : public DisplayDriver {
  bool colour_, eink_;
public:
  int advNum = 0, advDen = 1;      // advNum > 0: text is advNum/advDen columns a character (the T096 reports 6/1.25), else the OLED's 6n-1
  std::vector<std::string> log;
  FakeMono(int w = 128, int h = 64, bool colour = false, bool eink = false) : DisplayDriver(w, h), colour_(colour), eink_(eink) {}
  bool supportsColor() const override { return colour_; }
  bool isEink() override { return eink_; }
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
  uint16_t getTextWidth(const char* s) override {
    if (advNum > 0) return (uint16_t)(strlen(s) * advNum / advDen);
    return (uint16_t)(strlen(s) * 6 - 1);
  }
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

