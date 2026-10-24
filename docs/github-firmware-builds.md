# GitHub-hosted DX firmware builds

Use GitHub Actions instead of recompiling the full matrix on the development host.

- **Build LoRagotchi-DX standard images**: 10 existing standard profiles, including
  V3, V4 OLED, T096, T114, M2, T-Deck BLE/USB, Cardputer and both T-Beam radio variants.
- **Experimental TFT and OLED DX builds**: the 42 explicitly listed profiles in
  `experimental-screen-targets.json`. Experimental labels do not imply hardware
  acceptance. Screenless/e-ink and explicitly disabled profiles are not included.

Both run on relevant PRs to `main`/`dev`, pushes to `main`, and manual
**Actions → workflow → Run workflow** with the desired branch selected. Existing
release/experimental-branch triggers remain. PR jobs check out the exact PR head,
not a synthetic merge revision. Native and production host checks run on GitHub;
the standard matrix waits for its checks before compiling. The cross-repository
colour retry and busy-mesh integration tests still need independent RX/Aquarium
trees and are explicitly reported as not run by these self-contained workflows.

Download a board artifact from the completed workflow run. Names include
`standard-` or `experimental-`, the exact environment and source commit. Artifacts
contain the firmware, SHA256SUMS, source-sha.txt, dependency information and the
current egg/colour protocol notes. Experimental artifacts additionally include
resolved hardware configuration, board metadata and nRF application linker bounds.
Artifacts expire after 14 days; use a separately authorised release for permanent
public downloads. A workflow does not automatically publish a release or merge a PR.

ESP32 files are application-only images, **not merged installers**. Use the matching
board's compatible partition layout and the generated partition table to identify
the application offset; never assume every BIN belongs at address zero. nRF files
are board-specific UF2 images. No hardware flashing takes place in CI.

Overlapping runs for the same workflow/ref are cancelled when a newer revision
arrives. Failed experimental jobs do not cancel the remaining board jobs. Standard
public GitHub-hosted Ubuntu runners are used; no self-hosted homelab runner or paid
larger runner is configured. Hardware testing remains a separate status from build
success, including for the previously exercised V3/V4/T096 targets.
