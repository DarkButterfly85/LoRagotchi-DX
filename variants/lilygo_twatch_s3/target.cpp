#include <Arduino.h>
#include "target.h"

TWatchS3Board board;

// LoRa radio on its own SPI bus (the display uses SPI3_HOST separately).
// SX1262 on the sub-GHz watch, SX1280 on the 2.4 GHz revision (TWATCH_SX1280):
// same pins, only the radio chip differs.
static SPIClass loraSpi;
RADIO_CLASS radio = new Module(P_LORA_NSS, P_LORA_DIO_1, P_LORA_RESET, P_LORA_BUSY, loraSpi);

WRAPPER_CLASS radio_driver(radio, board);

// The PCF8563 RTC (backed by a coin cell) is found by AutoDiscoverRTCClock,
// so the clock survives reboots and reflashing once it has been set.
ESP32RTCClock fallback_clock;
AutoDiscoverRTCClock rtc_clock(fallback_clock);

// No GNSS and no environment sensors on this board.
SensorManager sensors;

#ifdef DISPLAY_CLASS
  DISPLAY_CLASS display;
  TWatchInput user_btn(board, display);
  TWatchS3TankView tank_display(display);
  TWatchS3TankView tank_scenery_display(display, false);
#endif

bool radio_init() {
  // board.begin() has already started Wire on the main I2C pins.
  fallback_clock.begin();
  rtc_clock.begin(Wire);

  loraSpi.begin(P_LORA_SCLK, P_LORA_MISO, P_LORA_MOSI, P_LORA_NSS);
  return radio.std_init(&loraSpi);
}

mesh::LocalIdentity radio_new_identity() {
  RadioNoiseListener rng(radio);
  return mesh::LocalIdentity(&rng);  // create new random identity
}
