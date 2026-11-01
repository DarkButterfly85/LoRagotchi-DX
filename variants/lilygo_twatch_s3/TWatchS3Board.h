#pragma once

#include "variant.h"

#include <Arduino.h>
#include <Wire.h>
#include <XPowersLib.h>
#include <helpers/ESP32Board.h>

// LilyGo T-Watch S3 board.
//
// Power is managed by an AXP2101 PMU on the main I2C bus. Two pointers to the
// same object are kept because XPowersLib splits its API: the power-channel
// calls are only reachable through XPowersLibInterface, while the PWR key
// press/release edges and setIrqLevelTime() exist only on XPowersAXP2101.
//
// Battery options (build flags, used by the no-phone build):
//   TWATCH_CPU_MHZ_AFTER_BOOT       drop the CPU to this clock once boot has
//                                   finished (the first-boot filesystem format
//                                   needs the higher boot clock)
//   TWATCH_DISPLAY_OFF_THROTTLE_MS  pause the main loop this long on each pass
//                                   while the display is off, so the idle task
//                                   can rest the CPU (the radio buffers packets
//                                   in its own FIFO)
class TWatchS3Board : public ESP32Board {
  XPowersLibInterface* PMU = NULL;
  XPowersAXP2101* _axp = NULL;   // same object as PMU, concrete type

  bool power_init();

public:
  void begin();
  void onBootComplete() override;
  void loop() override;

  // The AXP2101 handle, for the PWR key. NULL if the PMU failed to init.
  XPowersAXP2101* getPMU() { return _axp; }

  uint16_t getBattMilliVolts() override {
    return PMU ? PMU->getBattVoltage() : 0;
  }

  // USB power present, as reported by the PMU. Stops the low-battery
  // auto-shutdown from firing while the watch is charging.
  bool isExternalPowered() override {
    return PMU ? PMU->isVbusIn() : false;
  }

  // Full power-off through the PMU (all rails off, as a 6s PWR key hold does).
  // Hold the PWR key 2s to turn the watch back on.
  void powerOff() override;

  const char* getManufacturerName() const override {
    return "LilyGo T-Watch S3";
  }
};
