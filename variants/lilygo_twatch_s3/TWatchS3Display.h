#pragma once

// Colour display for the LilyGo T-Watch S3: ST7789V 240x240 IPS on SPI3 with a
// PWM backlight (GPIO45), and the FT6336U capacitive touch panel on Wire1
// (SDA 39 / SCL 40, INT 16). Panel and touch configuration ported from the
// Meck T-Watch firmware.
//
// The LoRaGotchi UI is laid out for a 128x64 canvas. Everything is drawn into
// a 128x128 RGB565 frame buffer, which endFrame() scales by 1.875 (240/128) to
// fill the square panel, keeping the layout's proportions:
//   - TWatchS3Display itself is the normal 128x64 canvas. Its drawing lands in
//     the middle of the frame (rows 32-95), so menus and other screens are
//     centred on the panel.
//   - TWatchS3TankView (below) is a 128x128 canvas over the same frame, used
//     for the aquarium screen so the tank fills the panel (see that class).

#include <helpers/ui/DisplayDriver.h>

#define LGFX_USE_V1
#include <LovyanGFX.hpp>

class LGFX_TWatchS3 : public lgfx::LGFX_Device {
  lgfx::Panel_ST7789  _panel_instance;
  lgfx::Bus_SPI       _bus_instance;
  lgfx::Light_PWM     _light_instance;
  lgfx::Touch_FT5x06  _touch_instance;

public:
  LGFX_TWatchS3(void) {
    {
      auto cfg = _bus_instance.config();
      cfg.spi_host   = SPI3_HOST;
      cfg.spi_mode   = 0;
      cfg.freq_write = 40000000;
      cfg.freq_read  = 16000000;
      cfg.spi_3wire  = true;
      cfg.use_lock   = true;
      cfg.dma_channel = SPI_DMA_CH_AUTO;
      cfg.pin_sclk = 18;
      cfg.pin_mosi = 13;
      cfg.pin_miso = -1;
      cfg.pin_dc   = 38;
      _bus_instance.config(cfg);
      _panel_instance.setBus(&_bus_instance);
    }
    {
      auto cfg = _panel_instance.config();
      cfg.pin_cs   = 12;
      cfg.pin_rst  = -1;
      cfg.pin_busy = -1;
      // ST7789 GRAM is 240x320; memory_height must be 320 so the 80px rotation
      // offset is applied (otherwise a strip of the panel shows noise).
      cfg.memory_width    = 240;
      cfg.memory_height   = 320;
      cfg.panel_width     = 240;
      cfg.panel_height    = 240;
      cfg.offset_x        = 0;
      cfg.offset_y        = 0;
      cfg.offset_rotation = 1;
      cfg.readable   = false;
      cfg.invert     = true;
      cfg.rgb_order  = false;
      cfg.dlen_16bit = false;
      cfg.bus_shared = false;
      _panel_instance.config(cfg);
    }
    {
      auto cfg = _light_instance.config();
      cfg.pin_bl      = 45;
      cfg.invert      = false;
      cfg.freq        = 44100;
      cfg.pwm_channel = 7;
      _light_instance.config(cfg);
      _panel_instance.setLight(&_light_instance);
    }
    {
      auto cfg = _touch_instance.config();
      cfg.x_min      = 0;
      cfg.x_max      = 239;
      cfg.y_min      = 0;
      cfg.y_max      = 239;
      cfg.pin_int    = 16;
      cfg.pin_rst    = -1;
      cfg.bus_shared = false;
      cfg.offset_rotation = 2;  // touch IC mounted 180deg vs the LCD horizontal axis
      cfg.i2c_port = 1;
      cfg.i2c_addr = 0x38;
      cfg.pin_sda  = 39;
      cfg.pin_scl  = 40;
      cfg.freq     = 400000;
      _touch_instance.config(cfg);
      _panel_instance.setTouch(&_touch_instance);
    }
    setPanel(&_panel_instance);
  }
};

class TWatchS3Display : public DisplayDriver {
  friend class TWatchS3TankView;

  LGFX_TWatchS3 _lcd;
  LGFX_Sprite _frame;
  bool _isOn = false;
  bool _buffered = false;
  uint16_t _color = 0xFFFF;
  uint8_t _brightness = 255;

  // Drawing in frame-buffer rows, shared by both canvases.
  void rawSetCursor(int x, int y);
  void rawFillRect(int x, int y, int w, int h);
  void rawDrawRect(int x, int y, int w, int h);
  void rawDrawXbm(int x, int y, const uint8_t* bits, int w, int h);

public:
  static const int LOGICAL_WIDTH = 128;    // canvas the UI is laid out for
  static const int LOGICAL_HEIGHT = 64;
  static const int FRAME_HEIGHT = 128;     // frame buffer rows (fills the panel)
  static const int MENU_OFFSET_Y = (FRAME_HEIGHT - LOGICAL_HEIGHT) / 2;   // 32

  TWatchS3Display() : DisplayDriver(LOGICAL_WIDTH, LOGICAL_HEIGHT), _frame(&_lcd) {}

  bool begin();

  bool supportsColor() const override { return true; }
  bool isOn() override { return _isOn; }
  void turnOn() override;
  void turnOff() override;
  void setBrightness(uint8_t brightness) override;
  void clear() override;
  void startFrame(ColorVal bkg = UIColor::window_bkg) override;
  void setTextSize(int sz) override;
  void setColor(ColorVal c) override;
  void setCursor(int x, int y) override { rawSetCursor(x, y + MENU_OFFSET_Y); }
  void print(const char* str) override;
  void fillRect(int x, int y, int w, int h) override { rawFillRect(x, y + MENU_OFFSET_Y, w, h); }
  void drawRect(int x, int y, int w, int h) override { rawDrawRect(x, y + MENU_OFFSET_Y, w, h); }
  void drawXbm(int x, int y, const uint8_t* bits, int w, int h) override { rawDrawXbm(x, y + MENU_OFFSET_Y, bits, w, h); }
  uint16_t getTextWidth(const char* str) override;
  void endFrame() override;

  // One line of hint text in the margin below a centred screen (frame rows
  // 117-124): `left` at the left edge, `right` against the right edge.
  void drawFooterHint(const char* left, const char* right, ColorVal color);

  // Touch position in panel pixels (0..239, same orientation as the display).
  // Returns false when no finger is reported.
  bool getTouch(int* x, int* y);
};

// TWatchS3TankView -- a 128x128 canvas over the same frame buffer, for the
// LoRaGotchi aquarium screen (selected in UITask.cpp under LORAFISH_TALL_TANK).
//
// The aquarium drawing places the header at fixed rows 0-15, the footer, floor
// and bubbles relative to height() (so they land at the bottom of the 128-row
// tank: rows 80 and below), and the fish, guest fish, egg, gravestone, food and
// messages at fixed rows 16-63. Those fixed tank rows are moved down by 32 so
// the tank contents sit in the middle of the taller tank, exactly as they sat
// in the middle of the 64-row one.
//
// With shiftTank=false it is a plain 128x128 canvas with no rows moved. That
// is used for the tank scenery (LORAFISH_CARDPUTER_25D), which already spreads
// itself over height() and must fill the whole tall tank.
//
// startFrame()/endFrame() are run on the main TWatchS3Display by UITask, so
// here they do nothing.
class TWatchS3TankView : public DisplayDriver {
  TWatchS3Display& _d;
  bool _shift;

  int mapY(int y) const {
    return (_shift && y >= 16 && y < TWatchS3Display::LOGICAL_HEIGHT) ? y + TWatchS3Display::MENU_OFFSET_Y : y;
  }

public:
  TWatchS3TankView(TWatchS3Display& d, bool shiftTank = true)
    : DisplayDriver(TWatchS3Display::LOGICAL_WIDTH, TWatchS3Display::FRAME_HEIGHT), _d(d), _shift(shiftTank) {}

  bool supportsColor() const override { return true; }
  bool isOn() override { return _d.isOn(); }
  void turnOn() override { _d.turnOn(); }
  void turnOff() override { _d.turnOff(); }
  void setBrightness(uint8_t brightness) override { _d.setBrightness(brightness); }
  void clear() override { _d.clear(); }
  void startFrame(ColorVal bkg = UIColor::window_bkg) override { }
  void endFrame() override { }
  void setTextSize(int sz) override { _d.setTextSize(sz); }
  void setColor(ColorVal c) override { _d.setColor(c); }
  void setCursor(int x, int y) override { _d.rawSetCursor(x, mapY(y)); }
  void print(const char* str) override { _d.print(str); }
  void fillRect(int x, int y, int w, int h) override { _d.rawFillRect(x, mapY(y), w, h); }
  void drawRect(int x, int y, int w, int h) override { _d.rawDrawRect(x, mapY(y), w, h); }
  void drawXbm(int x, int y, const uint8_t* bits, int w, int h) override { _d.rawDrawXbm(x, mapY(y), bits, w, h); }
  uint16_t getTextWidth(const char* str) override { return _d.getTextWidth(str); }
};
