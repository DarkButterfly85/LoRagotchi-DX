# Pet senses: mesh weather

*Colour screens get the full sparkle. Small black-and-white (OLED/LCD) screens get a tiny one. E-ink screens get no animation at all, by design.*

The pet notices when the mesh **suddenly gets much busier than it has been lately**, and
gives a brief sparkle. It uses the packet counts that [RF Monitor+](RF-MONITOR-PLUS.md) already
keeps: the total of each of the last 32 finished minutes.

## The rule (relative, not fixed)

A sparkle happens when the minute that just finished had

- **at least 2.5 times** as many packets as the mesh's own average over the previous 30 minutes, **and**
- **at least 8 packets** (so a quiet mesh going from 1 packet a minute to 3 does nothing).

Because it compares the mesh with itself, it behaves the same on a quiet country mesh and a busy city one.

- **Warm-up:** nothing sparkles until 10 earlier minutes exist to compare with (so, not in roughly the first 11 minutes after power-up).
- **Once per jump:** a sparkle fires when the mesh *jumps*, not while it stays high. A mesh that stays busy gives one sparkle.
- **Cooldown:** at most once every 3 minutes, however noisy the mesh is.
- The check is made once per finished minute, and only while the aquarium page is showing the awake pet. Eggs, sleeping pets, pets that are away, memorials and visits never sparkle.

## What you see

| Screen | Sparkle |
|--------|---------|
| Colour (T-Deck, Cardputer, Heltec T190 and the other colour displays) | three small yellow twinkles around the pet for about 5 seconds |
| Small black-and-white OLED/LCD (e.g. 128x64) | one tiny white plus (5 pixels) for about 1 second, then a single dot for a moment, then gone |
| E-ink | nothing, ever (no animation by design) |

The black-and-white sparkle sits in the **top-left corner of the tank**, just under the header line
(or the **top-right corner** if the pet happens to be swimming near the left). It stays clear of the pet, the
title, clock and battery in the header, the centred message rows, the poop spots, the rising bubbles
and the status bar at the bottom. If a visiting pet is on the tank, or the pet is near both corners, it is
simply not drawn. Whenever no sparkle is active, a black-and-white screen draws exactly what it always did.

**E-ink gets no animation, by design.** E-ink is for still images, so it never gets a sparkle or any
other moving effect. This is built in, not a setting: the sparkle code is left out of every e-ink
build entirely (Heltec Mesh Pocket and the other e-ink boards), and a second check at run time stops
it too. There is no option or switch to turn it on, and an e-ink page is drawn exactly as it would be
if the sparkle did not exist.

## What it does not do

It is purely presentational. It is not saved (the sparkle state is 12 bytes of memory and the
minute totals 64 bytes; both are gone after a restart), does not change the save file, any radio packet,
or how packets are received, forwarded or answered, and has no effect on food, growth, breeding or visits.

## Tuning

The constants at the top of `examples/companion_radio/LoRaFishMeshWeather.h` are the only thing to tune:

| Constant | Now | Meaning |
|----------|-----|---------|
| `SPIKE_TENTHS` | 25 | how many times the usual (25 = 2.5x) |
| `SPIKE_FLOOR` | 8 | the minute must have at least this many packets |
| `BASELINE_MINUTES` | 30 | how many earlier minutes make up "the usual" |
| `MIN_BASELINE_MINUTES` | 10 | earlier minutes needed before any sparkle |
| `COOLDOWN_MS` | 180000 | least time between sparkles |
| `SPARKLE_MS` | 5000 | how long the colour sparkle lasts |
| `MONO_PLUS_MS`, `MONO_DOT_MS` | 1000, 300 | the black-and-white plus, then the dot |

Written from scratch for LoRagotchi-DX. Test: `python3 test/ui/check_mesh_weather.py`.
