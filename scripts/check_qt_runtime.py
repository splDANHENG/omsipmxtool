# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Check the installed Qt wheel before running the GUI test suite."""
import sys

import PySide6
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication


def main():
    print(f'Python {sys.version.split()[0]}, PySide6 {PySide6.__version__}', flush=True)
    color = QColor('#101923')
    # A wrapped void call must return an owned reference to None. Warm up the
    # binding first, then detect wheels that consume it on older CPython.
    for _ in range(100):
        color.setAlpha(255)
    before = sys.getrefcount(None)
    for _ in range(100):
        color.setAlpha(255)
    after = sys.getrefcount(None)
    print(f'None references before={before}, after={after}, delta={after-before}', flush=True)
    if after < before:
        raise RuntimeError('Qt void calls consumed None references; this Qt wheel is unsafe')

    import omsimod.gui
    app = QApplication([])
    print('Qt runtime ready', flush=True)


if __name__ == '__main__':
    main()
