#!/usr/bin/env python3
"""Resolved T190 habitat/hardware parity and actual hosted selector execution."""
import json, os, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
config = {s: dict(v) for s,v in json.loads(subprocess.check_output(
    ['pio','project','config','--json-output'], cwd=ROOT, text=True))}
parent = config['env:Heltec_T190_LoRaGotchi_DX_ble']
assert parent['board'] == 'heltec_t190'
assert parent['platform'] == 'platformio/espressif32@6.11.0'
flags = ' '.join(parent['build_flags'])
for flag in ['DISPLAY_CLASS=ST7789LCDDisplay','LORAGOTCHI_T190_COLOR=1',
             'LORAFISH_TDECK_FRAMEBUFFER=1','PIN_TFT_MISO=-1','PIN_TFT_SCL=38',
             'PIN_TFT_SDA=48','DISPLAY_ROTATION=1','LORAFISH_UI=1','BLE_PIN_CODE=123456']:
    assert flag in flags, flag
unflags = ' '.join(parent['build_unflags'])
assert '-DST7789' in unflags
assert '-DDISPLAY_CLASS=ST7789Display' in unflags
for edition in ['water','air']:
    target = config['env:'+edition+'_heltec_t190_ble']
    assert target['build_flags'] == parent['build_flags'] + ['-D LORAGOTCHI_'+edition.upper()+'_EDITION=1']
    assert {k:v for k,v in target.items() if k not in {'extends','build_flags'}} == {
        k:v for k,v in parent.items() if k not in {'extends','build_flags'}}
# Compare every pre-existing environment to the captured baseline when supplied.
if os.environ.get('T190_BASELINE_CONFIG'):
    baseline = {s:dict(v) for s,v in json.loads(Path(os.environ['T190_BASELINE_CONFIG']).read_text())}
    for section,values in baseline.items():
        assert config[section] == values, section
workflow = (ROOT/'.github/workflows/air-owner-builds.yml').read_text()
assert 'L1_1W, T190]' in workflow
script = workflow.split("python3 - <<'PYSELECT'",1)[1].split('          PYSELECT',1)[0]
script = chr(10).join(line[10:] for line in script.splitlines())
with tempfile.TemporaryDirectory() as tmp:
    for edition in ['DX','Water','Air','all']:
        output = Path(tmp)/edition
        subprocess.run(['python3','-c',script],check=True,env=dict(os.environ,
            EDITION=edition,BOARD='T190',GITHUB_OUTPUT=str(output)),stdout=subprocess.DEVNULL)
        rows = json.loads(output.read_text().split('matrix=',1)[1])['include']
        assert len(rows) == (3 if edition=='all' else 1)
        for row in rows:
            assert row['environment'] in {'Heltec_T190_LoRaGotchi_DX_ble','water_heltec_t190_ble','air_heltec_t190_ble'}
            assert row['target']=='build' and row['format']=='bin' and row['board']=='T190'
            if edition!='all': assert row['edition']==edition
print('PASS T190 hardware/dependency/partition/PIN inheritance, unchanged baseline, and hosted selector DX/Water/Air/all')
