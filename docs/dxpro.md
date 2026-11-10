# DX-Pro edition

One firmware with the Water (0-14), Air (256-273) and Land (512-554) species sets together.
Branch: `feat/dxpro-combined-edition`. Design source: `docs/creature-compatibility.md` section 5.

## What it is

- Build flag `-D LORAGOTCHI_DXPRO=1` (default 0). It cannot be combined with
  `LORAGOTCHI_WATER_EDITION`, `LORAGOTCHI_AIR_EDITION` or `LORAGOTCHI_LAND_EDITION` (compile error).
- Targets: `dxpro_<board>` for the 16 screen boards, in `variants/loragotchi_dxpro/platformio.ini`.
  Each is the matching `water_<board>` target plus the DXPRO flag and nothing else.
- Species IDs, save format (SPC1, 18 bytes) and wire strings are unchanged.

## Menu

Two steps. Choosing the species first opens **ANIMAL SET** (Water / Air / Land), then the species list of
that set (with "Mystery egg" on a new pet). Only the species ID is stored; the set is derived from it.
Mystery egg draws inside the chosen set with the same formula a single-set build uses.
Back cancels the whole choice.

## Behaviour

- Sprites: Land, Air or Water art by the species' own set.
- Home scene follows the owner's pet: Air sky, Land meadow, Water tank (bubbles, reeds).
- Water surface/underwater bands apply to Water pets only, and still only where two adult sprites fit.
- Discovery markers: all Water, Air and Land emoji count.
- Breeding: any known species, same-species only (unchanged rule).
- Host ACK: the legacy ACK of the host's *current pet's* set (`S1`, `S1|A1`, `S1|L1`), so a visitor of
  another set arrives as the fish until the capability token (design section 3, phase 1) exists.

## Not included

- The visit gate (`canVisit`, "only swimmers visit water hosts") and the `C1` capability token are
  not implemented; they are steps 1, 2 and 5 of the design's implementation order.
- No firmware build, flash or hardware run was done for this branch; checks are host-compiled.
