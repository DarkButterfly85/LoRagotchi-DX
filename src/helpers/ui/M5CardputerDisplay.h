#pragma once

#include <M5Cardputer.h>
#include "DisplayDriver.h"

// M5Cardputer uses standard color constants
#ifndef TFT_BLACK
#define TFT_BLACK 0x0000
#define TFT_WHITE 0xFFFF
#define TFT_RED 0xF800
#define TFT_GREEN 0x07E0
#define TFT_BLUE 0x001F
#define TFT_YELLOW 0xFFE0
#define TFT_ORANGE 0xFD20
#endif

class M5CardputerDisplay : public DisplayDriver {
private:
  bool _isOn = false;
  M5Canvas _frame{&M5.Display};
  bool _buffered = false;
  uint16_t cursor_x = 0;
  uint16_t cursor_y = 0;
  uint16_t text_size = 1;
  uint16_t _color = 0xFFFF;  // White
  uint16_t _light_color = TFT_WHITE;  // Default foreground
  uint16_t _dark_color = TFT_BLACK;   // Default background
  static const uint16_t SCREEN_WIDTH = 240;
  static const uint16_t SCREEN_HEIGHT = 135;
  static const uint8_t CHAR_WIDTH = 6;
  static const uint8_t CHAR_HEIGHT = 8;

public:
  M5CardputerDisplay() : DisplayDriver(SCREEN_WIDTH, SCREEN_HEIGHT) {}

  bool begin() {
    _isOn = true;
    M5.Display.setRotation(0);  // Verified landscape orientation on Cardputer hardware
    _frame.setColorDepth(16);
    _buffered = _frame.createSprite(SCREEN_WIDTH, SCREEN_HEIGHT) != nullptr;
    Serial.printf("[Cardputer LCD] 16-bit framebuffer: %s\n", _buffered ? "enabled" : "allocation failed");
    M5.Display.fillScreen(TFT_BLACK);
    M5.Display.setTextColor(TFT_WHITE, TFT_BLACK);
    M5.Display.setTextSize(1);
    Serial.println("M5Cardputer Display initialized");
    return true;
  }

  bool isOn() override { return _isOn; }
  
  void turnOn() override {
    if (!_isOn) {
      M5.Display.wakeup();
      _isOn = true;
    }
  }
  
  void turnOff() override {
    if (_isOn) {
      M5.Display.sleep();
      _isOn = false;
    }
  }

  bool supportsColor() const override { return true; }

  void startFrame(ColorVal bkg = UIColor::window_bkg) override {
    if (!_isOn) return;
    if (_buffered) _frame.fillScreen((uint16_t)bkg);
    else M5.Display.fillScreen((uint16_t)bkg);
    cursor_x = 0;
    cursor_y = 0;
  }

  void endFrame() override {
    if (!_isOn) return;
    if (_buffered) _frame.pushSprite(0, 0);
  }

  void clear() override {
    if (!_isOn) return;
    if (_buffered) _frame.fillScreen(TFT_BLACK); else M5.Display.fillScreen(TFT_BLACK);
    cursor_x = 0;
    cursor_y = 0;
  }

  void setCursor(int x, int y) override {
    cursor_x = x;
    cursor_y = y;
    if (_buffered) _frame.setCursor(x, y); else M5.Display.setCursor(x, y);
  }

  void setTextSize(int sz) override {
    text_size = sz;
    if (_buffered) _frame.setTextSize(sz); else M5.Display.setTextSize(sz);
  }

  void setColor(ColorVal c) override {
    _color = (uint16_t)c;
    if (_buffered) _frame.setTextColor(_color); else M5.Display.setTextColor(_color);
  }

  // Methods to customize theme colors
  void setLightColor(uint16_t color) {
    _light_color = color;
  }
  
  void setDarkColor(uint16_t color) {
    _dark_color = color;
  }

  void print(const char* str) override {
    if (!_isOn) return;
    if (_buffered) _frame.print(str); else M5.Display.print(str);
  }

  void drawRect(int x, int y, int w, int h) override {
    if (!_isOn) return;
    if (_buffered) _frame.drawRect(x, y, w, h, _color); else M5.Display.drawRect(x, y, w, h, _color);
  }

  void fillRect(int x, int y, int w, int h) override {
    if (!_isOn) return;
    if (_buffered) _frame.fillRect(x, y, w, h, _color); else M5.Display.fillRect(x, y, w, h, _color);
  }

  void drawXbm(int x, int y, const uint8_t* bits, int w, int h) override {
    if (!_isOn) return;
    // XBM drawing - simplified implementation
    for (int yy = 0; yy < h; yy++) {
      for (int xx = 0; xx < w; xx++) {
        int byte_idx = (yy * ((w + 7) / 8)) + (xx / 8);
        int bit_idx = xx % 8;
        if (bits[byte_idx] & (1 << bit_idx)) {
          if (_buffered) _frame.drawPixel(x + xx, y + yy, _color); else M5.Display.drawPixel(x + xx, y + yy, _color);
        }
      }
    }
  }

  uint16_t getTextWidth(const char* str) override {
    return strlen(str) * CHAR_WIDTH * text_size;
  }

};

// Helper inline for text drawing
inline void drawTextLine(M5CardputerDisplay& disp, int y, const char* str) {
  disp.setCursor(0, y);
  disp.print(str);
}
