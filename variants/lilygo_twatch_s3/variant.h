#pragma once

// =============================================================================
// LilyGo T-Watch S3 (SX1262) - board-level pin definitions
//
// Pin map ported from the T-Watch edition of Meck (github.com/pelgraine/Meck), which
// cross-checked it against the T_WATCH-S3 schematic (rev 25-03-24) and LilyGo's
// TTGO_TWatch_Library (branch t-watch-s3, src/utilities.h).
//
// The LoRa (P_LORA_*) pins and SX1262 parameters are -D build flags in this
// variant's platformio.ini. The display SPI/backlight and FT6336U touch pins
// live in TWatchS3Display.h because LovyanGFX needs them in its panel config.
// =============================================================================

// Main I2C bus (shared): AXP2101 PMU, PCF8563 RTC, BMA423 accel, DRV2605 haptic.
// The FT6336U touch panel is on a separate bus (Wire1), set up by the display.
#define I2C_SDA 10
#define I2C_SCL 11

// Aliases used by the ESP32Board base class
#define PIN_BOARD_SDA I2C_SDA
#define PIN_BOARD_SCL I2C_SCL

// I2C device addresses (7-bit)
#define I2C_ADDR_PMU      0x34  // AXP2101 power management
#define I2C_ADDR_RTC      0x51  // PCF8563 real-time clock (found by AutoDiscoverRTCClock)

// Display (ST7789V 1.54" IPS)
#define LCD_HOR_SIZE 240
#define LCD_VER_SIZE 240

// User button: the T-Watch S3 has no GPIO button. Its only key is the side
// PWR key, wired to the AXP2101 PWRON pin, so presses are read from the PMU
// over I2C (see TWatchInput.h). PIN_USER_BTN is defined as -1 in
// platformio.ini purely to enable the single-button input path in UITask; it
// is never used as a GPIO.
