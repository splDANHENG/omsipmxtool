# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Collect only the Windows Widgets plugins used by this application."""
from pathlib import Path
from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
allowed_modules = {'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'PySide6.QtNetwork'}
hiddenimports = [name for name in hiddenimports if name in allowed_modules]
allowed_binaries = {
    'Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Widgets.dll', 'Qt6Network.dll',
    'qwindows.dll', 'qoffscreen.dll', 'qminimal.dll', 'qmodernwindowsstyle.dll',
    'qgif.dll', 'qico.dll', 'qjpeg.dll',
}
binaries = [(source, destination) for source, destination in binaries
            if Path(source).name in allowed_binaries]
