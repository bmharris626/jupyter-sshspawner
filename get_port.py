#!/usr/bin/env python3

import sys
from pathlib import Path


_SRC_PATH = Path(__file__).resolve().parent / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from sshspawner.get_port import main


if __name__ == "__main__":
    main()
