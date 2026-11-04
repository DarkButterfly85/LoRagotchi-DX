> **Station G2 / Station G3 ESP32 / T-Beam 1W LoRagotchi:** these profiles now use
> a larger single factory app (no OTA). App-only updates do not migrate tables.
> Back up first; see [migration/data-loss risks](docs/SINGLE-APP-MIGRATION.md).

# LoRaGotchi-DX — DX, Water and Air editions

**Build from `main`, then select your board and DX, Water or Air edition.**
Use the [single-source build guide and board/edition table](docs/BUILDING.md);
old feature/fix branches are history, not separate build sources.

Current product source candidate: **v1.1.0**, separate from underlying MeshCore
**v1.18.0** and the **Water v1** species registry. This version was already chosen
in the supplied in-progress source; it is not a claim that a v1.1.0 release exists.
The splash now reads **DX v1.1.0**, **WATER v1.1.0** or **AIR v1.1.0** from one shared header.
Historical v1.0 release notes remain historical.

**Existing target names stay DX by default.** Water is opt-in through the explicit
aliases in the [board/edition table](docs/BUILDING.md#board-and-edition-selection). DX retains the original fish art, four fish-name markers, five-row
Display menu and colour setup; Water adds 14 species, the new-game chooser and
Water markers. Both use the same mesh transport and compatible saved prefix.
See [Water controls and compatibility](WATER-EDITION.md).

**Air source candidate:** explicit air_* aliases select all 18 requested Air
animals, including penguin and worm, with mono/colour sprites and bounded
flight/ground motion. Existing targets remain DX/Water. Read
[Air IDs, controls, saves and negotiated fish fallback](AIR-EDITION.md) before
mixed-edition tests. Earlier Air-stack builds passed hosted compilation; the combined integration
requires its own exact-revision checks. Physical hardware acceptance remains unverified.

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
    - Touchscreen
 
  
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
| LilyGo T-Watch S3 (BLE) | TWatch_S3_LoRaFish_companion_ble
| LilyGo T-Watch S3 (no Bluetooth) | TWatch_S3_LoRaFish_standalone
| LilyGo T-Watch S3 SX1280 2.4 GHz (BLE) | TWatch_S3_1280_LoRaFish_companion_ble

## Additional experimental TFT/OLED devices

See the [experimental screen target matrix](docs/EXPERIMENTAL-SCREEN-TARGETS.md).
These additional builds are **experimental and have not been tested on real hardware**.
Screenless and e-ink variants are excluded; optional-display boards require a fitted panel and controls.

## Building

Start with the [main-based DX / Water / Air build guide](docs/BUILDING.md).
It lists all 15 Water and 15 Air aliases beside their DX board targets.
The examples below are additional DX examples; environment names are case-sensitive.

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

### LilyGo T-Watch S3

This section covers the T-Watch S3 builds: how the watch differs from the other boards, and how its touch controls work with each screen and menu. The menus, settings and pet rules are the same as on every other board; see [Getting Started](Getting_Started.md) for the full details of each item, the pet itself (growth, meals, hygiene, sleep and breeding), DX visits and aquarium eggs.

#### What is different on the watch

- **Touch controls.** The watch has a touch screen and a single side button, so it uses taps, swipes and holds instead of the click, double-click and long-press of the other boards (see Controls below).
- **Full-screen colour aquarium.** The aquarium fills the screen with the Cardputer's colour tank scenery (water, light, reef, sand and seaweed). The fish wanders around the tank: it glides to new spots, hovers with a few bubbles, and now and then darts.
- **Other screens are centred**, with their usual 128-pixel-wide layout scaled up to the width of the 240x240 screen.
- **No buzzer**, so the Sound menu is hidden.
- **No GNSS receiver**, so the GNSS page and the GNSS Monitor row in Options are left out. To put a position in your adverts, see Position in adverts below.

#### Builds

| Watch | Build environment | Notes |
| --- | --- | --- |
| T-Watch S3 (SX1262) | `TWatch_S3_LoRaFish_companion_ble` | MeshCore BLE companion for the phone app. 80 MHz, aquarium at about 30 frames a second. |
| T-Watch S3 (SX1262) | `TWatch_S3_LoRaFish_standalone` | No Bluetooth, for longer battery life. Drops the CPU to 40 MHz once booted, pauses briefly while the screen is off, and keeps the aquarium at 10 frames a second. |
| T-Watch S3 (SX1280, 2.4 GHz) | `TWatch_S3_1280_LoRaFish_companion_ble` | MeshCore BLE companion. 80 MHz, aquarium at about 30 frames a second. Starts on 2400.5 MHz / 406.25 kHz / SF11 / CR8. |

Build and flash over USB with, for example:

```bash
pio run -e TWatch_S3_LoRaFish_companion_ble -t upload
```

Without a phone app, the no-Bluetooth build takes its time from the watch's clock chip, which keeps time across reboots and reflashing once it has been set (for example from the MeshCore app while running the BLE build). Both SX1262 builds share the same stored data, so you can switch between them without losing your fish, contacts or settings.

#### Controls

| Gesture | Main screens (Aquarium to RF Monitor) | Lists (Options, Display, DX contacts, Send advert, Reset) | Rows and value pickers (settings) |
| --- | --- | --- | --- |
| Tap the top area (above the header, or the header itself) | Back to the Aquarium (from RF Monitor, back to Options) | Back to the screen it was opened from | Back to the parent menu; in a value picker, cancel without saving |
| Tap the right half | Next screen | Next item | Next row; in a value picker, next value |
| Tap the left half | Previous screen | Previous item | Previous row; in a value picker, previous value |
| Swipe left / right | Next / previous screen | - | - |
| Swipe down / up | - | Next / previous item | Next / previous row or value |
| Hold a finger still for about a second | The screen's action (for example, clean the tank, or open the DX contact list) | Open or carry out the highlighted item | Open the highlighted row's value picker; in a value picker, save |
| Short press of the side button | Next screen (and wakes the screen) | Next item | Next row or value |

- **Changing a setting:** browsing never saves anything. On a screen with rows (for example Schedule and Time), move to the row you want, then hold to open its value picker. Tap or swipe to choose a value, then hold to save it, or tap the top area to cancel. Brightness, Firmware theme and Game rendering open their value picker straight away.
- **Options:** Options is one of the main screens and also a list. Taps and up or down swipes move the highlight; left or right swipes move to the next or previous screen.
- **Start-up notices:** the watch may show a reminder to add a fish emoji to your node name, or a warning that the `#loragotchi-dx` channel could not be joined (see Getting Started). A tap, swipe or side-button press dismisses one notice and does nothing else.
- **Aquarium eggs:** on the AQUARIUM EGGS screen (see Getting Started), tap either half to select another tank, and hold or tap the top area to skip. Swipes do nothing on that screen.
- **Waking the watch:** taps are ignored while the screen is off, so a sleeve cannot wake it. Press the side button to wake it.
- **Power:** hold the side button for 2 seconds to turn the watch on, and for 6 seconds to turn it off. When the battery runs low (about 3.1 V) the watch switches itself off, unless it is charging.
- **Hints on screen:** the footer of each screen except the aquarium shows "<tap back" and "tap forward>", for the left and right halves. Above it, most screens show what a hold does there, such as "LONG HOLD:OPEN", "LONG HOLD:SELECT", "LONG HOLD:SEND" or "LONG HOLD:RECALL". On the Guess Game, "TAP:SWAP VALUE" switches between HIGHER and LOWER, and "HOLD:PICK" makes your guess. The start-up notices show "TAP TO DISMISS", and the aquarium eggs screen shows "Tap next/Hold skip".
- **Rescue mode:** holding a finger on the screen during the first 8 seconds after start-up opens MeshCore's serial rescue mode, the same as a long press on the other boards.

#### Main screens

Swipe left or right to move through the main screens in this order. Tapping the right half also moves forward, as far as Options, where taps move the Options highlight instead.

1. **Aquarium.** Your fish in its tank. The header shows the node name, battery and time; the footer shows the fish's stage, the number of packets heard (PKT) and unread messages (UNR). Pop-ups appear when something happens on the mesh: "* MESSAGE *" for a received message, "* SENT *" for an acknowledged send, "* HELLO! *" for a new contact, and "* EVOLVED! *" when the fish grows. **Hold** to clean the tank when there is waste in it.
   - *Egg:* a new fish starts as an egg, with a grey "HATCHING IN m:ss" countdown above the footer. It hatches after 5 minutes.
   - *Sleeping:* during the sleep hours set in Schedule and Time, the fish sleeps and the footer reads "Sleeping".
   - *Visitor:* a fish visiting from another LoRaGotchi DX node swims alongside yours, with its name shown.
   - *Memorial:* after 7 days the fish reaches the end of its life. Five minutes later the next generation starts as an egg: one bred with a visitor if there is one, or else one the fish lays itself.
2. **Stats.** Age, happiness, generation (G1, G2 and so on), mesh events (RF), messages (Msg), acknowledgements (ACK), and whether a phone is connected (BLE ON or OFF).
3. **Clock.** Local time and date, using the UTC offset from Schedule and Time. The header shows PHONE while the app is connected and MESH otherwise. The bottom line reads "RTC + LOCAL OFFSET" once the clock has been set, or "build-time fallback" if it has not.
4. **Phone pairing.** The Bluetooth PIN for pairing with the MeshCore app. The BLE builds choose a new random PIN each time the watch starts, unless a PIN has been saved on the watch, so use the one shown on this screen (see the BLE pairing PIN section of Getting Started). The no-Bluetooth build has nothing to pair, so it shows "No PIN configured".
5. **DX Visit.** Send your fish to visit another LoRaGotchi DX node. **Hold** to open the contact list, which only shows contacts with a fish emoji in their name. Tap either half, or swipe down or up, to choose a tank, then **hold** to send the fish. While it is away the screen reads "FISH AWAY"; open the contact list and **hold** again to call it home. Other messages include "CALLING...", "DELIVERING...", "NO REPLY - RETRY" and "NO FISH TANKS". Tap the top area to go from the contact list back to DX Visit. A sleeping fish cannot travel.
6. **Options.** The settings menu (see below). Tap either half, or swipe down or up, to move the highlight; **hold** to open the highlighted item.
7. **RF Monitor.** Signal strength (RSSI) and signal-to-noise ratio (SNR) of the last packet heard, a graph of recent signal strength, the battery level, and the time since the last packet.

#### Options

Tap the top area on any of these screens to go back to Options.

| Item | What it does |
| --- | --- |
| Send Advert | Opens Send advert with three choices: Local (zero-hop), Flood (multi-hop) and Back. Tap or swipe to choose, then **hold**. Opening it sends nothing. |
| Guess Game | Five rounds of higher or lower. Tap, or swipe down or up, to switch between HIGHER and LOWER, then **hold** to guess whether the next number will be higher or lower. Each correct guess adds one happiness point. After five rounds, **hold** to play again. |
| Breed with visitor | Only appears when your fish and a visiting fish are both Adult or Elder and no egg is already waiting. **Hold** to store an egg whose colours are inherited from the two parents. |
| Reset Pet | Opens "Start a new egg?" with Cancel highlighted. Tap or swipe to highlight "Yes, reset pet", then **hold** to confirm. Confirming starts a new egg at generation 1 but keeps your display and schedule settings; you then choose the new fish's colours. |
| Display | Opens the Display menu (below). |
| Schedule and Time | Three rows: **Sleep** and **Wake** set the hours of the fish's nightly sleep (set them the same to keep it awake all day), and **UTC offset** sets your time zone as an offset from UTC, in 15-minute steps. There is no automatic daylight saving: change the offset when your clocks change. |
| RF Monitor | Opens the RF Monitor screen. |
| Send visitor home | Only appears while a visiting fish is in your tank. **Hold** to send it back to its owner. |

#### Display menu

Tap either half, or swipe down or up, to move the highlight; **hold** to open the highlighted item. Tap the top area to go back.

| Item | What it does |
| --- | --- |
| Screen timeout | Three rows: **Awake** and **Asleep** set how long the screen stays on (15s, 30s, 1m, 2m, 3m or Always) while the fish is awake or asleep. **Dim after** (15s, 30s or 60s) sets how soon an always-on screen dims when you are not using it. |
| Brightness | 25%, 50%, 75% or 100%. |
| Firmware theme | Midnight, Paper, Lagoon or Sunset. |
| Fish color | Rows for the fish's **Scales**, **Body** and **Eyes**. Move to a row and **hold** to open its colours (Coral, Tangerine, Gold, Mint, Lagoon, Orchid and Mono), then **hold** again to save. When you start a new fish this screen appears on its own as "NEW FISH", with a fourth row, **Start fish**: move to it and **hold** when you are happy with the colours. Tapping the top area leaves without starting the fish; Fish color stays available here until you do. |
| Game rendering | **Smooth** or **Simulation**: how often the aquarium is redrawn. Simulation redraws less often. |

#### Position in adverts

The watch has no GNSS receiver, but it can still share a position. On a BLE build, set your position in the MeshCore app and turn on location sharing in adverts there. The watch saves the position, keeps it after a reboot, and includes it in its adverts.

#### Credits

The hardware support (power, display, touch, side button and the SX1280 radio) is ported from the T-Watch edition of [Meck](https://github.com/pelgraine/Meck) by pelgraine.

The project tree also retains the wider upstream MeshCore targets and infrastructure from which LoRaGotchi is derived.

## Project history

Development notes from the experimental LoRaFish/LoRaGotchi builds are retained under [`docs/development/`](docs/development/) for reference. The v1.0 release note is under [`docs/release/`](docs/release/).

## Credits

LoRaGotchi DX is by **Robert Rayner / M0YNW** and is based on **MeshCore** by Scott Powell / Ripple Radios. MeshCore provides the underlying mesh transport and substantial portions of the firmware foundation.

See [`NOTICE`](NOTICE) for attribution details.

## License

MIT. See [`LICENSE`](LICENSE).

## Air edition build targets

Use the existing GitHub firmware-build policy; do not run every inherited target.
The manual Air owner workflow selects these environments and their DX/Water
controls after host checks (publication/CI permission is still required):

- air_heltec_v3_ble — ESP32 application BIN
- air_heltec_v4_oled_ble — ESP32 application BIN
- air_heltec_t096_ble — nRF52 create_uf2

Additional aliases mirror Water: air_thinknode_m2_ble, air_m5stack_cardputer,
air_heltec_t114_ble, air_lilygo_tdeck_ble, air_lilygo_tdeck_usb,
air_rak4631_ble and air_rak4630_ble. They inherit unchanged hardware, RF and memory
profiles, not a hardware acceptance claim. Details and remaining gates:
[AIR-EDITION.md](AIR-EDITION.md).
