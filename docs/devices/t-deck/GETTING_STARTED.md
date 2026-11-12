# T-Deck: getting started

Short, T-Deck-specific steps. See the [T-Deck device page](../t-deck.md) for builds,
display, touch and storage notes, and the general
[Getting Started](../../../Getting_Started.md) guide for pet behaviour and menus.

## 1. Pick a build

- **BLE companion** (pairs with the MeshCore phone app): `LilyGo_TDeck_loragotchi_dx_ble`
  (Water `water_lilygo_tdeck_ble`, Air `air_lilygo_tdeck_ble`, Land
  `land_lilygo_tdeck_ble`, DX-Pro `dxpro_lilygo_tdeck_ble`).
- **USB:** `LilyGo_TDeck_loragotchi_dx_usb` (and the matching `_usb` aliases).

Build exactly one environment, for example:

```sh
pio run -e LilyGo_TDeck_loragotchi_dx_ble -j 1
```

## 2. Flash

The result is `.pio/build/<environment>/firmware.bin`, an application image, not a
complete installer. Back up first and follow
[check the device and protect existing data](../../BUILDING.md#check-the-device-and-protect-existing-data)
and the [install guide](../../BUILDING.md#install-using-the-boards-matching-method).
For the touch diagnostic build, install only its `firmware.bin` through the existing
T-Deck Launcher; do not direct-flash, erase flash, or alter partitions.

## 3. First boot

- On the BLE build, read the pairing PIN from the device's phone-pairing screen and
  pair from the MeshCore app. Set the clock from the app.
- The firmware joins the `#loragotchi-dx` channel automatically (see
  [First Use](../../../Getting_Started.md#first-use)). Add a fish emoji to your node
  name to take part in DX visits.
- Choose the new fish's colours, then select **Start fish** (see the general
  guide's First Use steps).

## 4. Controls

- **Trackball button:** the single user button. Short click = next item or screen,
  double-click = back, long-press (about one second) = select or the screen's action.
  Triple-click toggles quiet mode on boards with a buzzer. See
  [Button Controls](../../../Getting_Started.md#button-controls).
- The keyboard and trackball stay active in the diagnostic build.
- Touch navigation exists only in the `..._touch_test` build (top strip = Back,
  left/right thirds = Previous/Next, centre = Select, horizontal swipe navigates).
