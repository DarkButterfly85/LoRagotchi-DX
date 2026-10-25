# Juvenile genetic colour expression

Rendering-only change, based on `b8966f057a295339e6b37e7f31e732a04d0ba14d`
(the egg-adoption/H1 and hosted-build branch, PR #15). This branch retains that
parent; it is not an independent patch against an older main.

## Palette contract

Reuse `loRaFishColorValue` / `LoRaFishColour` conversion, including H1. Blend each
RGB565 channel with ivory `0xFFBC`, round to nearest, using eighths:

| Stage | Body | Tail / fins |
| --- | --- | --- |
| Fry | 2/8 primary + 6/8 ivory | 5/8 primary + 3/8 ivory |
| Young | 5/8 primary + 3/8 ivory | 6/8 secondary + 2/8 ivory |
| Adult / elder | Existing renderer | Existing renderer |

Juveniles have neutral contrasting ink/eyes and no secondary body markings.
The tail remains a simple outline; colour regions use mirrored body-local
coordinates. Cardputer's moving fin glint follows the juvenile fin palette.
Mono is not a hue: Mono components keep their existing theme colour. Fully
Mono fish, OLEDs, guest pixel tint and the temporary white return flash retain
the legacy path. Genes, saves, adoption, radio and lifecycle timing are unchanged.
Aquarium can use these blend weights with its own palette and art style; it
should not copy these tiny firmware silhouettes.

## Verification

Run `python3 test/ui/check_juvenile_rendering.py`. It compiles extracted production
C++ drawing functions against a host RGB565 framebuffer, including real stage,
home and travel wrappers. No Pillow or other third-party Python dependency.

- All 246 chromatic alleles, four themes, two juvenile stages, three renderer
  styles (classic, T-Deck, Cardputer); mirrored classic sprites, translated
  regions, neutral eyes, body/tail colours and mixed Mono genes.
- 1,440 original adult/elder/OLED/Mono/guest-tint/flash pixel signatures, checked
  independently against the committed parent source.
- 1,440 travel frames across clipping/entry/exit and the Cardputer glint phases,
  plus home wrapper equality and animation expiry.
- Existing lifecycle, egg menu and menu-navigation host checks pass.
- Existing standard GitHub workflow discovers this `check_*.py` automatically.

`--preview-dir PATH` exports production PPM frames, not artist mockups. The
fixture refresh option is maintenance-only: use verified pre-change source,
never a changed renderer to bless a regression.

No new board firmware compilation or physical-display test was performed for
this local change. Compilation stays on GitHub per the owner's current workflow;
publication, CI build results and hardware acceptance remain separate steps.
The reported hardware white-only appearance was not reproduced: the parent
source already passes genetic colours into juvenile sprites. This patch delivers
the requested age-based look, not a confirmed diagnosis of that device state.
