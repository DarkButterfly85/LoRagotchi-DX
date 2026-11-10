# LoRagotchi Land — early scaffold (draft art)

A habitat edition mirroring Water and Air. **Not a released or hardware-tested
firmware; sprite art is first-pass procedural placeholder art.** Only land_* /
LORAGOTCHI_LAND_EDITION=1 select Land. Defining more than one habitat flag is a
build error. Breeding stays same-species-only.

## Registry

Land owns **512..550**, permanently, in the owner's list order (Water 0..14 and
Air 256..273 are unchanged; everything else stays reserved/opaque). The
owner's brief said 34 animals, but its list contains 39 (28 land, 5
amphibious, 6 mythic); all 39 are registered. Unshipped IDs can be trimmed
before any release.

| IDs | Species |
|---|---|
| 512-539 | Dog, Cat, Horse, Cow, Elephant, Pig, Ram, Sheep, Goat, Giraffe, Kangaroo, Llama, Deer, Mouse, Hamster, Rabbit, Hedgehog, Koala, Panda, Sloth, Otter, Skunk, Badger, Hippo, Rhino, Camel, Bactrian camel, Bison |
| 540-544 | Frog, Crocodile, Lizard, Turtle, Snake |
| 545-550 | Unicorn, Dragon, Dragon face, Phoenix, Sauropod, T-Rex |

(IDs are consecutive in the order shown: Dog=512 ... TRex=550.) The
docs/number_allocations.md table covers MeshCore group data types, not species IDs.

## Behaviour

- **Gate:** editionKnown accepts Land IDs only in Land builds; Water/Air builds
  are unchanged and never draw a Land ID.
- **Wire:** the species extension is unchanged. A Land build answers a visit
  request with ACK "...|S1|L1"; a Land pet is only sent with its real ID to a
  peer that advertised L1, otherwise it visits as the legacy fish (same
  fallback as Air without A1). Water/Air peers still parse the ACK as an S1 ACK.
- **Motion:** shares the Air habitat model; most species walk, reptiles/amphibians
  crawl, Dragon/Dragon face/Phoenix fly.
- **Sniff (pilot):** 29 Land walkers (all Walk animals except Koala and Sloth) sometimes slow to
  30% speed with the nose down for 1.2-2.4 s during a walk, then walk on. The head-down picture is
  drawn by shearing the head columns of the normal frame (table `sniffTable` in LoRaFishSpecies.h),
  so it adds **no** art bytes. It is also shown on e-ink (different frames, not more frames; no
  sparkle). Presentation only: no save-file or radio change.
- **Art:** tools/land/generate_sprites.py writes ui-new/LoRaFishLandArt.h
  (39 x 2 frames x 192 bytes = 14976 bytes ROM). All 39 sprites are draft.
- **Discovery:** the Land animal emoji (except Phoenix, which has no single
  emoji) are discovery hints in Land builds only; shown as [L] on small displays.

## Targets

land_* aliases cover the same 16 boards as water_*/air_* and live in
variants/loragotchi_land/platformio.ini (picker); see BUILDING.md.
Checks: test/ui/check_land_registry.py, test/boards/check_edition_targets.py.
