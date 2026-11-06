# Pet/UI follow-up — 2026-11-06

## Baseline and preservation
Task checkout: projects/loragotchi-dx-pet-followup-20261106, branch fix/pet-followup-20261106.
Exact fetched owner main: 3a23f92c092584145149c990a1c83aca32ca4a0e (Anglerfish PR #19 merged). Local main remains 213ced5; original checkout remains fix/efficient-aquarium at b8966f0 with dirty experiments. The followup path did not exist when inspected; this isolated worktree was created from owner main, not the obsolete dirty branch. No existing worktree reset, cleaned, rebased, staged, committed or deleted. No push, flash or upstream-original fetch.

Final read-only remote recheck: main advanced to 9a2810fb15dedc71ee862baea69895242bc7b929 (PR #34 merge). Its complete tracked tree is identical to the task baseline (git diff HEAD..origin/main empty); no rebase or source reconciliation needed.

## Implemented
- Explicit shared marker/label positions for Display, Pet Setup, Colours, Schedule, Timeout and Sound; measured gutter supports advancing and stationary ST7789 print. Driver semantics unchanged.
- Pet-neutral menus/start/ready/travel and habitat-list messages. Fish fallback wording retained where describing real legacy fish fallback. Protocol identities, storage paths and API names unchanged.
- Sleep/Wake/UTC: physical one-button double-click flips +/-, click steps, hold saves, triple-click cancels. Reopening resets to +. Dedicated Back/keyboard/touch cancel, not reverse; literal left/right remain literal. UTC stays -12:00 to +14:00 in 15-minute steps. Direction/cancellation never persist drafts.
- Production-handler tests cover advancing/stationary print, mono/colour menus including Pet Setup, negative UTC save, positive UTC cancellation, wraparound and genuine Back. Existing entrypoint/wake/guard/optional-row checks retained.

## Follow-up implementation status (updated after independent review)
- Habitat policy resolved: preserve legacy-compatible visits and existing Water/Air discovery/adoption/breeding behavior, including Air accepting Water discovery markers. Added a cancel-default warning before REQ for all peers: pets may appear differently on older/other habitats. Emoji are discovery hints, not proof of habitat; no home-species or protocol changes. See legacy-visit-warning.md for behavior and host regression coverage.
- Species motion, egg/memorial art, runtime orientation/update controls, efficient rendering and experimental T190 colour are implemented in this worktree. See species-motion.md, egg-memorial-art.md, runtime-display-orientation.md, runtime-display-updates.md, efficient-rendering-and-menu-save.md and t190-colour-experimental.md for exact scope and limitations.
- Independent-review correction persists honest Mystery-selection provenance and immutable deceased art in append-only CRC-checked ART1. Legacy saves default non-mystery; existing visitor eggs remain intact. Death snapshots persist once per transition, never per frame.
- Physical panel appearance/orientation/wake, button timing, RF and power-cut durability remain unverified without hardware. Host checks and compilation do not establish these.

## Completed verification
- Final exact-source firmware builds PASS: Heltec_v3_LoRaFish_companion_ble, heltec_v4_LoRaFish_companion_ble, Heltec_t096_LoRaFish_companion_ble, Heltec_T190_LoRaGotchi_DX_ble (one compile job, serial).
- Native/native_kiss_modem: 117/117 cases PASS.
- Production menu harness PASS in DX, Water and Air, each with sound on/off and mono/colour plus advancing/stationary text semantics.
- Focused checks PASS: L1 buttons, T-Deck merged routes, egg menu, editions, Air discovery/adoption/rendering/menu/end-to-end and Anglerfish assets. Final wording changes rechecked through menus, L1/T-Deck/egg/discovery/end-to-end.
- git diff --check PASS. Source hashes and review.patch in .local-dev/pet-followup. No commit/push/flash.

## Evidence
.local-dev/pet-followup contains individual host/build logs. Mock text bounds/handler checks are not physical fonts, panel, OneButton timing or RF proof. No attached/flashed hardware. Final task report lists completed checks; partial logs are not success.

## Review correction evidence

Exact-source correction logs are in .local-dev/provenance-review. Pre-edit backup: ../loragotchi-provenance-preedit-20261106.tar. No publication, commit or flash performed.

Review correction verification PASS: lifecycle/save/reload and LFM1 migration on ESP32 + NRF52; pixel/strip art; savings/retry/legacy-prefix checks; production menus in DX/Water/Air with sound on/off, explicit same-species selection after Mystery and Mystery-colour-only behavior; egg/adoption/edition checks; juvenile/Water/Air rendering; L1 buttons. Corrected-source firmware builds PASS for Heltec_v3_LoRaFish_companion_ble, heltec_v4_LoRaFish_companion_ble, Heltec_t096_LoRaFish_companion_ble and Heltec_T190_LoRaGotchi_DX_ble. git diff --check PASS. Hardware and non-atomic multi-record power-loss limitations remain as documented in egg-memorial-art.md.
