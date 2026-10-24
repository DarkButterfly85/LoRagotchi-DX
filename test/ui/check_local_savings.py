#!/usr/bin/env python3
"""Production persistence/display checks with fault-injected RAM FS, ADC and clock.

python3 test/ui/check_local_savings.py (Python 3 and g++). No physical flash,
current measurement, panel, or radio. Reuses real care/lifecycle serializers.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
fixture_path = Path(__file__).with_name('check_fish_happiness.py')
ns = {'__file__': str(fixture_path), '__name__': 'savings_fixture'}
exec(compile(fixture_path.read_text().split('with tempfile.TemporaryDirectory(', 1)[0],
             str(fixture_path), 'exec'), ns)
block, declaration = ns['block'], ns['declaration']
parts = ns['parts'][:-1] + [ns['parts'][-1].split('int main() {', 1)[0]]
source = '\n'.join(parts)
source = source.replace('static int settingsWrites = 0;', '''static int settingsWrites = 0;
static std::map<std::string,int> saves, opens;
static std::string failOpen, shortWrite, failRemove;
static std::map<std::string,size_t> payloadBytes;''')
source = source.replace('auto& data = files[path];', '''if (path == shortWrite) count /= 2;
    payloadBytes[path] += count;
    auto& data = files[path];''')
source = source.replace('void close() { if (writing', 'void close() { if(writing)++saves[path]; if (writing')
source = source.replace('if (mode == FILE_WRITE) files[path].clear();', '''if (mode == FILE_WRITE) {
      ++opens[path];
      if (path == failOpen) return {"",0,false};
#ifdef ESP32
      files[path].clear();
#else
      // Real Adafruit FILE_O_WRITE appends; replacement must remove first.
      (void)files[path];
#endif
    }''')
source = source.replace('return files.erase(path);', 'if (path == failRemove) return false; return files.erase(path);')
source += r'''
#include "examples/companion_radio/ui-new/LoRaFishMenu.h"
#include "examples/companion_radio/ui-new/AdvertMenu.h"
#include "examples/companion_radio/ui-new/PetResetConfirmation.h"
static constexpr bool loRaFishHasSound = true;
struct DisplayDriver {
  bool on=true;
  int frames=0, brightness=0;
  bool isOn() { return on; }
  void turnOff() { on=false; }
  void startFrame() { ++frames; }
  void endFrame() {}
  int stripRows() {return 0;} int physicalHeight() {return 64;}
  void beginStrip(int) {} void endStrip() {}
  void setBrightness(uint8_t v) { brightness=v; }
};
static void loRaFishRegisterDisplayActivity(DisplayDriver&) {}
static uint32_t loRaFishScreenTimeoutMs() { return 0; }
struct UITask {
  DisplayDriver* _display=nullptr;
  uint32_t _auto_off=0,_next_refresh=0;
  int samples=0;
  uint16_t millivolts=3900;
  uint16_t getBattMilliVolts() { ++samples;return millivolts; }
  void gotoHomeScreen() {}
  void handleLoRaFishMessage();
} ui;
'''
source += block('void UITask::handleLoRaFishMessage() {')
for name in '''loRaFishBatteryValid loRaFishBatterySampledAt loRaFishBatteryMilliVolts
loRaFishChannelNotice loRaFishNameNotice loRaFishStaticFrameValid loRaFishStaticFrame loRaFishOption loRaFishDisplayOption
loRaFishTimeField loRaFishTimeoutField loRaFishSoundField loRaFishValuePicker
loRaFishResetConfirmation loRaFishAdvertMenu loRaFishScreenDimmed
loRaFishBrightnessNeedsApply loRaFishTimeoutSleepStateKnown loRaFishTimeoutSleepState
loRaFishLastActivityMs loRaFishAlwaysOnDimValues loRaFishBrightnessValues
LORAFISH_RESET_CONFIRM_PAGE LORAFISH_DX_CONTACT_PAGE'''.split():
    source += '\n' + declaration(name)
for marker in ['static uint16_t loRaFishDisplayBattery(', 'static bool shouldRenderLoRaFish(',
               'static void applyLoRaFishBrightness(']:
    source += '\n' + block(marker)
# Actual HomeScreen render cadence, with only pixel drawing mocked.
full_source = ns['fixture']['SOURCE']
home = full_source[full_source.index('class HomeScreen'):]
render_start = home.index('  int render(DisplayDriver& display) override {')
render = home[render_start:home.index('    display.setColor(UIColor::title_bkg);',render_start)]
render = render[:render.rfind('#else')]+ '#endif\n  }'
render = render.replace(' override', '').replace('    drawLoRaFish(display, _task);', '    ++drawCalls;')
source += '\nstatic int drawCalls=0;\nstruct Screen {\n' + render + '\n};\n'
# Exercise the real display-on/brightness/refresh block from UITask::loop.
render_loop = full_source[full_source.index('  if (_display != NULL && _display->isOn()) {\n#ifdef LORAFISH_UI\n    const bool sleeping='):].split('\n#ifdef PIN_VIBRATION\n  vibration.loop();',1)[0]
source += r'''
static void cancelLoRaFishReset() {}
static void drawUIAlertBox(DisplayDriver&,const char*) {}
static void displayLoop(DisplayDriver* _display, Screen* curr, Screen* home,
                        uint32_t& _next_refresh, uint32_t _alert_expiry=0) {
  const char* _alert="Test";
  uint32_t _auto_off=0;
'''
# Include the actual off-screen invalidation adjacent to the loop block.
source += full_source[full_source.index('  if (!_display || !_display->isOn()) loRaFishStaticFrameValid = false;'):].split('#endif',1)[0]
source += render_loop+'\n}\n'
source += r'''
static void clearCounts() { saves.clear();opens.clear();payloadBytes.clear(); }
static void beginCheck(int hour=12) {
  failOpen=shortWrite=failRemove="";
  resetHappy();localEpochBase=hour*3600;
  fish.messages=0;fish.txAcks=0;
  saveLoRaFishSettings();saveLoRaFish();clearCounts();
}
static void message() { ui.handleLoRaFishMessage(); }
static void report(const char* name) {
  printf("COUNTS %s pet=%d cfg=%d messages=%lu meals=%d\n",name,
      saves["/lorafish.dat"],saves["/lorafish.cfg"],(unsigned long)fish.messages,feeds);
}
static void hour(int every, int hour=12) {
  beginCheck(hour);
  for(int sec=1;sec<=3600;++sec) {
    clockMs+=1000;
    if(every && sec%every==0)message();
    service();
  }
}
int main() {
  beginCheck();
  for(int i=0;i<100;++i){saveLoRaFish();saveLoRaFishSettings();}
  assert(saves.empty());
  reboot();clearCounts();saveLoRaFish();saveLoRaFishSettings();
  assert(saves.empty());
  assert(files["/lorafish.dat"].size()==32 && files["/lorafish.cfg"].size()==LORAFISH_SETTINGS_SIZE);
  pass("identical requests and canonical boot snapshots cause no file writes");

  beginCheck();for(int i=0;i<100;++i){message();service();}
  assert(fish.messages==100 && saves["/lorafish.dat"]==1 && saves["/lorafish.cfg"]==1);
  report("100_message_burst");
  pass("one hundred messages batch, but their first eligible meal persists immediately");

  beginCheck(22);message();clockMs=299999;service();
  assert(saves.empty());clockMs=300000;service();
  assert(saves["/lorafish.dat"]==1);
  reboot();assert(fish.messages==1 && fish.ageMinutes==65);
  pass("passive counters reach disk exactly at five minutes and restore across boot");

  hour(6,22);assert(fish.messages==600 && saves["/lorafish.dat"]==12);
  report("600_messages_sleeping_hour");
  hour(6);assert(fish.messages==600 && saves["/lorafish.dat"]<=14 && saves["/lorafish.cfg"]<=16);
  report("600_messages_awake_hour");
  hour(60);report("60_messages_awake_hour");
  hour(0);report("quiet_awake_hour");
  beginCheck(7);advance(24*3600000UL);report("quiet_24h");
  pass("sustained traffic cannot postpone the checkpoint indefinitely");

  beginCheck(22);clockMs=3600000;service();
  assert(fish.ageMinutes==120 && saves["/lorafish.dat"]==1);
  report("one_hour_delayed_tick");
  pass("ordinary delayed age catch-up saves only the final state");

  beginCheck(22);clockMs=0xFFFFFF00UL;
  fishLastMinute=fishLastSave=loRaFishHappyLastMs=loRaFishHappyLastSavedMs=(uint32_t)clockMs;
  message();clockMs+=299999;service();assert(saves.empty());
  ++clockMs;service();assert(saves["/lorafish.dat"]==1);
  pass("five-minute checkpoint deadline survives millis wraparound");

  beginCheck();message();clockMs=17000;flushLoRaFish();
  reboot();assert(fish.messages==1 && loRaFishHappiness.awakeMs==17000);
  pass("LoRagotchi shutdown flush includes passive counters and partial Happy timing");

  beginCheck(22);loRaFishNeedsAppearanceSetup=true;message();
  clockMs=300000;service();reboot();assert(fish.messages==1 && fish.ageMinutes==60);
  pass("appearance setup pauses age without disabling counter checkpoints");

  for(bool settings:{false,true}) for(bool partial:{false,true}) {
    beginCheck();
    const std::string path=settings?"/lorafish.cfg":"/lorafish.dat";
    if(settings)loRaFishTheme=1;else ++fish.messages;
    if(partial)shortWrite=path;else failOpen=path;
    if(settings)saveLoRaFishSettings();else saveLoRaFish();
    assert(settings?loRaFishSettingsSaveFailed:loRaFishSaveFailed);
    assert(opens[path]==1);
    // Returning to the old RAM value must still repair an incomplete disk write.
    if(settings)loRaFishTheme=0;else --fish.messages;
    for(int i=0;i<100;++i)service();
    clockMs=4999;service();assert(opens[path]==1);
    failOpen=shortWrite="";clockMs=5000;service();assert(opens[path]==2);
    assert(!(settings?loRaFishSettingsSaveFailed:loRaFishSaveFailed));
    assert(files[path].size()==(settings?LORAFISH_SETTINGS_SIZE:32));
    reboot();assert(fish.messages==0 && loRaFishTheme==0);
  }
  pass("open/short-write failures remain dirty and retry at five seconds, never loop-spin");

#ifndef ESP32
  beginCheck();++fish.messages;failRemove="/lorafish.dat";
  const auto disk=files[failRemove];saveLoRaFish();
  assert(loRaFishSaveFailed && files[failRemove]==disk && opens.empty());
  failRemove="";clockMs=5000;service();assert(files["/lorafish.dat"].size()==32);
  pass("failed LittleFS replacement never appends to the existing record");
#endif

  beginCheck();++fish.messages;failOpen="/lorafish.dat";saveLoRaFish();
  failOpen="";clockMs=100;flushLoRaFish();
  assert(!loRaFishSaveFailed);reboot();assert(fish.messages==1);
  pass("shutdown makes one final write attempt without waiting for failure backoff");

  beginCheck();files["/lorafish.cfg"].resize(24);reboot();clearCounts();
  assert(!haveLastWrittenLoRaFishSettings);saveLoRaFishSettings();
  assert(saves["/lorafish.cfg"]==1 && files["/lorafish.cfg"].size()==LORAFISH_SETTINGS_SIZE);
  pass("legacy settings are not mistaken for a fully persisted current record");

  beginCheck();loRaFishTimeoutAwakeSetting=5;loRaFishPoopCount=2;
  loRaFishTheme=1;loRaFishColor=3;loRaFishSleepHour=22;loRaFishWakeHour=6;
  loRaFishUtcOffsetQuarters=-16;loRaFishTimeoutAsleepSetting=4;
  loRaFishBrightnessSetting=2;loRaFishAlwaysOnDimSetting=1;
  loRaFishBuzzerVolume=3;loRaFishWakeSound=2;loRaFishSleepSound=1;loRaFishMessageSound=3;
  loRaFishScaleColor=4;loRaFishEyeColor=5;loRaFishGeneration=0x1234;
  loRaFishPendingEgg=true;loRaFishEggAppearance={6,5,4};
  loRaFishNeedsAppearanceSetup=true;loRaFishSimulationMode=true;
  loRaFishHappiness.awakeMs=0x10203;loRaFishHappiness.mealCooldownMs=0x20304;
  saveLoRaFishSettings();
  const std::vector<uint8_t> expected={5,2,1,3,22,6,240,4,2,1,3,2,1,3,4,5,
      0x34,0x12,1,6,5,4,1,1,0x31,0x50,0x41,0x48,3,2,1,0,4,3,2,0,
      0x41,0x51,0x55,0x31,0,0,0,0,
      0x48,0x55,0x45,0x31,3,4,5,5,6,4};
  assert(files["/lorafish.cfg"]==expected);
  reboot();clearCounts();saveLoRaFishSettings();assert(saves.empty());
  pass("settings encoding retains every byte of the legacy prefix and HAP1 tail");

  beginCheck();failOpen="/lorafish.cfg";
  assert(loRaFishHappiness.aquarium(true,fish.happiness));saveLoRaFish();
  assert(loRaFishSettingsSaveFailed && opens["/lorafish.cfg"]==1);
  clockMs+=4999;tickLoRaFish();assert(opens["/lorafish.cfg"]==1);
  failOpen="";clockMs++;tickLoRaFish();
  assert(!loRaFishSettingsSaveFailed && opens["/lorafish.cfg"]==2);
  reboot();assert(loRaFishHappiness.aquariumCooldownMs==21595000);
  assert(!loRaFishHappiness.aquarium(true,fish.happiness));
  pass("failed aquarium-cap save stays pending and retries once at the existing deadline");

  beginCheck();failOpen="/lorafish.cfg";loRaFishTheme=2;saveLoRaFishSettings();
  clockMs=0xFFFFFF00UL;loRaFishSettingsLastAttempt=(uint32_t)clockMs;
  failOpen="";clockMs+=4999;saveLoRaFishSettings();assert(opens["/lorafish.cfg"]==1);
  ++clockMs;saveLoRaFishSettings();assert(opens["/lorafish.cfg"]==2);
  pass("failure retry deadline survives millis wraparound");

  loRaFishBatteryValid=false;ui.samples=0;clockMs=0;
  for(int i=0;i<100;++i){clockMs=i*100;assert(loRaFishDisplayBattery(&ui)==3900);}
  assert(ui.samples==2);
  clockMs=9999;ui.millivolts=4000;assert(loRaFishDisplayBattery(&ui)==3900);
  clockMs=10000;assert(loRaFishDisplayBattery(&ui)==4000 && ui.samples==3);
  clockMs=0xFFFFFF00UL;loRaFishBatteryValid=false;loRaFishDisplayBattery(&ui);
  clockMs+=4999;loRaFishDisplayBattery(&ui);assert(ui.samples==4);
  ++clockMs;loRaFishDisplayBattery(&ui);assert(ui.samples==5);
  pass("battery cache uses the board reading, expires exactly at five seconds and wraps safely");

  beginCheck();loRaFishPage=12;loRaFishStaticFrameValid=false;
  DisplayDriver panel;Screen screen;uint32_t next=0;drawCalls=0;
  for(int t=0;t<60000;t+=100){clockMs=t;displayLoop(&panel,&screen,&screen,next);}
  assert(drawCalls==1 && panel.frames==1);
  loRaFishDisplayOption=1;clockMs=60000;displayLoop(&panel,&screen,&screen,next);
  assert(panel.frames==2);
  next=0;displayLoop(&panel,&screen,&screen,next);assert(panel.frames==3);
  pass("unchanged static menu writes one frame per minute; change and input redraw immediately");

  loRaFishPage=5;loRaFishStaticFrameValid=false;
  assert(shouldRenderLoRaFish(true,false,false));assert(!shouldRenderLoRaFish(true,false,false));
  loragotchiDXGuest.present=true;fish.evolution=2;
  assert(shouldRenderLoRaFish(true,false,false));
  assert(shouldRenderLoRaFish(true,true,false));assert(shouldRenderLoRaFish(true,false,false));
  assert(shouldRenderLoRaFish(false,false,false));assert(shouldRenderLoRaFish(true,false,false));
  pass("breeding eligibility, alerts and screen transitions invalidate static menus");

  loRaFishAlwaysOnDimSetting=0;
  for(bool simulation:{false,true}) for(bool dim:{false,true}) {
    loRaFishPage=0;loRaFishSimulationMode=simulation;
    clockMs=dim?20000:1000;loRaFishLastActivityMs=0;
    next=0;drawCalls=0;panel.frames=0;panel.on=true;
    for(int i=0;i<100;++i){displayLoop(&panel,&screen,&screen,next);clockMs+=100;}
    assert(drawCalls==(simulation?34:100) && panel.frames==drawCalls);
    assert(loRaFishScreenDimmed==dim);
  }
  pass("normal and dimmed aquarium keep identical Smooth/Simulation frame cadence");

  loRaFishPage=12;next=0;displayLoop(&panel,&screen,&screen,next);
  const int before=panel.frames;panel.on=false;
  for(int i=0;i<100;++i){clockMs+=100;displayLoop(&panel,&screen,&screen,next);}
  assert(panel.frames==before && !loRaFishStaticFrameValid);
  panel.on=true;next=0;displayLoop(&panel,&screen,&screen,next);
  assert(panel.frames==before+1);
  beginCheck();panel.on=false;const auto age=fish.ageMinutes;
  clockMs+=60000;service();assert(fish.ageMinutes==age+1);
  pass("off display writes nothing, wake redraws and pet simulation remains independent");

  for (bool channel : {false,true}) {
    loRaFishPage=0;loRaFishSimulationMode=false;
    loRaFishChannelNotice=channel;loRaFishNameNotice=!channel;
    panel.on=true;panel.frames=0;drawCalls=0;next=0;clockMs=0;
    loRaFishStaticFrameValid=false;
    for(int i=0;i<100;++i){displayLoop(&panel,&screen,&screen,next);clockMs+=100;}
    assert(panel.frames==1 && drawCalls==1);
    loRaFishChannelNotice=loRaFishNameNotice=false;next=0;
    displayLoop(&panel,&screen,&screen,next);assert(panel.frames==2);
    clockMs+=100;displayLoop(&panel,&screen,&screen,next);assert(panel.frames==3);
  }
  pass("name and channel boot notices stay static until dismissed, then normal aquarium frames resume");
}
'''
# Call-site assertions protect isolation from the fresh safety path.
assert 'loRaFishDisplayBattery(task)' in block('static void drawLoRaFishTankBattery(')
assert 'loRaFishDisplayBattery(task)' in block('static void drawLoRaFishRFMonitor(')
assert 'uint16_t milliVolts = getBattMilliVolts();' in full_source.split('void UITask::loop() {',1)[1].split('char UITask::checkDisplayOn',1)[0]
assert 'flushLoRaFish();' in block('void UITask::shutdown(')
with tempfile.TemporaryDirectory(prefix='lorafish-savings-') as directory:
    cpp = Path(directory)/'savings.cpp'
    cpp.write_text(source)
    for platform in ('ESP32', 'NRF52_PLATFORM'):
        exe=Path(directory)/platform
        subprocess.run(['g++','-std=c++17','-O2','-I',str(ROOT),'-D'+platform,
                        str(cpp),'-o',str(exe)],check=True)
        print('Local savings checks: '+platform,flush=True)
        subprocess.run([str(exe)],check=True)
