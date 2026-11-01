#!/usr/bin/env python3
"""Full-channel notice through the production DX handlers; hardware is mocked."""
from pathlib import Path
import runpy
import subprocess
import tempfile

fixture = Path(__file__).with_name("check_menu_navigation.py")
ns = runpy.run_path(str(fixture))
parts = ns["parts"][:-1] + [ns["parts"][-1].split("int main(){", 1)[0]]
parts.append(r'''
int main() {
  UITask task;
  using Result = LoRagotchiChannel::Result;
  for (auto result : {Result::AlreadyJoined, Result::Added, Result::NameConflict, Result::SetFailed}) {
    LoRagotchiChannel::startupResult = result;
    beginLoRaFishChannelNotice(); assert(!loRaFishChannelNotice);
  }
  LoRagotchiChannel::startupResult = Result::Full;
  beginLoRaFishChannelNotice(); assert(loRaFishChannelNotice);
  task.display.clearBounds(); drawLoRaFishChannelNotice(task.display);
  assert(task.display.printed == (std::vector<std::string>{
    "#loragotchi-dx", "Could not join", "No free channel slot",
    "Channels unchanged", "CLICK TO DISMISS"}));
  puts("PASS full-channel reason and unchanged-channel assurance fit 128x64 without overlap");

  loRaFishMeshNodeName = "No marker"; beginLoRaFishNameNotice();
  loRaFishPage = 5; loRaFishOption = LoRaFishOption::Advert;
  task.display.turnOff();
  char c = task.checkDisplayOn(KEY_NEXT); if(c) shortPress(c);
  assert(task.display.isOn() && loRaFishChannelNotice && loRaFishNameNotice);
  c = task.checkDisplayOn(KEY_NEXT); if(c) shortPress(c);
  assert(!loRaFishChannelNotice && loRaFishNameNotice && loRaFishPage == 5);
  shortPress(KEY_NEXT);
  assert(!loRaFishNameNotice && loRaFishPage == 5);
  puts("PASS wake only, then one notice dismissed per click without navigating");

  for (int gesture=0; gesture<3; ++gesture) {
    beginLoRaFishChannelNotice(); beginLoRaFishNameNotice();
    task.display.turnOff();
    if (gesture==0) task.handleLongPress(KEY_ENTER);
    else if (gesture==1) task.handleDoubleClick(KEY_PREV);
    else task.handleTripleClick(KEY_ENTER);
    assert(task.display.isOn() && loRaFishChannelNotice);
    if (gesture==0) task.handleLongPress(KEY_ENTER);
    else if (gesture==1) task.handleDoubleClick(KEY_PREV);
    else task.handleTripleClick(KEY_ENTER);
    assert(!loRaFishChannelNotice && loRaFishNameNotice && loRaFishPage==5);
  }
  assert(settingsWrites==0 && petWrites==0 && dxWrites==0 && resets==0);
  assert(the_mesh.sends==0 && the_mesh.dxSends==0 && task.buzzerToggles==0);
  puts("PASS all gestures dismiss without settings/channel/pet writes or radio actions");

  beginLoRaFishChannelNotice(); task.ui_started_at=tick;
  task.handleLongPress(KEY_ENTER);
  assert(the_mesh.rescues==1 && loRaFishChannelNotice);
  LoRagotchiChannel::startupResult=Result::Added; beginLoRaFishChannelNotice();
  assert(!loRaFishChannelNotice);
  puts("PASS startup CLI rescue retained; successful next boot clears the notice");
}
''')
begin = ns["block"]("void UITask::begin(")
assert "beginLoRaFishChannelNotice();" in begin
draw = ns["block"]("static void drawLoRaFish(")
assert draw.index("drawLoRaFishChannelNotice(display)") < draw.index("drawLoRaFishNameNotice(display)")
with tempfile.TemporaryDirectory(prefix="dx-channel-notice-") as directory:
    cpp = Path(directory) / "notice.cpp"
    cpp.write_text("\n".join(parts))
    for sound in (False, True):
        exe = Path(directory) / str(sound)
        args = ["g++", "-std=c++17", "-I"+str(ns["root"]), "-I"+str(ns["root"]/"src")]
        if sound:
            args += ["-DPIN_BUZZER=6"]
        subprocess.run(args+[str(cpp), "-o", str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
