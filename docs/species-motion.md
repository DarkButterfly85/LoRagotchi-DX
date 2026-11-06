# Species motion

Presentation-only choreography in `LoRaFishSpecies::habitatPosition` now applies to home pets and visitors in DX, Water and Air. Stable species IDs and all save/wire formats remain unchanged. Shell-dweller (ID 12, existing snail-like art) glides slowly along the floor; crab (ID 9) scuttles sideways in short bursts with rests; jellyfish (ID 11) drifts horizontally and rises quickly then settles slowly. Stage adjusts horizontal speed.

Existing generic Water swim/wander and Air paths remain unchanged. The common hook runs before feeding, so feeding still overrides normal movement; sleep, travel/arrival/departure and rendering retain their existing precedence. Wander mouth bubbles are suppressed for these three animals. No additional mutable state, allocations, random calls or persistence writes are introduced.

The compact scene reserves 20-pixel side margins, grounded centre y=37, and jellyfish centre y=30..36. Adult water art remains at most 32x24. This is existing compact scene geometry, not a new native-resolution layout. Unsigned 32-bit clock/visitor-offset addition stays defined at rollover; absolute animation phase resets at millis wrap just as existing stateless animation does.

`test/ui/check_species_motion.py` compiles the production helper with UBSan for DX/Water/Air, sweeps stages/widths/offsets, checks grounded versus pulse motion, scuttle rests, speed/direction, rollover, legacy no-ops and Air parity. UI hook/order assertions supplement existing production lifecycle/render tests; they are not physical display/RF validation. Logs and restored-before-motion snapshot are in `.local-dev/species-motion`.

Important preservation caveat: UITask.cpp was accidentally truncated during this task, then reconstructed by the parent from retained evidence. `.local-dev/truncation-recovery/README.txt` describes recovery and its limits. Motion diffs after recovery are separately reviewable against `UITask.restored-before.cpp`; complete pre-accident source equivalence is not claimed.
