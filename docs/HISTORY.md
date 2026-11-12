# Feature history and testing notes

Moved from the main README. Nothing was removed.

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
 
  
## T190 Water and Air (experimental colour)

On `fix/pet-followup-20261106`, build `water_heltec_t190_ble` or
`air_heltec_t190_ble`; DX remains `Heltec_T190_LoRaGotchi_DX_ble`.
See [T190 commands and hosted selector](docs/BUILDING.md#t190-colour-edition-builds).
These are colour pet targets, not the stock companion-radio environment.
Fixed Age label, now displays appropriate labels for chosen pet species.
