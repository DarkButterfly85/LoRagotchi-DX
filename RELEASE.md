# Releasing Firmware

GitHub Actions builds and publishes LoRaGotchi firmware when a version tag is
pushed (`.github/workflows/release-firmware.yml`).

- Push a tag starting with `v`, for example `v1.1.0`.
- A tag containing a hyphen, for example `v1.1.0-rc1`, is published as a
  **pre-release**.
- Every LoRaGotchi env is built: the `*LoRaGotchi_DX*` / `*loragotchi*` boards
  plus the `Water_` and `Air_` edition envs (the list comes from
  `tools/ci/list-loragotchi-envs.py`). Stock MeshCore envs in
  `platformio-meshcore.ini` are never built.
- If every board builds, a GitHub Release is created for the tag with the images
  and a `SHA256SUMS` file. If any board fails, no release is created.

Image names are `<env>-<tag>-<shortsha>.<ext>`:

- ESP32 boards: `.bin` (application) and `-merged.bin` (full flash image)
- nRF52 boards: `.uf2` and `.zip` (DFU package)

Pull requests build the same env list in `.github/workflows/pr-build-check.yml`.
No secrets are needed; the workflow uses the built-in `GITHUB_TOKEN`.
