#pragma once

// Bedtime quiet: while the pet is asleep (the existing Sleep/Wake hours),
// incoming messages stay silent -- no beep, no buzz, and they do not keep the
// screen lit -- unless the sender is a favourite. Pure decision only: no
// settings, no flash, no radio format. The pet itself still counts the message.
struct LoRaFishBedtime {
  static constexpr bool quiet(bool petAsleep, bool senderIsFavourite) {
    return petAsleep && !senderIsFavourite;
  }
};
