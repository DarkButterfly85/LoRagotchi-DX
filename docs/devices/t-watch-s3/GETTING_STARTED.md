# T-Watch S3: getting started

Short, watch-specific steps. For the full picture see the
[T-Watch S3 device page](../t-watch-s3.md) and the general
[Getting Started](../../../Getting_Started.md) guide. The T-Watch S3 is a
DX-only target and is **untested on hardware**.

## 1. Pick a build

| Build environment | Use it when |
| --- | --- |
| `TWatch_S3_LoRaFish_companion_ble` | SX1262 watch, paired with the MeshCore phone app (80 MHz, aquarium at about 30 frames a second). |
| `TWatch_S3_LoRaFish_standalone` | SX1262 watch with no Bluetooth, for longer battery life (40 MHz after boot, aquarium at 10 frames a second). |
| `TWatch_S3_1280_LoRaFish_companion_ble` | SX1280 (2.4 GHz) watch; starts on 2400.5 MHz / 406.25 kHz / SF11 / CR8. |

Both SX1262 builds share the same stored data, so you can switch between them
without losing your fish, contacts or settings.

## 2. Flash

Back up first (see [check the device and protect existing data](../../BUILDING.md#check-the-device-and-protect-existing-data)),
then build and flash over USB with the environment you chose, for example:

```bash
pio run -e TWatch_S3_LoRaFish_companion_ble -t upload
```

## 3. First boot

- Hold the side button for 2 seconds to turn the watch on (6 seconds turns it off).
- On a BLE build, open the **Phone pairing** screen for the Bluetooth PIN and pair
  with the MeshCore app. The PIN is chosen at random each time the watch starts,
  unless one has been saved. The no-Bluetooth build shows "No PIN configured".
- Set the clock from the MeshCore app while running the BLE build. The watch's
  clock chip keeps the time across reboots and reflashing, and the no-Bluetooth
  build takes its time from it.
- Add a fish emoji to your node name in the app to be found for DX visits. A
  start-up reminder or channel warning is dismissed by a tap, swipe or side-button
  press.
- Choose the new fish's colours (Scales, Body, Eyes), then hold on **Start fish**.
  The egg hatches after 5 minutes.

## 4. Controls at a glance

- **Tap the right / left half:** next / previous screen, item or value.
- **Tap the top area:** back (or cancel in a value picker).
- **Swipe left or right:** next or previous main screen. **Swipe down or up:** next or previous item or row.
- **Hold a finger still for about a second:** the screen's action; open or save.
- **Side button, short press:** next screen or item, and wakes the screen. Taps are ignored while the screen is off.
- **Rescue mode:** hold a finger on the screen during the first 8 seconds after start-up.

The full gesture table, screens and menus are on the [device page](../t-watch-s3.md#controls).
