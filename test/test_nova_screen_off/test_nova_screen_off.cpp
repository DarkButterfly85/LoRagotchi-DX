// Host tests for the Nova "screen off" line (NovaPetLink.h Link::noteScreen / takeScreenOff, queued by MyMesh.cpp
// checkNovaSerial through the NovaStreams outbox): when the radio screen goes to sleep the link sends exactly one
// {"screen":"off"} line, once per transition, nothing else, and the picture lines stay byte for byte what they were.
#include <gtest/gtest.h>

#include <stdint.h>
#include <string>

#include <helpers/NovaStreams.h>
#include "../../examples/companion_radio/NovaPetLink.h"

using NovaPetLink::Link;

namespace {

// What the serial code does each pass (MyMesh.cpp checkNovaSerial): queue the off line when the link says it is due.
// Returns what the port would get from the outbox, and empties it.
std::string pass(Link& l, NovaStreams::Hub& hub, uint32_t now) {
  if (l.screenOffDue(now) && hub.out.append(NovaPetLink::SCREEN_OFF_LINE)) l.screenOffQueued();   // same as the call site
  std::string s((const char*)hub.out.data(), hub.out.pending());
  hub.out.consumed(hub.out.pending());
  return s;
}

// The two pictures the golden lines below were made from (encoder untouched by the screen-off change).
std::string picture(Link& l, int step, uint32_t now) {
  l.canvas.beginFrame(false);
  l.canvas.fillRect(10 + (step ? 2 : 0), 10, 20, 8);
  l.canvas.fillRect(100, 50, 5, 5);
  l.frameDone(now);
  std::string s((const char*)l.pendingData(), l.pending());
  l.consumed(l.pending());
  return s;
}

const std::string KEY = "{\"pet\":{\"s\":1,\"k\":1,\"d\":\"AKE///wADT///AANP//8AA0///wADT///AANP//8AA0///wADT///AD/AP8AGg+AAA4PgAAOD4AADg+AAA4PgACS\"}}\n";
const std::string DELTA = "{\"pet\":{\"s\":2,\"k\":0,\"d\":\"AKEwAAEDAA0wAAEDAA0wAAEDAA0wAAEDAA0wAAEDAA0wAAEDAA0wAAEDAA0wAAEDAP8A/wDu\"}}\n";

}  // namespace

TEST(NovaScreenOff, TheLineIsExactlyScreenOffAndANewline) {
  Link l; NovaStreams::Hub hub;
  l.request(1000);
  l.noteScreen(true);
  l.noteScreen(false);
  EXPECT_EQ(pass(l, hub, 1100), std::string("{\"screen\":\"off\"}\n"));
  EXPECT_EQ(l.pending(), 0u) << "nothing else goes out for the transition: no picture, no heartbeat";
}

TEST(NovaScreenOff, SentOncePerTransitionNotRepeated) {
  Link l; NovaStreams::Hub hub;
  l.request(1000);
  l.noteScreen(true);
  EXPECT_EQ(pass(l, hub, 1000), "");                       // awake: nothing
  l.noteScreen(false);
  EXPECT_EQ(pass(l, hub, 1100), "{\"screen\":\"off\"}\n");
  for (uint32_t t = 1200; t < 60000; t += 500) {           // still asleep, page keeps asking: silence, no heartbeat
    l.request(t);
    l.noteScreen(false);
    ASSERT_EQ(pass(l, hub, t), "") << "at " << t;
  }
  l.noteScreen(true);                                      // wakes: not a screen-off
  EXPECT_EQ(pass(l, hub, 61000), "");
  l.noteScreen(false);                                     // sleeps again: a second transition, a second line
  EXPECT_EQ(pass(l, hub, 61500), "{\"screen\":\"off\"}\n");
  EXPECT_EQ(pass(l, hub, 61600), "");
}

TEST(NovaScreenOff, NothingIsSentUnlessAPageIsAsking) {
  Link l; NovaStreams::Hub hub;                            // never requested
  l.noteScreen(true);
  l.noteScreen(false);
  EXPECT_EQ(pass(l, hub, 1000), "");
  l.request(2000);                                         // a page that starts while asleep is told once
  EXPECT_EQ(pass(l, hub, 2000), "{\"screen\":\"off\"}\n");
  EXPECT_EQ(pass(l, hub, 2100), "");
}

// The off transition must not be lost when no page is asking at that moment.
TEST(NovaScreenOff, TransitionWithNoPageStaysPendingUntilAPageAsks) {
  Link l; NovaStreams::Hub hub;
  l.noteScreen(true);
  l.noteScreen(false);                                     // goes to sleep, nobody asking
  for (uint32_t t = 1000; t < 30000; t += 1000) ASSERT_EQ(pass(l, hub, t), "") << "at " << t;   // waits, sends nothing
  l.request(30000);                                        // a page starts: the line goes out at once
  EXPECT_EQ(pass(l, hub, 30000), "{\"screen\":\"off\"}\n");
  for (uint32_t t = 30100; t < 40000; t += 100) { l.request(t); ASSERT_EQ(pass(l, hub, t), "") << "at " << t; }   // once only
}

TEST(NovaScreenOff, TransitionWhileAPageIsActiveIsSentOnce) {
  Link l; NovaStreams::Hub hub;
  l.request(1000);
  l.noteScreen(true);
  l.noteScreen(false);
  EXPECT_EQ(pass(l, hub, 1000), "{\"screen\":\"off\"}\n");
  EXPECT_EQ(pass(l, hub, 1001), "");
  EXPECT_EQ(pass(l, hub, 2000), "");
}

TEST(NovaScreenOff, WakingBeforeAPageAsksSendsNothing) {
  Link l; NovaStreams::Hub hub;
  l.noteScreen(true);
  l.noteScreen(false);                                     // pending, nobody asking
  EXPECT_EQ(pass(l, hub, 1000), "");
  l.noteScreen(true);                                      // screen back on before any page asked
  EXPECT_EQ(pass(l, hub, 1500), "");
  l.request(2000);                                         // awake page: still nothing, now or later
  EXPECT_EQ(pass(l, hub, 2000), "");
  EXPECT_EQ(pass(l, hub, 3000), "");
}

TEST(NovaScreenOff, NoDuplicateAfterTheLineWentOut) {
  Link l; NovaStreams::Hub hub;
  l.noteScreen(false);
  EXPECT_EQ(pass(l, hub, 500), "");
  l.request(1000);
  EXPECT_EQ(pass(l, hub, 1000), "{\"screen\":\"off\"}\n");
  for (uint32_t t = 1100; t < 3900; t += 100) { l.noteScreen(false); l.request(t); ASSERT_EQ(pass(l, hub, t), "") << "at " << t; }
  l.noteScreen(false);
  EXPECT_EQ(pass(l, hub, 3900), "");
}

TEST(NovaScreenOff, ALineThatCouldNotBeQueuedStaysDue) {
  Link l;
  l.request(1000);
  l.noteScreen(false);
  EXPECT_TRUE(l.screenOffDue(1000));
  EXPECT_TRUE(l.screenOffDue(1100));                       // asking again (outbox was full): still due, not dropped
  l.screenOffQueued();
  EXPECT_FALSE(l.screenOffDue(1200));
}

TEST(NovaScreenOff, WakingBeforeTheLineWentCancelsIt) {
  Link l; NovaStreams::Hub hub;
  l.request(1000);
  l.noteScreen(false);
  l.noteScreen(true);
  EXPECT_EQ(pass(l, hub, 1000), "");
}

TEST(NovaScreenOff, PictureLinesAreByteIdentical) {
  Link l;
  l.request(1000);
  l.noteScreen(true);
  EXPECT_EQ(picture(l, 0, 1000), KEY);
  l.noteScreen(false);                                     // sleep and wake in between: the pictures do not change
  l.takeScreenOff(1100);
  l.noteScreen(true);
  EXPECT_EQ(picture(l, 1, 1300), DELTA);
  EXPECT_EQ(l.sequence(), 2u);                             // the off line took no picture sequence number
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
