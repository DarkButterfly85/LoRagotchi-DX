# M5Stack Cardputer

The M5Stack Cardputer is a keyboard-driven ESP32-S3 handheld with a small colour
display, here fitted with an SX1262 LoRa Cap. This page collects what is specific to
the LoRaGotchi-DX builds for it. For a short walk-through see the
[Cardputer getting-started guide](cardputer/GETTING_STARTED.md); general setup is in
the [main Getting Started guide](../../Getting_Started.md).

**Status:** standard DX profile; see
[Compatibility and test status](../BUILDING.md#compatibility-and-test-status).
Hardware functionality of the merged Cardputer display build has not been
independently verified (see [Build notes](#build-notes)).

## Builds

| Edition | Environment |
| --- | --- |
| DX | `cardputer_loragotchi` |
| Water | `water_m5stack_cardputer` |
| Air | `air_m5stack_cardputer` |
| Land | `land_m5stack_cardputer` |
| DX-Pro | `dxpro_m5stack_cardputer` |

All produce an ESP32 application BIN. Hardware layer: SX1262 LoRa Cap
(NSS 5, DIO1 4, reset 3, busy 6, MOSI 14, MISO 39, SCLK 40), `default_8MB.csv`
partitions, 350 contacts, 40 channels, a 256-entry offline queue, and the screen
auto-off set to 30 seconds (AUTO_OFF_MILLIS). Estimated flash use of a DX build is about 1,496,105
bytes of 3,342,336 (44.8%), see [creature compatibility](../creature-compatibility.md).

## Keyboard controls

The Cardputer uses its keyboard instead of a single button:

- **Navigate:** arrows (Fn + `;` / `.` / `,` / `/`) or **W / A / S / D**, which work
  without holding Fn. Right or down = next, left or up = previous.
- **Select:** Enter or Space (the equivalent of a long-press).
- **Back:** Escape or Backspace (the equivalent of a double-click).
- Menu footers show **1:NEXT 2:BACK L:OK** for the three single-button gestures;
  the keyboard replaces them as above.

## Display

- 240x135 colour display, drawn through a 16-bit framebuffer; landscape orientation.
- Colour 2.5D aquarium scenery (water, light, reef, sand and seaweed, fish shading).
  The moving fin glint follows the juvenile fin palette
  ([JUVENILE-COLOURS.md](../../JUVENILE-COLOURS.md)).
- The **Efficient 1 FPS** game-rendering option also applies to the Cardputer
  ([efficient rendering](../efficient-rendering-and-menu-save.md)).
- Air uses a sky/ground scene rather than the Cardputer/T-Deck reef art
  ([AIR-EDITION.md](../../AIR-EDITION.md)).
- Runtime display rotation is not offered on the Cardputer
  ([runtime display orientation](../runtime-display-orientation.md)).

## DX visits

The Cardputer persists reserved and present DX guest state, and a Cardputer that is
already occupied answers BUSY to a different fish
([v0.4.5 reliability notes](../development/LORAGOTCHI_DX_V045_RELIABILITY.md)).

## Build notes

[CARDPUTER_MERGE_NOTES.md](../../CARDPUTER_MERGE_NOTES.md) records the Cardputer
merge: the Cardputer ColorVal display fix added `boards/m5stack_cardputer.json`,
`variants/m5stack_cardputer/*` and `src/helpers/ui/M5CardputerDisplay.{h,cpp}`, with
the existing source (including `ui-new/UITask.cpp`) left unchanged. It states that
the PlatformIO build and hardware functionality were **not** independently verified
for that base.

## Credits

The Cardputer hardware port comes from the working v0.4.4 build, and the display
uses the M5Cardputer library by M5Stack. The repository does not record an
individual author for the Cardputer port or the ColorVal display fix; see
[Credits](../CREDITS.md).
