#!/usr/bin/env python3
"""Audit fully resolved profiles, not just strings in the new INI file."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
manifest = json.loads((ROOT / 'docs/experimental-screen-targets.json').read_text())
config = {s: dict(options) for s, options in json.loads(subprocess.check_output(
    ['pio', 'project', 'config', '--json-output'], cwd=ROOT, text=True))}
allowed = {'SSD1306Display', 'SH1106Display', 'SH1107Display', 'ST7735Display',
           'ST7789Display', 'ST7789LCDDisplay', 'NV3001BDisplay'}
seen = set()
for row in manifest['targets']:
    name = row['environment']
    assert name not in seen
    seen.add(name)
    candidate = config['env:' + name]
    parent = config['env:' + row['base_environment']]
    flags = candidate['build_flags']
    joined = ' '.join(flags)
    displays = re.findall(r'DISPLAY_CLASS=(\w+)', joined)
    assert displays and set(displays) == {row['display']} and row['display'] in allowed, name
    assert row['experimental'] and row['hardware_tested'] is False, name
    assert '-D LORAFISH_UI=1' in flags and '-D LORAGOTCHI_EXPERIMENTAL=1' in flags, name
    assert 'BLE_PIN_CODE=' in joined and 'ENABLE_USB_INTERFACE' not in joined, name
    assert 'PIN_USER_BTN=-1' not in joined, name
    assert '+<../examples/companion_radio/ui-new/*.cpp>' in candidate['build_src_filter'], name
    assert not any('ui-tiny' in x or 'ui-orig' in x for x in candidate['build_src_filter']), name
    # The original board, partitions, memory layout and all radio/pin flags stay inherited.
    for key, value in parent.items():
        if key not in {'extends', 'build_flags', 'build_src_filter', 'lib_deps'}:
            assert candidate[key] == value, (name, key)
    assert flags[:len(parent['build_flags'])] == parent['build_flags'], name
    assert flags[len(parent['build_flags']):] == ['-D LORAFISH_UI=1',
        '-D LORAGOTCHI_EXPERIMENTAL=1', '-D AUTO_OFF_MILLIS=30000'] + [
        '-UENV_INCLUDE_' + sensor for sensor in row.get('disabled_optional_sensors', [])], name
    assert 'GPS' not in row.get('disabled_optional_sensors', []), name
    assert row['target'] == ('create_uf2' if '-D NRF52_PLATFORM' in flags else 'build'), name
assert seen == {s[4:] for s in config if s.startswith('env:') and
                '-D LORAGOTCHI_EXPERIMENTAL=1' in config[s].get('build_flags', [])}
assert len(seen) == 42
print(f'PASS: {len(seen)} resolved TFT/OLED DX profiles; original hardware/RF/memory options preserved')
