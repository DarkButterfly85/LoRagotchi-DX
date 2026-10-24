#include <gtest/gtest.h>
#include "../../examples/companion_radio/LoRaFishColour.h"
#include "../../examples/companion_radio/LoRaFishCommit.h"
TEST(LoRaFishColour, InheritanceKeepsEndpointsIdenticalParentsAndMonoSeparate) {
  for(unsigned sample=0;sample<=240;++sample) {
    EXPECT_EQ(LoRaFishColour::inherit(220,220,sample),220);
    auto mixed=LoRaFishColour::inherit(6,220,sample);EXPECT_TRUE(mixed==6 || mixed==220);
  }
  EXPECT_EQ(LoRaFishColour::inherit(8,168,0),8);
  EXPECT_EQ(LoRaFishColour::inherit(8,168,240),168);
  // Red to blue takes the short magenta arc, never green/brown.
  EXPECT_EQ(LoRaFishColour::inherit(8,168,120),208);
  EXPECT_EQ(LoRaFishColour::rgb565(208),0xf81f);
}
TEST(LoRaFishColour, EveryEncodedHueRendersAndHasLegacyFallback) {
  for(unsigned a=0;a<256;++a) {
    EXPECT_EQ(LoRaFishColour::valid(a),a<=6 || (a>=8 && a<=247));
    if(!LoRaFishColour::valid(a))continue;
    EXPECT_LE(LoRaFishColour::fallback(a),6);
    for(unsigned b=0;b<6;++b)for(unsigned sample:{0,37,120,200,240})
      EXPECT_TRUE(LoRaFishColour::valid(LoRaFishColour::inherit(a,b,sample)));
  }
}
TEST(LoRaFishColour, ExtensionIsStrictAndDoesNotModifyOnFailure) {
  uint8_t b=0,s=1,e=2;
  EXPECT_TRUE(LoRaFishColour::extension("|H1|247|8|6",b,s,e));
  EXPECT_EQ(b,247);EXPECT_EQ(s,8);EXPECT_EQ(e,6);
  for(const char* x:{"|H1|7|8|6","|H1|248|8|6","|H1|1|2|3|tail","|H1|-1|2|3","|H1|4294967296|2|3","|H2|1|2|3"}) {
    EXPECT_FALSE(LoRaFishColour::extension(x,b,s,e));EXPECT_EQ(b,247);
  }
}
TEST(LoRaFishColour, RetryCarriesFrozenHueAndPaletteFallback) {
  LoRaFishCommitFrame frame;uint8_t key[32]={1};frame.prepare(key,7,8,true,220,120,6,65535);
  const std::string original=frame.forVisit(key,7,8);
  EXPECT_NE(original.find("|H1|220|120|6"),std::string::npos);
  EXPECT_EQ(original,std::string(frame.forVisit(key,7,8)));
  unsigned long tx,fid;char mode;unsigned b,s,e,tint;
  ASSERT_EQ(sscanf(original.c_str(),"LFG1|COMMIT|%lu|%lu|%c|%u|%u|%u|%u",&tx,&fid,&mode,&b,&s,&e,&tint),7);
  EXPECT_LE(b,6);EXPECT_LE(s,6);EXPECT_EQ(e,6);
  key[31]=1;EXPECT_EQ(frame.forVisit(key,7,8),nullptr);
}
int main(int argc, char** argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
