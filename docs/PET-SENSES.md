# Pet senses: mesh weather

*Colour screens only. Monochrome and e-ink screens are unchanged.*

The pet notices how busy the mesh has been. It uses the packet counts that
[RF Monitor+](RF-MONITOR-PLUS.md) already keeps (the last 4 to 5 minutes of adverts,
messages, acks, requests and others) and turns them into one small "mesh weather" level:

| Level  | Packets heard in the last ~5 minutes |
|--------|---------------------------------------|
| quiet  | 4 or fewer                            |
| normal | 5 to 59                               |
| busy   | 60 or more (about 12 a minute)        |

**What you see:** when the mesh *becomes* busy, the awake pet gets a brief sparkle: three
small yellow twinkles around it for about 5 seconds. That is all. Quiet and normal weather
show nothing.

**How often:** the level is only worked out again when the count window rolls on to a new
minute, and the sparkle happens only when the weather changes *to* busy, and at most once
every 3 minutes. A mesh that stays busy gives one sparkle, not a constant light show. Eggs,
sleeping pets, pets that are away and memorials never sparkle.

**What it does not do:** it is purely presentational. It is not saved (about 12 bytes of
memory, gone after a restart), does not change the save file, any radio packet, or how
packets are received, forwarded or answered, and has no effect on food, growth, breeding or
visits.

**Boards:** every colour screen (T-Deck, Cardputer, Heltec T190 and the other colour
displays). Monochrome and e-ink screens return before drawing or counting anything, so
they stay pixel-identical.

Written from scratch for LoRagotchi-DX. Test: `python3 test/ui/check_mesh_weather.py`.
