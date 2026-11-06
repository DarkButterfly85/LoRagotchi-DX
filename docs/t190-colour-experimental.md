# Experimental T190 RGB565 display

Only Heltec_T190_LoRaGotchi_DX_ble switches to ST7789LCDDisplay. Existing T190 companion/repeater profiles retain ST7789Display; other boards retain their renderer and geometry.

## Source-derived wiring and orientation

variants/heltec_t190/platformio.ini supplies SCK 38, MOSI 48, CS 39, DC 47, reset 40, VDD control 7 (active LOW in ST7789Display::begin/turnOff), backlight 17 (active HIGH). VEXT 5 remains active HIGH and is not confused with panel VDD. The colour driver owns a separate HSPI SPIClass and explicitly starts those pins with MISO -1; it does not borrow the radio FSPI/default pin mapping (radio SCK 9/MOSI 10/MISO 11).

The existing ST7789Display.h specifies a 320x170 landscape panel. Its ST7789Spi::landscapeScreen writes MADCTL MV|MX. Adafruit_ST7789 rotation 3 has those same bits; rotation 1 writes MV|MY, exactly 180 degrees opposite. The experimental profile initializes native 170x320, sets rotation 1 after every init (including wake), and obtains a 320x170 drawing surface. Adafruit's centered-panel offset is 35 pixels on the native short axis. These are source-based choices, not physical calibration.

## Rendering and memory

Logical UI remains 128x64 (X scale 2.5, Y scale 2.65625). Bitmap art intentionally retains square pixels using X scale on both bitmap axes, matching the shared driver's previous intent; its anchor uses logical Y scale. T190 bitmap blocks now partition exact fractional edges rather than overlapping ceil(2.5) blocks. Rectangles likewise use scaled endpoint differences. Other boards' bitmap geometry is unchanged.

A reusable 320x170 RGB565 canvas requires 108800 pixel bytes plus small object overhead. Every startFrame fills the entire canvas and every endFrame transfers the complete image, removing stale pixels. Allocation is nothrow and the internal canvas buffer is checked. Allocation failure uses existing direct draw fallback (functional but may flicker); no unchecked buffer transfer. Wake reuses the allocation. Strip canvas allocation also checks its internal buffer.

## Checks

Run python3 test/ui/check_t190_colour.py. It compiles the actual production LCD cpp with recording boundary mocks and exercises RGB565 preservation, exact fractional bitmap footprint, complete background replacement, wake rotation, power polarity and failed internal canvas allocation. This is host evidence only, not pixel timing, SPI electrical, display brightness or power measurement.

Build using PlatformIO: Heltec_T190_LoRaGotchi_DX_ble. No flashing, publishing or hardware validation is part of this change. On hardware, confirm corner markers/text orientation, RGB primaries, 320x170 edge coverage, off/wake behavior and responsiveness before calling this supported.

Verified build-only on 2026-11-06: Heltec_T190_LoRaGotchi_DX_ble, unchanged Heltec_T190_companion_radio_ble_, heltec_v4_tft_LoRaGotchi_DX_ble (other RGB565 target), heltec_v4_LoRaFish_companion_ble and Heltec_v3_LoRaFish_companion_ble (monochrome targets) all succeeded. Host regression and git diff --check passed. No device proof.
