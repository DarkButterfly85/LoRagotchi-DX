# L1 controls and SH1106 brightness follow-up

This focused branch builds on a7bae70 (the existing L1 Back fixes), retaining
8d480ef's centre single-click Select and dedicated Menu single-click Back.
Legacy double-click Back, hold-only cleaning/rescue, and triple-click quiet-mode
classification remain intact. Single-click recognition retains the existing
280 ms multiclick delay. See Getting_Started.md for the full controls.

## Brightness root cause and correction

The L1 and L1-1W use SH1106Display, which inherited DisplayDriver's empty
setBrightness(). The UI already saved the selected level and dispatched
64/128/192/255; no command reached the OLED. SH1106Display now overrides this
with Adafruit_GrayOLED::setContrast(), retaining a cached byte (default 255).

Adafruit SH110X 2.1.15's SH1106G::begin() resets contrast to 255 and finishes with
DISPLAYON. The wrapper therefore marks successful initialization as on and
reapplies its cache. Explicit wake also restores the cache. Brightness changes
before initialization or while off only update the cache. Power/contrast calls
are suppressed after failed probing or driver initialization, including failed
reinitialization. Existing configured-address/alternate-SA0 probing is retained.

The implementation is shared by SH1106 boards, not restricted to L1. Other
display implementations, board pins, RF behavior, settings format and save
bindings are unchanged. Contrast zero remains a contrast command, not power-off.
The menu percentages are contrast settings, not calibrated luminance percentages.

## Verification and physical checks

- python3 test/ui/check_sh1106_brightness.py compiles the real wrapper, mocks only
  the Adafruit/Wire boundary, and covers all 256 byte values, virtual dispatch,
  initial defaults, pre-init/off caching, wake, re-init, configured/fallback
  addresses, absent panels and failed initialization/recovery.
- The same script reruns the production board constructors, MomentaryButton,
  GPIO input dispatch, menu handlers, brightness application and dim branch
  against the real wrapper: L1/L1-1W x DX/Water/Air x sound/no-sound. It starts at
  the aquarium, checks all four saves, browse/cancel without writes, inactivity
  dim, activity restoration and wake-only input.
- The ordinary L1 GPIO suite also protects the existing Heltec V3/V4 mappings,
  stock immediate-click behavior, optional rows and guarded destructive actions.
- Focused hosted workflow: six L1/L1-1W edition builds plus ThinkNode M2 as a
  separate ESP32-S3 SH1106 consumer. Native/standalone host checks gate builds.

These are software checks, not physical acceptance. Test actual button debounce,
visible brightness at all levels, dim/wake, reboot persistence and sound on both
L1 hardware revisions. No release, merge, PR, automatic flash, or partition
migration is implied. Preserve a known-good backup before any later flash.
