# T-Deck GT911 touch diagnostic - corrected register byte order and retry

Build: `pio run -e LilyGo_TDeck_loragotchi_dx_ble_touch_test`

Install only `.pio/build/LilyGo_TDeck_loragotchi_dx_ble_touch_test/firmware.bin` through the existing T-Deck Launcher. **Do not direct-flash, erase flash, or alter partitions.**

Open serial at 115200 baud. The GT911 is probed at 0x5D and 0x14 over the already-initialised I2C bus (GPIO18 SDA, GPIO8 SCL). Expect `[TDECK TOUCH] GT911 at ... product ID ...`, followed by raw coordinates when touched. A red marker is shown during a screen redraw (it may not update immediately if the screen is not otherwise refreshing). Touch does not navigate menus yet. No audio or trackball modifications.

The GT911 register address is now transmitted high byte first, and detection retries every two seconds. If NOT FOUND persists, send serial output; next step is board-specific reset/power/interrupt GPIO investigation (no speculative pin changes included). This build is source-level and not hardware-tested.
