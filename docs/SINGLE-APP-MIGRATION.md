# Experimental single-app layouts: Station G2, Station G3 ESP32, T-Beam 1W

Only their LoRagotchi DX profiles and explicit Water/Air aliases use
`variants/loragotchi_experimental/single_app.csv` in the shared `main` source.
Generic MeshCore companion/repeater/server profiles
and every other LoRagotchi board keep their existing layouts. All three actual
board JSON definitions specify ESP32-S3 with 16MB flash, not a generic 4MB ESP32.
RF pins/power, GPS, PSRAM, features and existing optional-sensor choices are
unchanged. The rejected no-inline compiler flags are absent.

The prior Arduino default table had app0 at 0x10000 (0x140000 bytes) and
app1 at 0x150000 (0x140000). The new sole **factory** app0 spans
0x10000..0x28ffff (0x280000 = 2,621,440 bytes). No OTA app or otadata partition
remains; 0xe000..0xffff is unused. NVS remains 0x9000/0x5000, SPIFFS
0x290000/0x160000, coredump 0x3f0000/0x10000. Flash above 4MB stays unused:
there is no need to move/resize saved-data partitions to gain app headroom.
The explicit upload maximum equals the app slot, not the chip capacity;
PlatformIO also derives its size check from the generated table. OTA/dual-app
updates and OTA rollback are no longer available for these profiles.

## Migration is not an ordinary application update

**No devices have been flashed or hardware-tested for this change.**
An application-only firmware.bin CANNOT replace the installed partition table.
An old app/table may still boot from app1; never assume an app-only BLE/web
flasher changed the table or chose app0. Do not install an oversized app against
the old 1,310,720-byte slots. No generic flashing command is supplied: verify
the actual board, flash capacity, installed table, compatible bootloader and
flash encryption/secure-boot state before a board-specific wired migration.

Before any write, export identity/keys, settings, channels, contacts and pet data,
and retain a full flash backup plus original table/bootloader/app images and
a verified recovery route. Backups contain private keys: store them privately.
Preserved offsets reduce migration risk but **do not guarantee retention**.
Current firmware calls SPIFFS.begin(true) and can format the filesystem if
mounting fails. Full-chip erasure, filesystem uploads or a merged installer
padding across data sectors can destroy saved state. Do not blindly write a
combined image over NVS/SPIFFS or restore old app1 over expanded app0.

A later migration must install and independently read back the matching table
(normally at 0x8000), compatible bootloader and factory app at 0x10000 without
unintended data-sector writes; do not mix commits. Rollback requires restoring
a compatible old table AND fitting app images, not selecting a previous OTA
slot. Physical migration/reboot/data-retention and recovery tests remain
outstanding. No runtime/RF/display or hardware acceptance is claimed.
