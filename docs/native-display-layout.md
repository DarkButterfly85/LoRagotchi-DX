# Native-pixel LoRagotchi layouts — local implementation, 2026-11-07

## Provenance and preservation

Worktree: projects/loragotchi-dx-pet-followup-20261106, branch fix/pet-followup-20261106, starting HEAD 53efe2e0780265a5b971b5a59782c664826fa703. Initially clean. Read-only remote inspection/fetch found main 84ce7f9ef9134c683739df1c902a1fc32abc64c6; its tracked tree is identical to starting HEAD (git diff --quiet HEAD origin/main returned 0). No merge/rebase/reset, commit, push, flash, radio operation or publication. Other worktrees and hardware paths preserved. The project vault's prior multi-display and transport notes were consulted. The available project graph returned no matching LoRagotchi nodes; direct source inspection supplied the evidence.

## What changed

LORAGOTCHI_NATIVE_UI is explicitly enabled for T190 DX (inherited by Water/Air), V4/V4-R8 TFT DX and both existing T114 LoRaFish declarations. Generic companions, OLED, T096, T-Deck and T-Watch retain their existing coordinate/input paths.

ST7789LCDDisplay reports its actual drawable geometry from panel dimensions and baseline rotation: T190 320x170, V4 TFT 320x240, T114 240x135. Native builds use one panel pixel per coordinate/primitive pixel. Text, XBM and rectangles no longer undergo independent fractional enlargement. Native layout does not change SPI buses, speed, power polarity, init offsets, orientation baseline, backlight or radio wiring.

The existing scene/state, menus and Adafruit renderer are reused rather than introducing another UI framework. LoRaFishLayout::Region supplies bounded translation/clipping, not framebuffer scaling. Presentation remains exclusively the real display driver's responsibility.

- Habitat uses native width/height, with fixed-size art. Whole home/guest movement, feeding targets, sleeping sprites and egg/memorial assets move into the taller body's centre without stretching their individual pixels. Header/footer remain edge-anchored.
- Panels at least 288 pixels wide reserve a 112-pixel information rail alongside the habitat: age, generation, happiness, RF/messages/ACK and BLE status. Counter text is width-bounded; it cannot overlap the habitat. Narrower T114 uses the full width for habitat.
- Menus, pickers and notices are centred cards, up to 224x64 pixels. This is deliberate compact content layout, not a 128x64 framebuffer scaled over the panel. Existing row spacing, selection semantics and input handlers are retained. Menus do not yet expand to more simultaneous rows.
- Existing T190 full/partial RGB565 final-row comparison and allocation fallback are retained. T114 retains 16-row band rendering and its existing transport budget. Native mode is not a throughput/power improvement claim.
- Orientation remains existing 0/180 mounting-relative behavior, not a new portrait/landscape switch. T-Deck/T-Watch touch transformations are unchanged and those targets are not enrolled in native mode.

## Pixel size is not physical size

This implements **same asset/font pixel dimensions**, not calibrated millimetre dimensions. Physical equality depends on actual active panel width/height, pixel pitch and font metrics. The source proves resolutions, not measured active millimetres. Do not infer physical equality from diagonals or resolution alone.

T096 remains 160x80 physical with its existing 128x64 logical compatibility path: coordinates/rectangles scale 1.25, but text size is passed through and XBM dimensions are not scaled. Thus there was never one uniform physical scale shared by every T096 UI element. V3 is a different 128x64 OLED/font path. One T190 pixel need not equal one V3 pixel in millimetres, and unchanged T096 primitive artwork can still differ in size from native T190 artwork.

For exact side-by-side physical matching, the remaining product decision is whether to calibrate to T096 text/art, V3 text/art, or a chosen millimetre size. Obtain active panel dimensions or a ruler photograph and choose the reference before adding density-specific integer assets/fonts. Do not restore fractional whole-screen enlargement to simulate physical matching.

## Verification

Bounded host checks, not hardware appearance/timing proof:

- check_native_layout.py: actual production T190 driver, native dimensions, text width, exact 1:1 XBM/rectangle footprints, bottom/right edges, clipped regions, unchanged-frame suppression, full/partial clearing, orientation/wake and allocation fallback.
- check_native_menus.py: actual production menu functions through native regions at 320x170, 320x240, 240x135 and 128x64; DX/Water/Air, all selections, glyph bounds/overlap, mono/colour and stationary/advancing text behavior.
- check_native_compositor.py: actual production native compositor with recorded scene dispatch; native habitat/rail dimensions, cards, notices/setup, maximum counters and non-overlapping glyph bounds. This is not a full aquarium simulator.
- Existing menu navigation, T190 compatibility-colour/partial, juvenile legacy pixels (1440 signatures plus travel cases), life art, species motion and T-Deck touch-route checks pass. The species hook assertion was updated for the native body offset; production species motion remains unchanged.
- Exact-source firmware builds: T190 DX, Water T190, Air T190, V4 TFT DX, T114 LoRaFish, V3 and T096 all SUCCESS. V4-R8 TFT and T114 serial-test native declarations are source-configured but not separately built in this matrix.
- git diff --check passes. Logs: .local-dev/native-ui/.

No physical display, RF, power/current measurement, full native screenshot golden suite, T114 flicker/stability acceptance or millimetre calibration was performed. Native rollout to other display classes (Cardputer/LGFX/e-ink) and touch-native layouts is not implemented; their existing behavior is preserved. Hardware acceptance should cover every native target's readability, RGB primaries, edge coverage, home/visitor/feeding/travel/death states, all menus, 180-degree rotation, full/partial or strips, off/wake and RF/BLE load.


## Independent-review correction

The review found the existing no-PIN pairing hint at y=63 would be omitted by a 64-pixel-high native card. It now uses y=56 (the complete 8-pixel glyph row fits); the PIN label moved from y=45 to y=47 to clear the 16-pixel PIN glyph row. Input/security behavior is unchanged.

check_native_pages.py now renders the actual production pairing (PIN and no PIN), stats, clock (valid/fallback), RF/battery/history, GNSS (receiver/on/fix combinations) and all three startup notices through the native cards, in DX/Water/Air variants. Assertions check glyph bounds/overlap and explicitly require the pairing/dismiss/toggle hints to be present, rather than accepting silent clipping.

check_native_t114_strips.py compiles the real native T114 driver against recording panel/canvas boundaries. Rectangles, region translation/clipping, XBM and actual production animated bubbles are compared pixel-for-pixel with a full-frame reference across all 240x135 pixels, including y=15/16, y=31/32 and final y=128..134. It requires eight 16-row transfers plus one 7-row final transfer and repeats after orientation/wake. The scene is a bounded test pattern plus production bubble animation, not a full native aquarium screenshot.

The review also exposed that only life-art animation had an immutable timestamp. A scoped pet-render clock now covers all existing pet millis() call sites during frame composition, while handlers outside rendering and the task scheduler retain the live clock. The T114 test advances its live clock between bands and verifies the production bubble frame remains identical across them; the scope releases between frames. This does not eliminate repeated scene evaluation or establish hardware tearing/performance behavior.


Reviewed-source verification completed: all seven firmware environments above rebuilt successfully after the pairing/frame-clock changes (review-build-matrix.log). Twelve focused host scripts passed: native pages, T114 strips, native layout/menus/compositor, menu navigation, species motion, life art, local savings/persistence, T-Deck routes, Air rendering and juvenile legacy pixels. The life-art and local-savings fixtures now consume/assert the actual new render-clock scope. git diff --check passed; reviewed firmware source hashes are recorded in .local-dev/native-ui/source-sha256.txt. No push, commit or flash.
