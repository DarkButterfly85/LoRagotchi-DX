> **Station G2 / Station G3 ESP32 / T-Beam 1W LoRagotchi:** these profiles now use
> a larger single factory app (no OTA). App-only updates do not migrate tables.
> Back up first; see [migration/data-loss risks](docs/SINGLE-APP-MIGRATION.md).

# LoRaGotchi-DX

LoRaGotchi-DX is a virtual LoRa pet for MeshCore radios. Your pet lives on a
small board, grows up, breeds, and visits other pets over the mesh. It is
built on MeshCore and originally written by Robert Rayner (M0YNW).

## Editions

Each edition is a separate build target. Pick the board and the edition at
build time; they share one source tree.

| Edition | What it is | Animals | Build targets |
| --- | --- | --- | --- |
| **DX** | The original fish-only pet, with DX travel between tanks | Fish | The existing LoRaFish/LoRaGotchi DX environments, see [the board matrix](docs/BUILDING.md#board-and-edition-selection) |
| **Water** | Underwater and surface tanks | 15 | `water_*`, see [WATER-EDITION.md](WATER-EDITION.md) |
| **Air** | Sky habitat with flyers and birds | 18 | `air_*`, see [AIR-EDITION.md](AIR-EDITION.md) |
| **Land** | Ground animals with natural idle motion and a nose-down sniff | 43 | `land_*`, see [LAND-EDITION.md](LAND-EDITION.md) |
| **DX-Pro** | One firmware with the Water, Air and Land animal sets together (combined DX + Water + Air + Land) | Water, Air and Land sets | `dxpro_<board>`, for example `dxpro_heltec_v3_ble`; see [DX-Pro](docs/dxpro.md) and [the board matrix](docs/BUILDING.md#board-and-edition-selection) |

Land and DX-Pro are available on the `orion` branch, not yet on `main`. A build target or a
successful compile is not a claim of physical hardware acceptance; see the
testing notes in [docs/BUILDING.md](docs/BUILDING.md).

For setup, controls, menus, pet behaviour and DX travel, see
[Getting Started](Getting_Started.md).

## Documentation

- [Getting Started](Getting_Started.md): setup, controls and menus
- [Building and board matrix](docs/BUILDING.md): exact build names and outputs
- [Device pages](docs/devices/): [T-Watch S3](docs/devices/t-watch-s3.md), [T-Deck](docs/devices/t-deck.md) and [Cardputer](docs/devices/cardputer.md), each with its own getting-started guide ([T-Watch S3](docs/devices/t-watch-s3/GETTING_STARTED.md), [T-Deck](docs/devices/t-deck/GETTING_STARTED.md), [Cardputer](docs/devices/cardputer/GETTING_STARTED.md))
- [Feature history and testing notes](docs/HISTORY.md): what changed and when
- [Credits](docs/CREDITS.md): who made what
- [Licence](LICENSE) and [NOTICE](NOTICE)

## Build and install

1. **Get the source.** Install Git and
   [PlatformIO Core](https://docs.platformio.org/en/latest/core/installation/index.html),
   then clone `main` (DX, Water and Air). Land and DX-Pro are on the `orion`
   branch: clone with `--branch orion` instead.

   ```sh
   git clone --branch main https://github.com/DrToxic/LoRagotchi-DX.git
   cd LoRagotchi-DX
   ```

2. **Choose the board and edition** from the
   [board/edition matrix](docs/BUILDING.md#board-and-edition-selection) (exact,
   case-sensitive names and BIN/UF2 output), then run **one** command for it.
   Select the exact radio, display and board variant: V4 OLED is not V4 TFT, and
   L1 is not L1-1W. Which boards are experimental or untested on hardware is in
   [Compatibility and test status](docs/BUILDING.md#compatibility-and-test-status).
   Heltec V3 examples are below. Do not run an unqualified `pio run`, which
   selects unrelated upstream targets.

   ```sh
   pio run -e Heltec_v3_LoRaFish_companion_ble -j 1  # DX
   pio run -e water_heltec_v3_ble -j 1              # Water
   pio run -e air_heltec_v3_ble -j 1                # Air
   ```

3. **Flash using the board's own method.** Building installs nothing; back up the
   device's keys, settings, contacts and pet data first
   ([details](docs/BUILDING.md#check-the-device-and-protect-existing-data)).
   ESP32 boards produce an application BIN (upload with the same environment and
   `-t upload`); nRF52 boards need `-t create_uf2` and the UF2 copied to the
   bootloader drive. Full steps for both:
   [install guide](docs/BUILDING.md#install-using-the-boards-matching-method).
   Station G2, Station G3 ESP32 and T-Beam 1W need the
   [partition migration warning](docs/SINGLE-APP-MIGRATION.md) first. Device
   guides: [T-Watch S3](docs/devices/t-watch-s3/GETTING_STARTED.md),
   [T-Deck](docs/devices/t-deck/GETTING_STARTED.md),
   [Cardputer](docs/devices/cardputer/GETTING_STARTED.md).

4. **First-boot check.** After reboot, check that the splash shows the intended
   edition, then verify display, controls, pairing and saved state (your pet,
   contacts and settings). A successful build is neither a published release nor
   physical hardware acceptance.

## Project history

Development notes from the experimental LoRaFish/LoRaGotchi builds are retained under [`docs/development/`](docs/development/) for reference. The v1.0 release note is under [`docs/release/`](docs/release/).

## Credits

LoRaGotchi DX is by **Robert Rayner / M0YNW** and is based on **MeshCore** by Scott Powell / Ripple Radios. MeshCore provides the underlying mesh transport and substantial portions of the firmware foundation.

See [`NOTICE`](NOTICE) for attribution details.

## License

MIT. See [`LICENSE`](LICENSE).
