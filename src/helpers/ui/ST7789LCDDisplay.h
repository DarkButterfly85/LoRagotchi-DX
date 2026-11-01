#pragma once

#include "DisplayDriver.h"
#include <Wire.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <helpers/RefCountedDigitalPin.h>

class ST7789LCDDisplay : public DisplayDriver {
  #if defined(LILYGO_TDECK) || defined(HELTEC_LORA_V4_TFT) || defined(HELTEC_V4_R8_TFT)
    SPIClass displaySPI;
  #endif
  Adafruit_ST7789 display;
  bool _isOn;
  uint16_t _color;
  RefCountedDigitalPin* _peripher_power;

  // Band buffer for strip redraw: when active, drawing goes into a small
  // off-screen band instead of straight to the panel, so the panel is never
  // blanked for the whole frame. Only used when LORAFISH_STRIP_REDRAW is set.
#ifdef LORAFISH_TDECK_FRAMEBUFFER
  GFXcanvas16* _frame = nullptr;
  bool _frameActive = false;
#endif
  GFXcanvas16* _band = nullptr;
  bool _bandActive = false;
  int _bandY0 = 0;
  int bandOffset() const { return _bandActive ? _bandY0 : 0; }
  Adafruit_GFX& gfx();

  bool i2c_probe(TwoWire& wire, uint8_t addr);
public:
#ifdef USE_PIN_TFT
  ST7789LCDDisplay(RefCountedDigitalPin* peripher_power=NULL) : DisplayDriver(128, 64), 
      display(PIN_TFT_CS, PIN_TFT_DC, PIN_TFT_SDA, PIN_TFT_SCL, PIN_TFT_RST),
      _peripher_power(peripher_power)
  {
    _isOn = false;
  }
#elif defined(LILYGO_TDECK) || defined(HELTEC_LORA_V4_TFT) || defined(HELTEC_V4_R8_TFT)
  ST7789LCDDisplay(RefCountedDigitalPin* peripher_power=NULL) : DisplayDriver(128, 64),
      displaySPI(HSPI),
      display(&displaySPI, PIN_TFT_CS, PIN_TFT_DC, PIN_TFT_RST),
      _peripher_power(peripher_power)
  {
    _isOn = false;
  }
#elif defined(HELTEC_T114_WITH_DISPLAY)
  // T114 TFT sits on SPI1 (SCK 40, MOSI 41), same bus as the ST7789Display driver
  ST7789LCDDisplay(RefCountedDigitalPin* peripher_power=NULL) : DisplayDriver(128, 64),
      display(&SPI1, PIN_TFT_CS, PIN_TFT_DC, PIN_TFT_RST),
      _peripher_power(peripher_power)
  {
    _isOn = false;
  }
#else
  ST7789LCDDisplay(RefCountedDigitalPin* peripher_power=NULL) : DisplayDriver(128, 64),
      display(&SPI, PIN_TFT_CS, PIN_TFT_DC, PIN_TFT_RST),
      _peripher_power(peripher_power)
  {
    _isOn = false;
  }
#endif
  bool begin();

  // RGB565 direct-draw: colour themes and fish colours render as set
  bool supportsColor() const override { return true; }
  bool isOn() override { return _isOn; }
  void turnOn() override;
  void turnOff() override;
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

  int stripRows() const override;
  int physicalHeight() const override;
  void beginStrip(int physY0) override;
  void endStrip() override;
};
