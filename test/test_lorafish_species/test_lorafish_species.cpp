#include <gtest/gtest.h>
#include "../../examples/companion_radio/LoRaFishSpecies.h"
#include "../../examples/companion_radio/LoRaFishCommit.h"
TEST(WaterSpecies, StableRegistryAndUnknownFallback) {
  EXPECT_EQ(LoRaFishSpecies::TropicalFish,0);EXPECT_EQ(LoRaFishSpecies::SeaStar,13);
  for(unsigned i=0;i<15;++i) {EXPECT_TRUE(LoRaFishSpecies::known(i));EXPECT_EQ(LoRaFishSpecies::renderId(i),i);}
  EXPECT_EQ(LoRaFishSpecies::renderId(65535),0);EXPECT_STREQ(LoRaFishSpecies::label(65535),"Unknown (fish)");
}
TEST(WaterSpecies, AppendOnlyAnglerfishIdentity) {
  using namespace LoRaFishSpecies;
  const uint16_t stable[]={TropicalFish,Blowfish,Shark,Dolphin,Whale,Seal,Shrimp,
    Squid,Lobster,Crab,Octopus,Jellyfish,ShellDweller,SeaStar,Anglerfish};
  for(unsigned i=0;i<15;++i)EXPECT_EQ(stable[i],i);
  EXPECT_EQ(count,15);EXPECT_EQ(Anglerfish,14);EXPECT_STREQ(label(Anglerfish),"Anglerfish");
  EXPECT_FALSE(known(15));EXPECT_FALSE(known(255));
  EXPECT_EQ(wireSpecies(Anglerfish,"LFG1|ACK|1|2|S1"),Anglerfish);
  EXPECT_EQ(wireSpecies(Anglerfish,"LFG1|ACK|1|2|S1|A1"),Anglerfish);
  uint8_t bytes[savedSize];encode(bytes,Anglerfish,Anglerfish,123,true);
  uint16_t local=0,egg=0;uint32_t seed=0;bool setup=false;
  ASSERT_TRUE(decode(bytes,sizeof(bytes),local,egg,seed,setup));
  EXPECT_EQ(local,14);EXPECT_EQ(egg,14);EXPECT_EQ(seed,123);EXPECT_TRUE(setup);
}
TEST(WaterSpecies, StrictWireNumbersAndDuplicateExtension) {
  uint16_t id=9;bool present=true;
  EXPECT_FALSE(LoRaFishSpecies::extension(nullptr,id,present));
  EXPECT_FALSE(LoRaFishSpecies::acknowledged(nullptr));
  EXPECT_TRUE(LoRaFishSpecies::extension("LFG1|COMMIT|1|2",id,present));EXPECT_EQ(id,0);EXPECT_FALSE(present);
  for(const char* x:{"|S1|0","|S1|13","|S1|65535","|P1|0|S1|100|FUTURE|7"}) {
    EXPECT_TRUE(LoRaFishSpecies::extension(x,id,present));EXPECT_TRUE(present);
  }
  for(const char* x:{"|S1","|S1|","|S1|-1","|S1|+1","|S1| 1","|S1|1x","|S1|65536","|S1|4294967295","|S1|999999999999999999999999999","|S1|1|S1|2"})
    EXPECT_FALSE(LoRaFishSpecies::extension(x,id,present))<<x;
}
TEST(WaterSpecies, CapabilityIsExplicitNotANameOrLooseSuffix) {
  EXPECT_TRUE(LoRaFishSpecies::acknowledged("LFG1|ACK|4294967295|4294967295|S1"));
  for(const char* text:{"LFG1|ACK|1|2","LFG1|ACK|1|2|S1|junk","LFG1|ACK|1|2|X|S1",
      "LFG1|ACK|1|2|S10","LFG1|ACK|1|2|s1","LFG1|ACK|4294967296|2|S1","💦"})
    EXPECT_FALSE(LoRaFishSpecies::acknowledged(text));
  LoRaFishCommitFrame f;uint8_t key[32]={};f.prepare(key,1,2,true,220,120,6,944,2,13,false);
  EXPECT_STREQ(f.forVisit(key,1,2),"LFG1|COMMIT|1|2|C|5|4|6|944");
}
TEST(WaterSpecies, PersistenceChecksumAndUnknownIdentity) {
  uint8_t data[LoRaFishSpecies::savedSize];LoRaFishSpecies::encode(data,65535,13,0xFACE1234,true);
  uint16_t local=0,egg=0;uint32_t seed=0;bool setup=false;
  ASSERT_TRUE(LoRaFishSpecies::decode(data,sizeof(data),local,egg,seed,setup));
  EXPECT_EQ(local,65535);EXPECT_EQ(egg,13);EXPECT_EQ(seed,0xFACE1234);EXPECT_TRUE(setup);
  for(unsigned n=0;n<sizeof(data);++n)EXPECT_FALSE(LoRaFishSpecies::decode(data,n,local,egg,seed,setup));
  for(unsigned bit=0;bit<sizeof(data)*8;++bit) {
    data[bit/8]^=1U<<(bit%8);EXPECT_FALSE(LoRaFishSpecies::decode(data,sizeof(data),local,egg,seed,setup));data[bit/8]^=1U<<(bit%8);
  }
}
TEST(WaterSpecies, MysteryStableAndIndependentOfChoiceOrder) {
  bool species[LoRaFishSpecies::selectableCount]={};
  for(uint32_t seed=1;seed<10000;++seed) {
    auto id=LoRaFishSpecies::mystery(seed);ASSERT_TRUE(LoRaFishSpecies::known(id));auto index=LoRaFishSpecies::selectionIndex(id);ASSERT_LT(index,LoRaFishSpecies::selectableCount);EXPECT_EQ(LoRaFishSpecies::selectionId(index),id);species[index]=true;
    for(unsigned role=0;role<3;++role){auto c=LoRaFishSpecies::mysteryColour(seed,role);EXPECT_TRUE(LoRaFishColour::valid(c));EXPECT_GE(c,8);EXPECT_EQ(c,LoRaFishSpecies::mysteryColour(seed,role));}
    EXPECT_EQ(id,LoRaFishSpecies::mystery(seed));
  }
  for(bool seen:species)EXPECT_TRUE(seen);
}
TEST(WaterSpecies, FrozenRetryAndFishOnlyLegacyParser) {
  LoRaFishCommitFrame f;uint8_t key[32]={9};
  f.prepare(key,UINT32_MAX,UINT32_MAX,true,247,246,245,65535,2,65535);
  std::string payload=f.forVisit(key,UINT32_MAX,UINT32_MAX);ASSERT_LT(payload.size(),128);
  EXPECT_NE(payload.find("|S1|65535"),std::string::npos);
  uint8_t body=0,scales=0,eyes=0;
  ASSERT_TRUE(LoRaFishColour::extension(strstr(payload.c_str(),"|H1|"),body,scales,eyes));
  EXPECT_EQ(body,247);EXPECT_EQ(scales,246);EXPECT_EQ(eyes,245);
  unsigned long tx,fid;char mode;unsigned b,s,e,tint;
  ASSERT_EQ(sscanf(payload.c_str(),"LFG1|COMMIT|%lu|%lu|%c|%u|%u|%u|%u",&tx,&fid,&mode,&b,&s,&e,&tint),7);
  EXPECT_LE(b,6);EXPECT_LE(s,6);EXPECT_LE(e,6);EXPECT_EQ(tint,65535);
  EXPECT_EQ(payload,std::string(f.forVisit(key,UINT32_MAX,UINT32_MAX)));
  key[31]=1;EXPECT_EQ(f.forVisit(key,UINT32_MAX,UINT32_MAX),nullptr);
}
TEST(AirSpecies, DisjointStableIdsAndExactOptIn) {
  EXPECT_EQ(LoRaFishSpecies::Eagle,256);EXPECT_EQ(LoRaFishSpecies::Bug,273);
  for(unsigned i=256;i<274;++i) {
    EXPECT_TRUE(LoRaFishSpecies::airKnown(i));EXPECT_FALSE(LoRaFishSpecies::waterKnown(i));
    EXPECT_EQ(LoRaFishSpecies::wireSpecies(i,"LFG1|ACK|1|2|S1"),0);
    EXPECT_EQ(LoRaFishSpecies::wireSpecies(i,"LFG1|ACK|1|2|S1|A1"),i);
  }
  EXPECT_FALSE(LoRaFishSpecies::known(255));EXPECT_FALSE(LoRaFishSpecies::known(274));
  EXPECT_TRUE(LoRaFishSpecies::airAcknowledged("LFG1|ACK|1|2|S1|A1"));
  EXPECT_FALSE(LoRaFishSpecies::airAcknowledged("LFG1|ACK|1|2|S1"));
  EXPECT_FALSE(LoRaFishSpecies::airAcknowledged("LFG1|ACK|1|2|S1|A1|junk"));
}
int main(int argc,char** argv){::testing::InitGoogleTest(&argc,argv);return RUN_ALL_TESTS();}
