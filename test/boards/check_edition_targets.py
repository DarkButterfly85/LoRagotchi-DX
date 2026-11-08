#!/usr/bin/env python3
"""Check resolved edition aliases; no radio/display/hardware acceptance claim."""
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
import re,tempfile
picker={s:dict(v) for s,v in json.loads(subprocess.check_output(
    ['pio','project','config','--json-output'],cwd=ROOT,text=True))}
# Some Water/Air parents (LoRaFish companion builds) are hidden from the picker and
# live in platformio-meshcore.ini. Resolve the picker config plus that file in a
# scratch project so the aliases are still compared with their real parents.
with tempfile.TemporaryDirectory() as tmp:
    tmp=Path(tmp)
    (tmp/'variants').symlink_to(ROOT/'variants')
    (tmp/'platformio-meshcore.ini').symlink_to(ROOT/'platformio-meshcore.ini')
    ini=(ROOT/'platformio.ini').read_text()
    ini,n=re.subn(r'(extra_configs\s*=\s*\n)',r'\1  platformio-meshcore.ini\n',ini,count=1)
    assert n==1
    (tmp/'platformio.ini').write_text(ini)
    config={s:dict(v) for s,v in json.loads(subprocess.check_output(
        ['pio','project','config','-d',str(tmp),'--json-output'],text=True))}
assert set(picker)<=set(config)
water={
    'water_heltec_t190_ble':'Heltec_T190_LoRaGotchi_DX_ble',
    'water_wio_tracker_l1_ble':'WioTrackerL1_LoRaGotchi_DX_ble',
    'water_wio_tracker_l1_1w_ble':'WioTrackerL1-1W_LoRaGotchi_DX_ble',
    'water_thinknode_m2_ble':'ThinkNode_M2_LoRaFish_companion_ble',
    'water_lilygo_tbeam_1w_ble':'LilyGo_TBeam_1W_LoRaGotchi_DX_ble',
    'water_station_g2_ble':'Station_G2_LoRaGotchi_DX_ble',
    'water_station_g3_esp32_ble':'Station_G3_ESP32_LoRaGotchi_DX_ble',
    'water_heltec_v3_ble':'Heltec_v3_LoRaFish_companion_ble',
    'water_heltec_v4_oled_ble':'heltec_v4_LoRaFish_companion_ble',
    'water_m5stack_cardputer':'cardputer_loragotchi',
    'water_heltec_t114_ble':'Heltec_t114_LoRaFish_companion_ble',
    'water_heltec_t096_ble':'Heltec_t096_LoRaFish_companion_ble',
    'water_lilygo_tdeck_ble':'LilyGo_TDeck_loragotchi_dx_ble',
    'water_lilygo_tdeck_usb':'LilyGo_TDeck_loragotchi_dx_usb',
    'water_rak4631_ble':'RAK_4631_LoRaGotchi_DX_ble',
    'water_rak4630_ble':'RAK_4631_LoRaGotchi_DX_ble',
}
for alias,parent in water.items():
 assert 'env:'+alias in picker,alias
 a=config['env:'+alias];p=config['env:'+parent]
 for key,value in p.items():
  if key not in {'extends','build_flags'}: assert a[key]==value,(alias,key)
 assert a['build_flags']==p['build_flags']+['-D LORAGOTCHI_WATER_EDITION=1'],alias
 assert 'LORAGOTCHI_WATER_EDITION' not in ' '.join(p['build_flags']),parent
 assert '-D LORAFISH_UI=1' in a['build_flags'],alias
assert {s[4:] for s in config if s.startswith('env:water_')}==set(water)
a=config['env:RAK_4630_LoRaGotchi_DX_ble'];p=config['env:RAK_4631_LoRaGotchi_DX_ble']
assert {k:v for k,v in a.items() if k!='extends'}=={k:v for k,v in p.items() if k!='extends'}
assert a['board']=='rak4631'
assert a['board_build.ldscript']=='boards/nrf52840_s140_v6_extrafs.ld'
assert int(a['board_upload.maximum_size'])==712704
flags=' '.join(a['build_flags'])
for expected in ['DISPLAY_CLASS=SSD1306Display','PIN_BOARD_SDA=13','PIN_BOARD_SCL=14',
                 'PIN_USER_BTN=9','PIN_USER_BTN_ANA=31','USE_SX1262','LORAGOTCHI_EXPERIMENTAL=1']:
 assert expected in flags,expected
print('PASS 16 explicit Water aliases and RAK4630 DX alias; existing DX, pins, radio, memory and dependencies preserved')

air={name.replace('water_','air_'):parent for name,parent in water.items()}
for alias,parent in air.items():
 assert 'env:'+alias in picker,alias
 a=config['env:'+alias];p=config['env:'+parent]
 for key,value in p.items():
  if key not in {'extends','build_flags'}:assert a[key]==value,(alias,key)
 assert a['build_flags']==p['build_flags']+['-D LORAGOTCHI_AIR_EDITION=1'],alias
assert {s[4:] for s in config if s.startswith('env:air_')}==set(air)
print('PASS 16 Air aliases; original DX/Water hardware, radio, memory and dependencies unchanged')
