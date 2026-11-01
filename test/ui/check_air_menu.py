#!/usr/bin/env python3
"""Air shares actual menu handlers and both sound/mono/colour test branches."""
import os,subprocess
from pathlib import Path
subprocess.run(['python3',str(Path(__file__).with_name('check_menu_navigation.py'))],
               env=dict(os.environ,LORAGOTCHI_TEST_EDITION='0',LORAGOTCHI_TEST_AIR='1'),check=True)
