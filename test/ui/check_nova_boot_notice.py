#!/usr/bin/env python3
"""Boot notice 'HOLD TO ENABLE NOVA' through the production handlers; hardware is mocked.

python3 test/ui/check_nova_boot_notice.py   (Python 3 and g++; no firmware build, no hardware)
"""
from pathlib import Path
import runpy
import subprocess
import tempfile

fixture = Path(__file__).with_name("check_menu_navigation.py")
ns = runpy.run_path(str(fixture))
source = ns["source"]
parts = ns["parts"][:-1] + [ns["parts"][-1].split("int main(){", 1)[0]]
parts.append("static bool loRaFishNovaNoticeTimed = false;\nstatic unsigned long loRaFishNovaNoticeEnd = 0;\n#define LORAFISH_NOVA_NOTICE_MILLIS 5000UL")
parts.append(ns["block"]("static void beginLoRaFishNovaNotice("))
parts.append(ns["block"]("static bool serviceLoRaFishNovaNotice("))
parts.append(ns["block"]("static void drawLoRaFishNovaNotice("))
parts.append(r'''
static std::string joined(BoundsDisplay& d) { std::string s; for (auto& l : d.printed) s += l + "|"; return s; }
int main() {
  UITask task;
  loRaFishChannelNotice = loRaFishNameNotice = loRaFishMonoDisplayNotice = false;
  loRaFishPage = 0;

  // (a) set at boot; the 5 s timer starts only once the home screen is up, then clears by itself.
  beginLoRaFishNovaNotice(); assert(loRaFishNovaNotice);
  unsigned long t = 1000;
  assert(!serviceLoRaFishNovaNotice(false, t));                 // splash showing: timer not started
  assert(!serviceLoRaFishNovaNotice(false, t + 60000UL) && loRaFishNovaNotice);   // never expires behind the splash
  t = 4000;                                                     // splash ends, home visible
  assert(!serviceLoRaFishNovaNotice(true, t) && loRaFishNovaNotice);
  assert(!serviceLoRaFishNovaNotice(true, t + LORAFISH_NOVA_NOTICE_MILLIS - 1) && loRaFishNovaNotice);
  assert(serviceLoRaFishNovaNotice(true, t + LORAFISH_NOVA_NOTICE_MILLIS) && !loRaFishNovaNotice);
  assert(!serviceLoRaFishNovaNotice(true, t + 99999) );         // gone for good until next boot
  assert(LORAFISH_NOVA_NOTICE_MILLIS == 5000UL);
  puts("PASS notice armed at boot, timer starts after the splash, clears after 5 s");

  // millis() wrap-around does not end the notice early or hold it forever.
  beginLoRaFishNovaNotice(); unsigned long near = 0xFFFFFFFFUL - 1000UL;
  serviceLoRaFishNovaNotice(true, near);
  assert(!serviceLoRaFishNovaNotice(true, near + 2000UL) && loRaFishNovaNotice);
  assert(serviceLoRaFishNovaNotice(true, near + 5000UL) && !loRaFishNovaNotice);
  puts("PASS timer survives millis() wrap");

  // (b) one single press dismisses it without navigating, saving or sending.
  loRaFishPage = 5; loRaFishOption = LoRaFishOption::Advert;
  beginLoRaFishNovaNotice(); serviceLoRaFishNovaNotice(true, t);
  shortPress(KEY_NEXT);
  assert(!loRaFishNovaNotice && loRaFishPage == 5 && loRaFishOption == LoRaFishOption::Advert);
  for (int gesture = 0; gesture < 3; ++gesture) {
    beginLoRaFishNovaNotice();
    if (gesture == 0) task.handleLongPress(KEY_ENTER, false);
    else if (gesture == 1) task.handleDoubleClick(KEY_PREV);
    else task.handleTripleClick(KEY_ENTER);
    assert(!loRaFishNovaNotice && loRaFishPage == 5);
  }
  assert(settingsWrites == 0 && petWrites == 0 && dxWrites == 0 && resets == 0);
  assert(the_mesh.sends == 0 && the_mesh.dxSends == 0 && task.buzzerToggles == 0 && the_mesh.rescues == 0);
  puts("PASS single press dismisses without navigation, saves or radio actions");

  // The existing startup hold is unchanged: inside the window it still enters CLI Rescue.
  beginLoRaFishNovaNotice(); task.ui_started_at = tick;
  task.handleLongPress(KEY_ENTER);
  assert(the_mesh.rescues == 1 && loRaFishNovaNotice);
  loRaFishNovaNotice = false;
  puts("PASS startup hold still enters CLI Rescue (notice only describes it)");

  // The other notices still behave: Nova goes first, then the name notice, one press each.
  loRaFishMeshNodeName = "No marker"; beginLoRaFishNameNotice(); beginLoRaFishNovaNotice();
  shortPress(KEY_NEXT); assert(!loRaFishNovaNotice && loRaFishNameNotice);
  shortPress(KEY_NEXT); assert(!loRaFishNameNotice && loRaFishPage == 5);
  assert(settingsWrites == 0 && petWrites == 0);
  puts("PASS other notices unchanged and queued behind it");

  // (c) not shown / not consumed with the screen off or away from the home screen.
  beginLoRaFishNovaNotice();
  task.display.turnOff();
  char c = task.checkDisplayOn(KEY_NEXT); if (c) shortPress(c);
  assert(task.display.isOn() && loRaFishNovaNotice);            // wake press only wakes
  task.curr = &task.other;                                      // another screen is in front
  assert(!serviceLoRaFishNovaNotice(task.curr == task.home, t));
  beginLoRaFishNovaNotice();
  task.handleLongPress(KEY_ENTER, false); task.handleDoubleClick(KEY_PREV);
  assert(loRaFishNovaNotice);                                   // off-home gestures do not consume it
  task.curr = task.home; loRaFishNovaNotice = false;
  puts("PASS not dismissed by wake press or off the home screen");

  // Text fits 128 px mono and nothing overlaps; static output (d).
  loRaFishNovaNotice = true;
  task.display.clearBounds(); drawLoRaFishNovaNotice(task.display);
  assert(task.display.printed == (std::vector<std::string>{
    "NOVA MODE", "", "HOLD TO ENABLE NOVA", "dashboard mode", "or wait: normal mode", "CLICK TO DISMISS"}) ||
    task.display.printed == (std::vector<std::string>{
    "NOVA MODE", "HOLD TO ENABLE NOVA", "dashboard mode", "or wait: normal mode", "CLICK TO DISMISS"}));
  std::string first = joined(task.display);
  for (const auto& line : task.display.printed) assert((int)strlen(line.c_str()) * 6 <= 128);
  assert(task.display.getTextWidth("HOLD TO ENABLE NOVA") == 114);
  task.display.clearBounds(); tick += 12345; drawLoRaFishNovaNotice(task.display);
  assert(joined(task.display) == first);                        // same frame at any time: no animation
  puts("PASS wording fits 128 px and renders the same still frame every time");
}
''')
begin = ns["block"]("void UITask::begin(")
assert "beginLoRaFishNovaNotice();" in begin
assert begin.index("beginLoRaFishNovaNotice();") > begin.index("beginLoRaFishNameNotice();")
loop = ns["block"]("void UITask::loop(")
assert "serviceLoRaFishNovaNotice(curr == home, millis())" in loop
assert loop.index("serviceLoRaFishNovaNotice") < loop.index("tickLoRaFish();")
draw = ns["block"]("static void drawLoRaFish(")
assert draw.index("drawLoRaFishNovaNotice(display)") < draw.index("drawLoRaFishChannelNotice(display)")
nova_draw = ns["block"]("static void drawLoRaFishNovaNotice(")
assert "millis" not in nova_draw and "animation" not in nova_draw.lower().replace("no animation", "")
# Static-page handling: no animation frame is produced while the notice shows.
assert "return 2000;" in source and "if (loRaFishNovaNotice || loRaFishChannelNotice || loRaFishNameNotice) return 2000;" in source
render = ns["block"]("static bool shouldRenderLoRaFish(")
assert "loRaFishNovaNotice ||" in render and "(uint8_t)loRaFishNovaNotice" in render
assert "if (loRaFishNovaNotice || loRaFishChannelNotice || loRaFishNameNotice || loRaFishMonoDisplayNotice || loRaFishAdoptionEligible)" in ns["block"]("static bool loRaFishListPage(")
# Splash timing, rescue window and long press constants are untouched.
assert "#define BOOT_SCREEN_MILLIS   3000" in source and "#define LONG_PRESS_MILLIS   1200" in source
assert "millis() - ui_started_at < 8000" in source
with tempfile.TemporaryDirectory(prefix="dx-nova-notice-") as directory:
    cpp = Path(directory) / "notice.cpp"
    cpp.write_text("\n".join(parts))
    for sound in (False, True):
        exe = Path(directory) / str(sound)
        args = ["g++", "-std=c++17", "-I" + str(ns["root"]), "-I" + str(ns["root"] / "src")]
        if sound:
            args += ["-DPIN_BUZZER=6"]
        subprocess.run(args + [str(cpp), "-o", str(exe)], check=True, timeout=240)
        subprocess.run([str(exe)], check=True, timeout=30)

