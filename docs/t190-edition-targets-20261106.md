# T190 edition target repair — 2026-11-06

The published follow-up base 603841567364f0ba0572147073210203a4a5ebc2
contained the DX colour profile but no Water/Air T190 aliases. Its hosted
edition selector omitted T190; the experimental manifest/audit still expected
the old monochrome driver. This change adds discoverable habitat aliases and
corrects that stale CI metadata without changing firmware source.

- Water: `water_heltec_t190_ble` — local PlatformIO build PASS, 90.37 s.
- Air: `air_heltec_t190_ble` — local PlatformIO build PASS, 85.73 s.
- Both inherit `Heltec_T190_LoRaGotchi_DX_ble` exactly plus one edition flag.
- Water flash usage 1,298,897 bytes; Air 1,306,201 bytes; app slot 6,553,600 bytes.
- Both reported static RAM 183,172 bytes. No runtime heap measurement.
- Generated partitions match each other and the existing default_16MB.csv:
  app0 0x10000/0x640000, app1 0x650000/0x640000, SPIFFS 0xc90000/0x360000.
- Both ESP32 images passed esptool checksum and validation-hash checks.
- All pre-existing resolved PlatformIO sections matched the captured baseline.
- 16 Water / 16 Air alias audits, 42 experimental DX profile audits, T190
  colour/partial-row host checks, edition save/wire/splash checks, Air state
  and protocol checks, 24 BLE PIN host configurations, and native Water/Air
  suites passed. Workflow YAML parsed; actual embedded selector passed
  DX/Water/Air/all T190 selections. Build listing contains both aliases.

No save/protocol implementation, pins, dependencies, BLE policy or partition
layout changed. No flash, OTA, release, tag or full build matrix was performed.
Local compilation/host tests do not prove hardware operation or data retention.
The hosted selector is updated but was not dispatched as part of this repair.

See [build guide](BUILDING.md#t190-colour-edition-builds) and
[hosted-build notes](github-firmware-builds.md#t190-colour-dx--water--air-selection).
