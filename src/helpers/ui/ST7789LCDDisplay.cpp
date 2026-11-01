#include "ST7789LCDDisplay.h"
#ifndef PIN_TFT_MISO
  #define PIN_TFT_MISO -1
#endif

#ifndef DISPLAY_ROTATION
  #define DISPLAY_ROTATION 3
#endif

#ifndef DISPLAY_SCALE_X
  #define DISPLAY_SCALE_X 2.5f // 320 / 128
#endif

#ifndef DISPLAY_SCALE_Y
  #define DISPLAY_SCALE_Y 3.75f // 240 / 64
#endif

// Panel size is overridable so boards like the T114 (135x240 panel, used landscape)
// can reuse this driver. Defaults keep the 240x320 boards unchanged.
#ifndef DISPLAY_WIDTH
  #define DISPLAY_WIDTH 240
#endif
#ifndef DISPLAY_HEIGHT
  #define DISPLAY_HEIGHT 320
#endif

#ifndef TFT_SPI_SPEED
  #define TFT_SPI_SPEED 40e6
#endif

// Physical rows per band when strip redraw is enabled (LORAFISH_STRIP_REDRAW).
#ifndef BAND_ROWS
  #define BAND_ROWS 16
#endif

bool ST7789LCDDisplay::i2c_probe(TwoWire& wire, uint8_t addr) {
  return true;
}

// Color scheme
ColorVal UIColor::window_bkg = ST77XX_WHITE;
ColorVal UIColor::title_bkg = ST77XX_BLUE;
ColorVal UIColor::title_txt = ST77XX_WHITE;
ColorVal UIColor::primary_txt = ST77XX_BLACK;
ColorVal UIColor::secondary_txt = (18 << 11) | (36 << 5) | 18;  // mid-gray
ColorVal UIColor::warning_txt = ST77XX_ORANGE;
ColorVal UIColor::popup_bkg = ST77XX_CYAN;
ColorVal UIColor::popup_txt = ST77XX_BLACK;
ColorVal UIColor::corp_blue = 0x001A;

bool ST7789LCDDisplay::begin() {
  if (!_isOn) {
    if (_peripher_power) _peripher_power->claim();

    // Panel power rail (T114: VDD_CTL is active low). Boards that define it as -1 skip this.
    #ifdef PIN_TFT_VDD_CTL
    if (PIN_TFT_VDD_CTL != -1) {
      pinMode(PIN_TFT_VDD_CTL, OUTPUT);
      digitalWrite(PIN_TFT_VDD_CTL, LOW);
    }
    #endif

    if (PIN_TFT_LEDA_CTL != -1) {
      pinMode(PIN_TFT_LEDA_CTL, OUTPUT);
      // Backlight polarity: default HIGH (existing boards); T114 sets PIN_TFT_LEDA_CTL_ACTIVE=LOW
      #ifdef PIN_TFT_LEDA_CTL_ACTIVE
        digitalWrite(PIN_TFT_LEDA_CTL, PIN_TFT_LEDA_CTL_ACTIVE);
      #else
        digitalWrite(PIN_TFT_LEDA_CTL, HIGH);
      #endif
    }

    // Im not sure if this is just a t-deck problem or not, if your display is slow try this.
    #if defined(LILYGO_TDECK) || defined(HELTEC_LORA_V4_TFT) || defined(HELTEC_V4_R8_TFT)
      displaySPI.begin(PIN_TFT_SCL, PIN_TFT_MISO, PIN_TFT_SDA, PIN_TFT_CS);
    #endif

    display.init(DISPLAY_WIDTH, DISPLAY_HEIGHT);
    display.setRotation(DISPLAY_ROTATION);

    display.setSPISpeed(TFT_SPI_SPEED);

    display.fillScreen(ST77XX_BLACK);
    display.setTextColor(ST77XX_WHITE);
    display.setTextSize(2 * DISPLAY_SCALE_X); 
    display.cp437(true); // Use full 256 char 'Code Page 437' font
  
#ifdef LORAFISH_TDECK_FRAMEBUFFER
    if (!_frame) {
      // GFXcanvas16 uses malloc; ESP32 Arduino can route large allocations to PSRAM.
      // Fall back to direct drawing if the allocation cannot be satisfied.
      _frame = new GFXcanvas16(display.width(), display.height());
      if (_frame && !_frame->getBuffer()) { delete _frame; _frame = nullptr; }
      if (_frame) {
        _frame->cp437(true);
        Serial.printf("[LFG FRAME] RGB565 buffer ready: %d x %d\n", display.width(), display.height());
      } else Serial.println("[LFG FRAME] allocation failed; direct display fallback");
    }
#endif
    _isOn = true;
  }

  return true;
}

void ST7789LCDDisplay::turnOn() {
  ST7789LCDDisplay::begin();
}

// "Off" level for the backlight pin, following the board's polarity
#ifdef PIN_TFT_LEDA_CTL_ACTIVE
  #define TFT_BL_OFF (PIN_TFT_LEDA_CTL_ACTIVE == LOW ? HIGH : LOW)
#else
  #define TFT_BL_OFF LOW
#endif

void ST7789LCDDisplay::turnOff() {
  if (_isOn) {
    if (PIN_TFT_LEDA_CTL != -1) {
      digitalWrite(PIN_TFT_LEDA_CTL, TFT_BL_OFF);
    }
    if (PIN_TFT_RST != -1) {
      digitalWrite(PIN_TFT_RST, LOW);
    }
    _isOn = false;

    if (_peripher_power) _peripher_power->release();
  }
}

void ST7789LCDDisplay::clear() {
#ifdef LORAFISH_TDECK_FRAMEBUFFER
  if (_frameActive && _frame) { _frame->fillScreen(ST77XX_BLACK); return; }
#endif
  display.fillScreen(ST77XX_BLACK);
}

// Where drawing goes right now: the band buffer while a band is open, else the panel.
Adafruit_GFX& ST7789LCDDisplay::gfx() {
#ifdef LORAFISH_TDECK_FRAMEBUFFER
  if (_frameActive && _frame) return *_frame;
#endif
#ifdef LORAFISH_STRIP_REDRAW
  if (_bandActive && _band) return *_band;
#endif
  return display;
}

void ST7789LCDDisplay::startFrame(ColorVal bkg) {
#ifdef LORAFISH_TDECK_FRAMEBUFFER
  _frameActive = _frame != nullptr;
#endif
  Adafruit_GFX& g = gfx();
  g.fillScreen(bkg);
  g.setTextColor(_color = UIColor::primary_txt);
  g.setTextSize(1 * DISPLAY_SCALE_X); // This one affects size of Please wait... message
  g.cp437(true); // Use full 256 char 'Code Page 437' font
}

void ST7789LCDDisplay::setTextSize(int sz) {
  display.setTextSize(sz * DISPLAY_SCALE_X);
#ifdef LORAFISH_TDECK_FRAMEBUFFER
  if (_frame) _frame->setTextSize(sz * DISPLAY_SCALE_X);
#endif
#ifdef LORAFISH_STRIP_REDRAW
  if (_band) _band->setTextSize(sz * DISPLAY_SCALE_X);
#endif
}

void ST7789LCDDisplay::setColor(ColorVal c) {
  display.setTextColor(_color = c);
#ifdef LORAFISH_TDECK_FRAMEBUFFER
  if (_frame) _frame->setTextColor(c);
#endif
#ifdef LORAFISH_STRIP_REDRAW
  if (_band) _band->setTextColor(c);
#endif
}

void ST7789LCDDisplay::setCursor(int x, int y) {
  gfx().setCursor((int)(x * DISPLAY_SCALE_X), (int)(y * DISPLAY_SCALE_Y) - bandOffset());
}

void ST7789LCDDisplay::print(const char* str) {
  gfx().print(str);
}

void ST7789LCDDisplay::fillRect(int x, int y, int w, int h) {
  gfx().fillRect((int)(x * DISPLAY_SCALE_X), (int)(y * DISPLAY_SCALE_Y) - bandOffset(),
                 (int)(w * DISPLAY_SCALE_X), (int)(h * DISPLAY_SCALE_Y), _color);
}

void ST7789LCDDisplay::drawRect(int x, int y, int w, int h) {
  gfx().drawRect((int)(x * DISPLAY_SCALE_X), (int)(y * DISPLAY_SCALE_Y) - bandOffset(),
                 (int)(w * DISPLAY_SCALE_X), (int)(h * DISPLAY_SCALE_Y), _color);
}

void ST7789LCDDisplay::drawXbm(int x, int y, const uint8_t* bits, int w, int h) {
  uint8_t byteWidth = (w + 7) / 8;

  for (int j = 0; j < h; j++) {
    for (int i = 0; i < w; i++) {
      uint8_t byte = bits[j * byteWidth + i / 8];
      bool pixelOn = byte & (0x80 >> (i & 7));

      if (pixelOn) {
        for (int dy = 0; dy < DISPLAY_SCALE_X; dy++) {
          for (int dx = 0; dx < DISPLAY_SCALE_X; dx++) {
            gfx().drawPixel((int)(x * DISPLAY_SCALE_X + i * DISPLAY_SCALE_X + dx),
                            (int)(y * DISPLAY_SCALE_Y + j * DISPLAY_SCALE_X + dy) - bandOffset(), _color);
          }
        }
      }
    }
  }
}

uint16_t ST7789LCDDisplay::getTextWidth(const char* str) {
  int16_t x1, y1;
  uint16_t w, h;
  display.getTextBounds(str, 0, 0, &x1, &y1, &w, &h);

  return w / DISPLAY_SCALE_X;
}

void ST7789LCDDisplay::endFrame() {
#ifdef LORAFISH_TDECK_FRAMEBUFFER
  if (_frameActive && _frame) {
    _frameActive = false;
    display.drawRGBBitmap(0, 0, _frame->getBuffer(), _frame->width(), _frame->height());
  }
#endif
  // display.display();
}

// Strip redraw: the caller draws the frame once per band. Only the T114 build
// enables this (LORAFISH_STRIP_REDRAW); other boards report 0 and keep the
// single full-screen frame.
int ST7789LCDDisplay::stripRows() const {
#ifdef LORAFISH_STRIP_REDRAW
  return BAND_ROWS;
#else
  return 0;
#endif
}

int ST7789LCDDisplay::physicalHeight() const {
  return _isOn ? display.height() : 0;
}

void ST7789LCDDisplay::beginStrip(int physY0) {
#ifdef LORAFISH_STRIP_REDRAW
  if (!_band) {
    _band = new GFXcanvas16(display.width(), BAND_ROWS);
    if (!_band) return;
    _band->setTextSize(1 * DISPLAY_SCALE_X);
    _band->cp437(true);
  }
  _bandY0 = physY0;
  _bandActive = true;
  _band->fillScreen(UIColor::window_bkg);
  _band->setTextColor(_color);
#else
  (void)physY0;
#endif
}

void ST7789LCDDisplay::endStrip() {
#ifdef LORAFISH_STRIP_REDRAW
  if (_bandActive && _band) {
    int rows = min((int)BAND_ROWS, (int)display.height() - _bandY0);
    if (rows > 0) display.drawRGBBitmap(0, _bandY0, _band->getBuffer(), _band->width(), rows);
  }
  _bandActive = false;
  _bandY0 = 0;
#endif
}
