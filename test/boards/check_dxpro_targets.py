#!/usr/bin/env python3
"""DX-Pro targets: 16 screen boards, each the matching water_* target with only LORAGOTCHI_DXPRO=1 added.
Resolved configuration only; no build, hardware or flash acceptance claim."""
import json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
cfg={s:dict(v) for s,v in json.loads(subprocess.check_output(['pio','project','config','--json-output'],cwd=ROOT,text=True))}
boards=['heltec_t096_ble','heltec_t114_ble','heltec_t190_ble','heltec_v3_ble','heltec_v4_oled_ble','lilygo_tbeam_1w_ble',
  'lilygo_tdeck_ble','lilygo_tdeck_usb','m5stack_cardputer','rak4630_ble','rak4631_ble','station_g2_ble',
  'station_g3_esp32_ble','thinknode_m2_ble','wio_tracker_l1_1w_ble','wio_tracker_l1_ble']
assert {s[10:] for s in cfg if s.startswith('env:dxpro_')}==set(boards)
for b in boards:
 a=cfg['env:dxpro_'+b];w=cfg['env:water_'+b]
 for k,v in w.items():
  if k not in {'extends','build_flags'}: assert a.get(k)==v,(b,k) # same board, platform, partitions, libraries, size limit
 assert a['build_flags']==[f for f in w['build_flags'] if 'LORAGOTCHI_WATER_EDITION' not in f]+['-D LORAGOTCHI_DXPRO=1'],b
 assert not any(x in ' '.join(a['build_flags']) for x in ('WATER_EDITION','AIR_EDITION','LAND_EDITION')),b
 assert '-D LORAFISH_UI=1' in a['build_flags'],b
# The flag is added to no other target and nothing was added to the hidden stock-MeshCore file.
assert {s for s,v in cfg.items() if any('LORAGOTCHI_DXPRO' in f for f in v.get('build_flags',[]))}=={'env:dxpro_'+b for b in boards}
assert 'DXPRO' not in (ROOT/'platformio-meshcore.ini').read_text()
print('PASS 16 dxpro_ targets = water_ targets + LORAGOTCHI_DXPRO=1 only')
