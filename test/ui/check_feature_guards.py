#!/usr/bin/env python3
"""Preprocess the real shared UI in generic/DX configurations without board SDKs.

This checks conditional isolation, not firmware compilation or physical hardware.
Headers are omitted so the host C++ preprocessor can inspect production guards;
the adoption include gets a marker to ensure it is excluded on generic targets.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "examples/companion_radio/ui-new/UITask.cpp"


def preprocess(definitions):
    source = SOURCE.read_text()
    source = source.replace('#include "LoRaFishAdoption.h"', 'LORAFISH_ADOPTION_IMPLEMENTATION')
    source = chr(10).join(line for line in source.splitlines() if not line.lstrip().startswith('#include'))
    source = '#include \"'+str(ROOT/'examples/companion_radio/LoRaGotchiVersion.h')+'\"\n'+source
    command = ['g++', '-E', '-P', '-x', 'c++', '-']
    command += ['-D' + value for value in definitions]
    return subprocess.check_output(command, input=source, text=True)


for edition in (0, 1, 2):
    for platform in ('ESP32', 'NRF52_PLATFORM'):
        for sound in (False, True):
            definitions = [platform, 'LORAGOTCHI_WATER_EDITION=' + str(int(edition==1)), 'LORAGOTCHI_AIR_EDITION=' + str(int(edition==2)), 'UI_DISCOVER_SCREEN=1', 'ENV_INCLUDE_GPS=1', 'UI_SENSORS_PAGE=1']
            if sound:
                definitions.append('PIN_BUZZER=1')
            generic = preprocess(definitions)
            dx = preprocess(definitions + ['LORAFISH_UI=1'])
            for required in ('class SplashScreen', 'class HomeScreen', 'class MsgPreviewScreen',
                             'void UITask::begin(', 'void UITask::loop()', 'drawUIAlertBox('):
                assert required in generic and required in dx, required
            for pet_only in ('loragotchiDX', 'static LoRaFishState fish',
                             'LORAFISH_ADOPTION_IMPLEMENTATION', 'static void drawLoRaFish('):
                assert pet_only not in generic, (platform, sound, pet_only)
                assert pet_only in dx, (platform, sound, pet_only)
            print(f'PASS edition={edition} {platform} sound={sound}: generic companion excludes pet state/API; DX retains it')
