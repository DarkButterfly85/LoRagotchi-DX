# Build DX, Water or Air from main

**One repository, one shared source: `main`.** Choose an edition and board with
its case-sensitive PlatformIO environment; do not hunt for an old feature/fix
branch. Existing LoRaFish/LoRaGotchi environment names select DX. Only explicit
`water_*` or `air_*` aliases select those habitat editions. Mono/colour handling
is shared, not a separate firmware branch.

## Start once

Install [PlatformIO Core](https://docs.platformio.org/en/latest/core/installation/index.html), then:

```sh
git clone --branch main https://github.com/DrToxic/LoRagotchi-DX.git
cd LoRagotchi-DX
pio run -e water_heltec_v3_ble -j 1
```

Replace the environment with one from the table. For nRF52 append
`-t create_uf2`; ESP32 builds produce an application BIN. Build only the selected
environment, never an unqualified `pio run` over inherited MeshCore targets.

## Board and edition selection

| Board | DX | Water | Air | Output |
| --- | --- | --- | --- | --- |
| Heltec V3 | `Heltec_v3_LoRaFish_companion_ble` | `water_heltec_v3_ble` | `air_heltec_v3_ble` | BIN |
| Heltec V4 OLED | `heltec_v4_LoRaFish_companion_ble` | `water_heltec_v4_oled_ble` | `air_heltec_v4_oled_ble` | BIN |
| Heltec T096 | `Heltec_t096_LoRaFish_companion_ble` | `water_heltec_t096_ble` | `air_heltec_t096_ble` | UF2 |
| Wio Tracker L1 | `WioTrackerL1_LoRaGotchi_DX_ble` | `water_wio_tracker_l1_ble` | `air_wio_tracker_l1_ble` | UF2 |
| Wio Tracker L1-1W | `WioTrackerL1-1W_LoRaGotchi_DX_ble` | `water_wio_tracker_l1_1w_ble` | `air_wio_tracker_l1_1w_ble` | UF2 |
| ThinkNode M2 | `ThinkNode_M2_LoRaFish_companion_ble` | `water_thinknode_m2_ble` | `air_thinknode_m2_ble` | BIN |
| M5Stack Cardputer | `cardputer_loragotchi` | `water_m5stack_cardputer` | `air_m5stack_cardputer` | BIN |
| Heltec T114 | `Heltec_t114_LoRaFish_companion_ble` | `water_heltec_t114_ble` | `air_heltec_t114_ble` | UF2 |
| LilyGo T-Deck BLE | `LilyGo_TDeck_loragotchi_dx_ble` | `water_lilygo_tdeck_ble` | `air_lilygo_tdeck_ble` | BIN |
| LilyGo T-Deck USB | `LilyGo_TDeck_loragotchi_dx_usb` | `water_lilygo_tdeck_usb` | `air_lilygo_tdeck_usb` | BIN |
| RAK4631 (experimental) | `RAK_4631_LoRaGotchi_DX_ble` | `water_rak4631_ble` | `air_rak4631_ble` | UF2 |
| RAK4630 module (experimental) | `RAK_4630_LoRaGotchi_DX_ble` | `water_rak4630_ble` | `air_rak4630_ble` | UF2 |
| LilyGo T-Beam 1W (experimental) | `LilyGo_TBeam_1W_LoRaGotchi_DX_ble` | `water_lilygo_tbeam_1w_ble` | `air_lilygo_tbeam_1w_ble` | BIN |
| Station G2 (experimental) | `Station_G2_LoRaGotchi_DX_ble` | `water_station_g2_ble` | `air_station_g2_ble` | BIN |
| Station G3 ESP32 (experimental) | `Station_G3_ESP32_LoRaGotchi_DX_ble` | `water_station_g3_esp32_ble` | `air_station_g3_esp32_ble` | BIN |

The aliases inherit their DX board's pins, RF, memory and dependencies; see
[Water definitions](../variants/loragotchi_water/platformio.ini) and
[Air definitions](../variants/loragotchi_air/platformio.ini). Other DX-only
boards remain in the [README](../README.md) and
[experimental screen matrix](EXPERIMENTAL-SCREEN-TARGETS.md).
RAK modules require the fitted display, carrier and controls described in
[RAK4630 prerequisites](RAK4630-EXPERIMENTAL.md). A target name or successful
compile is not physical hardware acceptance.

## Find the result; flashing is separate

- ESP32: `.pio/build/<environment>/firmware.bin` (application only, not an installer).
- nRF52: `.pio/build/<environment>/firmware.uf2`, after `-t create_uf2`.

Do not assume an application BIN belongs at address zero. Station G2/G3 and
T-Beam 1W now use a single factory app and no OTA; an app-only update cannot
migrate an old partition table. Read the [migration/data-loss warning](SINGLE-APP-MIGRATION.md)
and back up first. Matching data geometry is not a data-retention guarantee.

## GitHub-hosted builds and product scope

For existing workflow names, bounded matrices, exact-commit artifacts and their
14-day retention, see [GitHub firmware builds](github-firmware-builds.md).
When manually running a workflow, select `main`; matrices differ and no single
workflow builds every board/edition. No workflow success implies a published
release, hardware acceptance or permission to flash.

Current source provides DX, Water (14 species) and Air (18 animals), not a new
firmware release. The shared source already selects these by build target.
Future Water/Air product branding or distribution channels need a separate
decision, not duplicate source-maintenance branches. Land and combined-habitat
products remain future work. See [Water](../WATER-EDITION.md) and
[Air](../AIR-EDITION.md) for saves, adoption and negotiated visiting fallbacks.
