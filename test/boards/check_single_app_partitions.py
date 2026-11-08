#!/usr/bin/env python3
"""Check exact single-app scope, chip identity, data offsets and size guards."""
import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAMES = {
    'LilyGo_TBeam_1W_LoRaGotchi_DX_ble': ('t_beam_1w', 'lilygo_tbeam_1w_ble'),
    'Station_G2_LoRaGotchi_DX_ble': ('station-g2', 'station_g2_ble'),
    'Station_G3_ESP32_LoRaGotchi_DX_ble': ('station-g3-esp32', 'station_g3_esp32_ble'),
}
CSV = 'variants/loragotchi_experimental/single_app.csv'
EXPECTED = [
    ('nvs', 'data', 'nvs', 0x9000, 0x5000),
    ('app0', 'app', 'factory', 0x10000, 0x280000),
    ('spiffs', 'data', 'spiffs', 0x290000, 0x160000),
    ('coredump', 'data', 'coredump', 0x3f0000, 0x10000),
]


def check_table(path):
    rows = []
    for raw in csv.reader(line for line in path.read_text().splitlines()
                          if line.strip() and not line.lstrip().startswith('#')):
        fields = [v.strip() for v in raw]
        assert len(fields) == 6 and not fields[5], fields
        rows.append((*fields[:3], int(fields[3], 0), int(fields[4], 0)))
    assert rows == EXPECTED, rows
    end = 0x9000
    for name, kind, subtype, offset, size in rows:
        assert offset >= end and offset % (0x10000 if kind == 'app' else 0x1000) == 0
        end = offset + size
        assert end <= 16 * 1024 * 1024
    assert end == 0x400000


def check_config(config):
    expected = set()
    for name, (board, suffix) in NAMES.items():
        cfg = config['env:' + name]
        actual_board = json.loads((ROOT / 'boards' / (board + '.json')).read_text())
        assert cfg['board'] == board
        assert actual_board['build']['mcu'] == 'esp32s3'
        assert actual_board['upload']['flash_size'] == '16MB'
        assert actual_board['upload']['maximum_size'] == 16777216
        expected.add('env:' + name)
        for edition in ('water', 'air', 'land'):
            alias = 'env:' + edition + '_' + suffix
            if edition == 'air' and not (ROOT / 'variants/loragotchi_air/platformio.ini').exists():
                continue
            a = config[alias]
            for key, value in cfg.items():
                if key not in {'extends', 'build_flags'}:
                    assert a[key] == value, (alias, key)
            assert a['build_flags'] == cfg['build_flags'] + [
                '-D LORAGOTCHI_' + edition.upper() + '_EDITION=1'], alias
            expected.add(alias)
    selected = {s for s, cfg in config.items() if cfg.get('board_build.partitions') == CSV}
    assert selected == expected, (selected, expected)
    for name in expected:
        cfg = config[name]
        assert cfg['board_build.partitions'] == CSV
        assert str(cfg['board_upload.maximum_size']) == str(0x280000), name
        assert cfg['board_upload.flash_size'] == '16MB', name
        assert '-D LORAFISH_UI=1' in cfg['build_flags'], name
        assert not {'-fno-inline-small-functions', '-fno-inline-functions-called-once'} & set(cfg['build_flags'])
    return expected


if __name__ == '__main__':
    check_table(ROOT / CSV)
    config = {s: dict(v) for s, v in json.loads(subprocess.check_output(
        ['pio', 'project', 'config', '--json-output'], cwd=ROOT, text=True))}
    selected = check_config(config)
    print(f'PASS {len(selected)} exact single-app profiles; factory app 0x10000/0x280000; preserved data offsets')
