# Water verification history and edition-split checks

## Historical Water candidate 1 (856d420)

Baseline: owner-local f310240 (monochrome panel profiles) plus the accepted
juvenile-colour change 7254316 cherry-picked unchanged as 35ce94a. Both extend the
same owner-local b8966f0 application baseline; origin/main c0bde4c has an identical
tree to b8966f0. The newer visual-simulator branch adds host tooling only and was
not used as a firmware downgrade. No original/reference repository was fetched or
cloned. Other worktrees and the owner's uncommitted source work were not changed.

Completed host gates:

- Native/native_kiss_modem: **114/114 tests**.
- **19/19** production UI/integration Python suites, including the two real sibling
  RX/Aquarium integrations when their existing read-only checkouts are available.
- Water production renderer: **32,192 checks per display style × 3 = 96,576**,
  including 14 species, four stages, two frames, mono/colour/themes/genes, mirroring,
  home/travel callers, clipping/expiry and complete entry/exit intervals.
- Existing juvenile-rendering golden signatures remain unchanged for the legacy
  fish paths; all supported chromatic alleles, themes and three display styles
  retain their age-colour contract. No legacy golden data was regenerated.
- Actual production CFG serializers: all 14 and unknown IDs, legacy prefixes,
  every truncated SPC1 tail, each single-bit corrupt tail, pending species through
  succession, Mystery order/reboot/reselection, and explicit new-game completion.
- Actual production menus, with/without sound: initial species/Mystery/colours,
  draft cancellation, manual colour return, explicit Start pet, awake/alert guards,
  all existing menu routes plus 128×64 text bounds.
- Existing adoption journaling/fault tests (ESP32, nRF52, T-Deck NVS) retain accepted
  generation/genes, bypass local Mystery, suppress premature SAVED and recover
  interrupted adoption without rerolling a durable intent.
- Species/identity protocol: all 14, unknown/malformed/overflow/duplicate S1,
  full-key binding, corrected retry after bad metadata, immutable first accepted
  species, exact capability ACK and first-COMMIT-loss/frozen retry payloads.
- Preserved f310240 production receive/colour-codec fixtures prove old DX accepts
  extended visitors as legacy fish. The real existing RX parser's strict n==9
  requirement was reproduced; capability negotiation now sends it a no-suffix
  nine-field COMMIT. The actual old Aquarium decoder/SQLite integration proves
  colours survive that fallback and resharing updates rather than clones.
- Pairing-PIN host checks: **24 boot configurations** and active-PIN rendering.
- Exact 3 owner profiles resolved with PlatformIO config; workflow YAML, embedded
  shell/Python syntax, branch-only push/manual triggers, read-only permissions and
  matrix uniqueness validated. The editable art generator reproduces the committed
  semantic masks byte-for-byte. git diff --check passed.

Evidence files and production-rendered PNG/GIF previews are retained locally in
this worktree's ignored .local-dev directory and the handoff reports directory.
They are host rendering, not photographs, device framebuffer comparisons or RF
measurements. No physical panel/frame-time, radio/power-cut, board flash/RAM or
battery-life result is claimed.

## Reconciled v1.1.0 source candidate

The supplied ZIP includes owner main 251e631 plus an unfinished, uncommitted
edition split. Most other file differences are CRLF conversion, not code changes.
Only intentional source/docs/new aliases were reconciled; archive Git metadata
and cache files were not imported. Current source keeps original target names DX
and makes Water opt-in. Historical counts above belong to 856d420, not this delta.

New gates:
- native + native_water + native_kiss_modem test default and Water marker behavior.
- check_editions.py compiles actual reset/load, wire and splash bodies for both
  editions (ESP32/nRF52 RAM-storage mocks, 128x64 boot text bounds).
- Menu/navigation and emoji harnesses run both editions, with and without sound.
- Water state/protocol/rendering harnesses explicitly compile the Water edition.
- check_edition_targets.py verifies all resolved aliases preserve their parents'
  hardware, radio, memory and dependency settings. The original 42-profile
  experimental inventory remains canonical; edition/module aliases are separate.

## Firmware builds

Historical main 251e631 completed Water-owner run 41263409197 and standard-images
run 41263409250 successfully. Those binaries predate the edition split and version
fix. They must not be presented as v1.1.0 or proof of the experimental RAK aliases.
The current workflow requests eight selected DX/Water images. Check its exact-SHA
terminal job results before claiming any current binary is available. Other aliases
are configuration-validated only unless their own build result is recorded.

Download the matching source-SHA artifact, not an unrelated latest success.
Before use, validate ESP32 checksum/image/partition bounds or nRF UF2 family,
blocks and application linker bounds. Builds are not hardware acceptance.

## Explicit current limitations

Legacy DX/RX recipients show a fish, not the new species. Current LRX/1 77-byte
snapshots cannot export species/H1/P1; the PC starter prompt records the needed
negotiated successor work. Existing LEG1 eggs are fish-only, preserving accepted
genes/generation and the existing adoption flow. Downgrade saves can discard SPC1.
The settings file is not made power-cut atomic; a failed save followed by power
loss before retry can lose a recent Mystery choice. Physical targets are unchanged,
including T096's existing 128×64 logical presentation.
