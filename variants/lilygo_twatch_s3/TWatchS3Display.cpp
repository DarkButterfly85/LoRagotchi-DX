#include "TWatchS3Display.h"
#include "variant.h"

// RGB565 defaults; the LoRaGotchi UI replaces these with its own theme.
ColorVal UIColor::window_bkg = 0x0000;
ColorVal UIColor::title_bkg = 0x001F;
ColorVal UIColor::title_txt = 0xFFFF;
ColorVal UIColor::primary_txt = 0xFFFF;
ColorVal UIColor::secondary_txt = 0xBDF7;
ColorVal UIColor::warning_txt = 0xFD20;
ColorVal UIColor::popup_bkg = 0x001F;
ColorVal UIColor::popup_txt = 0xFFFF;
ColorVal UIColor::corp_blue = 0x001A;

// 128 frame columns -> 240 panel pixels; the 128-row frame fills the panel.
static const float FRAME_ZOOM = (float)LCD_HOR_SIZE / TWatchS3Display::LOGICAL_WIDTH;   // 1.875

bool TWatchS3Display::begin() {
  _lcd.init();
  _lcd.setRotation(1);
  _lcd.setColorDepth(16);
  _lcd.fillScreen((uint16_t)0x0000);
  _lcd.setBrightness(_brightness);

  _frame.setColorDepth(16);
  _frame.setPsram(false);
  _buffered = _frame.createSprite(LOGICAL_WIDTH, FRAME_HEIGHT) != nullptr;
  _frame.setTextSize(1);
  _isOn = true;
  return _buffered;
}

void TWatchS3Display::turnOn() {
  if (!_isOn) {
    _lcd.wakeup();
    _lcd.setBrightness(_brightness);
    _isOn = true;
  }
}

void TWatchS3Display::turnOff() {
  if (_isOn) {
    _lcd.sleep();   // backlight to 0 and panel sleep
    _isOn = false;
  }
}

void TWatchS3Display::setBrightness(uint8_t brightness) {
  _brightness = brightness;
  if (_isOn) _lcd.setBrightness(brightness);   // never light a sleeping panel
}

void TWatchS3Display::clear() {
  if (_buffered) _frame.fillScreen((uint16_t)0x0000);
}

void TWatchS3Display::startFrame(ColorVal bkg) {
  if (_buffered) {
    _frame.fillScreen((uint16_t)bkg);   // whole frame, so the margins match
    _frame.setCursor(0, 0);
  }
  // Same as SSD1306Display: each frame starts in the primary text colour.
  _color = (uint16_t)UIColor::primary_txt;
  _frame.setTextColor(_color);
}

void TWatchS3Display::setTextSize(int sz) {
  _frame.setTextSize(sz);
}

void TWatchS3Display::setColor(ColorVal c) {
  _color = (uint16_t)c;
  _frame.setTextColor(_color);
}

void TWatchS3Display::print(const char* str) {
  if (_buffered) _frame.print(str);
}

void TWatchS3Display::rawSetCursor(int x, int y) {
  _frame.setCursor(x, y);
}

void TWatchS3Display::rawFillRect(int x, int y, int w, int h) {
  if (_buffered) _frame.fillRect(x, y, w, h, _color);
}

void TWatchS3Display::rawDrawRect(int x, int y, int w, int h) {
  if (_buffered) _frame.drawRect(x, y, w, h, _color);
}

void TWatchS3Display::rawDrawXbm(int x, int y, const uint8_t* bits, int w, int h) {
  // The shared icons are MSB-first (as drawn by SSD1306Display via Adafruit
  // drawBitmap); LovyanGFX's drawBitmap uses the same order, drawXBitmap does not.
  if (_buffered) _frame.drawBitmap(x, y, bits, w, h, _color);
}

uint16_t TWatchS3Display::getTextWidth(const char* str) {
  return _frame.textWidth(str);
}

void TWatchS3Display::drawFooterHint(const char* left, const char* right, ColorVal color) {
  if (!_buffered) return;
  const int y = FRAME_HEIGHT - 11;
  _frame.setTextSize(1);
  _frame.setTextColor((uint16_t)color);
  _frame.setCursor(0, y);
  _frame.print(left);
  _frame.setCursor(LOGICAL_WIDTH - _frame.textWidth(right), y);
  _frame.print(right);
  _frame.setTextColor(_color);
}

void TWatchS3Display::endFrame() {
  if (!_isOn || !_buffered) return;
  _lcd.startWrite();
  _frame.pushRotateZoom(&_lcd, LCD_HOR_SIZE / 2.0f, LCD_VER_SIZE / 2.0f, 0, FRAME_ZOOM, FRAME_ZOOM);
  _lcd.endWrite();
}

bool TWatchS3Display::getTouch(int* x, int* y) {
  lgfx::touch_point_t point;
  if (_lcd.getTouch(&point) == 0) return false;
  *x = point.x;
  *y = point.y;
  return true;
}
