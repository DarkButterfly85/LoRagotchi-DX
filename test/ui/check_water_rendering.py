#!/usr/bin/env python3
"""Production pixels/stage/home/travel checks; optional --preview-dir writes PPM.
No panel/RF or board timing claims. Uses the legacy production extraction fixture.
"""
import argparse
from pathlib import Path
from check_juvenile_rendering import run, ROOT
p=argparse.ArgumentParser();p.add_argument('--preview-dir',type=Path);a=p.parse_args()
s=(ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text()
for variant in ('plain','LORAFISH_TDECK_PIXEL_ART','LORAFISH_CARDPUTER_25D'):
    r=run(s,variant,a.preview_dir/variant if a.preview_dir else None,False,True)
    print('PASS Water production renderer',variant,r)
