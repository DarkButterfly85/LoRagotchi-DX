#!/usr/bin/env python3
"""Real menu entry/skip/wake handlers and egg prompt geometry, mocked hardware."""
from pathlib import Path
import runpy,subprocess,tempfile
f=runpy.run_path(str(Path(__file__).with_name('check_menu_navigation.py')))
source='\n'.join(f['parts'][:-1])+f['parts'][-1].split('int main(){',1)[0]
source=source.replace('static bool selectLoRaFishEggTank(bool){return false;}',
 'static unsigned selections=0;static bool selectLoRaFishEggTank(bool){++selections;return true;}')
source=source.replace('static void resetLoRaFishPet(){++resets;}',
 'static void resetLoRaFishPet(){++resets;loRaFishAdoptionEligible=true;}')
source=source.replace('static void closeLoRaFishAdoption(){loRaFishAdoptionEligible=false;',
 'static void closeLoRaFishAdoption(){if(loRaFishEggApplying)return;loRaFishAdoptionEligible=false;')
source+='\nstatic char loRaFishEggTankName[24]="A long nursery name";\n'+f['block']('static void drawLoRaFishAdoption(')+r'''
int main(){
 UITask task;tick=100000;task.ui_started_at=0;loRaFishPage=0;
 for(unsigned i=0;i<5;++i)shortPress(KEY_NEXT);assert(loRaFishPage==5);
 while(loRaFishOption!=LoRaFishOption::Reset)shortPress(KEY_NEXT);
 task.handleLongPress(KEY_ENTER);assert(loRaFishPage==LORAFISH_RESET_CONFIRM_PAGE && !loRaFishAdoptionEligible);
 shortPress(KEY_NEXT);task.handleLongPress(KEY_ENTER);assert(resets==1 && loRaFishAdoptionEligible);
 task._alert_expiry=0;
 for(auto phase:{LoRaFishEgg::Closed,LoRaFishEgg::Probe,LoRaFishEgg::Choose,LoRaFishEgg::Offered}){
   loRaFishEggSession.phase=phase;task.display.clearBounds();drawLoRaFishAdoption(task.display);
 }
 loRaFishEggSession.phase=LoRaFishEgg::Choose;unsigned previous=selections;
 task.display.turnOff();task.handleLongPress(KEY_ENTER);assert(loRaFishAdoptionEligible);
 shortPress(KEY_NEXT);assert(selections==previous+1 && loRaFishAdoptionEligible);
 task.handleLongPress(KEY_ENTER);assert(!loRaFishAdoptionEligible && resets==1);
 loRaFishAdoptionEligible=true;task.handleDoubleClick(KEY_PREV);assert(!loRaFishAdoptionEligible);
 loRaFishAdoptionEligible=true;loRaFishEggApplying=true;task.handleLongPress(KEY_ENTER);assert(loRaFishAdoptionEligible);
 previous=selections;shortPress(KEY_NEXT);assert(selections==previous);
 puts("PASS aquarium -> options -> confirmed reset -> adoption; click selection, wake-only, skip/back, saving guard and 128x64 layout");
}
'''
with tempfile.TemporaryDirectory(prefix='dx-egg-menu-') as d:
    cpp=Path(d)/'menu.cpp';cpp.write_text(source)
    for sound in (False,True):
        exe=Path(d)/('sound' if sound else 'silent')
        subprocess.run(['g++','-std=c++17','-I',str(f['root']),'-I',str(f['root']/'test/mocks'),'-I',str(f['root']/'src')]+(['-DPIN_BUZZER=1'] if sound else [])+[str(cpp),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
