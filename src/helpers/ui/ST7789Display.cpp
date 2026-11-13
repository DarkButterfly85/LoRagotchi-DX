#ifdef ST7789

#include "ST7789Display.h"

#ifndef X_OFFSET
#define X_OFFSET 0  // No offset needed for landscape
#endif

#ifndef Y_OFFSET
#define Y_OFFSET 1  // Vertical offset to prevent top row cutoff
#endif

// Color scheme
ColorVal UIColor::window_bkg = OLEDDISPLAY_COLOR::BLACK;
ColorVal UIColor::title_bkg = OLEDDISPLAY_COLOR::BLACK;
ColorVal UIColor::title_txt = OLEDDISPLAY_COLOR::WHITE;
ColorVal UIColor::primary_txt = OLEDDISPLAY_COLOR::WHITE;
ColorVal UIColor::secondary_txt = OLEDDISPLAY_COLOR::WHITE;
ColorVal UIColor::warning_txt = OLEDDISPLAY_COLOR::WHITE;
ColorVal UIColor::popup_bkg = OLEDDISPLAY_COLOR::BLACK;
ColorVal UIColor::popup_txt = OLEDDISPLAY_COLOR::WHITE;
ColorVal UIColor::corp_blue = OLEDDISPLAY_COLOR::WHITE;

bool ST7789Display::begin() {
  if(!_isOn) {
    pinMode(PIN_TFT_VDD_CTL, OUTPUT);
    pinMode(PIN_TFT_LEDA_CTL, OUTPUT);
    digitalWrite(PIN_TFT_VDD_CTL, LOW);
  #ifdef PIN_TFT_LEDA_CTL_ACTIVE
    digitalWrite(PIN_TFT_LEDA_CTL, PIN_TFT_LEDA_CTL_ACTIVE);
  #else
    digitalWrite(PIN_TFT_LEDA_CTL, LOW);
  #endif
    digitalWrite(PIN_TFT_RST, HIGH);

    display.init();
    display.landscapeScreen();
    #ifdef DISPLAY_FLIP_VERTICALLY
    display.flipScreenVertically();
    #endif
    display.displayOn();
    setCursor(0,0);

    _isOn = true;
  }
  return true;
}

void ST7789Display::turnOn() {
  if (!_isOn) {
    // Restore power to the display but keep backlight off
    digitalWrite(PIN_TFT_VDD_CTL, LOW);
    digitalWrite(PIN_TFT_RST, HIGH);
    
    // Re-initialize the display
    display.init();
    display.displayOn();
    #ifdef DISPLAY_FLIP_VERTICALLY
    display.flipScreenVertically();
    #endif
    delay(20);

    // Now turn on the backlight
  #ifdef PIN_TFT_LEDA_CTL_ACTIVE
    digitalWrite(PIN_TFT_LEDA_CTL, PIN_TFT_LEDA_CTL_ACTIVE);
  #else
    digitalWrite(PIN_TFT_LEDA_CTL, LOW);
  #endif    
    _isOn = true;
  }
}

void ST7789Display::turnOff() {
  digitalWrite(PIN_TFT_VDD_CTL, HIGH);
#ifdef PIN_TFT_LEDA_CTL_ACTIVE
  digitalWrite(PIN_TFT_LEDA_CTL, !PIN_TFT_LEDA_CTL_ACTIVE);
#else
  digitalWrite(PIN_TFT_LEDA_CTL, HIGH);
#endif
  digitalWrite(PIN_TFT_RST, LOW);
  _isOn = false;
}

void ST7789Display::clear() {
  display.clear();
}

void ST7789Display::startFrame(ColorVal bkg) {
  display.clear();  // TODO: use bkg
  setColor(UIColor::primary_txt);
  display.setFont(ArialMT_Plain_10);
}

// Fonts are drawn at their own size (no scaling): the 128x64 OLED layouts keep their row spacing with
// the 10 pt face for size 1, 16 pt for size 2 and 24 pt for size 3.
void ST7789Display::setTextSize(int sz) {
  switch(sz) {
    case 1 :
      display.setFont(ArialMT_Plain_10);
      break;
    case 2 :
      display.setFont(ArialMT_Plain_16);
      break;
    case 3 :
      display.setFont(ArialMT_Plain_24);
      break;
    default:
      display.setFont(ArialMT_Plain_10);
  }
}

void ST7789Display::setColor(ColorVal c) {
  _color = c;
  display.setColor((OLEDDISPLAY_COLOR)_color);
  display.setRGB(_color == OLEDDISPLAY_COLOR::WHITE ? ST77XX_WHITE : ST77XX_BLACK);
}

void ST7789Display::setCursor(int x, int y) {
  _x = x + X_OFFSET;
  _y = y + Y_OFFSET;
}

void ST7789Display::print(const char* str) {
  display.drawString(_x, _y, str);
}

void ST7789Display::printWordWrap(const char* str, int max_width) {
  display.drawStringMaxWidth(_x, _y, max_width, str);
}

void ST7789Display::fillRect(int x, int y, int w, int h) {
  display.fillRect(x + X_OFFSET, y + Y_OFFSET, w, h);
}

void ST7789Display::drawRect(int x, int y, int w, int h) {
  display.drawRect(x + X_OFFSET, y + Y_OFFSET, w, h);
}

void ST7789Display::drawXbm(int x, int y, const uint8_t* bits, int w, int h) {
  // XBM art is MSB first; every set bit is exactly one panel pixel.
  const uint16_t startX = x + X_OFFSET;
  const uint16_t startY = y + Y_OFFSET;
  const uint16_t widthInBytes = (w + 7) / 8;

  for (uint16_t by = 0; by < h; by++) {
    for (uint16_t bx = 0; bx < w; bx++) {
      const uint16_t byteOffset = (by * widthInBytes) + (bx / 8);
      const uint8_t bitMask = 0x80 >> (bx & 7);
      if (pgm_read_byte(bits + byteOffset) & bitMask) {
        display.fillRect(startX + bx, startY + by, 1, 1);
      }
    }
  }
}

uint16_t ST7789Display::getTextWidth(const char* str) {
  return display.getStringWidth(str);
}

void ST7789Display::endFrame() {
  display.display();
}

#endif