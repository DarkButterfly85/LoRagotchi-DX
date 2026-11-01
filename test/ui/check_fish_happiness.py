#!/usr/bin/env python3
"""Exercise production Happy/meal/lifecycle/settings paths, with RAM files and time.

Run: python3 test/ui/check_fish_happiness.py (Python 3 and g++).
Uses the same production extraction fixture as the lifecycle regression, for
both ESP32 and nRF52 serializers. No radio, actual flash, or accelerated firmware.
"""
from pathlib import Path
import runpy
import subprocess
import tempfile

fixture = runpy.run_path(str(Path(__file__).with_name('check_fish_lifecycle.py')))
ROOT = fixture['ROOT']
block, declaration = fixture['block'], fixture['declaration']
parts = fixture['parts'][:-1]
parts.append(fixture['parts'][-1].split('int main() {', 1)[0])
parts.append(r'''
long random(long upper) { return upper/2; }
unsigned long micros() { return (uint32_t)(clockMs*1000); }
void randomSeed(uint32_t) {}
static void scheduleLoRaFishPoop();
static bool loRaFishIsSleeping() {
  return LoRaFishHappiness::sleeping((loRaFishLocalEpoch()/3600)%24,
                                    loRaFishSleepHour,loRaFishWakeHour);
}
''')
for name in '''loRaFishCleaningStarted LORAFISH_CLEAN_MS loRaFishGuessNumber
loRaFishGuessPrevious loRaFishGuessRounds loRaFishGuessScore loRaFishGuessHigher
loRaFishGuessResultShown loRaFishGuessCorrect loRaFishGuessComplete'''.split():
    parts.append(declaration(name))
for marker in ['static bool creditLoRaFishMeal(', 'static bool consumeLoRaFishMeals(',
               'static void scheduleLoRaFishPoop() {', 'static bool tickLoRaFishPoop(',
               'static void startLoRaFishCleaning(', 'static void reactLoRaFish(',
               'static void startLoRaFishGuessGame(', 'static void submitLoRaFishGuess(']:
    parts.append(block(marker))
parts.append(r'''
static int feeds=0;
static void resetHappy(uint32_t age=60,uint8_t value=80,uint8_t poop=0) {
  resetAt(age);
  localEpochBase=43200;loRaFishSleepHour=21;loRaFishWakeHour=7;
  fish.happiness=value;fish.rfEvents=0;loRaFishNextAutoFeed=10;
  loRaFishPoopCount=poop;loRaFishNextPoopAt=0;
  loRaFishCleaning=false;loRaFishFeeding=false;
  feeds=0;
}
static void service() {
  tickLoRaFish();
  if(consumeLoRaFishMeals(false))++feeds;
  tickLoRaFishPoop();
}
static void advance(uint32_t duration) {
  // Frequent service matches the main loop; coarse gaps are tested separately.
  while(duration) {
    const uint32_t step=min(duration,1000U);clockMs+=step;duration-=step;service();
  }
}
static void events(int count) {
  for(int i=0;i<count;++i)reactLoRaFish(1);
  service();
}
int main() {
  resetHappy();
  for(int i=0;i<100;++i)reactLoRaFish(1);
  assert(fish.rfEvents==100 && fish.happiness==80);
  assert(fishReaction==1 && fishReactionUntil==2500);
  pass("RF still counts/reacts but no longer grants direct Happy");

  resetHappy();events(9);assert(feeds==0 && fish.happiness==80);
  events(1);assert(feeds==1 && fish.happiness==83 && loRaFishNextPoopAt);
  events(990);assert(feeds==1 && fish.happiness==83 && loRaFishNextAutoFeed==1010);
  pass("ten events earn one meal; burst thresholds are consumed without a queue");

  resetHappy();events(10);advance(3599999);events(10);
  assert(feeds==1 && loRaFishHappiness.mealCooldownMs==1);
  advance(1);assert(feeds==1);events(10);assert(feeds==2);
  assert(loRaFishHappiness.mealCooldownMs==3600000);
  pass("meal blocked one millisecond before hour; fresh threshold required at expiry");

  resetHappy();advance(1799999);assert(fish.happiness==80);
  advance(1);assert(fish.happiness==79 && loRaFishHappiness.awakeMs==0);
  for(int i=0;i<100;++i)service();assert(fish.happiness==79);
  pass("clean-tank half-hour boundary is exact and repeated ticks are idempotent");

  for(uint8_t poop=0;poop<=3;++poop) {
    resetHappy(60,80,poop);advance(1800000);
    assert(fish.happiness==79-poop);
  }
  resetHappy(60,1,3);advance(3600000);assert(fish.happiness==0);
  pass("waste scales decay 1..4 points per half-hour, safely saturating at zero");

  resetHappy();localEpochBase=20*3600+45*60;
  advance(15*60000);assert(loRaFishHappiness.awakeMs==15*60000);
  advance(10*3600000);assert(fish.happiness==80);
  advance(15*60000);assert(fish.happiness==79);
  pass("scheduled sleep pauses a partial drain interval and resumes at wake");

  resetHappy();localEpochBase=20*3600+15*60;
  clockMs=11*3600000UL;service();
  assert(fish.happiness==78 && loRaFishHappiness.awakeMs==0);
  pass("delayed tick across midnight/sleep/wake counts only the one awake hour");

  resetHappy(0);advance(5*60000);assert(fish.happiness==80 && loRaFishHappiness.awakeMs==0);
  advance(30*60000);assert(fish.happiness==79);
  resetHappy(LORAFISH_LIFESPAN_MINUTES-1);loRaFishHappiness.awakeMs=28*60000;
  advance(60000);assert(fish.happiness==80);
  advance(4*60000);assert(fish.happiness==80 && loRaFishHappiness.awakeMs==29*60000);
  advance(60000);assert(fish.ageMinutes==0 && fish.happiness==80 && loRaFishHappiness.awakeMs==0);
  pass("egg and memorial do not decay; succession clears timers without changing waits");

  for(uint32_t age : {0U,LORAFISH_LIFESPAN_MINUTES}) {
    resetHappy(age);events(100);assert(feeds==0 && !loRaFishNextPoopAt);
    assert(fish.happiness==80 && loRaFishNextAutoFeed==110);
  }
  resetHappy();loRaFishNeedsAppearanceSetup=true;events(100);advance(3600000);
  assert(fish.happiness==80 && feeds==0 && fish.ageMinutes==60);
  pass("egg/memorial/appearance setup consume thresholds without meals or decay");

  resetHappy();localEpochBase=22*3600;events(100);
  assert(feeds==0 && fish.happiness==80);
  advance(9*3600000);assert(feeds==0 && fish.happiness==80);
  events(10);assert(feeds==1 && fish.happiness==83);
  pass("sleeping RF earns no Happy and does not create wake-up feeding backlog");

  resetHappy();events(10);advance(29*60000);saveLoRaFishSettings();saveLoRaFish();
  const auto saved=loRaFishHappiness;const auto happy=fish.happiness;
  const auto stateSize=files["/lorafish.dat"].size();
  assert(stateSize==sizeof(LoRaFishState));
  reboot();assert(loRaFishHappiness.same(saved) && fish.happiness==happy);
  advance(60000);assert(fish.happiness==happy-2);
  advance(30*60000);events(10);assert(feeds==2);
  pass("actual serializers restore partial decay/cooldown in real boot order");

  resetHappy();events(10);advance(5*60000);saveLoRaFish();
  files["/lorafish.cfg"].resize(24); // Legacy settings prefix, before HAP1 tail.
  reboot();assert(fish.rfEvents==10 && fish.happiness==83);
  assert(loRaFishHappiness.awakeMs==0 && loRaFishHappiness.mealCooldownMs==0);
  assert(loRaFishGeneration==7 && loRaFishPoopCount==1);
  pass("legacy settings preserve pet/generation/waste and safely initialize new timers");

  for(size_t tailLength=0;tailLength<12;++tailLength) {
    resetHappy();events(10);saveLoRaFish();
    files["/lorafish.cfg"].resize(24+tailLength);reboot();
    assert(fish.happiness==83 && loRaFishHappiness.awakeMs==0 && loRaFishHappiness.mealCooldownMs==0);
  }
  for(size_t corrupt : {size_t(24),size_t(28),size_t(32)}) {
    resetHappy();events(10);saveLoRaFish();
    for(size_t i=corrupt;i<corrupt+4;++i)files["/lorafish.cfg"][i]=255;
    reboot();assert(fish.happiness==83 && loRaFishHappiness.awakeMs==0 && loRaFishHappiness.mealCooldownMs==0);
  }
  pass("truncated/unknown/out-of-range timing tails cannot corrupt old pet data");

  resetHappy();events(10);advance(60000);
  resetLoRaFishPet();assert(loRaFishHappiness.awakeMs==0 && loRaFishHappiness.mealCooldownMs==0);
  reboot();assert(fish.ageMinutes==0 && fish.happiness==80 && loRaFishHappiness.mealCooldownMs==0);
  pass("explicit reset clears and persists both Happy timers");

  resetHappy(60,50,3);startLoRaFishCleaning();advance(1400);
  assert(fish.happiness==53 && loRaFishPoopCount==0);
  startLoRaFishCleaning();advance(1400);assert(fish.happiness==53);
  advance(1800000-2800);assert(fish.happiness==52);
  pass("cleaning stays +3, cannot repeat on an empty tank, and removes waste drain");

  resetHappy();startLoRaFishGuessGame();
  for(int i=0;i<5;++i){loRaFishGuessNumber=0;loRaFishGuessHigher=true;submitLoRaFishGuess();}
  assert(fish.happiness==85 && fish.rfEvents==0 && loRaFishGuessComplete);
  submitLoRaFishGuess();assert(!loRaFishGuessComplete);
  for(int i=0;i<5;++i){loRaFishGuessNumber=0;loRaFishGuessHigher=false;submitLoRaFishGuess();}
  assert(fish.happiness==85 && fish.rfEvents==0);
  pass("game reward/replay preserved; wrong guesses and games do not create RF");

  resetHappy(60,99,1);startLoRaFishCleaning();advance(1400);assert(fish.happiness==100);
  events(10);assert(fish.happiness==100 && feeds==1 && loRaFishHappiness.mealCooldownMs>0);
  pass("clean/meal rewards clamp at 100 and a full-Happy meal still consumes cooldown");

  resetHappy();clockMs=0xFFFFFF00ULL;
  fishLastMinute=fishLastSave=loRaFishHappyLastMs=(uint32_t)clockMs;
  loRaFishHappiness.awakeMs=1799000;loRaFishHappiness.mealCooldownMs=1000;
  loRaFishSleepHour=loRaFishWakeHour=0;
  advance(999);assert(fish.happiness==80 && loRaFishHappiness.mealCooldownMs==1);
  advance(1);assert(fish.happiness==79 && loRaFishHappiness.mealCooldownMs==0);
  pass("millis rollover preserves exact decay and cooldown intervals");

  // Start at 07:00 to cover all 14 awake hours, not the default noon fixture.
  resetHappy();localEpochBase=7*3600;advance(14*3600000);
  assert(fish.happiness==52);advance(10*3600000);assert(fish.happiness==52);
  pass("quiet clean default day: 80 -> 52, then unchanged through ten hours of sleep");

  resetHappy();localEpochBase=7*3600;
  for(int i=0;i<240;++i){advance(60000);events(1);}
  assert(fish.happiness==66 && feeds==4 && loRaFishPoopCount==3);
  pass("busy unattended four-hour production scenario agrees with proposed balance: 66");

  resetHappy();localEpochBase=7*3600;
  for(int second=1;second<=4*3600;++second) {
    advance(1000);
    if(second%60==0)events(1);
    if(second%3600==120 && loRaFishPoopCount) startLoRaFishCleaning();
  }
  assert(fish.happiness==85 && feeds==4);
  pass("hourly care four-hour production scenario agrees with proposed balance: 85");

  resetHappy();events(10);
  const int writes=settingsWrites;
  for(int i=0;i<100;++i) {advance(1);reactLoRaFish(1);saveLoRaFish();}
  assert(settingsWrites==writes);
  advance(5*60000);assert(settingsWrites>writes);
  pass("RF saves do not amplify settings writes; elapsed timers checkpoint every five minutes");

  // Timers are independent of rendering and DX ownership. No display is present
  // in this fixture; none of the extracted production care functions require it.
  for(int state=0;state<4;++state) {
    resetHappy();loragotchiDXHome.away=state==1;
    loragotchiDXHome.pending=state==2;loragotchiDXHome.committing=state==3;
    events(10);advance(30*60000);
    assert(fish.happiness==81 && feeds==1);
    assert(loragotchiDXHome.away==(state==1) && loragotchiDXHome.pending==(state==2) && loragotchiDXHome.committing==(state==3));
  }
  pass("display-free and home/pending/committing/away care leave DX state untouched");
}
''')
with tempfile.TemporaryDirectory(prefix='lorafish-happy-') as directory:
    cpp=Path(directory)/'happiness.cpp'
    cpp.write_text('\n'.join(parts))
    for platform in ('ESP32','NRF52_PLATFORM'):
        executable=Path(directory)/platform
        subprocess.run(['g++','-std=c++17','-I',str(ROOT),'-D'+platform,str(cpp),'-o',str(executable)],check=True)
        print('Happy production/save/load checks: '+platform,flush=True)
        subprocess.run([str(executable)],check=True)
