# Experimental RAK4630 / RAK4631-compatible OLED builds

RAK4630 is the nRF52840 + SX1262 module; RAK4631 is a WisBlock Core board using
that module. This source already has an experimental RAK4631 DX BLE target.
The new module-name aliases reuse it; they do not implement a new carrier PCB.

| Edition | Explicit module-name environment | Existing/canonical environment |
| --- | --- | --- |
| DX (default fish) | RAK_4630_LoRaGotchi_DX_ble | RAK_4631_LoRaGotchi_DX_ble |
| Water (14 species) | water_rak4630_ble | water_rak4631_ble |

## Hardware prerequisites — verify before flashing

- A RAK4631-compatible WisBlock carrier/module combination. A bare RAK4630 stamp
  or custom PCB needs a pin/power/clock/flash-layout audit first; these aliases do
  not promise compatibility. Confirm Arduino-compatible bootloader/SoftDevice,
  not an assumption that stock RUI3/LoRaWAN firmware accepts this application.
- External 128x64 I2C SSD1306 OLED (for example, the RAK1921) on the inherited
  Wire bus, board Arduino pin indices SDA=13 and SCL=14. These are BSP pin numbers,
  not header positions or raw nRF GPIO labels. Default display address is inherited
  from SSD1306Display.h; check the actual module and carrier wiring.
- A working navigation input wired to the inherited user-button configuration:
  digital Arduino pin 9 (active low/pull-up), or the existing analog-button path
  pin 31. Check carrier wiring and pin mapping before connecting a button. The
  carrier reset switch is not a game navigation button. No OLED/input is built
  into a bare RAK4630 module. No buzzer pin is added by these aliases.
- Correct LoRa antenna/frequency-band hardware and matching radio settings. The
  inherited SX1262 configuration is unchanged, including its maximum power;
  compilation is not approval for local RF use or a substitute for an antenna.
- Existing RAK4631 board/SoftDevice/linker layout is preserved:
  boards/nrf52840_s140_v6_extrafs.ld, maximum application size 712704 bytes,
  board variant WisCore_RAK4631_Board and S140 6.1.1 metadata. Do not flash a
  different board's UF2 or assume any RAK4630 bootloader has this layout.

## Build and test

~~~sh
pio run -e RAK_4630_LoRaGotchi_DX_ble -t create_uf2 -j 2
pio run -e water_rak4630_ble -t create_uf2 -j 2
python3 test/boards/check_edition_targets.py
~~~

Images are under .pio/build/<environment>/firmware.uf2. The owner-board workflow
requests both aliases, separately from the three usual owner boards. The aliases
are explicitly experimental and NOT hardware-tested. A successful compile/UF2
creation does not verify the carrier, OLED, navigation, flash persistence, USB,
BLE pairing, radio TX/RX, sleep/wake or power draw. Those require physical tests.
Confirm source SHA, build status, UF2 family and linker bounds before any flash.
No bootloader replacement or automatic hardware flashing is part of this work.

References: [RAK4631 overview](https://docs.rakwireless.com/product-categories/wisblock/rak4631/overview/),
[RAK PlatformIO BSP guide](https://docs.rakwireless.com/Knowledge-Hub/Learn/Board-Support-Package-Installation-in-PlatformIO/).
Repository evidence: variants/rak4631/, boards/rak4631.json,
variants/loragotchi_experimental/platformio.ini and src/helpers/ui/SSD1306Display.h.
