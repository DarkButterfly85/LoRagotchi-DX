#pragma once

#include "DisplayDriver.h"
#include <Wire.h>
#include <SPI.h>
#include "TFT_eSPI.h"
#include <helpers/RefCountedDigitalPin.h>

// 16-bit RGB565 colour panel: lets the pet UI compile its colour tank scenery (see UITask.cpp).
#define LORAGOTCHI_RGB565_PANEL 1

class ST7735Display : public DisplayDriver {
  bool _partial = false;
  bool _isOn;
  uint8_t _brightness = 255;
  RefCountedDigitalPin* _peripher_power;

  bool i2c_probe(TwoWire& wire, uint8_t addr);
public:
#ifdef USE_PIN_TFT
  ST7735Display(RefCountedDigitalPin* peripher_power=NULL) : DisplayDriver(128, 64), 
    //  display(PIN_TFT_CS, PIN_TFT_DC, PIN_TFT_SDA, PIN_TFT_SCL, PIN_TFT_RST),
      _peripher_power(peripher_power)
  {
    _isOn = false;
  }
#else
  ST7735Display(RefCountedDigitalPin* peripher_power=NULL) : DisplayDriver(128, 64),
    //  display(&SPI1, PIN_TFT_CS, PIN_TFT_DC, PIN_TFT_RST),
      _peripher_power(peripher_power)
  {
    _isOn = false;
  }
#endif
  bool begin();

  bool supportsPartialUpdates() const override { return true; }
  void setPartialUpdates(bool partial) override;
  void forceFullRefresh() override;
  bool supportsColor() const override { return true; }
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
  void print(const char* str) override;
  void fillRect(int x, int y, int w, int h) override;
  void drawRect(int x, int y, int w, int h) override;
  void drawXbm(int x, int y, const uint8_t* bits, int w, int h) override;
  uint16_t getTextWidth(const char* str) override;
  void endFrame() override;

protected:
  void _resetAndInit();
};
