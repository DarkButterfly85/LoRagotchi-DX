# Efficient rendering and menu-close settings

Game rendering offers Smooth (default), Simulation, and Efficient 1 FPS. Efficient changes only the aquarium render interval to 1000 ms, including Cardputer. Input-forced refreshes and alerts can render sooner. Pet age/care, radio servicing, and wall time are unchanged. This is not panel refresh safety: on e-ink, 1 FPS may still be unsuitable for the controller/panel waveform, ghosting, wear, or blocking refresh costs. No display driver or partial-transfer runtime option is changed.

## Apply, cancel, save

A picker is a draft until Select/Hold applies it in RAM; Back cancels only that draft. Non-identity preferences batch across the whole Options scope, including Display, schedule, sound, RF/GNSS, game and action children. Returning from a field/submenu does not close the batch. Leaving that scope, replacing the home screen, or display-off flushes accepted pending preferences. The loop checks before servicing and after input/display timeout. Display-off never confirms a draft; the existing draft can resume on wake. Controlled LoRagotchi shutdown/restart retains its final forced save attempt. Shared MeshCore restart paths are not intercepted.

Species/appearance confirmations, setup completion, mystery colours, adoption, breeding, hatch, reset, care/rewards and lifecycle saves retain immediate persistence paths. Because these share cfg, a required lifecycle/identity/timing write may also persist accepted preferences before menu close. Reset retains existing preference policy and does not confirm drafts.

## Durability limits

No fixed debounce deadline is added. Abrupt power loss before a successful save loses accepted preferences since the last successful cfg write. This window can last the entire open-menu session, unbounded if the menu remains open. Normal close attempts the write in that loop. Passive counters/Happy timing retain the five-minute checkpoint policy outside menus, with immediate care/transitions as before. Failed open/short writes retain dirty/failure state and retry at the existing five-second backoff; persistent failures make the window unbounded. Controlled shutdown makes a final backoff-bypassing attempt but still shuts down on storage failure. Ordinary FS replacement is not power-loss atomic; cfg/state are separate records, and NVS has different guarantees. Host RAM-FS checks are not physical power-cut proof.

## Format compatibility

Record sizes, signatures, offsets and species tails are unchanged. Existing byte 23 is 0 Smooth, 1 Simulation, 2 Efficient; invalid values load Smooth. Legacy 0/1 bytes stay exact; old firmware reads 2 as its existing nonzero Simulation mode. Host regressions cover legacy prefix/HAP1 bytes, both ESP32/nRF52 serializers, all 15 Water/18 Air species and pending/mystery/setup identities. No flash, push or commit is part of this change.

## Verification

All 35 `test/ui/check_*.py` scripts passed on the final source. Explicit one-job PlatformIO builds passed for `Heltec_v3_LoRaFish_companion_ble`, `Heltec_T190_LoRaGotchi_DX_ble`, and `Heltec_t096_LoRaFish_companion_ble` (ESP32 mono, ESP32 colour, nRF52). `git diff --check` passed. Logs, source hashes and the feature-only diff against the preserved pre-existing review snapshot are in `.local-dev/efficient-mode/`. No physical display, power/current, radio, or abrupt-cut hardware test was performed.
