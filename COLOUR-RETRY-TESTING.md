# Colour-preserving visit retries

This local DX test patch is based on `1867557903ecb9ae2193c6cb6fde5ca4d94ee813`
(the earlier community-return/+5 Happy work), not an independent patch on public
main. It changes the **sending DX fish firmware**, not LoRagotchi-RX or Aquarium.

## Reproduced defect

The production ACK handler sends `LFG1|COMMIT|tx|fish|C|5|4|2|65535`, but the old
three-second retry sent only `LFG1|COMMIT|tx|fish`. Dropping that first packet and
feeding the actual retry to RX produces a snapshot with mode M, all three colour
indices 6, and `appearance=false`. Aquarium correctly renders that fallback white.
This reproduces a mechanism matching the owner report; the owner's live packets
and saved database have not been inspected, so their exact loss sequence is not
claimed as proven.

## Fix and bounds

The first outgoing COMMIT's full appearance is cached in RAM, bound to the full
destination key, transaction and fish ID. Initial send and every retry use that
same packet. Changing local colour preferences during the handshake cannot alter
its appearance. A missing/mismatched cache never fabricates a colourless retry.
Each new visit replaces it; normal boot/session clearing still cancels travel.

No new wire format, flash write or persisted structure. Retry cadence and four-
retry budget stay unchanged. True monochrome fish and board-specific RGB565 tint
remain monochrome/tinted; the receiver's display type does not decide fish colour.
Shared MeshCore, radio settings, board pins, partitions and RX/Aquarium are untouched.

## Verification

- `python3 test/ui/check_dx_colour_retries.py PATH_TO_RX PATH_TO_AQUARIUM` exercises
  the actual sender ACK and UI retry handlers, drops the first colour packet,
  delivers retries into the production RX core, and decodes/saves the result with
  the actual Aquarium protocol and SQLite code. It also checks all four retries,
  immutable colour snapshots, peer/transaction guards, mixed alleles, tint and
  uint32 limits, the four-second return hold and repairing an old white copy.
- Existing DX handler, menu and emoji/navigation tests remain applicable.
- Native tests and V3, V4 OLED and T096 builds are recorded in the artifact manifest.
- Host mocks/build success are not proof of the owner's actual RF loss pattern.

## Device test

1. Update the **sending DX radio**, using its exact board image. Keep RX and the
   Aquarium app unchanged. No erase/reset is needed or requested; back up first.
2. Verify its local body/scales/eye colours are still correct, then send a **new**
   visit to RX. The already-saved white copy cannot recover missing genes without
   a new full-colour visit. No need to delete the tank or its SQLite database.
3. Aquarium should update the existing owner copy in place, not create a clone.
   Check purple/turquoise/yellow and confirm the original fish returns normally.
4. Re-share a monochrome fish and confirm it stays monochrome. Reconnect/restart
   Aquarium and check the saved appearance remains correct.
5. If a new share still appears white, inspect the saved appearance fields and
   the sender firmware revision before changing more code; that would require
   investigating a different path than the reproduced lost-first-packet case.

No source push, PR, release, flashing or live-radio action is performed here.
Rollback reference: the previous board-specific DX community-return `1867557`
image. That is a test baseline, not a claim of per-board hardware acceptance.
