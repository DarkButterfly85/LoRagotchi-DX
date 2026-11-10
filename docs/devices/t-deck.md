# LilyGo T-Deck

The LilyGo T-Deck is an ESP32-S3 handheld with a colour ST7789 display, a trackball,
a keyboard and a GT911 touch screen. This page collects what is specific to the
LoRaGotchi-DX builds for it. For a short walk-through see the
[T-Deck getting-started guide](t-deck/GETTING_STARTED.md); general setup is in the
[main Getting Started guide](../../Getting_Started.md).

**Status:** standard DX profile; see
[Compatibility and test status](../BUILDING.md#compatibility-and-test-status).
Touch navigation is only in the diagnostic build below, which is source-level and
not hardware-tested.

## Builds

All T-Deck builds produce an ESP32 application BIN
(`.pio/build/<environment>/firmware.bin`), which is not a merged installer.

| Edition | BLE companion | USB |
| --- | --- | --- |
| DX | `LilyGo_TDeck_loragotchi_dx_ble` | `LilyGo_TDeck_loragotchi_dx_usb` |
| Water | `water_lilygo_tdeck_ble` | `water_lilygo_tdeck_usb` |
| Air | `air_lilygo_tdeck_ble` | `air_lilygo_tdeck_usb` |
| Land | `land_lilygo_tdeck_ble` | `land_lilygo_tdeck_usb` |
| DX-Pro | `dxpro_lilygo_tdeck_ble` | `dxpro_lilygo_tdeck_usb` |
| Touch diagnostic (DX, BLE) | `LilyGo_TDeck_loragotchi_dx_ble_touch_test` | - |

The USB build is the original T-Deck USB bring-up (`ENABLE_USB_INTERFACE`); the
BLE build is the BLE companion and also uses the display framebuffer. Both use
350 contacts, 40 channels and a 256-entry offline queue. Estimated flash use of a
DX build is about 1,300,650 bytes of 6,553,600 (about 20%), see
[creature compatibility](../creature-compatibility.md).

## Display

- ST7789 colour LCD driven by `ST7789LCDDisplay`; the logical 128x64 UI is scaled
  by 2.5 horizontally and 3.75 vertically (320x240 pixels).
- The BLE build draws through a framebuffer.
- Pet art uses the T-Deck pixel-art style (`LORAFISH_TDECK_PIXEL_ART`), with
  juvenile colour handling described in [JUVENILE-COLOURS.md](../../JUVENILE-COLOURS.md).
- Air uses a sky/ground scene rather than the Cardputer/T-Deck reef art
  ([AIR-EDITION.md](../../AIR-EDITION.md)).
- T-Deck touch rotation and native-layout mode are deliberately not enabled
  ([runtime display orientation](../runtime-display-orientation.md),
  [native display layout](../native-display-layout.md)).

## Controls

- **Trackball button** (GPIO0, the board's user button) is the single-button input:
  hold about one second for a long-press, with the usual click, double-click and
  long-press gestures described in
  [Button Controls](../../Getting_Started.md#button-controls).
- The diagnostic build's notes say the existing **keyboard and trackball remain
  active**. Which keyboard keys the pet UI uses is not documented here.
- **Touch (diagnostic build only):** top strip (the top 24 pixels) = Back; left and
  right thirds = Previous and Next; centre = Select; a horizontal swipe of 45 pixels
  or more also navigates; the first gesture only wakes a sleeping screen.

## Storage

Pet and egg data on the T-Deck is kept in NVS (`LORAFISH_TDECK_NVS`), using
distinct `egg0`/`egg1` keys for the adoption journal, see
[EGG-ADOPTION.md](../../EGG-ADOPTION.md).

## GPS and power

GPS is included (UART pins 43 and 44 at 38400 baud). The peripheral power pin is
GPIO10 and the display backlight control is GPIO42.

## Touch diagnostic build

`LilyGo_TDeck_loragotchi_dx_ble_touch_test` probes the GT911 touch controller
at 0x5D and 0x14 on the shared I2C bus (SDA GPIO18, SCL GPIO8) and prints raw
coordinates on serial at 115200 baud. A red marker is shown during a screen
redraw. Install only its `firmware.bin` through the existing T-Deck Launcher; do
not direct-flash, erase flash, or alter partitions. If the controller is not
found, send the serial output. The full notes are in
[TDECK_TOUCH_TEST_README.md](../../TDECK_TOUCH_TEST_README.md).

## Credits

The T-Deck hardware support comes from the upstream MeshCore firmware (Scott Powell
/ Ripple Radios); see [Credits](../CREDITS.md). No individual contributor credit for
the LoRaGotchi T-Deck port (framebuffer, touch work) is recorded in this repository.
