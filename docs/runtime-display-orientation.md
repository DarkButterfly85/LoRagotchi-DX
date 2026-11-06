# Runtime display orientation

Display > Orientation offers **0 degrees** (board baseline) and **180 degrees**.
Browsing is a draft; Select applies, Back cancels. Accepted preferences use the
existing deferred save-on-menu-exit / shutdown-flush lifecycle. An abrupt power
cut before that flush can lose the latest preference.

Supported driver implementations: ST7789LCDDisplay (non-touch boards), SSD1306,
SH1106 and SH1107. The corrected experimental T190 RGB565 baseline remains
DISPLAY_ROTATION=1; 180 degrees selects rotation 3. Other mounting baselines are
unchanged. Full-frame and strip canvases keep their dimensions and logical
coordinates; only the physical panel rotates. State survives panel power/reset
and OLED reinitialization. Orientation changes invalidate the static frame cache
and request a full redraw.

The settings prefix (78 bytes including species) is unchanged. ORI1 appends six
bytes: magic, value 0/1, reserved zero. Old, missing, truncated or invalid tails
default to baseline. Older firmware ignores the appended tail (and can discard
it on its next save). No pet identity or colour gene is repurposed.

T-Deck and watch-touch profiles deliberately do not advertise this capability:
rotating pixels alone would leave touch coordinates, hit targets and swipe
semantics incorrect. Their display/input behaviour is unchanged. ST7735,
NV3001B, legacy ST7789Spi, LGFX, M5Cardputer, U8g2, e-paper and null drivers also
retain their existing mounting/orientation and hide the row. They require a
separate driver-specific implementation and validation, not a generic mirror.

Host tests and target builds are not physical panel acceptance. Check physical
mounting, panel offsets/corners, text direction, button usability and repeated
sleep/wake on each board. No device was flashed or hardware-tested here.

## Validation (2026-11-06)

Passing host checks: check_menu_navigation.py (sound absent/present, real
Aquarium -> Options -> Display -> Orientation route, Select/Back),
check_local_savings.py (ESP32/nRF52 saved tails and production display-loop
invalidation), check_t190_colour.py (rotation 1/3, repeat assignment, wake/reset,
canvas allocation fallback), check_oled_orientation.py (real SH1106/SH1107
wrappers, baselines 0/2, wake/reinit), check_sh1106_brightness.py,
check_l1_buttons.py, check_emoji_dx.py and check_fish_lifecycle.py.

Successful target builds, two compilation jobs maximum:
- Heltec_T190_LoRaGotchi_DX_ble (ST7789LCDDisplay)
- Heltec_v3_LoRaFish_companion_ble (SSD1306)
- Heltec_t096_LoRaFish_companion_ble (unsupported ST7735 regression control)
- WioTrackerL1_LoRaGotchi_DX_ble (SH1106, nRF52)
- Nano_G2_Ultra_LoRaGotchi_DX_ble (SH1106, nRF52)

SH1107 is production-wrapper host-tested, not target-built in this focused
matrix. T-Deck touch rotation remains unavailable by design.
