#include <gtest/gtest.h>
#include "../../examples/companion_radio/ui-new/PetResetConfirmation.h"

TEST(PetResetConfirmation, ClosedPromptCannotReset) {
  PetResetConfirmation prompt;
  prompt.toggle();
  EXPECT_FALSE(prompt.confirm(true));
}

TEST(PetResetConfirmation, OpeningAndRepeatingLongPressCancels) {
  PetResetConfirmation prompt;
  prompt.open();
  EXPECT_FALSE(prompt.resetSelected());
  EXPECT_FALSE(prompt.confirm(true));
  EXPECT_FALSE(prompt.confirm(true));
}

TEST(PetResetConfirmation, ExplicitResetSelectionAllowsOnlyOneReset) {
  PetResetConfirmation prompt;
  prompt.open();
  prompt.toggle();
  EXPECT_TRUE(prompt.resetSelected());
  EXPECT_TRUE(prompt.confirm(true));
  EXPECT_FALSE(prompt.confirm(true));
}

TEST(PetResetConfirmation, ReturningToCancelDoesNotReset) {
  PetResetConfirmation prompt;
  prompt.open();
  prompt.toggle();
  prompt.toggle();
  EXPECT_FALSE(prompt.confirm(true));
}

TEST(PetResetConfirmation, BackOrInterruptionDisarmsReset) {
  PetResetConfirmation prompt;
  prompt.open();
  prompt.toggle();
  prompt.cancel();
  EXPECT_FALSE(prompt.confirm(true));
}

TEST(PetResetConfirmation, ReopeningAlwaysSelectsCancel) {
  PetResetConfirmation prompt;
  prompt.open();
  prompt.toggle();
  prompt.open();
  EXPECT_FALSE(prompt.resetSelected());
  EXPECT_FALSE(prompt.confirm(true));
}

TEST(PetResetConfirmation, HiddenPromptCannotResetOrRemainArmed) {
  PetResetConfirmation prompt;
  prompt.open();
  prompt.toggle();
  EXPECT_FALSE(prompt.confirm(false));
  EXPECT_FALSE(prompt.confirm(true));
}

int main(int argc, char** argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
