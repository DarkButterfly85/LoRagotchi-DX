#!/usr/bin/env python3
"""Exact production mono/colour Air pixels, lifecycle stages and travel callers."""
import argparse
from pathlib import Path
from check_juvenile_rendering import run, ROOT
p=argparse.ArgumentParser();p.add_argument('--preview-dir',type=Path);a=p.parse_args()
s=(ROOT/'examples/companion_radio/ui-new/UITask.cpp').read_text()
for variant in ('plain','LORAFISH_TDECK_PIXEL_ART','LORAFISH_CARDPUTER_25D'):
    print('PASS Air production renderer',variant,
          run(s,variant,a.preview_dir/variant if a.preview_dir else None,False,air=True))
