#pragma once

#include "DisplayDriver.h"
#include "MonoPagePresenter.h"
#include <Wire.h>
#include <Adafruit_GFX.h>
#define SH110X_NO_SPLASH
#include <Adafruit_SH110X.h>

#ifndef PIN_OLED_RESET
#define PIN_OLED_RESET -1
#endif

#ifndef DISPLAY_ADDRESS
#define DISPLAY_ADDRESS 0x3C
#endif

class SH1106Display : public DisplayDriver
{
  Adafruit_SH1106G display;
  MonoPagePresenter<128, 8> _presenter;
  bool _partial = false;
  uint8_t _presentAddress = DISPLAY_ADDRESS;
  bool _rotated = false;
  bool _isOn;
  bool _initialized = false;
  uint8_t _brightness = 255;
  uint8_t _color;

  bool i2c_probe(TwoWire &wire, uint8_t addr);

public:
  SH1106Display() : DisplayDriver(128, 64), display(128, 64, &Wire, PIN_OLED_RESET) { _isOn = false; }
  bool begin();

  bool supportsPartialUpdates() const override { return true; }
  void setPartialUpdates(bool partial) override { _partial = partial; _presenter.invalidate(); }
  void forceFullRefresh() override { _presenter.invalidate(); }
  bool supportsOrientation() const override { return true; }
  void setOrientation(bool rotated) override;
  bool isOn() override { return _isOn; }
  void turnOn() override;
  void turnOff() override;
  bool supportsBrightness() const override { return true; }
  void setBrightness(uint8_t brightness) override;
  void clear() override;
  void startFrame(ColorVal bkg = UIColor::window_bkg) override;
  void setTextSize(int sz) override;
  void setColor(ColorVal c) override;
  void setCursor(int x, int y) override;
  void print(const char *str) override;
  void fillRect(int x, int y, int w, int h) override;
  void drawRect(int x, int y, int w, int h) override;
  void drawXbm(int x, int y, const uint8_t *bits, int w, int h) override;
  uint16_t getTextWidth(const char *str) override;
  void endFrame() override;
};
