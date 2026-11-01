# Host-initiated returns and community aquariums

This change is confined to ordinary LoRagotchi-DX. It does not implement a PC
aquarium, multi-visitor receiver, USB/BLE/WLAN bridge or new shared MeshCore protocol.
Receiver firmware can reuse the existing encrypted/contact-addressed `LFG1` text
exchange. A regular DX tank still has one visitor slot; a community receiver owns
its own bounded multi-visitor table.

## Receiver contract

```text
Owner DX                  Community receiver               Aquarium PC
REQ|tx|fish|stage|name --> reserve capacity
                      <-- ACK|tx|fish
COMMIT|tx|fish|C|...   --> capture snapshot + return job
                      <-- ARRIVED|tx|fish
                          export snapshot ----------------> persist display copy
                          wait a few seconds
                      <-- RETURN|tx|fish|C|AQUARIUM1
pet remains at home                                        copy remains on display
```

Every line on the radio begins with `LFG1|`; omitted above for readability.
For example, the complete reward-bearing return is:

```text
LFG1|RETURN|7|8|C|AQUARIUM1
```

- Preserve the owner's full 32-byte public key, transaction ID and fish ID. Route
  replies to that identity, never a display name or mutable contact-list position.
- `REQ` carries a stage (`0` fry, `1` young, `2` adult, `3` elder) and bounded name.
  A full `COMMIT` is `LFG1|COMMIT|tx|fish|mode|body|scales|eyes|monoTint`, with
  `C`/`M` mode, colour indices 0–6 and a 16-bit RGB565 mono tint. Some retries are
  only `LFG1|COMMIT|tx|fish`; retain appearance already captured for that transaction.
- Send `ARRIVED` after accepting the committed fish. Start the short-stay timer
  once, not again on duplicates. A few seconds is a receiver policy, not a radio
  delivery deadline. Use `BUSY|tx|fish` when intake/storage is unavailable.
- Return mode **C** preserves the owner's colours even if the receiver itself has
  a monochrome display: the destination is the colour PC aquarium.
- Add **AQUARIUM1** only for an accepted community-aquarium visit. The exact suffix
  is required for the bonus; `C`, `M`, unknown or malformed suffixes still use the
  legacy return behavior but do not qualify for the bonus. No extra opcode/ACK is
  needed. Existing DX revisions parse the preceding fields and ignore this suffix.
- The marker is a claim by the authenticated visit destination, **not certification
  of its software or proof of PC persistence**. The receiver must make that claim
  honestly. Fish emoji remain a discovery convention, not an aquarium identity.
- Keep the radio return job independent from PC connectivity. Persist a snapshot
  before acknowledging capture; export/replay it across USB, BLE or a real WLAN
  endpoint/explicit bridge. PC acknowledgement should mean durable copy storage.
  Do not strand a pet waiting for the PC, and do not delete its display copy on return.
- Retransmit returns using MeshCore's delivery ACK and estimated timeout. A queue
  success is not delivery; a transport ACK is not a new application-level HOME
  receipt. Retain bounded completed transactions so late COMMIT/RECALL cannot
  create another fish or bonus. Receiver reboot recovery is its own responsibility.
- Advertise as a companion/chat contact with a supported fish emoji and ensure the
  owner has saved it. USB, WLAN and BLE capabilities are properties of the receiver,
  not features added by this DX change.

## Ordinary DX behavior

**Options → Send visitor home** queues up to four attempts. Each waits at least
10 seconds, or the radio's longer estimated timeout, before retrying. A matching
ACK for any queued attempt (including a late ACK after the retry budget expires)
clears the visitor. Queue failure or an unavailable owner never clears it. A user
or the owner can explicitly retry an unconfirmed return. Returning/unconfirmed
visitors are not available for breeding.

REQ/COMMIT/RECALL are bound to the visitor's full owner key and transaction;
ACK/ARRIVED/BUSY/RETURN are bound to the selected destination key and transaction.
During a return, duplicate REQ/COMMIT do not bypass retry timing. After confirmed
return, they replay RETURN without resurrecting the guest. The last completed
guest remains a tombstone until the next visitor; this is not an indefinite ledger.

Owners accept unsolicited RETURN while pending, committing or away. A pending-only
cancellation gives no completed-visit credit. Completion while committing or away
counts once even if ARRIVED was lost or both packets arrived between care-loop
ticks. Duplicate RETURN and late ARRIVED cannot repeat the reward or hide the fish.

The reward is +5 Happy, saturating at 100, once per six powered-on hours. Only a
living, initialized pet is eligible. Cooldown visits are consumed, not banked. Full
Happy still consumes the allowance. The per-device cap survives pet reset/succession
and is independent from meal cooldown, sleep and screen rendering.

## Persistence and compatibility

- DX travel remains session-only: reboot repatriates the local pet and clears the
  visitor/retry state. Ordinary DX does not persist retry jobs like a dedicated RX.
- ESP32 retains the fish ID from the exact old 48-byte home record or the new
  layout; unknown/truncated sizes safely reset it. nRF52's existing non-persisted
  DX session identity policy is unchanged. Pet progress storage is separate.
- The original 24-byte settings prefix and 12-byte `HAP1` timing tail are unchanged.
  At offset 36, an eight-byte `AQU1` tail stores little-endian magic `0x31555141`
  followed by a uint32 remaining cooldown in milliseconds, valid from 0 to 21600000.
  Legacy settings with no tail start at zero; a present damaged/unknown tail uses
  the full cooldown conservatively. Old firmware ignores/drops the extension.
- Awards request immediate cooldown/pet saves through the existing persistence
  path; elapsed cooldown uses five-minute checkpoints. Retransmits cause no reward
  saves. Healthy checkpoint rollback can lengthen the remaining cooldown, not
  shorten it. Storage failures retry after five seconds; these files are not an
  atomic multi-record journal, so physical power-loss durability is not guaranteed.

## Verification and integration checklist

Host tests: `test/ui/check_dx_handlers.py`, `check_dx_storage.py`,
`check_return_menu.py`, `check_aquarium_bonus.py`, plus existing native and UI
regressions. They exercise production handlers, timer boundaries, loss/reordering,
identity/transaction mismatch, bounded retries, queue/storage failures, migration,
and mono/sound menu variants using mocks. They are not live-radio evidence.

For hardware: send a fish between two radios, send it home from the host, exercise
owner recall and an unavailable owner, then use a community receiver with the exact
marker. Check +5 once, no reward on a second visit or duplicate RETURN, retained cap
after restart, a persistent PC copy and an autonomous return with PC disconnected.
Builds for V3, V4 OLED and T096 validate compilation; physical tests remain separate.
