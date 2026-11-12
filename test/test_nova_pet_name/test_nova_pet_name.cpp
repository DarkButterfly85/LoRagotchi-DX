// Host tests for helpers/NovaPetName.h: the pet name on its way to the Nova dashboard.
// The name rules: 16 characters at most (the /lorafish.id limit), printable ASCII only, and no '"' or '\'
// so the JSON line the dashboard reads always stays valid JSON. The encoder tests use the real
// PetMirrorEncoder (helpers/PetMirror.h) with the name argument produced by the same rules.
#include <gtest/gtest.h>

#include <stdint.h>
#include <string.h>
#include <string>

#include <helpers/NovaCli.h>
#include <helpers/NovaPetName.h>
#include <helpers/PetMirror.h>

using namespace NovaPetName;

namespace {

std::string prep(const char* arg, Status* st = nullptr) {
  char out[kMax + 1];
  memset(out, '!', sizeof(out));
  Status s = prepare(arg, out, sizeof(out));
  if (st) *st = s;
  return std::string(out);
}

std::string safe(const char* in) {
  char out[kMax + 1];
  memset(out, '!', sizeof(out));
  jsonSafe(in, out, sizeof(out));
  return std::string(out);
}

std::string say(Status s, const char* name) {
  char out[160];
  size_t n = reply(s, name, out, sizeof(out));
  EXPECT_EQ(n, strlen(out));
  return std::string(out);
}

// A hand-rolled check that a line is one JSON object whose strings hold no raw '"' or '\' or control byte:
// walks the text, honours backslash escapes, and reports the string contents it saw.
bool jsonStringsClean(const std::string& line) {
  bool in = false;
  for (size_t i = 0; i < line.size(); i++) {
    const unsigned char c = (unsigned char)line[i];
    if (!in) { if (c == '"') in = true; continue; }
    if (c == '\\') return false;              // our lines never need an escape: any backslash is a bug
    if (c < 0x20 || c > 0x7E) return false;
    if (c == '"') in = false;
  }
  return !in;
}

}  // namespace

TEST(NovaPetName, LimitMatchesIdentityFile) {
  EXPECT_EQ(kMax, 16u);
}

TEST(NovaPetName, PrepareAcceptsPlainNames) {
  Status st;
  EXPECT_EQ(prep("Fluffy", &st), "Fluffy"); EXPECT_EQ(st, Status::Ok);
  EXPECT_EQ(prep("Mr Bubbles", &st), "Mr Bubbles"); EXPECT_EQ(st, Status::Ok);
  EXPECT_EQ(prep("  padded  ", &st), "padded"); EXPECT_EQ(st, Status::Ok);        // outer spaces trimmed, inner kept
  EXPECT_EQ(prep("0123456789ABCDEF", &st), "0123456789ABCDEF"); EXPECT_EQ(st, Status::Ok);   // exactly 16
  EXPECT_EQ(prep("a~{|}!#$%&'()*+,", &st), "a~{|}!#$%&'()*+,"); EXPECT_EQ(st, Status::Ok);  // other symbols are fine
}

TEST(NovaPetName, PrepareDashClearsAndEmptyIsUsage) {
  Status st;
  EXPECT_EQ(prep("-", &st), ""); EXPECT_EQ(st, Status::Cleared);
  EXPECT_EQ(prep("  -  ", &st), ""); EXPECT_EQ(st, Status::Cleared);
  EXPECT_EQ(prep("--", &st), "--"); EXPECT_EQ(st, Status::Ok);                     // a dash inside a name is a name
  EXPECT_EQ(prep("", &st), ""); EXPECT_EQ(st, Status::Usage);
  EXPECT_EQ(prep("    ", &st), ""); EXPECT_EQ(st, Status::Usage);
  EXPECT_EQ(prep(nullptr, &st), ""); EXPECT_EQ(st, Status::Usage);
}

TEST(NovaPetName, PrepareRefusesTooLong) {
  Status st;
  EXPECT_EQ(prep("0123456789ABCDEFG", &st), ""); EXPECT_EQ(st, Status::TooLong);   // 17
  EXPECT_EQ(prep(std::string(90, 'x').c_str(), &st), ""); EXPECT_EQ(st, Status::TooLong);
}

TEST(NovaPetName, PrepareRefusesNonPrintableAscii) {
  Status st;
  for (const char* n : {"caf\xC3\xA9", "tab\there", "bell\x07", "\x7F", "nl\nx", "cr\rx", "\x80"}) {
    EXPECT_EQ(prep(n, &st), "") << n; EXPECT_EQ(st, Status::NonAscii) << n;
  }
}

TEST(NovaPetName, PrepareRefusesQuoteAndBackslash) {
  Status st;
  for (const char* n : {"\"", "a\"b", "\"quoted\"", "back\\slash", "\\", "a\\\"b", "x\"}}"}) {
    EXPECT_EQ(prep(n, &st), "") << n; EXPECT_EQ(st, Status::JsonChar) << n;
  }
  // a name that is both too long and has a quote is still refused, and nothing is copied
  EXPECT_EQ(prep("0123456789ABCDEF\"", &st), ""); EXPECT_NE(st, Status::Ok);
}

TEST(NovaPetName, PrepareNeedsRoomForTheNameAndNeverWritesPastIt) {
  char tiny[kMax];                                  // one byte too small
  EXPECT_EQ(prepare("Fluffy", tiny, sizeof(tiny)), Status::Usage);
  EXPECT_EQ(prepare("Fluffy", nullptr, 0), Status::Usage);
  char buf[kMax + 1 + 8];
  memset(buf, 'Z', sizeof(buf));
  EXPECT_EQ(prepare("0123456789ABCDEF", buf, kMax + 1), Status::Ok);
  for (size_t i = kMax + 1; i < sizeof(buf); i++) EXPECT_EQ(buf[i], 'Z');
}

TEST(NovaPetName, JsonSafeKeepsPrintableAsciiOnly) {
  EXPECT_EQ(safe("Fluffy"), "Fluffy");
  EXPECT_EQ(safe("Mr Bubbles"), "Mr Bubbles");
  EXPECT_EQ(safe(""), "");
  EXPECT_EQ(safe(nullptr), "");
  EXPECT_EQ(safe("a\"b"), "ab");
  EXPECT_EQ(safe("a\\b"), "ab");
  EXPECT_EQ(safe("\"\\\"\\"), "");
  EXPECT_EQ(safe("caf\xC3\xA9"), "caf");
  EXPECT_EQ(safe("t\tn\nr\rx\x7F"), "tnrx");
  EXPECT_EQ(safe("0123456789ABCDEFGHIJ"), "0123456789ABCDEF");                 // capped at 16
  EXPECT_EQ(safe("\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"ab"), "ab");          // stripped characters do not count
}

TEST(NovaPetName, JsonSafeSmallBuffers) {
  char out[kMax];                                   // too small: empty, never overflows
  memset(out, 'Q', sizeof(out));
  jsonSafe("Fluffy", out, sizeof(out));
  EXPECT_EQ(out[0], 0);
  jsonSafe("Fluffy", nullptr, 0);                   // no crash
  char one[1] = {'Q'};
  jsonSafe("Fluffy", one, 1);
  EXPECT_EQ(one[0], 0);
}

TEST(NovaPetName, EveryByteIsEitherKeptOrStripped) {
  for (int c = 0; c < 256; c++) {
    const char in[3] = {'a', (char)c, 0};
    const std::string s = safe(in);
    const bool keep = c >= 0x20 && c <= 0x7E && c != '"' && c != '\\';
    EXPECT_EQ(s.size(), keep ? 2u : 1u) << c;
    if (c == 0) EXPECT_EQ(s, "a");                  // a NUL ends the name
  }
}

TEST(NovaPetName, ReplyLines) {
  EXPECT_EQ(say(Status::Ok, "Fluffy"), "{\"nova_ok\":\"petname\",\"name\":\"Fluffy\"}");
  EXPECT_EQ(say(Status::Ok, "Mr Bubbles"), "{\"nova_ok\":\"petname\",\"name\":\"Mr Bubbles\"}");
  EXPECT_EQ(say(Status::Cleared, "ignored"), "{\"nova_ok\":\"petname\",\"name\":\"\"}");
  EXPECT_EQ(say(Status::Usage, ""), "{\"nova_error\":\"petname_usage\"}");
  EXPECT_EQ(say(Status::TooLong, ""), "{\"nova_error\":\"petname_too_long\"}");
  EXPECT_EQ(say(Status::NonAscii, ""), "{\"nova_error\":\"petname_not_ascii\"}");
  EXPECT_EQ(say(Status::JsonChar, ""), "{\"nova_error\":\"petname_bad_char\"}");
  EXPECT_EQ(say(Status::NoPet, ""), "{\"nova_unavailable\":\"petname\"}");
  EXPECT_EQ(say(Status::SaveFailed, ""), "{\"nova_error\":\"petname_save_failed\"}");
}

TEST(NovaPetName, ReplyNeverRepeatsABadName) {
  // even if an unsafe name reaches reply() (a stored name from an older file), the line stays valid
  for (const char* n : {"a\"b", "a\\b", "\"}}{\"x\":1", "caf\xC3\xA9", "\x01\x02"}) {
    const std::string s = say(Status::Ok, n);
    EXPECT_TRUE(jsonStringsClean(s)) << s;
    EXPECT_EQ(s.rfind("{\"nova_ok\":\"petname\",\"name\":\"", 0), 0u) << s;
    EXPECT_EQ(s.back(), '}');
    EXPECT_EQ(s.find('\n'), std::string::npos);
  }
  EXPECT_EQ(say(Status::Ok, "a\"b\\c"), "{\"nova_ok\":\"petname\",\"name\":\"abc\"}");
  EXPECT_EQ(say(Status::Ok, nullptr), "{\"nova_ok\":\"petname\",\"name\":\"\"}");
}

TEST(NovaPetName, ReplyLinesAreOneLineJsonAndNotNovaStatusOrProfile) {
  for (Status s : {Status::Ok, Status::Cleared, Status::Usage, Status::TooLong, Status::NonAscii, Status::JsonChar, Status::NoPet, Status::SaveFailed}) {
    const std::string l = say(s, "Fluffy");
    EXPECT_EQ(l.rfind("{", 0), 0u) << l;
    EXPECT_EQ(l.find('\n'), std::string::npos);
    EXPECT_TRUE(jsonStringsClean(l)) << l;
    EXPECT_EQ(l.find("nova status"), std::string::npos);
    EXPECT_EQ(l.find("nova profile"), std::string::npos);
  }
}

TEST(NovaPetName, ReplySmallBuffersNeverHoldHalfALine) {
  const size_t full = strlen("{\"nova_ok\":\"petname\",\"name\":\"Fluffy\"}");
  for (size_t cap = 1; cap <= full; cap++) {
    char out[64]; memset(out, '!', sizeof(out));
    EXPECT_EQ(reply(Status::Ok, "Fluffy", out, cap), 0u) << cap;
    EXPECT_EQ(out[0], 0);
  }
  char out[64];
  EXPECT_EQ(reply(Status::Ok, "Fluffy", out, full + 1), full);
  EXPECT_EQ(reply(Status::Ok, "Fluffy", nullptr, 8), 0u);
  EXPECT_EQ(reply(Status::Ok, "Fluffy", out, 0), 0u);
}

TEST(NovaPetName, HelloCapIsOnlyOneWhenTheHandlerWorks) {
  // The handler in MyMesh.cpp sets caps.petname from whether the pet screen registered its setter.
  NovaCli::Caps none;
  char out[400];
  ASSERT_GT(NovaCli::reply(NovaCli::parse("nova hello"), "DX-PRO", none, out, sizeof(out)), 0u);
  EXPECT_NE(std::string(out).find("\"petname\":0"), std::string::npos);
  NovaCli::Caps works; works.petname = 1;
  ASSERT_GT(NovaCli::reply(NovaCli::parse("nova hello"), "DX-PRO", works, out, sizeof(out)), 0u);
  EXPECT_NE(std::string(out).find("\"petname\":1"), std::string::npos);
  EXPECT_EQ(std::string(out).rfind("{\"ed\":\"dx-pro\",", 0), 0u);
}

// ---- the PetMirror encoder: the name argument is the pet's name, made JSON safe ------------------------

namespace {

// pulls the value of "n":"..." out of a key frame line ("" and false when there is none)
bool nameField(const std::string& line, std::string* v) {
  const std::string key = "\"n\":\"";
  size_t a = line.find(key);
  if (a == std::string::npos) return false;
  a += key.size();
  size_t b = line.find('"', a);
  if (b == std::string::npos) return false;
  *v = line.substr(a, b - a);
  return true;
}

// what the firmware does: the stored name goes through jsonSafe before it becomes the encoder's name argument
std::string keyLineFor(const char* storedPetName, const char* radioNodeName) {
  PetMirror m;
  PetMirrorEncoder e;
  char nm[kMax + 1];
  jsonSafe(storedPetName, nm, sizeof(nm));
  char out[4096];
  size_t n = e.line(m.fb, 0, out, sizeof(out), nm, 0, 0, 1, 0);
  EXPECT_GT(n, 0u);
  (void)radioNodeName;                               // deliberately not passed anywhere
  return std::string(out);
}

}  // namespace

TEST(NovaPetNameEncoder, KeyFrameCarriesThePetNameNotTheRadioName) {
  const std::string l = keyLineFor("Fluffy", "MyRadio-Node-42");
  std::string v;
  ASSERT_TRUE(nameField(l, &v));
  EXPECT_EQ(v, "Fluffy");
  EXPECT_EQ(l.find("MyRadio"), std::string::npos);
}

TEST(NovaPetNameEncoder, UnsafeStoredNamesCannotBreakTheLine) {
  for (const char* stored : {"a\"b", "a\\b", "\"},\"x\":\"", "caf\xC3\xA9", "0123456789ABCDEFGHIJ"}) {
    const std::string l = keyLineFor(stored, "radio");
    EXPECT_TRUE(jsonStringsClean(l)) << l;
    std::string v;
    ASSERT_TRUE(nameField(l, &v));
    EXPECT_LE(v.size(), kMax);
    EXPECT_EQ(v.find('\\'), std::string::npos);
  }
  std::string v;
  ASSERT_TRUE(nameField(keyLineFor("a\"b\\c", "radio"), &v));
  EXPECT_EQ(v, "abc");
}

TEST(NovaPetNameEncoder, NoPetNameMeansAnEmptyNameFieldNeverARadioName) {
  const std::string l = keyLineFor("", "MyRadio-Node-42");
  std::string v;
  ASSERT_TRUE(nameField(l, &v));
  EXPECT_EQ(v, "");
  EXPECT_EQ(l.find("MyRadio"), std::string::npos);
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
