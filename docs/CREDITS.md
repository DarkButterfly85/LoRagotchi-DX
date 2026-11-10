# Credits

LoRaGotchi-DX is built on MeshCore and on work by other people. This page
lists who made what, so the credit stays with them.

## Original author

- **Robert Rayner (M0YNW)**, original LoRaGotchi author.

## MeshCore

LoRaGotchi-DX is built on MeshCore firmware, copyright (c) 2025 Scott Powell /
rippleradios.com, released under the MIT License (see `LICENSE` and
`license.txt`).

## LODESTAR ORION and LODESTAR NOVA

Ideas and code from these projects are used in LoRaGotchi-DX, with the
permission of their authors. Aries Thorne confirmed in writing on 2026-11-09,
in the public LoRaGotchi Discord channel:

> "Yes, I am very happy with this and Todd and I would be honored if you used
> whatever code you need from Nova / Orion."

(Discord message 1569352241851273331 in channel 1510581740974903436.)

- **Aries Thorne** and **Todd Steinhauer**, creators of the LODESTAR ORION
  firmware and the LODESTAR NOVA web dashboard.
- **Wolf Reactive Systems / FEAR REACTIVE**, the studio behind LODESTAR ORION,
  which made the original 1-bit emblems and artwork used in those projects.
  (Listed under both names for now; the studio's preferred name is to be
  confirmed with Aries Thorne.)

Where we have rewritten an idea rather than copying code, we still credit the
original. Where code or artwork has been copied, its header comment keeps the
original attribution.

Features taken from or inspired by ORION:

- Bedtime quiet (silent messages while the pet sleeps)
- Power-safe pet save with a backup copy
- Accurate battery percentage and time-left estimate
- Range check and RF monitor
- Land species Wolf, Fox, Bear, Kitsune and Griffin, drawn as a visual take on
  the ORION wolf and creature art (no code or packets copied)
- Natural idle motion and the nose-down sniff, based on the ORION wolf's motion
- USB and web dashboard (planned, colour screens)
- Trip tracking and wardriving (planned, GPS boards only)

The Nova dashboard sync in our fork (`lodestar_nova_alpha`) is also built on
LODESTAR NOVA by Aries Thorne and Todd Steinhauer, with the same permission.
