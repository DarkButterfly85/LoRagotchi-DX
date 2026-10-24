#!/usr/bin/env python3
"""Exercise real name rendering, DX picker/send/recall and boot-notice handlers.

Mock only the contact store, radio and display boundary; start at the aquarium.
The glyph bounds check targets the smallest 128x64 display, with/without buzzer.
"""
from pathlib import Path
import runpy
import subprocess
import tempfile

fixture=runpy.run_path(str(Path(__file__).with_name('check_menu_navigation.py')))
root=fixture['root']
parts=fixture['parts'][:-1]
parts.append(fixture['parts'][-1].split('int main(){',1)[0])
parts.append(r'''
static ContactInfo contact(const char* name,uint8_t type,uint32_t key) {
  ContactInfo c={};snprintf(c.name,sizeof(c.name),"%s",name);c.type=type;
  c.index=key;c.id.pub_key[0]=key+1;return c;
}
static void pass(const char* name){printf("PASS: %s\n",name);fflush(stdout);}
int main(){
  UITask task;tick=100000;task.ui_started_at=0;
  loRaFishPage=0;
  the_mesh.useCustom=true;
  the_mesh.custom={contact("RPT 🐟",2,0),contact("Plain",1,1),
    contact("Alpha 🐟",1,2),contact("Beta 🐠️",1,3),contact("Room 🐡",3,4),
    contact("Gamma 🐡",1,5),contact("Delta 🦈",1,6),contact("Other 🙂",1,7),contact("",1,8)};
  assert(loRaFishDXContactCount()==4);
  for(int i=0;i<4;++i)shortPress(KEY_NEXT);
  assert(loRaFishPage==4 && the_mesh.dxSends==0);
  task.handleLongPress(KEY_ENTER);assert(loRaFishPage==LORAFISH_DX_CONTACT_PAGE);
  task.display.clearBounds();drawLoRaFishDX(task.display);assert(loRaFishDXContactIndex==2);
  assert(std::find(task.display.printed.begin(),task.display.printed.end(),"1/4 fish tanks")!=task.display.printed.end());
  for(uint32_t index:{3,5,6,2}){shortPress(KEY_NEXT);assert(loRaFishDXContactIndex==index);}
  shortPress(KEY_PREV);assert(loRaFishDXContactIndex==6);shortPress(KEY_NEXT);assert(loRaFishDXContactIndex==2);
  pass("aquarium route reaches only fish-marked companions, across all four emoji and both directions");

  shortPress(KEY_NEXT);shortPress(KEY_NEXT);assert(loRaFishDXContactIndex==5);
  loRaFishMeshNodeName="Local 🐠";
  assert(!strcmp(loRaFishDisplayName(),"Local ><>") && !strcmp(loRaFishProtocolName(),"Local"));
  task.handleLongPress(KEY_ENTER);
  assert(the_mesh.dxSends==1 && the_mesh.lastDestination==5);
  assert(loragotchiDXHome.destinationIndex==5 && loRaFishDXDestinationKnown);
  assert(!strcmp(loragotchiDXHome.destinationName,"Gamma 🐡"));
  assert(the_mesh.lastMessage.find("|Local")!=std::string::npos);
  pass("filtered row maps to the original contact; display fallback never leaks into protocol names");

  // Host removes its marker and moves to a different table slot during the trip.
  auto dest=the_mesh.custom[5];snprintf(dest.name,sizeof(dest.name),"%s","Renamed host");
  the_mesh.custom={contact("Not the host 🐟",1,22),dest};
  loragotchiDXHome.pending=false;loragotchiDXHome.away=true;
  task._alert_expiry=0;task.handleLongPress(KEY_ENTER);
  assert(the_mesh.dxSends==2 && the_mesh.lastDestination==5);
  assert(the_mesh.lastMessage.find("LFG1|RECALL|")==0);
  pass("recall uses peer identity after rename/reorder, independent of new-visit eligibility");

  the_mesh.custom={dest};assert(loRaFishDXContactCount()==0);
  task._alert_expiry=0;task.handleLongPress(KEY_ENTER);
  assert(the_mesh.dxSends==3 && the_mesh.lastDestination==5);
  the_mesh.custom.clear();task._alert_expiry=0;task.handleLongPress(KEY_ENTER);
  assert(the_mesh.dxSends==3 && task.alert=="Tank not in contacts");
  pass("zero eligible peers cannot block a valid recall; missing host never falls back to another contact");

  the_mesh.custom={contact("Unrelated 🐟",1,19),dest};
  loragotchiDXHome.away=false;loragotchiDXHome.committing=true;
  ContactInfo resolved;assert(loRaFishDXDestination(resolved) && resolved.index==5);
  the_mesh.custom={contact("Unrelated 🐟",1,19)};
  assert(!loRaFishDXDestination(resolved) && the_mesh.dxSends==3);
  pass("active destination resolver keeps full identity after reorder; retry service is covered by check_busy_mesh");

  loragotchiDXHome.away=loragotchiDXHome.pending=loragotchiDXHome.committing=false;
  loRaFishDXDestinationKnown=false;the_mesh.custom={contact("No marker",1,0),contact("Fish RPT 🐟",2,1)};
  loRaFishDXContactIndex=999;
  ContactInfo c;assert(!loRaFishDXGetContact(c));shortPress(KEY_NEXT);
  task._alert_expiry=0;task.handleLongPress(KEY_ENTER);
  assert(the_mesh.dxSends==3 && task.alert=="No fish tanks");
  task.display.clearBounds();drawLoRaFishDX(task.display);
  the_mesh.custom.push_back(contact("New fish 🐠",1,2));
  assert(loRaFishDXGetContact(c) && loRaFishDXContactIndex==2);
  the_mesh.custom.resize(2);assert(!loRaFishDXGetContact(c));
  task.handleDoubleClick(KEY_PREV);assert(loRaFishPage==4);
  shortPress(KEY_NEXT);assert(loRaFishPage==5);
  pass("empty/changing filtered lists stay navigable without sending or trapping Options");

  loRaFishMeshNodeName="No fish here";beginLoRaFishNameNotice();assert(loRaFishNameNotice);
  loRaFishPage=9;loRaFishNeedsAppearanceSetup=true;
  task.display.clearBounds();drawLoRaFishNameNotice(task.display);
  const int saved=settingsWrites+petWrites,sent=the_mesh.dxSends;
  shortPress(KEY_NEXT);
  assert(!loRaFishNameNotice && loRaFishPage==9 && loRaFishNeedsAppearanceSetup);
  assert(saved==settingsWrites+petWrites && sent==the_mesh.dxSends);
  for(int i=0;i<5;++i){task.display.clearBounds();drawLoRaFishNameNotice(task.display);}
  assert(!loRaFishNameNotice);
  beginLoRaFishNameNotice();assert(loRaFishNameNotice);
  pass("boot reminder is bounded, dismisses without action or save, and returns on the next unmarked boot");

  for(const char* name:{"🐟 Home","Home 🐠","Home 🐡️","🦈"}) {
    loRaFishMeshNodeName=name;beginLoRaFishNameNotice();assert(!loRaFishNameNotice);
  }
  loRaFishMeshNodeName=nullptr;beginLoRaFishNameNotice();assert(loRaFishNameNotice);
  loRaFishMeshNodeName="No marker";beginLoRaFishNameNotice();
  task.display.turnOff();char key=task.checkDisplayOn(KEY_NEXT);if(key)shortPress(key);
  assert(task.display.isOn() && loRaFishNameNotice);
  key=task.checkDisplayOn(KEY_NEXT);if(key)shortPress(key);
  assert(!loRaFishNameNotice && loRaFishPage==9);
  pass("all supported markers suppress reminder; sleeping display first click only wakes");

  for(int gesture=0;gesture<3;++gesture) {
    beginLoRaFishNameNotice();task._alert_expiry=0;
    if(gesture==0)task.handleLongPress(KEY_ENTER);
    else if(gesture==1)task.handleDoubleClick(KEY_PREV);
    else task.handleTripleClick(KEY_ENTER);
    assert(!loRaFishNameNotice && loRaFishPage==9 && task.buzzerToggles==0);
  }
  beginLoRaFishNameNotice();task.ui_started_at=tick;const int rescues=the_mesh.rescues;
  task.handleLongPress(KEY_ENTER);assert(the_mesh.rescues==rescues+1 && loRaFishNameNotice);
  pass("visible reminder consumes gestures while the first-eight-second CLI rescue remains intact");

  char longName[32];memset(longName,'X',sizeof(longName));
  for(const char* name:{"Tank🐟", "Fish 🐠️ 🙂", "Long name with emoji🐡",(const char*)longName}) {
    task.display.clearBounds();drawLoRaFishName(task.display,27,name,32);
  }
  task.showAlert("Alert 🙂🐟",1000);assert(task.alert=="Alert  ><>");
  assert(saved==settingsWrites+petWrites && sent==the_mesh.dxSends);
  pass("name and alert display boundaries emit only printable ASCII and fit the 128-pixel panel");
}
''')
assert 'beginLoRaFishNameNotice();' in fixture['block']('void UITask::begin(')
assert 'drawLoRaFishNameNotice(display);' in fixture['block']('static void drawLoRaFish(')
with tempfile.TemporaryDirectory(prefix='lorafish-emoji-') as directory:
    cpp=Path(directory)/'emoji.cpp';cpp.write_text('\n'.join(parts))
    for sound in (False,True):
        exe=Path(directory)/f'emoji-{int(sound)}'
        args=['g++','-std=c++17','-I',str(root),'-I',str(root/'src'),str(cpp),'-o',str(exe)]
        if sound:args+=['-DPIN_BUZZER=6']
        subprocess.run(args,check=True)
        print(f'Emoji/DX production checks: sound={int(sound)}',flush=True)
        subprocess.run([str(exe)],check=True)
