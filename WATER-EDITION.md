# LoRagotchi-DX Water — v1.1.0 source candidate

> **Air coexistence:** the new shared sender also recognizes an exact S1|A1 ACK.
> Water still advertises S1 only and keeps IDs 0..13, existing saves, mystery
> outcomes and artwork. Stored Air IDs are preserved but render as fish; outgoing
> Air IDs require A1 and otherwise explicitly visit as fish. Pre-Air Water
> senders remain strict-S1 and conservatively send legacy fish to an Air peer.
> See [Air interoperability and validation gates](AIR-EDITION.md).

Water edition in the shared LoRagotchi-DX repository; not a published
firmware release. The underlying MeshCore remains **v1.18.0**; this is not LFG2
or MeshCore 1.19. Host tests do not imply board binaries, hardware acceptance
or release publication.

## Edition and version selection

`LoRaGotchiVersion.h` defaults `LORAGOTCHI_WATER_EDITION` to 0 (DX).
The explicit `water_*` aliases set it to 1. Product candidate v1.1.0 is the
version already present in the owner's unfinished upload, not an invented release.
The boot label and current README use that header's product version; MeshCore's
separate FIRMWARE_VERSION and historical release documents are not renumbered.

DX hides species selection/setup and renders the original fish. DX does not
advertise S1 capability; when sending to an S1-capable peer it identifies itself
as tropical fish. Water retains species negotiation/art/chooser. Loading Water
settings in DX preserves species/seed bytes, but suppresses an unfinished Water
chooser; a later DX settings save clears its pending flag. This is a display
fallback, not full lossless cross-edition gameplay: a DX reset starts a fish egg.

## Catalogue and controls

Registry **Water v1**, permanent unsigned 16-bit species IDs:

| ID | Species | ID | Species |
|---:|---|---:|---|
| 0 | Tropical fish (existing evolution art) | 7 | Squid |
| 1 | Blowfish | 8 | Lobster |
| 2 | Shark | 9 | Crab |
| 3 | Dolphin | 10 | Octopus |
| 4 | Whale | 11 | Jellyfish |
| 5 | Seal | 12 | Shell-dweller |
| 6 | Shrimp | 13 | Sea star |

All 14 approved concept-sheet animals are included. Sizes are stylised, not
biological scale. This is a habitat edition, not a separate mono/colour firmware
architecture. No species-based visiting/breeding restriction is introduced;
existing custody and safety rules remain.

Fresh games and explicit pet reset retain the existing notice/egg-adoption flow.
After skipping/timing out adoption, **CHOOSE WATER PET** offers:

- Species: all 14, plus **Mystery egg**. Click browses, hold selects, double-click
  cancels the draft. Mystery resolves only on selection, never while browsing.
- **Mystery colours** independently chooses the three initial H1 genes. It works
  on OLEDs too; those genes travel to colour peers.
- **Choose colours** on colour panels opens the existing palette menu; mono
  panels show **Keep colours**. Back from manual setup returns to the chooser.
- **Start pet** explicitly completes the chooser. Age/care timing pauses until
  then. This does not replace the existing adoption-first workflow.

Both mysteries share one per-new-game saved seed but use distinct mixing domains.
Choosing one does not choose/change the other. Re-selecting a mystery, navigating,
cancelling or rebooting cannot roll a new result after a successful save. A
purposeful pet reset starts a new game/seed. This is gameplay randomness, not a
cryptographic source. As with existing settings, storage failure plus power loss
before a successful retry can lose an unsaved choice.

**Options → Display → Pet species** allows later explicit species changes on
mono and colour panels without resetting age/genes or changing an already laid
egg. Mystery is a new-game option only. Solo succession copies the parent;
visitor breeding selects one parent's species once while retaining the existing
colour inheritance. Pending eggs keep their species until hatch.

### Adopted eggs

Adoption takes priority over local setup. Existing **LEG1/H1** carries generation
and three colour genes, not species. Those eggs are explicitly species 0, tropical
fish. Successful adoption preserves generation/genes and suppresses local Mystery
setup, including journal recovery. No unsupported LEG1 suffix is sent to old apps.
Species-aware Aquarium adoption requires a separate capability change; see the
[PC starter prompt](docs/WATER-PC-AQUARIUM-STARTER.md).

## Art, stages and resource scope

Species 0 keeps the original fish renderer plus accepted juvenile-colour work.
13 original aquatic sprite sets each have two independently drawn animation
frames, packed as **2-bit semantic masks**: transparent/body/fins/eyes-detail.
Mask storage is **4,992 bytes**, not RGB565 frames per palette. The renderer uses
a four-colour stack palette, no heap and no per-species framebuffer. Adult/elder
max footprint is 32×24; fry/young sample 20×15 / 26×19. Existing world motion is
shared; tails/flippers/legs/tentacles/blowhole/shell details animate at 280 ms
phases. These are distinct silhouettes, not the original fish with new names.

Colours use existing runtime converters/H1 genes. Juvenile body/fins use existing
blend weights and neutral contrast eyes; adult/elder eyes express their gene
unless it would disappear into the body. Mono, tint and white-flash exceptions
remain. The T096 still uses the existing 128×64 logical renderer: no new native
160×80 layout, display-transport speed or measured battery claim is made.

Recreate the generated masks with:

~~~sh
uv run --with pillow==12.1.0 python tools/water/generate_sprites.py
python3 test/ui/check_water_rendering.py --preview-dir DIR
uv run --with pillow==12.1.0 python tools/water/preview_sheet.py DIR/plain OUTPUT
~~~

CI consumes the committed mask header without Pillow. Preview frames run exact
production drawing functions on a clipped host framebuffer, not concept art,
photographs or electrical panel emulation. Real board flash/RAM and frame timing
remain subject to CI and physical checks.

## Save migration

The pet DAT record is unchanged. CFG keeps its entire **60-byte old prefix**:
24 legacy + 12 HAP1 + 8 AQU1 + 10 HUE1 + 6 MON1. A new **18-byte SPC1** tail makes
current CFG **78 bytes**:

| Tail offset | Field |
|---:|---|
| 0..3 | ASCII SPC1 |
| 4..5 | local species LE16 |
| 6..7 | pending egg species LE16 |
| 8..11 | mystery seed LE32, 0 = not generated |
| 12 | chooser pending 0/1 |
| 13 | reserved zero |
| 14 | tail version 1 |
| 15 | reserved zero |
| 16..17 | CRC16-CCITT-FALSE over bytes 0..15, initial 0xFFFF, LE16 |

Missing/old/truncated/bad-CRC tails default species to fish without resetting an
established pet or altering age/generation/genes. Unknown valid uint16 IDs survive
save/inheritance/transfer and render as legacy fish; never treat them as array
indices. Old firmware reads the prefix, but a downgrade save may discard SPC1;
a later upgrade then defaults to fish and loses unresolved Mystery state.
Existing dedup and failed-write retry behaviour remains. This does not make CFG
an atomic two-bank journal or prove physical power-cut safety.

## Backward-compatible LFG1

REQ, custody, return markers and retry timing stay unchanged:

~~~text
LFG1|REQ|tx|fish|stage|name
LFG1|ACK|tx|fish|S1
LFG1|COMMIT|tx|fish|C|body|scales|eyes|tint[|H1|b|s|e]|P1|panel|S1|species
LFG1|ARRIVED|tx|fish
LFG1|RECALL|tx|fish
LFG1|RETURN|tx|fish|mode[existing exact marker]
~~~

Only the expected-peer/transaction **ACK ending exactly with S1** enables all
optional H1/P1/S1 fields. Plain ACK produces the original **nine-field COMMIT**,
with nearest named-colour genes and existing RGB565 tint, no suffix at all. This
is necessary: the inspected old RX parser requires exactly nine fields and
otherwise captures absent appearance. Old DX/RX see a normal fish and retain
normal return flow; unsupported species/fine hues cannot be preserved there.
The home pet never loses its species because of this presentation fallback.

S1 species is decimal 0..65535, separate from stage, fish ID and genetics. Missing
S1 means tropical fish. Malformed/overflow/duplicate S1 rejects that COMMIT without
consuming its reservation. First accepted guest species is immutable: later
short/full duplicates cannot change it. Full public key/transaction/fish binding
remains. Water also accepts older senders, including existing H1/P1 extensions.
H1 parsing now accepts its known following P1/S1 fields without losing fine genes.

Every retry is the exact first COMMIT cached for the active full key/transaction/
fish, including negotiated legacy/extended form. Local edits or duplicate ACKs
cannot mutate it; first-COMMIT loss does not strip metadata from the actual retry.
Capability is a peer claim, not PC durability proof or a live RF test.

### Discovery

Exact accepted markers: **🐟 🐠 🐡 🦈 🐬 🐳 🐋 🦭 🦐 🦑 🦞 🦀 🐙 🪼 🐚 💦**.
Legacy four render as ><>, others as bounded [W] on ASCII fonts. Raw names stay
unchanged; outgoing clean pet labels still strip emoji/delimiters with bounded
UTF-8 handling. Generic **💧 🌊 ⚓ 🎣**, stars, turtle/snail/penguin/boating symbols,
and plain fish or ><> text are not markers. There is no dedicated sea-star marker;
use **💦** for any Water pet. Markers are discovery convention, **not capability
proof**; only the explicit transaction-bound ACK controls extensions.

## Build and validation

Use the [explicit Water aliases and build commands in README](README.md#water-edition-build-targets).
The original environment names now build DX; they must not be used as Water
selection instructions. V3/V4 OLED/T096 are the owner regression profiles; the
other new aliases require their own current-revision build/hardware validation.
RAK aliases remain explicitly experimental with external OLED and input required.

The [owner-board workflow](.github/workflows/water-owner-builds.yml) gates both
editions on V3, V4 OLED, T096 and experimental RAK behind host checks. It runs on
main, feature/water-edition and the scoped integration branch, or manual dispatch.
Existing workflows are retained. Read-only permissions, three parallel build jobs
and 14-day artifacts remain. No release, merge, flash or hardware result is implied.

Run native tests plus all test/ui/check_*.py. The Water tests cover real settings
migration/corrupt tails/mystery state, all 14 production sprites/stages/mirroring/
travel, and actual production packet-loss/full-key/capability handlers. Preserved
f310240 production receiver and colour-codec fixtures prove old DX fallback. The
separate older RX→Aquarium test verifies the real nine-field fallback and SQLite
path. That test and busy-mesh integration require sibling checkouts and are
explicitly NOT RUN in standalone CI; self-contained regressions remain enabled.

After CI, validate images/hashes/partition or UF2/linker bounds before delivering.
Physical V3/V4/T096 checks still need selection/reset/reboot/adoption/mixed-version
visits and panel/radio testing. Host faults and pixels are not physical flash,
RF-loss, power-cut, memory-budget or panel-appearance proof.
