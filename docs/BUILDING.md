# Build DX, Water, Air or Land from main

**One repository, one shared source: `main`.** Choose an edition and board with
its case-sensitive PlatformIO environment; do not hunt for an old feature/fix
branch. Existing LoRaFish/LoRaGotchi environment names select DX. Only explicit
`water_*`, `air_*` or `land_*` aliases select those habitat editions. Mono/colour handling
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

| Board | DX | Water | Air | Land | DX-Pro | Output |
| --- | --- | --- | --- | --- | --- | --- |
| Heltec V3 | `Heltec_v3_LoRaFish_companion_ble` | `water_heltec_v3_ble` | `air_heltec_v3_ble` | `land_heltec_v3_ble` | `dxpro_heltec_v3_ble` | BIN |
| Heltec V4 OLED | `heltec_v4_LoRaFish_companion_ble` | `water_heltec_v4_oled_ble` | `air_heltec_v4_oled_ble` | `land_heltec_v4_oled_ble` | `dxpro_heltec_v4_oled_ble` | BIN |
| Heltec T096 | `Heltec_t096_LoRaFish_companion_ble` | `water_heltec_t096_ble` | `air_heltec_t096_ble` | `land_heltec_t096_ble` | `dxpro_heltec_t096_ble` | UF2 |
| Heltec T190 colour (experimental) | `Heltec_T190_LoRaGotchi_DX_ble` | `water_heltec_t190_ble` | `air_heltec_t190_ble` | `land_heltec_t190_ble` | `dxpro_heltec_t190_ble` | BIN |
| Wio Tracker L1 | `WioTrackerL1_LoRaGotchi_DX_ble` | `water_wio_tracker_l1_ble` | `air_wio_tracker_l1_ble` | `land_wio_tracker_l1_ble` | `dxpro_wio_tracker_l1_ble` | UF2 |
| Wio Tracker L1-1W | `WioTrackerL1-1W_LoRaGotchi_DX_ble` | `water_wio_tracker_l1_1w_ble` | `air_wio_tracker_l1_1w_ble` | `land_wio_tracker_l1_1w_ble` | `dxpro_wio_tracker_l1_1w_ble` | UF2 |
| ThinkNode M2 | `ThinkNode_M2_LoRaFish_companion_ble` | `water_thinknode_m2_ble` | `air_thinknode_m2_ble` | `land_thinknode_m2_ble` | `dxpro_thinknode_m2_ble` | BIN |
| M5Stack Cardputer | `cardputer_loragotchi` | `water_m5stack_cardputer` | `air_m5stack_cardputer` | `land_m5stack_cardputer` | `dxpro_m5stack_cardputer` | BIN |
| Heltec T114 | `Heltec_t114_LoRaFish_companion_ble` | `water_heltec_t114_ble` | `air_heltec_t114_ble` | `land_heltec_t114_ble` | `dxpro_heltec_t114_ble` | UF2 |
| LilyGo T-Deck BLE | `LilyGo_TDeck_loragotchi_dx_ble` | `water_lilygo_tdeck_ble` | `air_lilygo_tdeck_ble` | `land_lilygo_tdeck_ble` | `dxpro_lilygo_tdeck_ble` | BIN |
| LilyGo T-Deck USB | `LilyGo_TDeck_loragotchi_dx_usb` | `water_lilygo_tdeck_usb` | `air_lilygo_tdeck_usb` | `land_lilygo_tdeck_usb` | `dxpro_lilygo_tdeck_usb` | BIN |
| RAK4631 (experimental) | `RAK_4631_LoRaGotchi_DX_ble` | `water_rak4631_ble` | `air_rak4631_ble` | `land_rak4631_ble` | `dxpro_rak4631_ble` | UF2 |
| RAK4630 module (experimental) | `RAK_4630_LoRaGotchi_DX_ble` | `water_rak4630_ble` | `air_rak4630_ble` | `land_rak4630_ble` | `dxpro_rak4630_ble` | UF2 |
| LilyGo T-Beam 1W (experimental) | `LilyGo_TBeam_1W_LoRaGotchi_DX_ble` | `water_lilygo_tbeam_1w_ble` | `air_lilygo_tbeam_1w_ble` | `land_lilygo_tbeam_1w_ble` | `dxpro_lilygo_tbeam_1w_ble` | BIN |
| Station G2 (experimental) | `Station_G2_LoRaGotchi_DX_ble` | `water_station_g2_ble` | `air_station_g2_ble` | `land_station_g2_ble` | `dxpro_station_g2_ble` | BIN |
| Station G3 ESP32 (experimental) | `Station_G3_ESP32_LoRaGotchi_DX_ble` | `water_station_g3_esp32_ble` | `air_station_g3_esp32_ble` | `land_station_g3_esp32_ble` | `dxpro_station_g3_esp32_ble` | BIN |

The aliases inherit their DX board's pins, RF, memory and dependencies; see
[Water definitions](../variants/loragotchi_water/platformio.ini),
[Air definitions](../variants/loragotchi_air/platformio.ini),
[Land definitions](../variants/loragotchi_land/platformio.ini) and
[DX-Pro definitions](../variants/loragotchi_dxpro/platformio.ini). Each `dxpro_<board>`
target is the matching `water_<board>` target plus the DX-Pro flag and nothing
else, see [DX-Pro](dxpro.md). Other DX-only boards are in the
[compatibility and test status](#compatibility-and-test-status) table below and the
[experimental screen matrix](EXPERIMENTAL-SCREEN-TARGETS.md).
RAK modules require the fitted display, carrier and controls described in
[RAK4630 prerequisites](RAK4630-EXPERIMENTAL.md). A target name or successful
compile is not physical hardware acceptance.

## Compatibility and test status

One table for every board in this tree. A target name or a successful compile is
not physical hardware acceptance. The statuses are:

- **Previously exercised on hardware**: tried on the owner's own board, see
  [GitHub firmware builds](github-firmware-builds.md). Hardware testing remains a
  separate status from build success, and no board in this table is recorded as
  formally hardware-accepted for the Water, Air, Land or DX-Pro aliases.
- **Standard DX profile**: an existing DX target in the standard build matrix; no
  hardware-acceptance claim is recorded here.
- **Experimental**: not hardware-accepted. Optional-display boards need a fitted
  panel and controls. Screenless and e-ink profiles are excluded.
- **Untested on hardware**: retained DX-only target; there are no corresponding
  Water/Air aliases.

| Board / radio | Status | Notes |
| --- | --- | --- |
| Heltec V3 | Previously exercised on hardware | Owner profile (BIN). |
| Heltec V4 OLED | Previously exercised on hardware | Owner profile (BIN). V4 OLED is not V4 TFT. |
| Heltec T096 | Previously exercised on hardware | Owner profile (UF2). |
| Heltec T114 | Standard DX profile | UF2. |
| ThinkNode M2 | Standard DX profile | BIN; uses a single larger primary app partition without OTA (see [history](HISTORY.md)). |
| M5Stack Cardputer | Standard DX profile | BIN; see [Cardputer](devices/cardputer.md). Hardware functionality of the merged Cardputer display build has not been independently verified. |
| LilyGo T-Deck BLE / USB | Standard DX profile | BIN; see [T-Deck](devices/t-deck.md). The touch diagnostic build is source-level and not hardware-tested. |
| Wio Tracker L1 / L1-1W | Experimental | In the [experimental screen matrix](EXPERIMENTAL-SCREEN-TARGETS.md) (UF2). L1 is not L1-1W. |
| Heltec T190 colour | Experimental | RGB565 colour target, BIN. See [T190 colour edition builds](#t190-colour-edition-builds) and [T190 colour limitations](t190-colour-experimental.md). |
| RAK4631 / RAK4630 module | Experimental | UF2. RAK modules need the [correct carrier, fitted display and controls](RAK4630-EXPERIMENTAL.md). |
| LilyGo T-Beam 1W | Experimental | BIN. Single factory app, no OTA: read the [migration/data-loss warning](SINGLE-APP-MIGRATION.md). |
| Station G2 | Experimental | BIN. Single factory app, no OTA: read the [migration/data-loss warning](SINGLE-APP-MIGRATION.md). |
| Station G3 ESP32 | Experimental | BIN. Single factory app, no OTA: read the [migration/data-loss warning](SINGLE-APP-MIGRATION.md). |
| T-Beam SX1262 | Untested on hardware | DX environment `Tbeam_SX1262_LoRaFish_companion_ble`. |
| T-Beam SX1276 | Untested on hardware | DX environment `Tbeam_SX1276_LoRaFish_companion_ble`. |
| T-Watch S3 SX1262, BLE | Untested on hardware | DX environment `TWatch_S3_LoRaFish_companion_ble`; see [T-Watch S3](devices/t-watch-s3.md). |
| T-Watch S3 SX1262, no Bluetooth | Untested on hardware | DX environment `TWatch_S3_LoRaFish_standalone`; see [T-Watch S3](devices/t-watch-s3.md). |
| T-Watch S3 SX1280, 2.4 GHz | Untested on hardware | DX environment `TWatch_S3_1280_LoRaFish_companion_ble`; see [T-Watch S3](devices/t-watch-s3.md). |

RAK4631/4630, T-Beam 1W and Station G2/G3 profiles are **experimental**;
RAK modules need the [correct carrier, fitted display and controls](RAK4630-EXPERIMENTAL.md).
See the [experimental screen matrix](EXPERIMENTAL-SCREEN-TARGETS.md)
for further DX-only targets and board-specific limitations. Its experimental
profiles are not hardware-accepted; optional-display boards need a fitted panel
and controls. Screenless and e-ink profiles are excluded.

These additional DX-only targets (the last five rows above) are retained, but are **untested on hardware**;
there are no corresponding Water/Air aliases.

## T190 colour edition builds

On this follow-up branch (`fix/pet-followup-20261106`), select:

```sh
pio run -e water_heltec_t190_ble -j 1
pio run -e air_heltec_t190_ble -j 1
```

Both inherit the experimental DX RGB565 LCD target, 170×320 panel rotated to
320×170, framebuffer/partial updates, BLE PIN policy, pinned RadioLib,
dependencies, and existing 16 MB board partition layout. They add only the
habitat flag. The stock `Heltec_T190_companion_radio_ble_` is not the pet target.
No save format, wire protocol, partition migration or flash operation is changed.

For hosted builds use **Air DX and Water selected owner-board test images**,
choose this branch, board **T190**, and edition **Water**, **Air**, **DX** or
**all**. This manual selector does not run automatically on follow-up branch
pushes. Artifacts are app-only BINs, not merged installers. Compilation is not
physical T190 acceptance or a save-retention guarantee. See
[T190 colour limitations](t190-colour-experimental.md).

## Tester firmware

Adding `-DLORAGOTCHI_TESTER_FIRMWARE=1` to a build's flags compiles a tester firmware. It only adds the pet
colour (Pet colours) and plain species (Pet species) rows back to **Options > Display**; normal builds leave the flag
undefined and hide them. The DX-Pro **Animal set** row is always shown. Pet setup still asks for the species and colours, and saved settings and pets are not
changed in either case.

## Find the result; flashing is separate

- ESP32: `.pio/build/<environment>/firmware.bin` (application only, not an installer).
- nRF52: `.pio/build/<environment>/firmware.uf2`, after `-t create_uf2`.

For the USB upload command, UF2 copy procedure and pre-install backup checklist,
see [Check the device and protect existing data](#check-the-device-and-protect-existing-data)
and [Install using the board's matching method](#install-using-the-boards-matching-method)
below.
Use the same environment for building and installing; choose the exact board
variant rather than a similarly named target.

Do not assume an application BIN belongs at address zero. Station G2/G3 and
T-Beam 1W now use a single factory app and no OTA; an app-only update cannot
migrate an old partition table. Read the [migration/data-loss warning](SINGLE-APP-MIGRATION.md)
and back up first. Matching data geometry is not a data-retention guarantee.

## Check the device and protect existing data

Building does not install anything. Before writing to a device, confirm the
board/radio/display variant and export or back up its identity/keys, settings,
contacts and pet data using a verified recovery route. Keep key backups private.
Read the [Water](../WATER-EDITION.md) or [Air](../AIR-EDITION.md) save/compatibility
notes before changing editions; matching storage layouts do not guarantee
saved-data retention.

**Station G2, Station G3 ESP32 and T-Beam 1W:** stop and read the
[partition migration and data-loss warning](SINGLE-APP-MIGRATION.md)
first. These profiles use a single factory app with no OTA. An app-only update
does not migrate an old partition table; the generic upload example below is
not a migration procedure. Do not erase flash, upload a filesystem or blindly
write a combined image to make a firmware fit.

## Install using the board's matching method

- **ESP32 (BIN):** `.pio/build/<environment>/firmware.bin` is an application,
  not a complete installer. For a supported serial-programmed board with a
  compatible installed layout, connect its USB data cable and use PlatformIO's
  board-specific upload recipe with the **same environment**. For Water on
  Heltec V3, for example:

  ```sh
  pio run -e water_heltec_v3_ble -j 1 -t upload
  ```

  Select the correct serial device with `--upload-port <port>` if necessary;
  use the board's documented boot/download-mode procedure if it cannot connect.
  An upload may also write bootloader/partition images: it is not a promise of
  app-only writes or data retention. Do not flash an application BIN at address
  zero or assume a web flasher migrates partition tables.
- **nRF52 (UF2):** build with `-t create_uf2`. For Water on **Heltec T096**:

  ```sh
  pio run -e water_heltec_t096_ble -j 1 -t create_uf2
  ```

  Enter the board's existing UF2 bootloader using its documented procedure,
  then copy `.pio/build/water_heltec_t096_ble/firmware.uf2` to the mounted
  bootloader drive. Use the selected environment's own UF2 for DX, Air or
  another board; do not copy the application BIN instead. If no UF2 drive
  appears, consult the board's bootloader instructions rather than erasing or
  replacing its bootloader blindly.

After reboot, check the splash shows the intended edition and verify display,
controls, pairing and saved state. The [GitHub-hosted builds](#github-hosted-builds-and-product-scope)
section also covers exact-commit hosted artifacts. A successful build is neither a
published release nor physical hardware acceptance.

## Buzzer pins

LoRaFish buzzer outputs are assigned per board:

| Device | Buzzer pin |
| --- | --- |
| ThinkNode M2 | GPIO5 |
| Heltec WiFi LoRa 32 V3 | GPIO6 |
| Heltec WiFi LoRa 32 V4 OLED | GPIO6 |
| Heltec T114 | GPIO46 / P1.14 |
| Heltec T096 | GPIO45 / P1.13 |

## GitHub-hosted builds and product scope

For existing workflow names, bounded matrices, exact-commit artifacts and their
14-day retention, see [GitHub firmware builds](github-firmware-builds.md).
When manually running a workflow, select `main`; matrices differ and no single
workflow builds every board/edition. No workflow success implies a published
release, hardware acceptance or permission to flash.

Current source provides DX, Water (14 species), Air (18 animals) and an early Land
scaffold (43 animals, draft art; see [Land](../LAND-EDITION.md)), not a new
firmware release. The shared source already selects these by build target.
Future Water/Air product branding or distribution channels need a separate
decision, not duplicate source-maintenance branches. Combined-habitat
products remain future work. See [Water](../WATER-EDITION.md) and
[Air](../AIR-EDITION.md) for saves, adoption and negotiated visiting fallbacks.

## Air edition build targets

Use the existing GitHub firmware-build policy; do not run every inherited target.
The manual Air owner workflow selects these environments and their DX/Water
controls after host checks (publication/CI permission is still required):

- air_heltec_v3_ble — ESP32 application BIN
- air_heltec_v4_oled_ble — ESP32 application BIN
- air_heltec_t096_ble — nRF52 create_uf2

Additional aliases mirror Water: air_thinknode_m2_ble, air_m5stack_cardputer,
air_heltec_t114_ble, air_lilygo_tdeck_ble, air_lilygo_tdeck_usb,
air_rak4631_ble and air_rak4630_ble. They inherit unchanged hardware, RF and memory
profiles, not a hardware acceptance claim. Details and remaining gates:
[AIR-EDITION.md](../AIR-EDITION.md).

Note: this list predates the later Air aliases. The `air_*` environments in
[the Air definitions](../variants/loragotchi_air/platformio.ini) now also include
`air_wio_tracker_l1_ble`, `air_wio_tracker_l1_1w_ble`, `air_heltec_t190_ble`,
`air_lilygo_tbeam_1w_ble`, `air_station_g2_ble` and `air_station_g3_esp32_ble`;
the [board matrix](#board-and-edition-selection) lists every current name.
