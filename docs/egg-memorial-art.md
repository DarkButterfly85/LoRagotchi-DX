# Egg and memorial art (2026-11-06)

- Speckled egg with five real age-minute crack stages (0/20/40/60/80%). Initial eggs use age 0..5; successor eggs use deceased age minus lifespan. Visitor-bred eggs deliberately do not appear to incubate before death: the existing succession clock starts at death, not breeding.
- Four warming animation phases: planted-base shear/tilt plus a small glitter cross. Animation time is captured once before strip composition. Pixel routines read no clock, mutate no lifecycle state, use no RNG and perform no storage writes.
- Stable vivid shell hue and speckles hash existing persisted seed/generation/species/traits. This is pseudo-random identity variation, not fresh entropy. Append-only ART1 settings persist actual Mystery provenance and deceased art; original prefix, species, lifecycle state and wire fields are unchanged. Legacy seed-zero saves receive deterministic art too.
- Mystery glyph is hand-pixelled and protected from cracks. Only explicit Mystery selection enables it. Mystery colours alone never do; explicit species selection clears it even for the same seeded species. Successor, adopted and reset eggs clear it. Missing, truncated or invalid ART1 defaults honestly to non-mystery rather than guessing.
- Three memorial silhouettes: rounded stone, stepped obelisk, winged marker. Deterministic deceased identity selects variant and egg side, stable from death through reboot. Body hue fills the marker; scales colour supplies the inset diamond. Theme contrast overrides identical fill/ink. Eye trait participates in stable selection but is not painted as eyes on a grave.
- All art occupies rows 22..46 on 128x64 with two separated 36-pixel-spaced centres; footer starts at 49. One-bit panels use background-filled interiors and foreground outlines, RIP and ornaments, including light theme.

## Compatibility / tradeoffs

ART1 appends 16 bytes at offset 90 (106-byte settings record): magic, provenance/snapshot flags, little-endian art key, body/scales colours, version/reserved and CRC16. Earlier settings extensions remain unchanged. Death snapshots freeze variant, side and colours before later appearance edits, including existing visitor-bred eggs. Transition persistence uses existing retries, never per-frame writes. Old memorial saves freeze their currently available identity once; historical pre-edit identity is unrecoverable. Separate settings/state files remain non-atomic under power loss, as before. Generation saturation can repeat art.

Cracks follow authoritative whole-minute simulation progression, not smooth wall time; animation remains cosmetic. Existing tall-screen countdown and other render routines retain their pre-existing clocks. This patch only snapshots these new life-art animations; it does not refactor unrelated strip renderer timing.

Full safe pre-edit copy: sibling directory loragotchi-visuals-safe-20261106-1956 (complete copy including local build files; source was edited with exact replacements, never reconstructed from capped tool output).

## Verification

Production C++ pixel helper is compiled with warnings-as-errors and UBSan by test/ui/check_life_art.py: all three variants, five crack stages, four phases, mystery glyph protection, 128x64 bounds, repeatability, identity variation and strip replay equivalence. Existing check_fish_lifecycle.py exercises production save/load and lifecycle functions under both ESP32 and NRF52 RAM files, including old memorial recovery, visitor egg, reset, multi-generation and delayed ticks. No physical device, flash or visual panel measurement is implied.

Verified builds: Heltec_t096_LoRaFish_companion_ble (nRF52: RAM 149740, flash 511532 bytes), Heltec_v3_LoRaFish_companion_ble (ESP32: RAM 174748, flash 1337057 bytes). Both succeeded. Relevant host checks passed: life_art, fish_lifecycle (both storage branches), local_savings, egg_adoption, egg_menu, juvenile_rendering, water_rendering, air_rendering; git diff --check clean. Savings extraction fixture was extended to include the new timestamp declaration. Logs and a visually inspected 12-frame production-pixel contact sheet are under .local-dev/life-art/. T190 driver was not touched, and no commit/push/flash was performed.

## Independent-review correction

Pre-edit source backup: ../loragotchi-provenance-preedit-20261106.tar (excludes generated .pio/.local-dev and .git). Exact edits preserve existing work. Correction tests/build logs: .local-dev/provenance-review. Host checks passed: real lifecycle/save/load on ESP32 and NRF52, explicit/colour-only/same-species selection through production menu handlers (DX/Water/Air; sound on/off), missing/truncated/corrupt ART1, successor/reset/reload, real memorial art-key stability after appearance edits, dying with an existing visitor egg, bounded writes, pixel/strip rendering, adoption, edition and juvenile/Water/Air render regressions. No commit/push/flash; physical hardware and power-cut testing remain outstanding.

Correction firmware matrix PASS (one compile job, serial): Heltec_v3_LoRaFish_companion_ble, heltec_v4_LoRaFish_companion_ble, Heltec_t096_LoRaFish_companion_ble, Heltec_T190_LoRaGotchi_DX_ble. This supersedes the earlier two-target art verification for the corrected source. LFM1 migration is explicitly regression-tested on both storage branches. Full baseline-source comparison found exactly six intended source/docs files changed (UITask.cpp, three host tests and two status/art docs); all other source work was preserved.
