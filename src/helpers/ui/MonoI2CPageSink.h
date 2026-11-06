#pragma once
#include <Wire.h>
#include <stddef.h>
#include <stdint.h>

// These adapters are I2C-only. Keep chunks below the smallest supported Wire
// buffer (32 bytes), including control byte; never depend on address wrapping.
class MonoI2CPageSink {
  TwoWire& wire;
  uint8_t address, columnOffset;
  bool ssd1306;
  bool writePageAtSpeed(size_t page, size_t column, const uint8_t* data, size_t count);
  bool transaction(uint8_t control, const uint8_t* bytes, size_t size) {
    wire.beginTransmission(address);
    bool ok = wire.write(control) == 1;
    for (size_t i = 0; i < size; ++i) ok = (wire.write(bytes[i]) == 1) && ok;
    return wire.endTransmission() == 0 && ok;
  }
public:
  MonoI2CPageSink(TwoWire& w, uint8_t addr, bool ssd, uint8_t offset = 0)
      : wire(w), address(addr), columnOffset(offset), ssd1306(ssd) {}
  bool writePage(size_t page, size_t column, const uint8_t* data, size_t count) {
    // Match the Adafruit constructors: 400kHz during display transfer,
    // 100kHz afterwards for other peripherals on the shared bus.
    wire.setClock(400000);
    const bool ok = writePageAtSpeed(page, column, data, count);
    wire.setClock(100000);
    return ok;
  }
};

inline bool MonoI2CPageSink::writePageAtSpeed(size_t page, size_t column, const uint8_t* data, size_t count) {
    if (!data || !count || page >= (ssd1306 ? 8u : 16u) || column >= 128 || count > 128 - column) return false;
    if (ssd1306) {
      // Explicit horizontal mode and one-page window, as in Adafruit's init.
      const uint8_t cmd[] = {0x20, 0x00, 0x21, uint8_t(column),
                            uint8_t(column + count - 1), 0x22, uint8_t(page), uint8_t(page)};
      if (!transaction(0x00, cmd, sizeof(cmd))) return false;
    } else {
      // SH1106 has 132 RAM columns (visible x+2); SH1107 uses x+0.
      const size_t x = column + columnOffset;
      const uint8_t cmd[] = {uint8_t(0xB0 + page), uint8_t(0x10 | (x >> 4)), uint8_t(x & 15)};
      if (!transaction(0x00, cmd, sizeof(cmd))) return false;
    }
    while (count) {
      const size_t n = count < 16 ? count : 16;
      if (!transaction(0x40, data, n)) return false;
      data += n; count -= n;
      yield();
    }
    return true;
}
