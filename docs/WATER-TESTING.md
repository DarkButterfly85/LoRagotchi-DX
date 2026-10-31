# Water candidate 1 local verification

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

## Firmware build blocker

The owner requested GitHub-hosted compilation to conserve local resources and has
not authorised pushing this new source branch. Therefore **zero board firmware
builds have run for Water candidate 1 and no firmware binaries exist for it**.
The branch-scoped Water workflow is prepared for V3 BLE BIN, V4 OLED BLE BIN and
T096 BLE UF2. A source-branch push to the owner's fork is needed to start those
builds; it does not require a PR, merge or release. Do not bypass that permission
boundary by compiling locally or publishing source elsewhere.

After permission: push the exact tested branch, identify the matching Actions SHA,
wait for terminal checks/build jobs, download the three exact-SHA artifacts,
validate ESP32 chip/checksum/hash/partition fit and T096 UF2 family/block/linker
bounds, then package images/checksums/instructions for owner hardware testing.
Report any failed profile without claiming a complete matrix or usable binary.

## Explicit current limitations

Legacy DX/RX recipients show a fish, not the new species. Current LRX/1 77-byte
snapshots cannot export species/H1/P1; the PC starter prompt records the needed
negotiated successor work. Existing LEG1 eggs are fish-only, preserving accepted
genes/generation and the existing adoption flow. Downgrade saves can discard SPC1.
The settings file is not made power-cut atomic; a failed save followed by power
loss before retry can lose a recent Mystery choice. Physical targets are unchanged,
including T096's existing 128×64 logical presentation.
