# Cardputer: getting started

Short, Cardputer-specific steps. See the [Cardputer device page](../cardputer.md)
for builds and display notes, and the general
[Getting Started](../../../Getting_Started.md) guide for pet behaviour and menus.

## 1. Build

The Cardputer builds are BLE companions that produce an application BIN. For DX:

```sh
pio run -e cardputer_loragotchi -j 1
```

Other editions: `water_m5stack_cardputer`, `air_m5stack_cardputer`,
`land_m5stack_cardputer`, `dxpro_m5stack_cardputer` (see the
[board matrix](../../BUILDING.md#board-and-edition-selection)).

## 2. Flash

The result is `.pio/build/<environment>/firmware.bin`, an application image, not a
complete installer. Back up first and follow
[check the device and protect existing data](../../BUILDING.md#check-the-device-and-protect-existing-data)
and the [install guide](../../BUILDING.md#install-using-the-boards-matching-method).
Use the same environment for building and installing.

## 3. First boot

- Read the Bluetooth PIN on the device's phone-pairing screen and pair from the
  MeshCore app, then set the clock from the app.
- The firmware joins the `#loragotchi-dx` channel automatically (see
  [First Use](../../../Getting_Started.md#first-use)). Add a fish emoji to your
  node name to take part in DX visits.
- The screen auto-off is set to 30 seconds in this build. As on other boards, a sleeping display's first input only wakes it (see the general guide's Button Controls).
- On the new-fish screen choose Scales, Body and Eyes, then select **Start fish**.

## 4. Keyboard controls

| Key | Action |
| --- | --- |
| Arrows (Fn + `;` `.` `,` `/`) or W A S D | Navigate: right/down = next, left/up = previous |
| Enter or Space | Select, save, or the screen's action (long-press) |
| Escape or Backspace | Back, or cancel without saving (double-click) |
