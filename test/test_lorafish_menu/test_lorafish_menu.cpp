#include <gtest/gtest.h>
#include "../../examples/companion_radio/ui-new/LoRaFishMenu.h"

using Option = LoRaFishOption;
using Setting = LoRaFishSetting;

TEST(LoRaFishMenu, RequestedOrderWithSound) {
  const Option expected[] = {Option::Advert, Option::Guess, Option::Reset, Option::Display,
      Option::Sound, Option::Schedule, Option::RF, Option::GNSS};
  ASSERT_EQ(LoRaFishOptions::count(true, false), 8);
  for (uint8_t i = 0; i < 8; ++i) EXPECT_EQ(LoRaFishOptions::at(i, true, false), expected[i]);
}

TEST(LoRaFishMenu, SoundIsOmittedWithoutReorderingOtherItems) {
  const Option expected[] = {Option::Advert, Option::Guess, Option::Reset, Option::Display,
      Option::Schedule, Option::RF, Option::GNSS};
  ASSERT_EQ(LoRaFishOptions::count(false, false), 7);
  for (uint8_t i = 0; i < 7; ++i) EXPECT_EQ(LoRaFishOptions::at(i, false, false), expected[i]);
  EXPECT_FALSE(LoRaFishOptions::available(Option::Sound, false, false));
}

TEST(LoRaFishMenu, BreedingStaysWithActionsWhenAvailable) {
  EXPECT_EQ(LoRaFishOptions::at(2, true, true), Option::Breed);
  EXPECT_EQ(LoRaFishOptions::at(3, true, true), Option::Reset);
  EXPECT_EQ(LoRaFishOptions::count(true, true), 9);
  EXPECT_EQ(LoRaFishOptions::count(false, true), 8);
  EXPECT_FALSE(LoRaFishOptions::available(Option::Breed, true, false));
}

TEST(LoRaFishMenu, ParentSelectionsRemainStableAcrossOptionalRows) {
  for (bool sound : {false, true}) {
    for (bool breed : {false, true}) {
      for (Option option : {Option::Advert, Option::Reset, Option::Display, Option::Schedule, Option::RF, Option::GNSS}) {
        const auto row = LoRaFishOptions::index(option, sound, breed);
        EXPECT_EQ(LoRaFishOptions::at(row, sound, breed), option);
      }
    }
  }
}

TEST(LoRaFishMenu, CancelDoesNotProduceAValueToPersist) {
  LoRaFishValuePicker picker;
  uint8_t saved = 21;
  picker.open(Setting::SleepHour, saved, 24);
  picker.move();
  EXPECT_EQ(picker.value(), 22);
  EXPECT_EQ(saved, 21);
  picker.cancel();
  EXPECT_FALSE(picker.select(saved));
  EXPECT_EQ(saved, 21);
}

TEST(LoRaFishMenu, SelectCommitsOnlyOnce) {
  LoRaFishValuePicker picker;
  uint8_t saved = 3;
  picker.open(Setting::Brightness, saved, 4);
  picker.move();
  ASSERT_TRUE(picker.select(saved));
  EXPECT_EQ(saved, 0);
  EXPECT_FALSE(picker.active());
  EXPECT_FALSE(picker.select(saved));
}

TEST(LoRaFishMenu, ReopeningStartsFromSavedValueNotCancelledDraft) {
  LoRaFishValuePicker picker;
  picker.open(Setting::WakeSound, 1, 4);
  picker.move();
  picker.cancel();
  picker.open(Setting::WakeSound, 1, 4);
  EXPECT_EQ(picker.value(), 1);
}

TEST(LoRaFishMenu, NextAndPreviousWrapAtBothEnds) {
  LoRaFishValuePicker picker;
  picker.open(Setting::UtcOffset, 104, 105);
  picker.move();
  EXPECT_EQ(picker.value(), 0);
  picker.move(true);
  EXPECT_EQ(picker.value(), 104);
}

TEST(LoRaFishMenu, ClosedAndEmptyPickersCannotCommit) {
  LoRaFishValuePicker picker;
  uint8_t saved = 7;
  picker.move();
  EXPECT_FALSE(picker.select(saved));
  picker.open(Setting::Theme, 0, 0);
  picker.move();
  EXPECT_FALSE(picker.select(saved));
  EXPECT_EQ(saved, 7);
}

int main(int argc, char** argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
