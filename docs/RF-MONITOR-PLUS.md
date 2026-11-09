# RF Monitor+

*Colour screens only. Monochrome and e-ink RF Monitor pages are unchanged.*

On a colour screen the **RF Monitor** page (title `RF MONITOR+ 5m`) gains a small table
of what the pet heard in roughly the **last 5 minutes**:

```
ADV 12 h0.8    ACK 2 h--
DM 4 h3.0      REQ 0 h--
CHAN 999+ h1.0 OTHER 0 h--
```

* **ADV** adverts, **DM** direct messages, **CHAN** channel messages and data,
  **ACK** acknowledgements, **REQ** requests, responses and returned paths,
  **OTHER** everything else (trace, control, raw).
* The number is how many were heard (shows `999+` above 999).
* `h0.8` is the **average hops**: how many repeaters, on average, passed the packet on
  before you heard it (0 = heard straight from the sender). `h--` means none had a
  hop count. Direct-routed packets (for example ACKs on a known path) are counted but
  have no hop figure, so they are left out of the average.

The counts live in memory only (about 200 bytes), are not saved, and start from zero
after a restart. The window slides by minute, so counts fall off after 4 to 5 minutes.

It reads the header of every frame the radio already hands to the existing receive hook
(`MyMesh::logRxRaw`); how packets are received, forwarded or answered is not changed.
Narrow colour screens too small for the table keep the classic page.
