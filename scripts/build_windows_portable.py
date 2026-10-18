# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Assemble official Windows binaries without executing them on the build host.

Inputs: build/python-3.12.10-embed-amd64.zip and build/windows-wheels/.
The portable archive still requires native Windows smoke testing.
"""
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent.parent
NAME = 'omsipmxtool-Windows-x64'


def main():
    runtime = ROOT/'build/python-3.12.10-embed-amd64.zip'
    wheels = []
    for pattern in ('pyside6_essentials-6.12.0-*-win_amd64.whl',
                    'shiboken6-6.12.0-*-win_amd64.whl',
                    'pillow-12.3.0-cp312-cp312-win_amd64.whl',
                    'pypinyin-0.55.0-py2.py3-none-any.whl'):
        matches = list((ROOT/'build/windows-wheels').glob(pattern))
        if len(matches) != 1:
            raise RuntimeError('Expected one wheel: '+pattern)
        wheels.extend(matches)
    dist = ROOT/'dist';dist.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dist, prefix='.windows-build-') as temp:
        package = Path(temp)/NAME;package.mkdir()
        shutil.copy2(ROOT/'MODEL-RIGHTS.txt', package/'MODEL-RIGHTS.txt')
        python = package/'runtime';python.mkdir()
        with ZipFile(runtime) as archive:archive.extractall(python)
        site = python/'Lib/site-packages';site.mkdir(parents=True)
        for wheel in wheels:
            with ZipFile(wheel) as archive:archive.extractall(site)
        (python/'python312._pth').write_text(
            'python312.zip\n.\nLib/site-packages\n..\nimport site\n', encoding='ascii')
        shutil.copytree(ROOT/'omsimod', package/'omsimod',
                        ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (package/'Start.bat').write_bytes(
            b'@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\n'
            b'"%~dp0runtime\\python.exe" -m omsimod.gui\r\n'
            b'if errorlevel 1 pause\r\n')
        (package/'Diagnose.bat').write_bytes(
            b'@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\n'
            b'"%~dp0runtime\\python.exe" -c "from PySide6.QtWidgets import QApplication; from omsimod.gui import Window; from PIL import Image; a=QApplication([]); w=Window(); print(\'GUI imports and construction OK\'); w.close()"\r\n'
            b'pause\r\n')
        (package/'README.txt').write_text(
            'omsipmxtool - Windows x64 portable build\n\n'
            'Extract the WHOLE ZIP before running Start.bat.\n'
            'Target: Windows 10/11 x64. Python installation is not required.\n'
            'Keep the console open while using the application. Errors remain visible.\n'
            'Use Diagnose.bat to check GUI imports and construction.\n'
            'This package was assembled on macOS; native Windows launch has NOT been verified.\n'
            'No characters or game files are included. Import your own PMX/HUM.\n'
            'Choose openomsi.exe and your OMSI content folder in the manager.\n'
            'Settings and backups: %LOCALAPPDATA%\\OMSI Mod Studio\n\n'
            'Runtime: Python 3.12.10 (python.org).\n'
            'Dependencies: PySide6 Essentials/Shiboken6 6.12.0 and Pillow 12.3.0 (PyPI).\n'
            'License notices are retained in runtime/LICENSE.txt and package dist-info directories.\n',encoding='utf-8')
        manifest = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [runtime,*wheels]}
        (package/'build-inputs.sha256.json').write_text(json.dumps(manifest,indent=2))
        target=dist/(NAME+'.zip')
        with ZipFile(target,'w',ZIP_DEFLATED) as archive:
            for path in sorted(package.rglob('*')):
                if path.is_file():archive.write(path,Path(NAME)/path.relative_to(package))
        with ZipFile(target) as archive:
            if archive.testzip():raise RuntimeError('Archive verification failed')
        print(target)
        print(f'{target.stat().st_size/1024/1024:.1f} MiB; native Windows test pending')


if __name__ == '__main__':main()
