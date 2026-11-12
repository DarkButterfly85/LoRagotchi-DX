#pragma once
// LORAGOTCHI NOVA serial link: copies what the pet draws on the screen.
// Picture format and dashboard: LODESTAR ORION / LODESTAR NOVA (Aries Thorne, Todd Steinhauer,
// FEAR REACTIVE), used with the authors' permission; see NOTICE and docs/CREDITS.md.
//
// A DisplayDriver that sits in front of the real screen for one frame. Every call goes to the real
// screen exactly as before (so the OLED looks the same, and the pet is drawn once, not twice) and is
// also drawn into a 128x64 one-bit picture for the Nova dashboard. UITask puts it in place only while
// a page has asked with "nova pet"; otherwise this file does nothing.
//
// Only black-and-white 128x64 screens that are not e-ink are copied. Colour, e-ink and larger screens
// are left alone (they are later steps), and the dashboard is told so.

#include <helpers/ui/DisplayDriver.h>
#include "../NovaPetLink.h"

class NovaPetTee : public DisplayDriver {
  DisplayDriver& _d;
  NovaPetLink::Link& _l;
  uint32_t _now;
public:
  // The screens the link can copy today.
  static bool suitable(DisplayDriver& d) {
    return !d.supportsColor() && !d.isEink() && d.width() == NovaPetLink::W && d.height() == NovaPetLink::H &&
           d.stripRows() == 0;
  }

  NovaPetTee(DisplayDriver& real, NovaPetLink::Link& link, uint32_t now)
    : DisplayDriver(real.width(), real.height()), _d(real), _l(link), _now(now) {}

  // plain pass-through: how the real screen behaves does not change
  bool supportsOrientation() const override { return _d.supportsOrientation(); }
  void setOrientation(bool rotated) override { _d.setOrientation(rotated); }
  bool supportsPartialUpdates() const override { return _d.supportsPartialUpdates(); }
  void setPartialUpdates(bool partial) override { _d.setPartialUpdates(partial); }
  bool supportsColor() const override { return _d.supportsColor(); }
  int menuRowPitch() const override { return _d.menuRowPitch(); }
  bool isOn() override { return _d.isOn(); }
  bool isEink() override { return _d.isEink(); }
  void forceFullRefresh() override { _d.forceFullRefresh(); }
  void turnOn() override { _d.turnOn(); }
  void turnOff() override { _d.turnOff(); }
  bool supportsBrightness() const override { return _d.supportsBrightness(); }
  void setBrightness(uint8_t b) override { _d.setBrightness(b); }
  uint16_t getTextWidth(const char* s) override { return _d.getTextWidth(s); }
  int stripRows() const override { return _d.stripRows(); }
  int physicalHeight() const override { return _d.physicalHeight(); }
  void beginStrip(int y) override { _d.beginStrip(y); }
  void endStrip() override { _d.endStrip(); }

  // drawing: real screen first, then the copy. Black (the window background colour) erases.
  void clear() override { _d.clear(); _l.canvas.clear(); }
  void startFrame(ColorVal bkg = UIColor::window_bkg) override {
    _d.startFrame(bkg);
    _l.canvas.beginFrame(bkg != UIColor::window_bkg);
  }
  void endFrame() override { _d.endFrame(); _l.frameDone(_now); }
  void setTextSize(int sz) override { _d.setTextSize(sz); _l.canvas.setTextSize(sz); }
  void setColor(ColorVal c) override { _d.setColor(c); _l.canvas.setOn(c != UIColor::window_bkg); }
  void setCursor(int x, int y) override { _d.setCursor(x, y); _l.canvas.setCursor(x, y); }
  void print(const char* s) override { _d.print(s); _l.canvas.print(s); }
  void fillRect(int x, int y, int w, int h) override { _d.fillRect(x, y, w, h); _l.canvas.fillRect(x, y, w, h); }
  void drawRect(int x, int y, int w, int h) override { _d.drawRect(x, y, w, h); _l.canvas.drawRect(x, y, w, h); }
  void drawXbm(int x, int y, const uint8_t* bits, int w, int h) override {
    _d.drawXbm(x, y, bits, w, h);
    _l.canvas.drawXbm(x, y, bits, w, h);
  }
  // printWordWrap, drawTextCentered/Right/Left, drawTextEllipsized and translateUTF8ToBlocks are not
  // overridden: the black-and-white drivers use the base versions, which call the methods above.
};
