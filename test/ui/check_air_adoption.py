#!/usr/bin/env python3
"""Air retains fish-only LEG1 and production interrupted-adoption journal recovery."""
import os,subprocess
from pathlib import Path
subprocess.run(['python3',str(Path(__file__).with_name('check_egg_adoption.py'))],
               env=dict(os.environ,LORAGOTCHI_TEST_AIR='1'),check=True)
