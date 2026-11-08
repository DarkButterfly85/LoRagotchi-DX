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
# The rejected size experiment must not leak into any profile or edition alias.
rejected_size_flags = {'-fno-inline-small-functions', '-fno-inline-functions-called-once'}
for section, options in config.items():
    assert rejected_size_flags.isdisjoint(options.get('build_flags', [])), section
single_app_profiles = {
    'LilyGo_TBeam_1W_LoRaGotchi_DX_ble',
    'Station_G2_LoRaGotchi_DX_ble',
    'Station_G3_ESP32_LoRaGotchi_DX_ble',
}
native_ui_profiles = {'heltec_v4_tft_LoRaGotchi_DX_ble', 'heltec_v4_r8_tft_LoRaGotchi_DX_ble'}
partition_override = {
    'board_build.partitions': 'variants/loragotchi_experimental/single_app.csv',
    'board_upload.flash_size': '16MB',
    'board_upload.maximum_size': '2621440',
}
seen = set()
for row in manifest['targets']:
    name = row['environment']
    assert name not in seen
    seen.add(name)
    candidate = config['env:' + name]
    parent = config['env:' + row['base_environment']]
    flags = candidate['build_flags']
    joined = ' '.join(flags)
    # T190 explicitly removes the inherited mono driver before defining RGB565.
    effective = joined
    if name == 'Heltec_T190_LoRaGotchi_DX_ble':
        assert candidate['build_unflags'] == ['-DST7789 -DDISPLAY_CLASS=ST7789Display']
        effective = effective.replace('-D DISPLAY_CLASS=ST7789Display', '')
    displays = re.findall(r'DISPLAY_CLASS=(\w+)', effective)
    assert displays and set(displays) == {row['display']} and row['display'] in allowed, name
    assert row['experimental'] and row['hardware_tested'] is False, name
    assert '-D LORAFISH_UI=1' in flags and '-D LORAGOTCHI_EXPERIMENTAL=1' in flags, name
    assert 'BLE_PIN_CODE=' in joined and 'ENABLE_USB_INTERFACE' not in joined, name
    assert 'PIN_USER_BTN=-1' not in joined, name
    assert '+<../examples/companion_radio/ui-new/*.cpp>' in candidate['build_src_filter'], name
    assert not any('ui-tiny' in x or 'ui-orig' in x for x in candidate['build_src_filter']), name
    # Hardware/RF stays inherited. Only these three LoRagotchi layouts may differ.
    if name in single_app_profiles:
        for key, value in partition_override.items():
            assert str(candidate[key]) == value, (name, key)
    for key, value in parent.items():
        if key not in {'extends', 'build_flags', 'build_src_filter', 'lib_deps'}:
            assert candidate[key] == value or (name in single_app_profiles and
                key in partition_override and str(candidate[key]) == partition_override[key]), (name, key)
    assert flags[:len(parent['build_flags'])] == parent['build_flags'], name
    additions = flags[len(parent['build_flags']):]
    if name == 'Heltec_T190_LoRaGotchi_DX_ble':
        assert additions == ['-D DISPLAY_CLASS=ST7789LCDDisplay',
            '-D LORAGOTCHI_T190_COLOR=1', '-D LORAGOTCHI_NATIVE_UI=1',
            '-D LORAFISH_TDECK_FRAMEBUFFER=1',
            '-D PIN_TFT_MISO=-1', '-D DISPLAY_WIDTH=170', '-D DISPLAY_HEIGHT=320',
            '-D DISPLAY_ROTATION=1', '-D DISPLAY_SCALE_X=2.5f', '-D DISPLAY_SCALE_Y=2.65625f',
            '-D LORAFISH_UI=1', '-D LORAGOTCHI_EXPERIMENTAL=1', '-D AUTO_OFF_MILLIS=30000']
        assert '-<helpers/ui/ST7789Display.cpp>' in candidate['build_src_filter']
        assert '+<helpers/ui/ST7789LCDDisplay.cpp>' in candidate['build_src_filter']
        continue
    # docs/native-display-layout.md: V4 and V4-R8 TFT profiles opt in to native layout.
    native = ['-D LORAGOTCHI_NATIVE_UI=1'] if name in native_ui_profiles else []
    assert additions == ['-D LORAFISH_UI=1'] + native + [
        '-D LORAGOTCHI_EXPERIMENTAL=1', '-D AUTO_OFF_MILLIS=30000'] + [
        '-UENV_INCLUDE_' + sensor for sensor in row.get('disabled_optional_sensors', [])], name
    assert 'GPS' not in row.get('disabled_optional_sensors', []), name
    assert row['target'] == ('create_uf2' if '-D NRF52_PLATFORM' in flags else 'build'), name
# Edition/module aliases are audited separately by check_edition_targets.py.
assert seen == {s[4:] for s in config if s.startswith('env:') and
                not s.startswith(('env:water_','env:air_')) and s != 'env:RAK_4630_LoRaGotchi_DX_ble' and
                '-D LORAGOTCHI_EXPERIMENTAL=1' in config[s].get('build_flags', [])}
assert len(seen) == 42
print(f'PASS: {len(seen)} resolved TFT/OLED DX profiles; original hardware/RF preserved; three audited single-app layouts')
