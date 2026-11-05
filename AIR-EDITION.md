# LoRagotchi Air — local source candidate

A habitat edition, not a mono/colour fork. **Not a released or hardware-tested
firmware.** Product version remains the repository's v1.1.0 source candidate;
MeshCore remains v1.18.0. Default environments still build DX, water_* still
build Water, and only air_* / LORAGOTCHI_AIR_EDITION=1 select Air. Defining both
habitat flags is a build error. No native-resolution/display-transport refactor.

## Registry and taxonomy

Shared unsigned 16-bit namespace, independent of names, emoji, menu positions,
stage, genetics or fish/device IDs. Water 0..13 is unchanged; Anglerfish is appended at 14; 15..255 remains
reserved. Air v1 owns **256..273**, permanently and in the original candidate
order. Other uint16 values remain opaque identities, never array indices.
No mapping to unofficial/third-party wolf IDs is asserted.

| ID | Candidate | Motion |
|---:|---|---|
| 256 | Eagle | Flight |
| 257 | Bird | Flight |
| 258 | Owl | Flight |
| 259 | Duck | Flight |
| 260 | Swan | Flight |
| 261 | Penguin | Ground/waddle |
| 262 | Parrot | Flight |
| 263 | Flamingo | Ground/step |
| 264 | Peacock | Ground/step |
| 265 | Turkey | Ground/step |
| 266 | Rooster | Ground/step |
| 267 | Dove | Flight |
| 268 | Bat | Flight |
| 269 | Honeybee | Flutter |
| 270 | Butterfly | Flutter |
| 271 | Fly | Flutter |
| 272 | Worm | Crawl |
| 273 | Bug | Crawl |

This is the requested **candidate collection**, not a biological assertion that
penguins fly or worms live in air. All 18 are selectable; none was silently
reclassified or removed. Insects flutter faster, ground birds walk, and worm/bug
crawl more slowly. Existing stage/sleep/feeding/travel mechanics remain shared;
no new diet, hunger balance, metamorphosis or breeding restriction is invented.
Air uses a sky/ground scene on every display style, not Cardputer/T-Deck reef art.
Water visitors and old fish retain their original movement/presentation in Air.

## Controls and saved state

Existing notices and adoption have priority. A genuinely new Air game starts an
Eagle egg; after adoption is skipped/times out, **CHOOSE AIR PET** offers species,
Mystery egg, independent Mystery colours, existing manual colour setup on colour
panels, and explicit **Start pet**. Mono panels can choose species and mystery
genes too. Browsing/cancel never rolls. Both mysteries retain the one saved seed;
Air's 18-choice mystery mapping is unchanged. Water now offers 15 choices;
already selected/saved species remain unchanged (see WATER-EDITION.md).

Options → Display → Pet species offers all 18 without changing age, genes or an
already-laid egg. Solo succession copies species; visitor breeding chooses one
parent once. Existing lifecycle/care, colour inheritance and safety guards stay.

The **32-byte DAT, complete 60-byte CFG prefix and 18-byte SPC1 tail are unchanged**.
Air uses the existing LE16 local/egg fields, version/CRC and failed-save retry
logic. Established fish DAT + absent/old/truncated/corrupt SPC1 stays fish 0,
not an auto-conversion to a bird or new setup. Water and opaque saved identities
remain intact; fresh-game defaults are not applied to established pets. Current
DX/Water builds preserve Air bytes, render unsupported Air as fish, and only an
explicit species selection/reset changes identity. Old firmware can discard the
SPC1 tail on saving: downgrade/re-upgrade is not lossless. Settings are not newly
power-cut atomic; an unsaved choice can be lost after write failure/power loss.

**LEG1/H1 eggs remain fish-only.** Air adoption retains accepted generation/genes,
sets species 0 and bypasses the Air chooser, including journal recovery. No
invented species suffix is sent to an older Aquarium. Actual species-aware egg
adoption still needs a separately negotiated protocol revision.

## Mesh interoperability: never infer capability from a marker

REQ, identity binding, custody, COMMIT retries, ARRIVED, return/reward markers and
reservation deadlines are unchanged. Air explicitly replies:

    LFG1|ACK|tx|fish|S1|A1

Only this **exact transaction/full-peer-bound ACK** opts into Air v1 IDs. The
species still occupies the existing COMMIT |S1|decimal-ID field; A1 is an ACK
capability, not a new unversioned numeric field. Each first COMMIT is frozen and
all retries carry its exact negotiated bytes, even after local species edits or
loss of the first packet.

| Destination ACK | Air outgoing presentation |
|---|---|
| Exact S1\|A1 | Real 256..273 species + existing H1/P1 |
| Exact S1 only (Water/current RX) | Explicit tropical fish 0 + existing H1/P1 |
| Plain/unknown legacy ACK (old DX/RX) | Original strict **nine-field** COMMIT, no extension |

The home Air identity/save is never changed by visiting as fish. The DX Visit page
shows **DELIVERING FISH / FISH FALLBACK**, and the serial log explains why. Invalid,
extra or loosely matching capability suffixes never authorize Air IDs. Older DX/RX
retain normal recall/return flow. Unsupported fine genes/panel/species metadata
cannot survive strict legacy wire presentation, as before.

Updated Water/DX senders understand the new exact ACK grammar; Air can display
Water visitors. **Pre-Air Water senders accept only ACK ending exactly S1**: when
visiting Air they therefore conservatively send the original nine fields and
appear as a fish (their home Water species remains intact). This deliberate,
tested compatibility limitation avoids pretending an old peer understood A1.
S1's existing opaque uint16 forwarding semantics outside the assigned Air range
are retained; future unknown identities are not reinterpreted as Air.

Current RX/PC/HA sources are not modified by this task. Air→RX visits deliberately
use negotiated fish presentation until RX gains explicit A1 support. Existing
LRX/1 snapshots remain unable to export Air species; no unsupported numeric ID
is injected into a legacy snapshot or LEG1 egg. Discovery is not support proof.

Air discovery accepts the 18 exact animal emoji (including penguin, worm, bug),
plus existing fish/Water markers for mixed-edition visits. Air-only glyphs render
as bounded [A], Water as [W], legacy fish as ><>, on ASCII fonts. Raw names are
unchanged; no name or emoji is ever used to guess a stored species ID. Wind,
cloud, plain animal words and generic nature symbols are not extra Air markers.
The existing explicit LRX1 repeater/type guards stay intact.

## Art and resource bounds

18 original two-frame 32×24 sprites, packed transparent/body/wings/detail roles:
**6,912 bytes**. Air also retains the **5,376-byte** Water masks (including Anglerfish) for old
saves/visitors: total packed masks **11,904 bytes**, not RGB565-per-palette frames.
No heap/per-species framebuffer. Runtime horizontal runs draw at most 768 source
pixels/runs per full sprite; actual juveniles use 20×15 and 26×19 sampling.
Adult/elder use 32×24. No claims of biologically distinct juvenile forms: these
are readable stage-scaled silhouettes with the existing juvenile gene blending.
Mono contrast details, themes, tint/flash, mirroring, home and travel callers use
the existing production palette pipeline. See tools/air for editable generation
and production-frame preview sheets; Pillow 12.1.0 is generation-only, not needed
by firmware or host pixel CI.

This is a source/host ceiling, **not** measured MCU flash/static RAM/stack/heap,
frame time, display-bus speed or battery savings. T096 retains 128×64 logical
presentation, not a new native 160×80 layout.

## Targets, CI and hardware gate

Ten air_* aliases mirror the ten water_* aliases, including inherited experimental
RAK4630/4631 external-OLED/button requirements. No pins, RF, partitions, linker
bounds, display drivers, feature switches or existing target profiles change.
Owner profiles: **air_heltec_v3_ble**, **air_heltec_v4_oled_ble**,
**air_heltec_t096_ble** (create_uf2). Other aliases are configuration/host validated
only, not implicitly board-qualified; no e-ink or screenless target is added.

The branch-scoped .github/workflows/air-owner-builds.yml offers edition/board
choices on manual dispatch; pushes to feature/air-edition run all nine bounded
hosted builds: Air/DX/Water × V3/V4 OLED/T096, after standalone host/native gates.
It preserves read-only permissions, explicit exact-SHA checkout, max-parallel 3,
one compilation job per image, 14-day checksummed artifacts and no release/flash.
Cross-repository tests explicitly skip on standalone runners; local sibling
integration evidence is separate. Existing workflows/triggers remain unchanged.

**Publication/CI was separately authorized after the initial local handoff.**
Only this feature branch may be pushed; no main merge, release or flash is implied.
The initial da1d313 source candidate remained unbuilt at that handoff; the hosted
run must be checked by exact SHA before claiming images exist. No local
firmware build substitutes for that gate; no existing baseline image proves Air.
The last measured tight-flash experimental TBeam1W/Station G2/G3 images were
oversized. Owner main advanced during this task and now includes the prior
compiler-flag trial; that owner baseline is retained unchanged, not presented as
a successful size fix. No new Air profile fit has been measured.
No repartitioning, feature removal or suppressed size validation.

After authorized CI, validate ESP32 checksum/hash/partition fit or UF2 family/
block/linker bounds for the exact SHA before any handoff. Physical V3/V4/T096
selection/reboot/adoption/mono-colour/mixed-version visit and sustained BLE+RF/
sleep-wake/display timing tests remain required. No real-device result is claimed.

## Reproducing host checks (no firmware compilation)

    pio test -e native -e native_water -e native_air -e native_kiss_modem
    python3 test/boards/check_edition_targets.py
    python3 test/boards/check_experimental_screens.py
    python3 test/ui/check_air_end_to_end.py
    python3 test/ui/check_air_state.py
    python3 test/ui/check_air_protocol.py
    python3 test/ui/check_air_legacy_water.py
    python3 test/ui/check_air_menu.py
    python3 test/ui/check_air_discovery.py
    python3 test/ui/check_air_adoption.py
    python3 test/ui/check_air_resources.py
    python3 test/ui/check_air_rendering.py --preview-dir OUTPUT

Run all other test/ui/check_*.py regressions as well; check_menu_navigation.py
and check_emoji_dx.py each need the additional LORAGOTCHI_TEST_EDITION=1 run.
The existing check_dx_colour_retries.py and check_busy_mesh.py need read-only
sibling checkouts. Optional current RX/PC production fallback test:

    python3 test/integration/check_air_rx_pc.py RX_CHECKOUT AQUARIUM_CHECKOUT

Preview generation (generation-only dependency, not a firmware/UI mock):

    uv run --with pillow==12.1.0 python tools/air/generate_sprites.py
    uv run --with pillow==12.1.0 python tools/air/preview_sheet.py OUTPUT/plain PREVIEWS

Add --mono to preview_sheet.py for the 1-bit catalogue/animation. Frame PPMs run
the production stage/home/travel renderer, not a reconstruction of its sprites.

### Selecting Air builds on GitHub

Open **Actions → Air DX and Water selected owner-board test images** and choose
**feature/air-edition**. Manual inputs select edition **Air/DX/Water/all** and
board **V3/V4_OLED/T096/all**; the default runs the nine-image regression matrix.
Each successful image is a separate named artifact including its environment and
source SHA. Air profiles have an air_ prefix; selecting an original DX target is
not Air. A feature-branch push bootstraps workflow registration because a new
manual-only workflow absent from default main cannot initially be dispatched.
No main modification is needed. Existing release/tag automation is not invoked.
Artifacts are retained for 14 days and require GitHub access; a permanent Air
Release, its tag/version and prerelease/latest policy need separate confirmation.
