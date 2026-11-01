# Busy-mesh visits and arrival recovery

This change improves visit setup and explicit recall over ordinary MeshCore
routes. Repeaters need no LoRagotchi modifications. It is not an airtime quota,
an RX backlog redesign, or an over-the-air acceptance result.

## Sender policy (DX)

- REQ, COMMIT and explicit RECALL each allow at most **four queued sends total**
  and **120 seconds** of automatic work per phase. Failed enqueue attempts do
  not consume a queued-send slot; they are paced and still bounded by the phase
  deadline. A missing contact cannot reroute to a different contact index.
- Retries preserve the original transaction, full destination key and request
  text. Every COMMIT repeats the cached original complete appearance.
- Retry delay is `max(backoff, 2 * MeshCore estimate + 2s)` plus random jitter of
  0–25%. Backoff is 10, 20, 40, then 60 seconds. The 60-second cap applies only
  to backoff, **not** to the transport estimate. Saturation and deadlines are
  rollover-safe; an exceptionally long estimate may outlast the phase budget.
- A retry waits for the local outbound queue to drain and the radio to return
  to idle receive mode. Each queued send can receive one fresh response window
  after its observed local TX backlog drains. Unrelated incoming traffic and
  subsequent outgoing traffic do not restart that timer. This is conservative
  queue observation, not a precise
  per-packet transmission-complete callback or a network-wide congestion meter.
- The phase deadline bounds automatic retransmissions; it cannot retract a
  packet already accepted into MeshCore's queue.
- A request that never queued COMMIT ends as **NO REPLY - RETRY**. Once COMMIT
  was queued, expiry instead leaves the visit **UNCONFIRMED**, retaining its
  identity and blocking another visit/breeding. It does not declare the fish
  HOME. Late matching ARRIVED or RETURN still resolves the state.
- Open DX Visit, then hold to recall an unconfirmed visit. RECALL is paced by
  the same policy. Repeated presses during that recall do not reset its budget.
  If recall remains unconfirmed, another explicit recall can be attempted.
  A late ARRIVED during recall does not cancel the recall job.
- Timers and reservation expiry run in `MyMesh::loop()`, not drawing code.
  The DX page displays CALLING, DELIVERING, UNCONFIRMED, RECALLING, or NO REPLY;
  the aquarium no longer shows a normally swimming local fish during COMMIT.

## Arrival confirmation (DX)

MeshCore receipt ACKs and LFG1 acceptance messages are distinct. A transport ACK
for COMMIT does not prove the fish was accepted, so home becomes FISH AWAY only
after the matching application's ARRIVED. No new wire opcode is introduced.

- On accepted COMMIT, the host starts one RAM-only ARRIVED outbox bound to the
  full owner key, transaction and fish ID. It retries from the mesh loop without
  requiring another COMMIT or a display refresh. The existing MeshCore ACK is
  tracked for every successfully queued confirmation, including a zero hash.
- ARRIVED uses the same route-aware jitter, queue/radio gate, four queued sends
  and 120-second budget as setup. Failed enqueue consumes no queued-send slot,
  but is paced and bounded. Duplicate COMMIT cannot reset or bypass this budget,
  even after exhaustion or receipt confirmation.
- A matching ACK for any queued attempt stops the job once. A delayed ACK can
  still settle an exhausted job. No ACK or timeout removes the visitor, grants
  a reward, or claims saved home state. A missing contact never redirects it.
- Starting a return cancels the confirmation job; new intake, cleared session
  identity or reboot also invalidates it. Existing RETURN ACK handling remains.
  Already queued MeshCore packets cannot be retracted; late ARRIVED is ignored
  by a home that has already accepted RETURN.
- Update both DX radios to get the corrected sender timer and independent host
  confirmation retries in either direction. Older peers still understand the
  messages, but retain their own retry limitations. RX firmware is unchanged by
  this follow-up and continues its existing durable capture/fast-return policy.

## Receiver lease (DX and RX)

An uncommitted reservation lasts **300 seconds from the first accepted REQ**.
Duplicate requests do not extend it. This covers the two 120-second setup
phases with a nominal 60-second delivery margin; unbounded queueing can still
outlast it. Expiry releases only a reservation, never an actual visitor or a
durably captured RX record. Expiry is checked on ingress as well as in the loop.

DX retains the cancelled identity until a different visit replaces the slot
or reboot clears session state. RX retains up to four RAM-only cancellation
identities, each for another 300 seconds. A matching late REQ/COMMIT/RECALL gets
a cancellation response instead of resurrecting the reservation. These are
bounded replay guards, not an infinite ledger. An explicit recall of a reserved
but uncommitted slot uses the same cancellation path.

## Wire and storage compatibility

All existing LFG1 opcodes, identity checks, normal RETURN messages and appearance
fields remain. Reservation cancellation adds the optional suffix:

```text
LFG1|RETURN|<transaction>|<fish>|C|CANCEL1
LFG1|RETURN|<transaction>|<fish>|M|CANCEL1
```

Updated DX recognizes the exact suffix from the expected full-key peer and
returns HOME without a completed-visit count, community reward or monochrome
colour effect. Ordinary RETURN still supports a fast successful visit whose
ARRIVED was lost. AQUARIUM1 keeps its existing durable-capture meaning.

Older DX understands the leading RETURN but may count cancellation as a visit;
older RX retains its 30-second reservation lease. **Update both endpoints for
the coordinated policy.** Mixed-version operation retains the old endpoint's
limitations. No new message opcode or repeater support is required.

Home/guest record layout, pet/settings files, and RX journal/LRX/1 layout are
unchanged. RX snapshot save-before-ARRIVED, PC-independent return, upload replay
and existing RETURN retry budgets are unchanged. Cancellation records and DX
retry timers are RAM-only. DX retains its existing **reboot clears travel**
policy; this patch does not provide reboot-safe exactly-once travel.

## Remaining limits

- No full per-peer/global airtime quota, BUSY cooldown, or route-refresh policy.
- RX still has four durable slots; unresolved returns can block intake. Fair
  admission and safe archive/operator recovery are separate work.
- Other immediate receiver responses and existing host RETURN jobs have not been
  converted into a new global traffic scheduler.
- A lost request acceptance can leave the receiver reserved until its lease
  expires; a newly started transaction may receive BUSY meanwhile.
- Physical multi-repeater RF latency, channel loading and device input/display
  behaviour still require testing. Host tests are not a radio benchmark.

## Verification

Run the production-handler checks with the matching RX checkout:

```sh
python3 test/ui/check_busy_mesh.py ../loragotchi-rx-busy-mesh
python3 test/ui/check_arrival_recovery.py
python3 test/ui/check_dx_handlers.py
python3 test/ui/check_dx_colour_retries.py ../loragotchi-rx-busy-mesh
python3 test/ui/check_dx_storage.py
python3 test/ui/check_menu_navigation.py
python3 test/ui/check_return_menu.py
python3 test/ui/check_emoji_dx.py
```

The busy-mesh harness compiles actual handlers and scheduler functions with
ASan/UBSan, controlled clocks, and mocked radio/storage boundaries. It checks
lost/late/reordered messages, queued and failed sends, full-key routing after
contact changes, jitter, clock wrap, reservation boundaries, cancellation
effects, and the production RX's durable fast-return path after a 110-second
acceptance delay. The colour test passes the real retry through RX and the
Aquarium decoder/SQLite store. Storage tests retain the existing boot policy.

For hardware testing, start with normal bidirectional DMs, then one direct
visit, then a repeater route. Exercise recall after intentionally missing a
confirmation, radio loss longer than the retry window, display off throughout
setup, and another visitor after reservation expiry. Never generate a traffic
flood on a shared mesh to test this feature.
