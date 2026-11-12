#include <gtest/gtest.h>
#include <string>
#include "helpers/NovaCli.h"

using namespace NovaCli;

static std::string say(const char* line, const char* ed = "DX-PRO", const Caps& c = Caps()) {
  char out[400];
  size_t n = reply(parse(line), ed, c, out, sizeof(out));
  EXPECT_EQ(n, strlen(out));
  return std::string(out);
}

TEST(NovaCli, OnlyTheWordNovaIsOurs) {
  for (const char* l : {"", "  ", "get name", "reboot", "novae hello", "Nova hello", "xnova", "nov", "set name nova", "ls", "cat /x"})
    EXPECT_EQ(parse(l).cmd, Cmd::NotNova) << l;
  EXPECT_EQ(parse(nullptr).cmd, Cmd::NotNova);
  char out[64];
  EXPECT_EQ(reply(parse("reboot"), "DX", Caps(), out, sizeof(out)), 0u);
  EXPECT_STREQ(out, "");
}

TEST(NovaCli, ParsesEverySubCommand) {
  EXPECT_EQ(parse("nova hello").cmd, Cmd::Hello);
  EXPECT_EQ(parse("nova mesh").cmd, Cmd::Mesh);
  EXPECT_EQ(parse("nova pet").cmd, Cmd::Pet);
  EXPECT_EQ(parse("nova petname Bubbles").cmd, Cmd::PetName);
  EXPECT_STREQ(parse("nova petname Bubbles").arg, "Bubbles");
  EXPECT_STREQ(parse("nova   petname   My Pet ").arg, "My Pet ");
  EXPECT_STREQ(parse("nova petname").arg, "");
  EXPECT_EQ(parse("  nova   hello").cmd, Cmd::Hello);   // spaces around are fine
}

TEST(NovaCli, SubCommandsMatchWholeWordsOnly) {
  for (const char* l : {"nova", "nova ", "nova hell", "nova hello2", "nova pets", "nova meshes", "nova petnam", "nova status", "nova profile", "nova contacts", "nova Hello"})
    EXPECT_EQ(parse(l).cmd, Cmd::Unknown) << l;
}

TEST(NovaCli, HelloLineIsExact) {
  EXPECT_EQ(say("nova hello"),
    "{\"ed\":\"dx-pro\",\"nova\":{\"v\":1,\"caps\":{\"pet\":0,\"mesh\":0,\"contacts\":0,\"petname\":0,\"keys\":0,"
    "\"clean\":0,\"feed\":0,\"guess\":0,\"ping\":0,\"sendpet\":0}},\"lg\":{\"hello\":1,\"pet\":0,\"mesh\":0}}");
  EXPECT_EQ(say("nova hello", "DX").substr(0, 11), "{\"ed\":\"dx\",");
  EXPECT_EQ(say("nova hello", "WATER").substr(0, 14), "{\"ed\":\"water\",");
}

TEST(NovaCli, HelloIsOneLineAndStartsWithEd) {
  const std::string s = say("nova hello");
  EXPECT_EQ(s.find('\n'), std::string::npos);
  EXPECT_EQ(s.find('\r'), std::string::npos);
  EXPECT_EQ(s.rfind("{\"ed\":", 0), 0u);              // "ed" first, so the dashboard's router sees it
  EXPECT_NE(s.find("\"nova\":{"), std::string::npos);
}

TEST(NovaCli, CapsAreOnlyOneWhenSet) {
  Caps c; c.contacts = 1; c.petname = 5;   // any non-zero counts as 1
  const std::string s = say("nova hello", "DX-PRO", c);
  EXPECT_NE(s.find("\"contacts\":1"), std::string::npos);
  EXPECT_NE(s.find("\"petname\":1"), std::string::npos);
  EXPECT_NE(s.find("\"pet\":0,\"mesh\":0,\"contacts\""), std::string::npos);
  EXPECT_NE(s.find("\"lg\":{\"hello\":1,\"pet\":0,\"mesh\":0}"), std::string::npos);
  Caps d; d.pet = 1; d.mesh = 1;
  EXPECT_NE(say("nova hello", "DX", d).find("\"lg\":{\"hello\":1,\"pet\":1,\"mesh\":1}"), std::string::npos);
}

TEST(NovaCli, EditionNameIsSanitised) {
  EXPECT_EQ(say("nova hello", "A\"b\\c\n d").substr(0, 13), "{\"ed\":\"abcd\",");
  EXPECT_EQ(say("nova hello", "").substr(0, 11), "{\"ed\":\"dx\",");
  EXPECT_EQ(say("nova hello", nullptr).substr(0, 11), "{\"ed\":\"dx\",");
  EXPECT_EQ(say("nova hello", "!!!").substr(0, 11), "{\"ed\":\"dx\",");
  std::string longname(100, 'x');
  const std::string s = say("nova hello", longname.c_str());
  EXPECT_EQ(s.rfind("{\"ed\":\"", 0), 0u);
  EXPECT_NE(s.find("\"nova\":{"), std::string::npos);
}

TEST(NovaCli, UnavailableLines) {
  EXPECT_EQ(say("nova mesh"), "{\"nova_unavailable\":\"mesh\"}");
  EXPECT_EQ(say("nova pet"), "{\"nova_unavailable\":\"pet\"}");
  EXPECT_EQ(say("nova petname Bubbles"), "{\"nova_unavailable\":\"petname\"}");
  EXPECT_EQ(say("nova petname"), "{\"nova_unavailable\":\"petname\"}");
}

TEST(NovaCli, UnknownSubCommandGetsOneErrorLineAndNeverEchoesInput) {
  for (const char* l : {"nova", "nova bogus", "nova status", "nova profile", "nova \"}{evil"}) {
    const std::string s = say(l);
    EXPECT_EQ(s, "{\"nova_error\":\"unknown_command\"}") << l;
  }
}

TEST(NovaCli, NoReplyStartsWithNovaStatusOrProfile) {
  for (const char* l : {"nova hello", "nova mesh", "nova pet", "nova petname x", "nova status", "nova profile", "nova x"}) {
    const std::string s = say(l);
    EXPECT_EQ(s.rfind("nova", 0), std::string::npos) << s;
    EXPECT_EQ(s.rfind("{", 0), 0u) << s;
    EXPECT_EQ(s.find('\n'), std::string::npos);
  }
}

TEST(NovaCli, SmallBuffersStayTerminatedAndNeverHoldHalfALine) {
  for (size_t cap = 1; cap < 40; ++cap) {
    char out[400]; memset(out, '!', sizeof(out));
    size_t n = reply(parse("nova hello"), "DX-PRO", Caps(), out, cap);
    EXPECT_EQ(n, 0u);
    EXPECT_EQ(out[0], 0);
  }
  char out[8];
  EXPECT_EQ(reply(parse("nova pet"), "DX", Caps(), out, 0), 0u);
  EXPECT_EQ(reply(parse("nova pet"), "DX", Caps(), nullptr, 8), 0u);
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
