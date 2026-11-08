# Creature compatibility: design

Status: DESIGN ONLY. No firmware code is changed by this document.
Base: `origin/feat/land-edition` at `bbe1a7a` (main does not yet carry the Land registry, so
this doc needs a rebase once Land is merged). Branch: `docs/creature-compatibility`.

Everything marked **R** below was read in the code; **I** marks my inference. Nothing here has
been built or run; flash/RAM numbers other than the quoted Heltec V3 builds are estimates.

## 0. What the code does today (read, not inferred)

- **Registry** (`examples/companion_radio/LoRaFishSpecies.h`): one shared ID space.
  Water 0..14 (15), Air 256..273 (18), Land 512..550 (39), 72 species in total.
  IDs are permanent. `known()` already accepts all three ranges; `editionKnown()` limits a
  *build* to its own range. Water art is compiled into every species build, Air art only in
  Air builds, Land art only in Land builds (sprite dispatch at UITask.cpp ~2111-2140: a Land
  build draws Land + Water, an Air build draws Air + Water, a Water build draws Water only;
  anything else is drawn as the fish).
- **Movement** is already a per-species fact, but only for drawing: `movement()` returns
  Swim / FlyMotion / Flutter / Walk / Crawl. It is *presentation*, nothing in the protocol uses it.
- **Visit handshake** (MyMesh.cpp ~584-770), all text messages starting `LFG1|`:
  `REQ|tx|fid|stage|name` (host parses `%lu|%lu|%u|%23[^\n]`), then `ACK|tx|fid` with a suffix
  chosen by the *host's build*: none = DX, `|S1` = Water, `|S1|A1` = Air, `|S1|L1` = Land.
  The visitor accepts only those exact strings (`acknowledged()`). Only after an accepted
  suffix does it add `|S1|<speciesId>` to COMMIT; otherwise it sends the old nine-field COMMIT
  and the pet is shown as the fish ("FISH FALLBACK"). Air/Land IDs need the matching
  A1/L1 suffix; Water IDs pass with any S1 form. Other replies: `BUSY`, `RECALL`,
  `RETURN|..|CANCEL1`. An unknown `LFG1|..` opcode is silently dropped (the block ends in `return;`).
- So there is **no version field and no visitor-side capability**. The host announces its
  *edition* in the ACK; the host never learns the visitor's edition before COMMIT.
- **Who is eligible to visit** is decided by a name marker only: `loRaFishDXEligible()`
  (UITask.cpp ~2899) calls `LoRaFishText::hasFish()`, which is `hasDiscoveryMarker()`: the
  four legacy fish emoji everywhere, plus Water markers (Water/Air/Land builds), Air markers
  (Air build only), Land markers (Land build only). The code itself says markers are
  "discovery hints only, never proof of habitat".
- Today the *only* compatibility rule is "does the host's build contain my art; if not,
  show the fish". There is no concept of a land animal being unable to visit water.

## 1. Every creature

Columns: **Set** = which registry range / edition it ships in. **Habitat (home)** = where
its own tank is, i.e. what a visitor must be able to reach. **Locomotion** = how it moves.
**Basis**: R = read in code (movement() or the registry comment), I = inferred from the name,
R/I = code gives the motion and the name gives the rest. **‡** = my recommendation differs
from, or adds to, what the code literally says; these are open decisions in section 7.

Locomotion words map to abilities: swim = Swim; walk, crawl = Walk (ground); fly, flutter = Fly.
Code reads: Water: all Swim. Air: Worm and Bug Crawl; Penguin, Flamingo, Peacock, Turkey,
Rooster Walk; Honeybee, Butterfly, Fly Flutter; the rest FlyMotion. Land: Frog, Crocodile,
Lizard, Turtle, Snake Crawl; Dragon, Dragon face, Phoenix FlyMotion; everything else Walk.

| Name | ID | Set | Habitat (home) | Locomotion | Mythic | Basis | Note |
|---|---:|---|---|---|---|---|---|
| Tropical fish | 0 | Water | water | swim | no | R | DX single fish |
| Blowfish | 1 | Water | water | swim | no | R |  |
| Shark | 2 | Water | water | swim | no | R |  |
| Dolphin | 3 | Water | water | swim | no | R |  |
| Whale | 4 | Water | water | swim | no | R |  |
| Seal | 5 | Water | water | swim | no | R | candidate: also walk (haul out) ‡ |
| Shrimp | 6 | Water | water | swim | no | R |  |
| Squid | 7 | Water | water | swim | no | R |  |
| Lobster | 8 | Water | water | swim | no | R |  |
| Crab | 9 | Water | water | swim | no | R | seabed crawler in art; stays water |
| Octopus | 10 | Water | water | swim | no | R |  |
| Jellyfish | 11 | Water | water | swim | no | R | bell drift |
| Shell-dweller | 12 | Water | water | swim | no | R | snail-like sprite |
| Sea star | 13 | Water | water | swim | no | R |  |
| Anglerfish | 14 | Water | water | swim | no | R |  |
| Eagle | 256 | Air | air | fly | no | R |  |
| Bird | 257 | Air | air | fly | no | R |  |
| Owl | 258 | Air | air | fly | no | R |  |
| Duck | 259 | Air | air | fly | no | R | candidate: also swim ‡ |
| Swan | 260 | Air | air | fly | no | R | candidate: also swim ‡ |
| Penguin | 261 | Air | land | walk | no | R | code draws it as a walker; candidate: also swim ‡ |
| Parrot | 262 | Air | air | fly | no | R |  |
| Flamingo | 263 | Air | land | walk | no | R | code: walker |
| Peacock | 264 | Air | land | walk | no | R | code: walker |
| Turkey | 265 | Air | land | walk | no | R | code: walker |
| Rooster | 266 | Air | land | walk | no | R | code: walker |
| Dove | 267 | Air | air | fly | no | R |  |
| Bat | 268 | Air | air | fly | no | R |  |
| Honeybee | 269 | Air | air | flutter | no | R |  |
| Butterfly | 270 | Air | air | flutter | no | R |  |
| Fly | 271 | Air | air | flutter | no | R |  |
| Worm | 272 | Air | land | crawl | no | R | code: crawler |
| Bug | 273 | Air | land | crawl | no | R | code: crawler |
| Dog | 512 | Land | land | walk | no | R |  |
| Cat | 513 | Land | land | walk | no | R |  |
| Horse | 514 | Land | land | walk | no | R |  |
| Cow | 515 | Land | land | walk | no | R |  |
| Elephant | 516 | Land | land | walk | no | R |  |
| Pig | 517 | Land | land | walk | no | R |  |
| Ram | 518 | Land | land | walk | no | R |  |
| Sheep | 519 | Land | land | walk | no | R |  |
| Goat | 520 | Land | land | walk | no | R |  |
| Giraffe | 521 | Land | land | walk | no | R |  |
| Kangaroo | 522 | Land | land | walk | no | R |  |
| Llama | 523 | Land | land | walk | no | R |  |
| Deer | 524 | Land | land | walk | no | R |  |
| Mouse | 525 | Land | land | walk | no | R |  |
| Hamster | 526 | Land | land | walk | no | R |  |
| Rabbit | 527 | Land | land | walk | no | R |  |
| Hedgehog | 528 | Land | land | walk | no | R |  |
| Koala | 529 | Land | land | walk | no | R |  |
| Panda | 530 | Land | land | walk | no | R |  |
| Sloth | 531 | Land | land | walk | no | R |  |
| Otter | 532 | Land | land | walk | no | R | candidate: also swim ‡ |
| Skunk | 533 | Land | land | walk | no | R |  |
| Badger | 534 | Land | land | walk | no | R |  |
| Hippo | 535 | Land | land | walk | no | R | candidate: also swim ‡ |
| Rhino | 536 | Land | land | walk | no | R |  |
| Camel | 537 | Land | land | walk | no | R |  |
| Bactrian camel | 538 | Land | land | walk | no | R |  |
| Bison | 539 | Land | land | walk | no | R |  |
| Frog | 540 | Land | water+land (amphibious) | swim+crawl | no | R/I | amphibious by registry label; name implies |
| Crocodile | 541 | Land | water+land (amphibious) | swim+crawl | no | R/I | amphibious by registry label; name implies |
| Lizard | 542 | Land | land | crawl | no | I | registry says amphibious/reptile; recommend land-only ‡ |
| Turtle | 543 | Land | water+land (amphibious) | swim+crawl | no | R/I | amphibious by registry label; name implies |
| Snake | 544 | Land | land | crawl | no | I | registry says amphibious/reptile; recommend land-only ‡ |
| Unicorn | 545 | Land | land | walk | yes | R | mythic: horse-like, code walks |
| Dragon | 546 | Land | land+air | fly+walk | yes | R/I | mythic: code flies; walk and L+A home are my choice ‡ |
| Dragon face | 547 | Land | land+air | fly+walk | yes | I | mythic: same creature as Dragon (inferred) ‡ |
| Phoenix | 548 | Land | air | fly | yes | R | mythic: code flies; sky home |
| Sauropod | 549 | Land | land | walk | yes | R | listed as mythic by registry; extinct dinosaur, grounded |
| T-Rex | 550 | Land | land | walk | yes | R | listed as mythic by registry; extinct dinosaur, grounded |

Totals: 72 species. Water-only swimmers 15; grounded 40 (36 walk + 4 crawl); sky 12;
amphibious 3; land+sky 2. Mythic (as the registry groups them): 6.

**Mythic choices (explicit).**
- *Unicorn*: land, walk. It is horse-like and the code walks it. No wings, so no flight.
- *Dragon* and *Dragon face*: **land + air** home, walk + fly. The code flies them, so they
  must reach the sky; they also stand on the ground. Home = both so that a Land owner's
  dragon can receive walkers and a sky owner's dragon can receive fliers. Dragon face is a
  portrait of the same creature (I), so it is treated identically.
- *Phoenix*: **air** home, fly (code flies it). Perches on land (the fly rule), so it can still
  visit land hosts, but walkers cannot visit its tank. Alternative in section 7.
- *Sauropod*, *T-Rex*: land, walk. They are extinct animals rather than myth; the registry
  files them as "mythic", so I keep the Mythic flag but they behave as ground animals.
- The Mythic flag changes no rule. It exists for display/rarity and future use.

**Rows I am not sure about** (all flagged ‡ or I above): Lizard and Snake (registry comment
says "amphibious/reptiles"; I recommend land-only because nothing in the name implies water);
Frog/Crocodile/Turtle amphibious (registry label, name agrees); Bug (the name is ambiguous,
the code crawls it, the Air marker list uses the caterpillar emoji); Dragon face; and the
"candidate: also swim/walk" animals Seal, Otter, Hippo, Duck, Swan, Penguin. I did **not**
apply those upgrades because the code does not say so; the owner can switch any of them on
by changing one table row.

## 2. Compatibility model

Firmware-side, data-driven, no emoji. One byte per species in the registry:

~~~
Zone bits:   WATER=1  LAND=2  AIR=4     // used for sets, homes and reach alike
Ability bits SWIM=1   WALK=2  FLY=4  MYTHIC=8   (bit 4 reserved for CLIMB)

struct Traits { uint8_t home; uint8_t abilities; };   // 2 bytes x 72 = 144 bytes of flash
set(id)   = Water / Air / Land by ID range           // already free from the ID
reach(id) = home | (SWIM?WATER) | (WALK?LAND) | (FLY? AIR|LAND)
canVisit(visitor, host) = set(visitor)==set(host)  ||  (reach(visitor) & home(host)) != 0
~~~

Unknown or future IDs use the fish row (Water, Swim), which is what `renderId()` already does.
Invariant for a host test: home is always a subset of reach, and the traits agree with
`movement()` (Walk/Crawl rows have no FLY, FlyMotion/Flutter rows have FLY).

### Rules

| # | Rule | Effect |
|---|---|---|
| R0 | Same set always visits same set | Water-Water, Air-Air, Land-Land keep working exactly as today. |
| R1 | Swim reaches WATER hosts | A water animal visits water and amphibious hosts. |
| R2 | Walk (and crawl) reaches LAND hosts | A land animal visits land, amphibious and land+air hosts. |
| R3 | Fly reaches AIR hosts and LAND hosts | Fliers can visit sky tanks and perch on land. |
| R4 | Fly alone does NOT reach WATER hosts | A bat or eagle cannot visit a shark tank. Fliers get water access only with Swim. |
| R5 | Amphibious (Swim+Walk) reaches WATER and LAND | Frog, Crocodile, Turtle; and their hosts accept both swimmers and walkers. |
| R6 | A walker cannot reach an AIR-only host | "Not every creature that walks can fly." Dog cannot visit Eagle; Eagle can visit Dog. |
| R7 | No Water creature has FLY | "Very few water creatures can fly": in the current list none, so Water-to-Air is closed. |

Outcome by visitor type (cross-set; R0 aside). ✓ = allowed, ✗ = blocked.

| Visitor can | host WATER | host LAND | host AIR | host WATER+LAND | host LAND+AIR |
|---|---|---|---|---|---|
| Swim only (15 Water) | ✓ | ✗ | ✗ | ✓ | ✗ |
| Walk only (40 grounded) | ✗ | ✓ | ✗ | ✓ | ✓ |
| Fly only (12 sky) | ✗ | ✓ | ✓ | ✓ | ✓ |
| Swim + Walk (Frog, Crocodile, Turtle) | ✓ | ✓ | ✗ | ✓ | ✓ |
| Walk + Fly (Dragon, Dragon face) | ✗ | ✓ | ✓ | ✓ | ✓ |

(Swim+Fly would reach everything; no species has it unless Duck/Swan are upgraded.)

Species-pair counts that result (visitor species set, then host set; allowed / all pairs):
Water to Water 225/225; Water to Air 0/270; Water to Land 45/585 (only the 3 amphibious
hosts); Air to Air 324/324; Air to Water 0/270; Air to Land 695/702 (blocked only into the
Phoenix tank by the 7 grounded Air-set birds and bugs); Land to Land 1521/1521; Land to Water
45/585 (only the 3 amphibious visitors); Land to Air 306/702.

### Arguments on the rules I am unsure about

- **R0 (same set always allowed).** For: the grounded Air-set animals (Penguin, Turkey, Worm,
  Bug...) would otherwise be unable to visit their own Air friends, which is a regression for
  every Air player. It also keeps the old "I installed the Air edition, I can see Air friends"
  promise. Against: it makes the habitat model only matter across editions, and it lets a Worm
  visit an Eagle's sky tank. I recommend keeping it; the alternative is a per-species fix
  (give the Air birds home AIR+LAND), which is more data to maintain.
- **R3 (Fly reaches LAND).** Birds, bats and insects land; the sprite already draws fliers
  hovering above a ground line in a land scene. Low risk. Without it, Land owners could never
  receive any Air animal.
- **R4 (Fly does not reach WATER).** The owner's draft rule says fliers may visit water hosts
  "where they can perch or hover". The Water tank is an underwater scene; a honeybee in a
  shark tank is wrong and there is no surface or perch drawn. I recommend: only Swim reaches
  water, so waterfowl are the way in (Duck, Swan after upgrade). Variant B (any flier hovers
  over water) is one line, section 7 item 2.
- **R5 hosts accept both.** An amphibious host is a shore scene: both a swimmer and a walker
  can plausibly meet it. The cost is that Shark can visit Frog and Dog can visit Frog, though
  Shark and Dog still cannot visit each other. That is the intended asymmetry.
- **Climb.** I left it out: it adds a bit but no rule (a climbing animal still reaches LAND).
  Bit 4 is reserved so Koala/Sloth can get it later if the owner wants art/animation only.
- **Symmetry.** Visits are *directional* (the visitor must reach the host's home). A pure
  "share a habitat" rule would let Dog visit Eagle, contradicting the owner's examples.

## 3. How a remote peer tells us its capabilities (the wire)

Two things must not be confused: **can the host draw my art** (art mask, exists today as
S1/A1/L1) and **may I visit this host** (new, from the species traits). A host's *home* is
needed, and a Dog cannot tell its host's home from today's ACK except by edition.

### Phase 0: no wire change at all (smallest possible)

The visitor already receives the host's edition in the ACK. Map it to the host's set and home:

| ACK suffix | Host set | Host home | Art host can draw |
|---|---|---|---|
| none (DX) | Water (fish) | WATER | fish only |
| `S1` | Water | WATER | Water |
| `S1\|A1` | Air | AIR | Water + Air |
| `S1\|L1` | Land | LAND | Water + Land |

Then in the ACK handler, before `prepare()`, call `canVisit(localSpecies, hostSet, hostHome)`.
If false, do what the BUSY branch already does (clear pending/committing/away, `visit.stop()`)
and also send `LFG1|RECALL|tx|fid`: the host's existing RECALL branch with a reserved guest
releases the reservation at once. Show a new message ("CAN'T REACH THAT HOME"). Fish
fallback for missing art stays as it is. Lossiness: an Air-edition host that happens to own a
Worm (really LAND) is treated as AIR, so walkers are refused. That is conservative.
Older builds are untouched: nothing new is sent.

### Phase 1: C1 capability token (needed for DX-Pro, optional before)

Hosts in DX-Pro can hold any species, so the edition no longer says what the host *is*.
Add two small tokens. Each digit is one hex character using the zone bits above.

- Visitor to host: add a second line to REQ: `LFG1|REQ|tx|fid|stage|name\nC1|<set><reach>`
  e.g. a Frog visitor (set Land=2, reach WATER+LAND=3): `C1|23`.
- Host to visitor, only when the REQ carried `C1`: `LFG1|ACK|tx|fid|S1|C1|<set><home><art>`
  e.g. a Dog host (set Land=2, home LAND=2) in a build that carries Water and Land art
  (1+2=3): `S1|C1|223`.
- Host-side refusal: reply `LFG1|BUSY|tx|fid|NC1` without reserving the slot. Legacy visitors
  parse only the prefix and treat it as BUSY; new visitors read NC1 as "not compatible".

**Does it break older builds? No, by construction:**
- Legacy host receiving a new REQ: its parser stops the name at the first newline
  (`%23[^\n]`), so the `C1` line is ignored; it replies with its old ACK; the new visitor
  falls back to Phase 0 logic. (To verify on hardware/CI: that a newline survives the
  MeshCore text path unchanged. If not, send the line as a separate `LFG1|CAP|..` message;
  legacy drops unknown LFG1 opcodes silently, at the cost of one extra packet.)
- Legacy visitor (including every DX-only build) receiving from a new host: no `C1` in the
  REQ, so the host answers with the *legacy* ACK form for its current pet's set (none/S1/
  S1|A1/S1|L1), exactly as today. A new suffix must never be sent to a legacy visitor,
  because `acknowledged()` is a strict whole-string match and would downgrade the visit to
  the fish.
- Unannounced visitors (no `C1`): the host cannot evaluate them. Recommended policy:
  allow, and they are shown as today (species by S1, otherwise the fish). Alternative is deny;
  section 7 item 3. The host should still re-check the species in COMMIT (it can look the ID
  up in its own registry) and answer `RETURN|..|CANCEL1` if the owner chose "deny".
- If old Water/Air/Land test builds need not stay at full fidelity (the docs say no release has been made), the
  REQ line can be dropped and the C1 suffix put straight on the ACK; old species builds would
  then show new-host visitors as the fish. I recommend the REQ line anyway: it costs ~5 bytes.

Budget: REQ ~ 33 + 23 name + 1 + 5 ~ 62 bytes (buffers are 112); ACK ~ 40 bytes (buffer 80).
No change to COMMIT, ARRIVED, RETURN, RECALL or the saved records.

## 4. Replacing the emoji markers

Honest limit: a contact's advert carries only a name, so the visitor does **not** know the
host's species before the handshake. A registry lookup therefore cannot replace the marker for
*discovery*; it replaces it for *compatibility*.

1. **Discovery** stays name-based but is generated from the registry: add one `glyph`
   codepoint column to the species table (72 entries, ~300 bytes). `isWaterMarker`,
   `isAirMarker`, `isLandMarker` (three hand-kept switches) become one lookup
   `speciesForGlyph(code)`. A name is a LoRagotchi tank if it contains any registry glyph.
2. **Compatibility** is decided by the handshake and the traits (sections 2 and 3), never by
   the name. The glyph is also a *hint*: `speciesForGlyph` gives a guessed host species, so
   the picker can mark contacts that probably cannot be visited. The hint never blocks
   sending; the ACK or the host's BUSY|NC1 is final.
3. **Existing contact names** keep working with no rename: 🐟 🐠 🐡 🦈 (fish), the Water/Air/Land
   emoji and 💦 all stay valid markers. Names with several markers use the first glyph for the
   hint. Names with no marker are not listed, as today. Phoenix still has no single-codepoint
   glyph and stays unmarked (comment in LoRaFishText.h).
4. **Which builds see which markers.** Today an Air build ignores Land markers, which would
   hide Land friends it can now visit. New rule: every *species* build recognises the union of
   all glyphs (compatibility is the handshake's job). **DX-only builds keep exactly the four
   fish glyphs and the `><>` display fallback**; there is no reason to change them (they have
   no species to compare).
5. Display fallback for the small fonts: `><>` for fish, [W] / [A] / [L] by the glyph's set
   (replaces the three-way ternary in `display()`).
6. The "Add a Water/Air/Land emoji to your name" notice (UITask.cpp ~3712) becomes
   "Add an animal emoji" in DX-Pro; per-edition text is unchanged elsewhere.
7. `protocolName()` keeps stripping every emoji from the wire name, unchanged.

## 5. DX-Pro: one firmware, every set

### What has to change (IDs do not)

- **IDs: no change.** The ID space is already disjoint and permanent, and `known()` already
  accepts all three ranges. Saves (SPC1, 18 bytes) store the ID, so a pet created in any
  edition loads in DX-Pro.
- **Build flag.** Replace "select one habitat edition" (#error in LoRaGotchiVersion.h) with a
  set mask using the same zone bits (WATER=1, LAND=2, AIR=4; or one PRO flag = all three). `editionKnown(id)` becomes
  `ownsSet(set(id))`. Existing single-set builds keep working as masks of one bit.
- **Art and dispatch.** Include all three sprite headers; the compile-time #if chain at UITask
  ~2111-2140 becomes a per-ID branch (Land ID -> Land sprite, Air ID -> Air sprite, else Water).
- **Menu.** `selectableCount`, `selectionId`, `selectionIndex`, `freshSpecies`, and
  `mystery(seed)` are compile-time constants for one range. For 72 species use two steps:
  pick the **set** (Water / Air / Land), then the species in that set (largest list stays 39,
  the Land length today). Only the species ID is persisted, the set is derived from it, so no
  save-format change. Mystery egg: draw inside the chosen set with the same formula as today
  (set count and base), so an existing seed gives the same animal as in the single-set build.
  The value picker count is a uint8_t and would still hold 73 entries, so a flat list is
  technically possible but not recommended.
- **UI strings** ("CHOOSE LAND PET" etc.) become "CHOOSE PET" with the set name.
- **Breeding** (`editionKnown(guest.species)` at UITask ~993) becomes `ownsSet()`: any set
  the device owns. Cross-set eggs are reachable only through allowed visits.
- **Wire.** A DX-Pro host answers legacy visitors with the legacy ACK of its *current pet's*
  set, and `C1` visitors with section 3. Receiving already accepts every known ID.
- **Targets/CI.** Add `pro_*` aliases for the 16 screen boards, extend
  `test/boards/check_edition_targets.py` and add a `native_pro` test environment.

### Flash and RAM

Measured on Heltec V3 (quoted from the earlier builds, logs in /tmp/land-{water,air,land}_heltec_v3_ble.log):

| Build | Flash used | % of 3,342,336 | Static RAM |
|---|---:|---:|---:|
| Water | 1,346,221 | 40.3% | 174,780 |
| Air | 1,353,845 | 40.5% | 174,780 |
| Land | 1,362,017 | 40.8% | 174,780 |

Air costs +7,624 over Water (its art is 6,912 bytes); Land costs +15,796 (art 14,976 bytes).
So the extra sets cost almost exactly their art, and **RAM is identical** (the masks are
constant data in flash).

**DX-Pro estimate (Heltec V3):** 1,346,221 + 7,624 + 15,796 = 1,369,641, plus runtime
set-dispatch, the two-step menu and the 144-byte trait table, say +5 to 10 KB: **about 1.375
to 1.38 MB, roughly 41-42% of the app partition** (about 1.96 MB spare). RAM about 174,780
plus a few hundred bytes (still ~53%). The static numbers say nothing about heap or stack
during the sprite draws; those are unmeasured.

### What could exceed a limit, per board (app limit from the partition tables)

Quantities below the V3 line are estimates built from the nearest measured numbers.

| Board (16 screen targets) | Chip / app limit | Evidence | DX-Pro verdict |
|---|---|---|---|
| Heltec V3 | ESP32-S3, 3,342,336 | measured Water/Air/Land | **Fits**, ~1.38 MB (41%) |
| M5Stack Cardputer | ESP32-S3, 3,342,336 | DX build measured 1,496,105 (44.8%) | **Fits**, est. 1.53-1.56 MB (~47%) |
| Heltec V4 OLED | ESP32-S3, 6,553,600 | same family as V3 | **Fits**, est. ~21% |
| T-Deck (BLE and USB) | ESP32-S3, 6,553,600 | DX build measured ~1,300,650 (19.8%) | **Fits**, est. ~21% |
| Heltec T190 | ESP32-S3, 6,553,600 | default_16MB table | **Fits**, est. ~21% |
| ThinkNode M2 | ESP32-S3, single app 2,621,440 | README: DX about 42% after repartition | **Fits**, est. ~44% |
| T-Beam 1W, Station G2, Station G3 | ESP32-S3, single app 2,621,440 | last DX builds 1,319,581 / 1,324,353 / 1,325,985 on the OLD 1,310,720 slot | **Fits only on the new single-app table**, est. 1.37-1.42 MB (~53%). They do not fit the old 1,310,720 slot even as plain DX, so DX-Pro adds nothing new to that problem. |
| Heltec T114, Heltec T096, RAK4631, RAK4630 | nRF52840, 712,704 | **no measured edition build in the repo** | **Unknown, the real risk.** DX-Pro adds ~23-33 KB, about 3-5% of the limit. Fits only if today's Land build is more than ~35 KB under 712,704. |
| Wio Tracker L1, L1 1W | nRF52840, 708,608 | no measurement | **Unknown**, same arithmetic with the smaller limit. |

No board is proven unable to fit. No nRF52 toolchain is installed on this machine and no
nRF sizes are recorded in the repo or docs (CI logs need GitHub login I do not have), so I
could not measure them. If an nRF Land build turns out to be within ~35 KB of its limit,
those six boards should keep per-set builds (DX / Water / Air / Land) rather than DX-Pro.
Boards outside the 16 (4 MB min_spiffs ESP32, 229,376-byte repeaters) are DX-only and out of
scope for any species build, so not DX-Pro candidates either.

## 6. Suggested implementation order

1. Traits table + `canVisit()` + host tests (no behaviour change yet): invariants in section 2.
2. Phase 0 visitor gate and the "can't reach" message, Water/Air/Land builds only.
3. Glyph column; one marker lookup; picker hint labels.
4. DX-Pro build flag, sprite dispatch, two-step menu, `pro_*` targets, measure nRF sizes first.
5. Phase 1 `C1` tokens (only needed once a host can hold any species).
Each step is separately shippable; steps 1-3 touch no wire bytes.

## 7. Open decisions for the owner

1. ~~Keep rule R0 (same set always visits same set), or enforce habitats even inside a set?~~ **Decided by owner 2026-11-08: keep R0. A creature can always visit its own habitat group.**
2. May fliers visit water hosts: never (my default), only swimmers (Duck/Swan), or all fliers?
3. Legacy DX hosts and unannounced visitors: allow as fish (my default, no regression) or deny?
4. Which borderline animals get extra abilities: Seal (walk); Otter, Hippo, Duck, Swan, Penguin (swim); Lizard and Snake amphibious or land-only?
5. Mythic homes: Dragon and Dragon face land+air, Phoenix air-only, Unicorn/Sauropod/T-Rex land. OK, or Phoenix land+air?
6. Wire: Phase 0 only for now, or go straight to the C1 token; must old Water/Air/Land test builds stay at full fidelity (REQ second line)?
7. Picker: show contacts whose emoji hints "can't visit" greyed, hide them, or show normally?
8. Should every species build recognise all emoji markers (my default), or only its own?
9. DX-Pro: ship it at all, on which boards, and measure nRF sizes before deciding for those six?
10. DX-Pro menu: set first then species (my default), and mystery egg inside the chosen set or across all 72?
11. Cross-set breeding in DX-Pro: allowed, or only same-set pairs?
12. Wording and name of the edition ("Pro", "All") and the new "can't reach" message text.
