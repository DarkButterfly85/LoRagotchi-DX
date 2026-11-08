# LoRaGotchi FAQ

## What is LoRaGotchi?
A virtual pet aquarium that runs on a LoRa radio board. It is built on top of MeshCore, the open-source mesh firmware, so your device still works as a normal MeshCore companion (Bluetooth or USB) for messages and contacts.

## Do I need MeshCore first?
No. The firmware is a MeshCore build with the pet on top. You can flash LoRaGotchi without losing your MeshCore settings, channels or contacts.

## Which editions are there?
- **DX:** the original fish-only aquarium, with fish visits between devices.
- **Water:** 15 animals, including fish and an Anglerfish, with its own new-game egg.
- **Air:** 18 animals, selected with a Choose Air Pet option.

All editions come from the same source. You pick the edition when you build the firmware. Land is a future idea, not available yet.

## Which boards are supported?
The list changes as boards are tested. See the README section "Supported LoRaGotchi targets", or the list of release files once a release is published.

## Where do I get firmware?
Pre-built files are published on the GitHub Releases page for each version tag. Tags with a hyphen (for example `v1.1.0-rc1`) are test builds (pre-releases). Each release includes a `SHA256SUMS` file so you can check your download.

## How do I flash it?
Use the flashing method for your board from the Getting Started guide. ESP32 boards use the full-flash `-merged.bin`. nRF52 boards use the `.uf2` or the DFU `.zip`.

## What is the Bluetooth PIN?
By default, LoRaGotchi picks a random six-digit PIN each boot and shows it on the screen. Use the PIN on the device, not an old shared default. If you save your own PIN, that saved PIN is used instead.

## Will my pet be lost if the power goes off?
Your pet is saved to flash. A power cut during a save can still lose recent changes, so back up important saves before testing. This is a known issue being worked on.

## Can two pets breed?
Breeding and visits follow the rules in the Getting Started guide. Breeding is between matching species only (rule being finalised in the current development branch).

## Is this a finished product?
It is a development firmware. Each board's status is listed as tested or not tested in the docs. Treat anything marked "not tested" as untested on real hardware.

## Where can I report a bug?
Use the GitHub issues page of the LoRaGotchi repository. Please include your board, edition, and firmware version.

## Is LoRaGotchi open source?
Yes. It is built on MeshCore, which is MIT-licensed. Contributors' work stays in the repository.
