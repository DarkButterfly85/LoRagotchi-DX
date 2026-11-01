# LoRaGotchi-DX — DX and Water editions

Current product source candidate: **v1.1.0**, separate from underlying MeshCore
**v1.18.0** and the **Water v1** species registry. This version was already chosen
in the supplied in-progress source; it is not a claim that a v1.1.0 release exists.
The splash now reads **DX v1.1.0** or **WATER v1.1.0** from one shared header.
Historical v1.0 release notes remain historical.

**Existing target names stay DX by default.** Water is opt-in through the explicit
aliases below. DX retains the original fish art, four fish-name markers, five-row
Display menu and colour setup; Water adds 14 species, the new-game chooser and
Water markers. Both use the same mesh transport and compatible saved prefix.
See [Water controls and compatibility](WATER-EDITION.md).

LoRaGotchi is a virtual LoRa fish built on MeshCore, originally by M0YNW,
with contributor work retained in this repository.

For setup, controls, menus, pet behavior, and DX travel, see [Getting Started](Getting_Started.md).

## Historical v1.0 highlights
- LoRaGotchi virtual-pet aquarium and evolution/gameplay
- DX fish visiting using the LFG1 protocol
    - LFG1 protocol upgraded to include colour information
    - Improved the visiting and eating animations
    - Send, acknowledge, commit, arrival confirmation and recall/return flow
    - Host and visiting fish can coexist and swim independently
    - Visiting fish keeps its own evolution stage
    - A fish away from it's own tank will no longer poop in it's own tank
    - Travel is locked while the local fish is asleep
    - DX session state is cleared on reboot as a recovery mechanism
- LoRaGotchi / M0YNW boot branding
- MeshCore remains the underlying radio/mesh transport
- Buzzer support
- Colour screen support
- Higher/Lower game - 5 rounds; each correct guess adds 1 Happy (max +5 per game)

## Testing features:
- Emoji-safe names and fish-marked DX discovery
    - Fish markers 🐟 🐠 🐡 🦈 render as `><>`; unsupported Unicode renders as spaces
    - The DX picker lists only saved companion contacts with a fish marker in their name
    - Dismissible boot reminder for unmarked names; no automatic renaming
- LoRagotchi-local flash and display savings
    - Five-minute passive-counter checkpoints; immediate care/lifecycle/settings saves
    - Identical-record suppression and bounded retries after failed file writes
    - Shared five-second battery display cache using MeshCore's existing readings
    - Unchanged static menus skip redraws; dimmed animation keeps its normal cadence
    - Shared MeshCore, radio, board power configuration and save formats unchanged
- Lifecycle improvements, basic fish-colour DNA, breeding & self-fertilization
    - Your fish now has generations > everyone starts with a 1st gen fish. old-age death no longer ends the LoRagotchi game
    - Your game will ask for what colour your fish should start as. breeding can evolve the fish.
- happiness re-balance
    - RF interactions count toward meals, without a direct Happy bonus
    - +3 Happy per ten-event meal, limited to one meal per hour; no queued backlog
    - -1 Happy per 30 awake minutes, plus -1 per waste piece at the same interval
    - Scheduled sleep, eggs and Memorial pause decay; turning the screen off does not
    - Cleaning stays +3; new generations start at 80; Happy stays between 0 and 100
- M2 Partition change - dropped 2nd app partition in favour of a larger primary app partition.
    - alleviates flash from 95.5% to about 42%, in line with other nodes.
    - retained NVS, Filesystem and Coredump partitions.
    - Disables OTA updates (not used or planned)
- M5Stack CardPuter
    - Updated graphics and keyboard controls for the menu
- LilyGo T-Deck
    - Framebuffer for the display.
 
  
## Supported LoRaGotchi targets in this tree

| MeshCore Node | Build Environment |
| --- | --- |
| ThinkNode M2 | ThinkNode_M2_LoRaFish_companion_ble |
| Heltec V3 | Heltec_v3_LoRaFish_companion_ble |
| Heltec V4 | heltec_v4_LoRaFish_companion_ble |
| M5Stack CardPuter | cardputer_loragotchi |
| Heltec T114 | Heltec_t114_LoRaFish_companion_ble -t create_uf2 |
| Heltec T096 | Heltec_t096_LoRaFish_companion_ble -t create_uf2 |
| LilyGo T-Deck | LilyGo_TDeck_loragotchi_dx_ble / LilyGo_TDeck_loragotchi_dx_usb |

| Untested nodes | build Environment |
| --- | --- |
| T-Beam (SX1262) | Tbeam_SX1262_LoRaFish_companion_ble
| T-Beam (SX1276) | Tbeam_SX1276_LoRaFish_companion_ble
| RAK WisBlock RAK4631 / RAK4630-module carrier (experimental; compile-tested, hardware unverified) | `RAK_4631_LoRaGotchi_DX_ble` / `RAK_4630_LoRaGotchi_DX_ble` -t create_uf2 |

The RAK4630 alias reuses the RAK4631 target; see the [experimental RAK build and hardware prerequisites](docs/RAK4630-EXPERIMENTAL.md).

## Water edition build targets

Water is selected by the following aliases, not by the original DX environment.
All aliases inherit the matching board, radio, display, dependencies and memory
layout; only the edition define changes. An alias is not hardware certification.

| Board/profile | Water environment | Output |
| --- | --- | --- |
| ThinkNode M2 BLE | `water_thinknode_m2_ble` | BIN |
| Heltec V3 BLE | `water_heltec_v3_ble` | BIN |
| Heltec V4 OLED BLE | `water_heltec_v4_oled_ble` | BIN |
| M5Stack Cardputer | `water_m5stack_cardputer` | BIN |
| Heltec T114 BLE | `water_heltec_t114_ble` | UF2 |
| Heltec T096 BLE | `water_heltec_t096_ble` | UF2 |
| LilyGo T-Deck BLE / USB | `water_lilygo_tdeck_ble` / `water_lilygo_tdeck_usb` | BIN |
| RAK4631-compatible / RAK4630-module carrier, experimental | `water_rak4631_ble` / `water_rak4630_ble` | UF2 |

The RAK DX module-name alias is `RAK_4630_LoRaGotchi_DX_ble`, identical to the
existing experimental `RAK_4631_LoRaGotchi_DX_ble`. Read the required
[OLED, controls, carrier and bootloader prerequisites](docs/RAK4630-EXPERIMENTAL.md).
A bare RAK4630 module or a different carrier is not plug-and-play support.

Run from the repository root, selecting one target explicitly:

~~~sh
pio run -e water_heltec_v3_ble -j 2
pio run -e water_heltec_t096_ble -t create_uf2 -j 2
pio run -e RAK_4630_LoRaGotchi_DX_ble -t create_uf2 -j 2
pio run -e water_rak4630_ble -t create_uf2 -j 2
~~~

Outputs are in `.pio/build/<environment>/`. ESP32 BINs are application-only,
not merged installers. UF2 files require the matching board bootloader/layout.
The [owner-board workflow](.github/workflows/water-owner-builds.yml) now requests
both editions on V3, V4 OLED and T096, plus both experimental RAK module aliases.
It does not compile every alias above. Check the exact source SHA and each job;
older successful Water-candidate builds do not validate this changed revision.
Artifacts expire after 14 days and are not releases or hardware acceptance.

## Additional experimental TFT/OLED devices

See the [experimental screen target matrix](docs/EXPERIMENTAL-SCREEN-TARGETS.md).
These additional builds are **experimental and have not been tested on real hardware**.
Screenless and e-ink variants are excluded; optional-display boards require a fitted panel and controls.

## Building

Install PlatformIO, clone the repository, then build the required environment from the repository root. For example:

```bash
git clone <your-repository-url>
cd LoRaGotchi-DX
pio run -e [BUILD ENVIRONMENT]
```
⚠️ The build environment is Case Specific!

Examples:
```bash
git clone <your-repository-url>
cd LoRaGotchi-DX
pio run -e Heltec_t114_LoRaFish_companion_ble -t create_uf2
```
The resulting file will end up in `LoRagotchi-DX-main\.pio\build\Heltec_t114_LoRaFish_companion_ble\firmware.uf2`
NRF52 devices, After the build, enter the board's UF2 bootloader and copy `firmware.uf2` to its mounted drive. 
```bash
git clone <your-repository-url>
cd LoRaGotchi-DX
pio run -e heltec_v4_LoRaFish_companion_ble
```
The resulting file will end up in `LoRagotchi-DX-main\.pio\build\heltec_v4_LoRaFish_companion_ble\firmware.bin`
Upload with PlatformIO using the normal `-t upload` target for supported serial-programmed boards. The T096 uses -t create_uf2 and the UF2 procedure above.
the meshcore.io/flasher also works, scroll to the bottom and select custom device firmware!

### Buzzer pins

LoRaFish buzzer outputs are assigned per board:

| Device | Buzzer pin |
| --- | --- |
| ThinkNode M2 | GPIO5 |
| Heltec WiFi LoRa 32 V3 | GPIO6 |
| Heltec WiFi LoRa 32 V4 OLED | GPIO6 |
| Heltec T114 | GPIO46 / P1.14 |
| Heltec T096 | GPIO45 / P1.13 |

The project tree also retains the wider upstream MeshCore targets and infrastructure from which LoRaGotchi is derived.

## Project history

Development notes from the experimental LoRaFish/LoRaGotchi builds are retained under [`docs/development/`](docs/development/) for reference. The v1.0 release note is under [`docs/release/`](docs/release/).

## Credits

LoRaGotchi DX is by **Robert Rayner / M0YNW** and is based on **MeshCore** by Scott Powell / Ripple Radios. MeshCore provides the underlying mesh transport and substantial portions of the firmware foundation.

See [`NOTICE`](NOTICE) for attribution details.

## License

MIT. See [`LICENSE`](LICENSE).
