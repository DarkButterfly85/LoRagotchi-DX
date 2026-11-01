# Experimental screen-equipped targets

**EXPERIMENTAL — NONE OF THESE NEW TARGETS HAS BEEN TESTED ON REAL HARDWARE.**

A successful build is not proof of display orientation, input, power, storage, BLE, GPS or over-the-air operation. Use only the exact board/radio/display variant listed. These profiles inherit existing MeshCore wiring, radio settings, partitions and transport; they enable the LoRagotchi pet UI. No screenless or e-ink builds are included. Optional-display kits require the listed panel **and control input** fitted.

These are BLE companion builds. Existing supported DX images remain in the regular release; this prerelease adds hardware coverage rather than replacing them. TFT drivers that expose a monochrome framebuffer retain that rendering mode.

## Build matrix

| Environment | Inherited MeshCore profile | Display | Format |
| --- | --- | --- | --- |
| `Ebyte_EoRa-S3_LoRaGotchi_DX_ble` | `Ebyte_EoRa-S3_companion_radio_ble` | SSD1306Display | ESP32 application BIN |
| `GAT562_30S_Mesh_Kit_LoRaGotchi_DX_ble` | `GAT562_30S_Mesh_Kit_companion_radio_ble` | SSD1306Display | UF2 |
| `GAT562_Mesh_Tracker_Pro_LoRaGotchi_DX_ble` | `GAT562_Mesh_Tracker_Pro_companion_radio_ble` | SSD1306Display | UF2 |
| `GAT562_Mesh_Watch13_LoRaGotchi_DX_ble` | `GAT562_Mesh_Watch13_companion_radio_ble` | SSD1306Display | UF2 |
| `Heltec_T190_LoRaGotchi_DX_ble` | `Heltec_T190_companion_radio_ble_` | ST7789Display | ESP32 application BIN |
| `Heltec_Wireless_Tracker_LoRaGotchi_DX_ble` | `Heltec_Wireless_Tracker_companion_radio_ble` | ST7735Display | ESP32 application BIN |
| `Heltec_t1_LoRaGotchi_DX_ble` | `Heltec_t1_companion_radio_ble` | ST7735Display | UF2 |
| `Heltec_v2_LoRaGotchi_DX_ble` | `Heltec_v2_companion_radio_ble` | SSD1306Display | ESP32 application BIN |
| `KeepteenLT1_LoRaGotchi_DX_ble` | `KeepteenLT1_companion_radio_ble` | SSD1306Display | UF2 |
| `LilyGo_T3S3_sx1262_LoRaGotchi_DX_ble` | `LilyGo_T3S3_sx1262_companion_radio_ble` | SSD1306Display | ESP32 application BIN |
| `LilyGo_T3S3_sx1276_LoRaGotchi_DX_ble` | `LilyGo_T3S3_sx1276_companion_radio_ble` | SSD1306Display | ESP32 application BIN |
| `LilyGo_TBeam_1W_LoRaGotchi_DX_ble` | `LilyGo_TBeam_1W_companion_radio_ble` | SH1106Display | ESP32 application BIN |
| `LilyGo_TLora_V2_1_1_6_LoRaGotchi_DX_ble` | `LilyGo_TLora_V2_1_1_6_companion_radio_ble` | SSD1306Display | ESP32 application BIN |
| `Meshadventurer_sx1262_LoRaGotchi_DX_ble` | `Meshadventurer_sx1262_companion_radio_ble` | SSD1306Display | ESP32 application BIN |
| `Meshadventurer_sx1268_LoRaGotchi_DX_ble` | `Meshadventurer_sx1268_companion_radio_ble` | SSD1306Display | ESP32 application BIN |
| `Meshtiny_LoRaGotchi_DX_ble` | `Meshtiny_companion_radio_ble` | SSD1306Display | UF2 |
| `Nano_G2_Ultra_LoRaGotchi_DX_ble` | `Nano_G2_Ultra_companion_radio_ble` | SH1106Display | UF2 |
| `ProMicro_LoRaGotchi_DX_ble` | `ProMicro_companion_radio_ble` | SSD1306Display | UF2 |
| `RAK_3401_LoRaGotchi_DX_ble` | `RAK_3401_companion_radio_ble` | SSD1306Display | UF2 |
| `RAK_4631_LoRaGotchi_DX_ble` | `RAK_4631_companion_radio_ble` | SSD1306Display | UF2 |
| `Station_G2_LoRaGotchi_DX_ble` | `Station_G2_companion_radio_ble` | SH1106Display | ESP32 application BIN |
| `Station_G3_ESP32_LoRaGotchi_DX_ble` | `Station_G3_ESP32_companion_radio_ble` | SH1106Display | ESP32 application BIN |
| `T_Beam_S3_Supreme_SX1262_LoRaGotchi_DX_ble` | `T_Beam_S3_Supreme_SX1262_companion_radio_ble` | SH1106Display | ESP32 application BIN |
| `ThinkNode_M9_LoRaGotchi_DX_ble` | `ThinkNode_M9_companion_radio_ble_` | ST7789Display | ESP32 application BIN |
| `WioTrackerL1-1W_LoRaGotchi_DX_ble` | `WioTrackerL1-1W_companion_radio_ble` | SH1106Display | UF2 |
| `WioTrackerL1_LoRaGotchi_DX_ble` | `WioTrackerL1_companion_radio_ble` | SH1106Display | UF2 |
| `Xiao_S3_WIO_LoRaGotchi_DX_ble` | `Xiao_S3_WIO_companion_radio_ble` | SSD1306Display | ESP32 application BIN |
| `heltec_rc32_LoRaGotchi_DX_ble` | `heltec_rc32_companion_radio_ble` | NV3001BDisplay | ESP32 application BIN |
| `heltec_tracker_v2_LoRaGotchi_DX_ble` | `heltec_tracker_v2_companion_radio_ble` | ST7735Display | ESP32 application BIN |
| `heltec_v4_r8_LoRaGotchi_DX_ble` | `heltec_v4_r8_companion_radio_ble` | SSD1306Display | ESP32 application BIN |
| `heltec_v4_r8_tft_LoRaGotchi_DX_ble` | `heltec_v4_r8_tft_companion_radio_ble` | ST7789LCDDisplay | ESP32 application BIN |
| `heltec_v4_tft_LoRaGotchi_DX_ble` | `heltec_v4_tft_companion_radio_ble` | ST7789LCDDisplay | ESP32 application BIN |
| `ikoka_handheld_nrf_e22_30dbm_096_LoRaGotchi_DX_ble` | `ikoka_handheld_nrf_e22_30dbm_096_companion_radio_ble` | SSD1306Display | UF2 |
| `ikoka_handheld_nrf_e22_30dbm_096_rotated_LoRaGotchi_DX_ble` | `ikoka_handheld_nrf_e22_30dbm_096_rotated_companion_radio_ble` | SSD1306Display | UF2 |
| `ikoka_stick_nrf_22dbm_LoRaGotchi_DX_ble` | `ikoka_stick_nrf_22dbm_companion_radio_ble` | SSD1306Display | UF2 |
| `ikoka_stick_nrf_30dbm_LoRaGotchi_DX_ble` | `ikoka_stick_nrf_30dbm_companion_radio_ble` | SSD1306Display | UF2 |
| `ikoka_stick_nrf_33dbm_LoRaGotchi_DX_ble` | `ikoka_stick_nrf_33dbm_companion_radio_ble` | SSD1306Display | UF2 |
| `meshnology_w12_LoRaGotchi_DX_ble` | `meshnology_w12_companion_radio_ble` | SSD1306Display | ESP32 application BIN |
| `muzi_base_duo_superIO_LoRaGotchi_DX_ble` | `muzi_base_duo_superIO_companion_radio_ble` | SH1107Display | UF2 |
| `muzi_base_uno_superIO_LoRaGotchi_DX_ble` | `muzi_base_uno_superIO_companion_radio_ble` | SH1107Display | UF2 |
| `nibble_screen_connect_LoRaGotchi_DX_ble` | `nibble_screen_connect_companion_radio_ble_` | SSD1306Display | ESP32 application BIN |
| `nibble_zero_connect_LoRaGotchi_DX_ble` | `nibble_zero_connect_companion_radio_ble_` | SSD1306Display | ESP32 application BIN |

## Tight-flash profiles

T-LoRa V2.1, Station G2 and Station G3 omit optional environmental/I2C sensor add-on drivers to fit the pet UI in their existing application partitions. Board battery readings, radio limits/pins, display/input, storage layouts, BLE, and configured GPS support are retained. These images do not support those optional environmental sensor add-ons; no repartitioning is required.

## Not enabled

E-ink profiles (Wireless Paper, E213/E290, T-Echo/T-Echo Lite, MeshPocket, ThinkNode M1/M5/M6/M8, Wio Tracker e-ink) and null/no-display profiles are intentionally excluded. The OLED T-Echo Card is a separate device and is not classified as e-ink.

- `Xiao_S3_companion_radio_ble`: Bare XIAO S3 profile has no mapped control button (PIN_USER_BTN=-1); display/button wiring needs a defined hardware variant.
- `LilyGo_T_Impulse_Plus_companion_radio_ble`: Inherited target explicitly leaves the button disabled until screen support is implemented.
- `LilyGo_T-Echo_Card_companion_radio_ble`: 72x40 OLED requires a dedicated compact pet/menu layout; DX currently requires at least a 128x64 logical viewport.

## Build and test

```sh
pio run -e <environment> -j 2
# nRF52840 profiles:
pio run -e <environment> -t create_uf2 -j 2
```

Before reporting support, check display start/orientation/animation, click/hold/double-click navigation from the aquarium, pairing PIN and BLE connection, persistence after reboot, and a fish visit/recall in both directions. Match RF settings on the peer. Reboot still clears active DX travel. Do not erase or replace bootloader/partitions just to install an application-only update; use the release-specific flashing instructions and export settings first.

The machine-readable matrix is [experimental-screen-targets.json](experimental-screen-targets.json).
