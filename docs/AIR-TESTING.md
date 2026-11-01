# Air source verification — 2026-11-01

## Revisions and authority

Runtime/art/tests source commit: **945717cec7df7a21196996d39a9c97dee4f11dc6**.
This document and the manual owner-build workflow are a separate automation/docs
commit; they do not change the tested firmware tree.

Branch feature/air-edition, isolated worktree loragotchi-dx-air. Final base is
**53cc11633988dc68de87721074dcc0db529e44bd**, the newest observed owner-fork main.

At task start, main was 251e631 and the newest compatible integration branch was
1dfe536. Final ref verification detected that owner main had advanced during the
work, containing that integration plus the prior size-trial commits and new
T-Watch S3 support. The initial tested Air commits are retained on the local
feature/air-edition-pre-owner-refresh backup. Only our unpublished Air commits
were rebased onto 53cc116; no owner branch was rewritten, pushed or merged.

Two narrow rebase conflicts were resolved: README retains the owner's T-Watch
guide plus Air instructions, and Air scene selection wraps the owner's unchanged
LORAFISH_SCENERY_CANVAS Cardputer/T-Watch call. All owner T-Watch drivers, input,
radio, headers, profiles and conditional UI behavior remain present. Final Air
is now directly based on current main, not stacked on an unmerged integration.
The prior compiler trial is already part of owner main and is retained, not
claimed as a successful size fix. No Air-specific T-Watch qualification is made.

Owner origin only was refreshed. DarkButterfly was not cloned/fetched/synced;
newly imported upstream commits arrived through the owner's permitted origin.
Existing dirty worktrees were not edited. All host/native/config and current
RX/PC checks were rerun after the baseline refresh; historical logs remain
attributed to their original source instead of being relabelled.

No push, PR, merge, release, new hosted run, local firmware compilation or flash.
The user's no-push boundary and existing GitHub firmware-compilation policy mean
new exact-Air target builds are **BLOCKED pending publication/CI authorization**.
The manual workflow is prepared, not executed. Old baseline firmware artifacts
are not Air evidence and are not substituted for new builds.

## Completed host checks

- **332/332 native cases**, native/native_water/native_air/native_kiss_modem.
- **30/30 production UI suites**, plus Water menu/emoji variants and BLE PIN
  tests. Includes both retained local sibling DX/RX/Aquarium integration checks.
  New Air suites are self-contained; the workflow explicitly excludes only the
  two older sibling-dependent suites on standalone runners, retaining local proof.
- Linked executable uses actual CFG/DAT serializers and reboot, actual negotiated
  LFG1 sender/frozen retry/receiver/recall, then actual production mono/colour
  drawing for every Air ID. ESP32 and nRF52 file branches both pass.
- All 18 Air identities/pending offspring, independent persistent mysteries,
  legacy prefixes, every truncated SPC1 tail and every single-bit corrupted tail,
  unknown uint16 IDs, solo and both visitor parent paths. Fresh boot defaults
  Eagle; established legacy DAT remains fish. Cross-edition real serializers
  preserve IDs 9/256/273/65535 in DX, Water and Air.
- Actual adoption/journal fault tests run in Air for ESP32, nRF52 and T-Deck NVS
  with ASan/UBSan: existing LEG1 adopted eggs remain fish 0 with accepted genes/
  generation, bypassing local Mystery, including interrupted-journal recovery.
- Actual menu entry route, mono/colour, sound/no-sound, awake/alert guards,
  independent mysteries, cancel/reselection and explicit Start. All 18 Air markers
  traverse the real contact picker; names/malformed UTF8/wind/cloud/nature negatives,
  bounded [A] fallback, and unchanged LRX1/type guards. No emoji-to-ID mapping.
- Production protocol: all 18, exact A1, S1-only explicit fish 0, strict nine-field
  legacy fallback, malformed/overflow/duplicate species/capabilities, full-key
  spoofing, reservation preservation, immutable first visitor metadata and exact
  first-COMMIT-loss retries. UINT32 ACK and uint16 species boundaries use checked
  arithmetic, not host-width-dependent strtoul overflow behavior.
- Preserved pre-Air Water production handlers/codecs execute alongside current
  sender tests: old strict-S1 sender falls back to nine fields for Air A1 ACK;
  Air→old Water uses species 0 but retains fine genes and recall.
- Additional optional **actual current RX → PC decoder/SQLite** test passes all
  18 Air visitors using RX's actual S1-only ACK: rich fish-0 snapshot, fine genes
  220/120/6, first-packet loss/retry, real receiver return, one SQLite roster fish.
  Sibling RX/PC sources are read-only; no A1 support was added to them.
- Air production renderer: **44,352 counted scenarios × 3 styles = 133,056**.
  All 18 × four stages × both frames, mono/colour, themes, alleles/tint/flash,
  mirroring, home/travel callers, complete entry/exit intervals, travel expiry.
  Each species has distinct two-frame monochrome animation at **every** stage.
- Water renderer retains **96,576** counted scenarios; explicit saved Air-ID
  fallback renders identically to legacy fish on Water. Legacy juvenile test
  retains **1,440** original pixel signatures and all chromatic allele/theme/style
  contracts, without rewriting any goldens.
- C++11 **ASan+UBSan** resource test sweeps all 65,536 IDs for both mask renderers,
  plus **12,096** clipped/mirrored/staged Air frames with framebuffer canaries.
  Air packed masks 6,912 bytes; unchanged Water masks 4,992 bytes; max 768 source
  pixels/runs per sprite; SPC1 remains 18 bytes; worst COMMIT remains <128 bytes.
  This is not a target linker/stack/frame-time measurement.
- Generator reproduces committed Air art header byte-for-byte (SHA256
  7bcd473a6afef59e0ef0c2905a1fa57a82f1a1477d368fb679456def89bd1a12).
  Production-frame mono/colour catalogue PNGs were visually inspected; GIFs
  retain both real animation phases. They are host pixels, not board photos.
- Full PlatformIO resolution: **688 existing environments unchanged**, exactly
  ten new Air aliases plus native_air. Forty-two canonical experimental profile
  audits still pass; edition aliases are audited separately, not counted as new
  hardware. RF/pins/display/memory/dependency settings preserved.
- Twelve edition/platform/sound preprocessing checks keep generic companions
  free of pet implementation. Actual DX/Water/Air reset/load/wire/boot bodies pass;
  splash text fits 128×64. Workflow YAML, embedded Python/shell syntax, manual-only
  trigger, read-only permission, exact SHA and nine unique matrix profiles checked.
- git diff --check passes. Source commits contain no firmware/cache/log/binaries.

Detailed local logs, resolved configs and production previews are retained under
reports/loragotchi-air-20261101 in the coordinator workspace. Host fixtures mock
files/radio/display boundaries; they are not electrical peripheral emulation.

## What is still unbuilt / unmeasured

No firmware target has been compiled at the Air source revision. The prepared
minimum hosted matrix is Air/DX/Water × V3, V4 OLED and T096 (nine images).
All other Air aliases are config/host-only coverage, including experimental RAK,
T114, Cardputer, T-Deck USB/BLE and ThinkNode. The last measured three tight experimental
DX images were oversized (new Air revision unbuilt): TBeam1W, Station G2 and Station G3.
No partition/feature/validation tradeoff was made or approved.

After explicit publication/CI permission: require exact-SHA terminal checks/builds;
inspect successful ESP32 checksum/hash/partition fit and nRF UF2 family/block/
linker bounds, retain any failed profiles separately, and report actual flash/
static RAM. Then obtain owner physical acceptance before any release/flash action:

1. V3/V4/T096 chooser, all species, new game/reset, cancel/start, mystery/genes,
   warm/cold reboot, old fish saves and pending eggs; confirm no reroll/corruption.
2. Real mono/colour readability in every life stage, sleep/wake, theme/tint/flash,
   travel and guest overlap; inspect frame timing and memory under animation.
3. Two Air peers A1 species visits; updated and pre-Air Water, DX, old/current RX
   fish fallback, explicit UI warning, loss/retry/late arrival/recall and unchanged
   home species. Physical BLE+RF stress and storage failure/power-cut checks.
4. LEG1 adoption stays fish/genetics-compatible; PC/HA still lack Air A1 export.

No native T096 layout, RF-loss performance, power/battery, sustained heap,
physical power-cut or per-board acceptance claim is made by these host results.
