# Range Check

*Colour screens only. Monochrome and e-ink pages are unchanged.*

**What it tells you:** "Can my pet reach anyone from here?" - one of
**GOOD**, **OK**, **WEAK** or **NONE**.

## How to use it

1. Go to the **RF Monitor** page (click through the main pages, or Options > RF Monitor).
2. On colour screens it shows `L:RANGE CHECK` in the top right. Do the long press /
   Enter / Select press you use for "open".
3. The Range Check page says **CHECKING** for 10 seconds, then the verdict, how many
   repeaters answered and the best RSSI / SNR.
4. Long press again to re-check (at most one check every 20 seconds). A click or
   double click goes back to the RF Monitor.

## What it sends

One ordinary MeshCore *node discover* control packet: the same small zero-hop packet
the stock Discovery page sends, asking **repeaters** to answer. Nothing new was added
to the protocol and no packet format changed. Zero-hop means it is never forwarded.
Repeaters answer with a short reply (they limit themselves to 4 replies per 2 minutes).

Only **repeaters** answer a discover packet. Other pets, phones and companions do not,
so "NONE" means "no repeater heard you", not "nobody is nearby".

## How the verdict is decided

Each reply is graded by the weaker of how well you heard it (RSSI) and how well the
repeater heard you (SNR, carried in the reply). The best reply in the 10 second window
counts.

| Verdict | Needs |
| --- | --- |
| GOOD | RSSI >= -100 dBm and SNR >= 4 dB |
| OK | RSSI >= -112 dBm and SNR >= -3 dB |
| WEAK | anything heard that is worse |
| NONE | no repeater answered in 10 seconds |

Thresholds are a guide, the same for every spreading factor. Nothing is saved.

Not shown on the LilyGo T-Watch S3 (it has its own touch navigation).
