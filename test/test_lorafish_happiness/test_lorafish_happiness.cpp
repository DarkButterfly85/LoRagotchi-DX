#include <gtest/gtest.h>
#include "../../examples/companion_radio/ui-new/LoRaFishHappiness.h"

using Happy = LoRaFishHappiness;
static constexpr uint32_t minuteMs = 60000;
static constexpr uint32_t noon = 12 * Happy::hourMs;

TEST(LoRaFishHappiness, ExactHalfHourAndSaturation) {
  Happy timer; uint8_t value=80;
  timer.advance(Happy::decayMs-1,true,noon,21,7,0,value);
  EXPECT_EQ(value,80);
  timer.advance(1,true,noon+1,21,7,0,value);
  EXPECT_EQ(value,79); EXPECT_EQ(timer.awakeMs,0);
  value=1;timer.advance(Happy::decayMs,true,noon,21,7,3,value);
  EXPECT_EQ(value,0);
  timer.advance(Happy::decayMs,true,noon,21,7,3,value);
  EXPECT_EQ(value,0);
}
TEST(LoRaFishHappiness, EachWastePieceAddsOneDrain) {
  for(uint8_t waste=0;waste<=3;++waste) {
    Happy timer;uint8_t value=80;
    timer.advance(Happy::decayMs,true,noon,21,7,waste,value);
    EXPECT_EQ(value,79-waste);
  }
}
TEST(LoRaFishHappiness, SleepPausesPartialAwakeInterval) {
  Happy timer;uint8_t value=80;
  timer.advance(15*minuteMs,true,21*Happy::hourMs,21,7,0,value);
  timer.advance(10*Happy::hourMs,true,7*Happy::hourMs,21,7,0,value);
  EXPECT_EQ(value,80);EXPECT_EQ(timer.awakeMs,15*minuteMs);
  timer.advance(15*minuteMs,true,7*Happy::hourMs+15*minuteMs,21,7,0,value);
  EXPECT_EQ(value,79);
}
TEST(LoRaFishHappiness, DelayedGapSpansMidnightAndAwakeDay) {
  Happy timer;uint8_t value=80;
  timer.advance(Happy::dayMs,true,noon,21,7,0,value);
  EXPECT_EQ(value,52);EXPECT_EQ(timer.awakeMs,0);
}
TEST(LoRaFishHappiness, DaytimeSleepAndDisabledSchedule) {
  Happy timer;uint8_t value=80;
  timer.advance(8*Happy::hourMs,true,17*Happy::hourMs,9,17,3,value);
  EXPECT_EQ(value,80);
  timer.advance(Happy::hourMs,true,18*Happy::hourMs,9,17,0,value);
  EXPECT_EQ(value,78);
  timer.advance(Happy::hourMs,true,18*Happy::hourMs,9,9,0,value);
  EXPECT_EQ(value,76);
}
TEST(LoRaFishHappiness, InactiveStagesDoNotAccumulateDecay) {
  Happy timer;uint8_t value=80;
  timer.advance(10*minuteMs,true,noon,21,7,0,value);
  timer.advance(3*Happy::hourMs,false,noon,21,7,3,value);
  EXPECT_EQ(value,80);EXPECT_EQ(timer.awakeMs,10*minuteMs);
}
TEST(LoRaFishHappiness, MealCooldownExactBoundaryAndEligibility) {
  Happy timer;uint8_t value=80;
  EXPECT_FALSE(timer.meal(false,value));EXPECT_EQ(timer.mealCooldownMs,0);
  ASSERT_TRUE(timer.meal(true,value));EXPECT_EQ(value,83);
  for(int i=0;i<1000;++i)EXPECT_FALSE(timer.meal(true,value));
  timer.advance(Happy::mealMs-1,false,noon,21,7,0,value);
  EXPECT_FALSE(timer.meal(true,value));
  timer.advance(1,false,noon,21,7,0,value);
  EXPECT_TRUE(timer.meal(true,value));EXPECT_EQ(value,86);
}
TEST(LoRaFishHappiness, MealsCapAt100ButStillConsumeCooldown) {
  for(uint8_t initial : {uint8_t(98),uint8_t(99),uint8_t(100)}) {
    Happy timer;uint8_t value=initial;
    EXPECT_TRUE(timer.meal(true,value));EXPECT_EQ(value,100);
    EXPECT_FALSE(timer.meal(true,value));
  }
}
TEST(LoRaFishHappiness, CooldownRunsDuringSleepAndInactiveStages) {
  Happy timer;uint8_t value=80;timer.meal(true,value);
  timer.advance(Happy::hourMs,true,23*Happy::hourMs,21,7,3,value);
  EXPECT_EQ(value,83);EXPECT_EQ(timer.mealCooldownMs,0);
  timer.meal(true,value);timer.advance(Happy::hourMs,false,noon,21,7,3,value);
  EXPECT_EQ(value,86);EXPECT_EQ(timer.mealCooldownMs,0);
}
TEST(LoRaFishHappiness, LargeAndSmallUpdatesAgreeAcrossSleepBoundary) {
  Happy coarse,fine;uint8_t a=80,b=80;
  const uint32_t end=7*Happy::hourMs+15*minuteMs;
  coarse.advance(11*Happy::hourMs,true,end,21,7,1,a);
  uint32_t local=20*Happy::hourMs+15*minuteMs;
  for(int i=0;i<660;++i) {
    local=(local+minuteMs)%Happy::dayMs;
    fine.advance(minuteMs,true,local,21,7,1,b);
  }
  EXPECT_EQ(a,b);EXPECT_TRUE(coarse.same(fine));EXPECT_EQ(a,76);
}
TEST(LoRaFishHappiness, InvalidPersistedRangesAreRejected) {
  Happy timer;EXPECT_TRUE(timer.valid());
  timer.awakeMs=Happy::decayMs;EXPECT_FALSE(timer.valid());
  timer.awakeMs=0;timer.mealCooldownMs=Happy::mealMs+1;EXPECT_FALSE(timer.valid());
  timer.mealCooldownMs=Happy::mealMs;EXPECT_TRUE(timer.valid());
}

int main(int argc, char** argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
