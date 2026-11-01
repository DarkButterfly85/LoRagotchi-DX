#include <Arduino.h>
#include "TWatchS3Board.h"
#include "target.h"

void TWatchS3Board::begin() {
  ESP32Board::begin();
  power_init();
}

// Power setup ported from the Meck T-Watch firmware.
bool TWatchS3Board::power_init() {
  _axp = new XPowersAXP2101(Wire, PIN_BOARD_SDA, PIN_BOARD_SCL, I2C_ADDR_PMU);
  PMU = _axp;
  if (!PMU->init()) {
    MESH_DEBUG_PRINTLN("Warning: Failed to find AXP2101 power management");
    delete _axp;
    _axp = NULL;
    PMU = NULL;
    return false;
  }

  PMU->setChargingLedMode(XPOWERS_CHG_LED_CTRL_CHG);

  // Power rails (T-Watch S3 PowerManage table, cross-checked by Meck against
  // the schematic):
  //   ALDO2 = display backlight, ALDO3 = display + touch, ALDO4 = LoRa,
  //   BLDO2 = DRV2605 haptic, DLDO1 = MAX98357A speaker amp,
  //   VBACKUP = coin cell backing the PCF8563 RTC.
  // LoRaGotchi uses neither the haptic motor nor the speaker, so those rails
  // stay off.
  PMU->setPowerChannelVoltage(XPOWERS_ALDO4, 3300);  // LoRa radio
  PMU->enablePowerOutput(XPOWERS_ALDO4);
  PMU->setPowerChannelVoltage(XPOWERS_ALDO3, 3300);  // display + touch
  PMU->enablePowerOutput(XPOWERS_ALDO3);
  PMU->setPowerChannelVoltage(XPOWERS_ALDO2, 3300);  // display backlight
  PMU->enablePowerOutput(XPOWERS_ALDO2);

  PMU->disablePowerOutput(XPOWERS_DCDC2);
  PMU->disablePowerOutput(XPOWERS_DCDC3);
  PMU->disablePowerOutput(XPOWERS_DCDC4);
  PMU->disablePowerOutput(XPOWERS_DCDC5);
  PMU->disablePowerOutput(XPOWERS_ALDO1);    // unused
  PMU->disablePowerOutput(XPOWERS_BLDO1);    // GNSS rail on the S3 Plus; unpopulated here
  PMU->disablePowerOutput(XPOWERS_BLDO2);    // DRV2605 haptic, not used
  PMU->disablePowerOutput(XPOWERS_DLDO1);    // MAX98357A speaker amp, not used
  PMU->disablePowerOutput(XPOWERS_DLDO2);

  // Keep the RTC backup cell charged so the PCF8563 holds the time.
  PMU->setPowerChannelVoltage(XPOWERS_VBACKUP, 3300);
  PMU->enablePowerOutput(XPOWERS_VBACKUP);

  // PWR key (side switch, wired to PWRON):
  //   press < 1s        -> PKEY_SHORT_IRQ, read as a click by TWatchInput
  //   1s <= press < 6s  -> nothing (PKEY_LONG_IRQ left masked)
  //   press >= 6s       -> hardware power-off
  //   hold 2s from off  -> power-on
  PMU->setPowerKeyPressOnTime(XPOWERS_POWERON_2S);
  PMU->setPowerKeyPressOffTime(XPOWERS_POWEROFF_6S);
  _axp->setIrqLevelTime(XPOWERS_AXP2101_IRQ_TIME_1S);

  PMU->disableIRQ(XPOWERS_AXP2101_ALL_IRQ);
  PMU->clearIrqStatus();
  PMU->enableIRQ(XPOWERS_AXP2101_PKEY_SHORT_IRQ |
                 XPOWERS_AXP2101_PKEY_NEGATIVE_IRQ |
                 XPOWERS_AXP2101_PKEY_POSITIVE_IRQ);

  // The fitted cell is a 470 mAh 3.8 V-nominal LiHV (4.35 V max), per the
  // physical label checked by Meck; LilyGo's own library also charges this
  // board to 4.35 V. 150 mA is about 0.3C.
  PMU->setChargerConstantCurr(XPOWERS_AXP2101_CHG_CUR_150MA);
  PMU->setChargeTargetVoltage(XPOWERS_AXP2101_CHG_VOL_4V35);

  PMU->disableTSPinMeasure();
  PMU->enableSystemVoltageMeasure();
  PMU->enableVbusVoltageMeasure();
  PMU->enableBattVoltageMeasure();
  return true;
}

void TWatchS3Board::powerOff() {
#ifdef DISPLAY_CLASS
  display.turnOff();
#endif
  radio_driver.powerOff();
  Serial.flush();
  if (PMU) {
    PMU->shutdown();
    delay(1000);   // the PMU cuts power during this wait
  }
  // No PMU (or it did not act): fall back to deep sleep.
  ESP32Board::powerOff();
}

void TWatchS3Board::onBootComplete() {
#ifdef TWATCH_CPU_MHZ_AFTER_BOOT
  setCpuFrequencyMhz(TWATCH_CPU_MHZ_AFTER_BOOT);
#endif
}

void TWatchS3Board::loop() {
#if defined(TWATCH_DISPLAY_OFF_THROTTLE_MS) && defined(DISPLAY_CLASS)
  // delay() lets the RTOS idle task wait for an interrupt instead of the loop
  // spinning. 50 ms still runs the loop 20 times a second.
  if (!display.isOn()) {
    delay(TWATCH_DISPLAY_OFF_THROTTLE_MS);
  }
#endif
}
