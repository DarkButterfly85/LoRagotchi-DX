# Aquarium eggs and inherited colours (DX implementation)

This contract is implemented on **DX only**. Aquarium/receiver integration must
implement the other end before adoption works. No RX, aquarium or mesh-core
transport modifications are included here. Normal visits remain LFG1.

## User flow

On a fresh pet, or **Options → Reset Pet → Yes**, DX looks for saved **chat
companions** whose original advertised name contains **🥚 (U+1F95A)**. A repeater
with the same marker is not eligible. Refresh adverts/save the contact as usual;
this does not add an automatic network scan or change any node name.

The first candidate is probed. Click selects the next candidate; hold or back
skips to normal pet creation. No candidates after ten seconds means normal
creation automatically. The total adoption window is two minutes (selection does
not extend it). An existing pet, pending successor or ordinary visiting fish does
not open adoption. Existing reset confirmation still guards intentional resets.

Only a matching capability response changes the screen to **Aquarium detected! /
Choose egg in app**. The aquarium app is where the user chooses the egg. Successful
adoption bypasses manual colour selection, not the existing five-minute egg stage.
It works on monochrome DX as well: genes remain stored and travel to colour peers.
The first input on an off display only wakes it. Saving a durably accepted egg
cannot be cancelled halfway; failures retry every five seconds and recover at boot.

## LEG1 text DM contract

Use authenticated MeshCore **contact-addressed text messages** (same transport
as LFG1, potentially routed through repeaters). The receiver/app must send as the
full public key of the selected 🥚 companion, not a different gateway identity.
An emoji is only a discovery hint; it is not a cryptographic capability claim.

```text
DX → aquarium: LEG1|HELLO|<nonce0>|<nonce1>|H1
aquarium → DX: LEG1|READY|<nonce0>|<nonce1>|H1
aquarium → DX: LEG1|EGG|<nonce0>|<nonce1>|<egg-id>|<generation>|H1|<body>|<scales>|<eyes>
DX → aquarium: LEG1|SAVED|<nonce0>|<nonce1>|<egg-id>
```

- All numbers are unsigned decimal; nonce halves span 0..4294967295, egg ID
  1..4294967295, generation 1..65535. No signs, whitespace or extra fields.
- DX generates two random 32-bit nonce halves on every selection. Bind a proposed
  transfer to **full DX public key + nonce pair + egg ID**, with an immutable payload.
- HELLO is version/capability negotiation **and opens the app selection session**.
  Repeated identical HELLO must repeat READY, not create a new session or egg.
  DX makes at most four probe attempts, at least five seconds apart, honouring
  transport estimates up to sixty seconds, inside the fixed two-minute window.
- READY must arrive before EGG. Preserve FIFO when delivering them; if EGG overtakes
  READY it is ignored and the sender must retry. An unsupported peer never gets
  an adoption offer. Retransmitted READY does not reopen or extend the session.
- The app must reserve the egg to one device/session, persist that reservation,
  and retry the **identical** EGG until SAVED. A transport ACK is **not** SAVED.
  Do not silently reassign an ambiguous delivered-but-unacknowledged egg to another
  device: reconcile it using the same transaction first. HELLO/EGG are not chat
  commands users need to copy/paste.
- A skipped/expired session rejects new EGG packets. There is no CANCEL opcode;
  the app should expire its UI session, but keep unresolved delivery state for
  reconciliation. The deadline stops acceptance, not completion of an already
  journaled egg. Retransmissions of the most recently completed payload receive
  SAVED even after reboot/reset, without modifying the pet.
- Successful adoption persists settings and age-zero pet state, reads both back,
  then persists a completed receipt before sending SAVED. Lost first SAVED is
  recovered by resending EGG. The app must retain its own durable egg ledger.

Maximum generated frames are comfortably below the existing text-DM limit (EGG
at maximum field values is under 90 bytes). No binary framing or BLE command was
added. An RX firmware bridge and app integration are still required for a typical
PC-controlled aquarium; this DX build does not make an unmodified RX forward LEG1.

## H1 colour alleles

Each trait remains a byte, but uses an extended, versioned domain:

| Value | Meaning |
| --- | --- |
| 0..5 | Original exact Coral, Tangerine, Gold, Mint, Lagoon, Orchid palette |
| 6 | Mono (not a hue) |
| 8..247 | Hue `(value - 8) × 1.5°`, full saturation/value, rendered as RGB565 |
| 7, 248..255 | Invalid wire/stored genes; some are reserved UI rendering sentinels |

This is **240 hue steps, not arbitrary RGB or saturation/brightness genetics**.
Breeding samples the shortest circular hue arc independently for scales, body and
eyes, including both parent endpoints. Red/blue produces purple/magenta variants,
not muddy RGB averages. Equal parents and solo reproduction retain exact genes.
Mono/colour pairings select one parent's trait with approximately equal chance;
two Mono parents remain Mono. A 180° tie follows the signed parent order.
Existing manual colour controls still offer the original seven choices; inherited
traits are labelled `Inherited`. Opening/cancelling a picker does not change genes;
saving a palette choice intentionally replaces that trait.

Updated COMMITs with fine-hue genes append an optional suffix:

```text
LFG1|COMMIT|<tx>|<fish>|C|<fallback-body>|<fallback-scales>|<fallback-eyes>|<mono-tint>|H1|<body>|<scales>|<eyes>
```

The old fields always contain nearest-palette colours (Mono stays 6). Updated DX
reads H1; old DX/RX sees a valid palette fish. Every retry carries the same frozen
full frame, even if the first packet is lost or local colours change. Aquarium/RX
must explicitly preserve/decode H1 to show the finer shades; unmodified receivers
show the fallback. Plain seven-field and short legacy COMMITs remain supported.

## Names and storage

Only the outgoing **fish label** is sanitised: emoji/presentation/joiner remnants,
protocol separators and controls are removed or separated; whitespace is trimmed,
valid international letters remain, truncation ends at a UTF-8 character boundary,
and an empty result becomes `DX Fish`. Raw node names/adverts/contact names retain
🥚 and fish markers. The built-in display still uses its existing ASCII fallback.

`lorafish.cfg` retains its exact 44-byte palette-compatible prefix, including HAP1
and AQU1. A ten-byte tail is `HUE1` followed by local body/scales/eyes and pending
successor body/scales/eyes. A missing/truncated/invalid tail falls back to the old
palette fields. The pet record layout is unchanged. Older firmware may discard
fine hues when it saves; back up before rollback.

Adoption uses two separate 64-byte checksum-protected receipt banks (`lfegg0.dat`
and `lfegg1.dat`, or distinct `egg0`/`egg1` T-Deck NVS keys). The inactive bank is
written/read back before promotion. A pending intent is replayed at boot; a
completed receipt never recreates the egg. Both corrupt banks disable adoption
without deleting existing pet/config data. Only the latest completed adoption is
retained for ACK replay, not an infinite history; older unsolicited packets still
cannot replace a pet because they lack an active matching nonce. Local raw-flash
corruption/rollback can lose recent state; host fault tests are not physical
power-cut guarantees. Do not erase the filesystem to update.

## Verification / hardware checklist

Host checks cover real parsers, serializers, adoption handlers, radio dispatch and
menu handlers with mocked peripherals: identity/nonce binding, malformed numeric
limits, deadline/skip, no candidate, deleted/reordered contacts, duplicate/reboot
ACK, torn journal/config writes and failed readback. Existing travel, arrival,
reward/cooldown and lifecycle regressions remain applicable.

On hardware, check normal startup of an existing pet, name sanitisation without
losing node markers, visitor breeding and successor colour persistence, then fresh
pet/reset discovery with no 🥚 peer and an unsupported 🥚 peer. With an implemented
receiver, test selection, skip/late packets, adoption, lost SAVED retry, restart,
monochrome storage and colour rendering. Do not claim end-to-end adoption tested
until the aquarium/RX implement this contract and physical radio tests pass.
