# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Build locally on each OS/architecture; no user data goes into the bundle."""
import subprocess
import shutil
import os
import sys
import argparse
from pathlib import Path

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('--dist-dir', type=Path, default=root/'dist')
dist = parser.parse_args().dist_dir.resolve()
if not dist.is_relative_to((root/'dist').resolve()):
    raise ValueError('Build output must stay inside the project dist directory')
if (root/'MODEL-RIGHTS.txt').read_bytes() != (root/'omsimod'/'MODEL-RIGHTS.txt').read_bytes():
    raise RuntimeError('请同步根目录和 omsimod 内的 MODEL-RIGHTS.txt 后再打包')
args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
        '--windowed', '--name', 'omsipmxtool', '--paths', str(root),
        '--distpath', str(dist), '--workpath', str(root/'build'),
        '--specpath', str(root/'build'), '--collect-data', 'pypinyin',
        '--add-data', str(root/'omsimod'/'MODEL-RIGHTS.txt')+os.pathsep+'omsimod',
        '--add-data', str(root/'LICENSES'/'pypinyin-0.55.0.txt')+os.pathsep+'LICENSES']
if sys.platform == 'darwin':
    args += ['--osx-bundle-identifier', 'org.omsipmxtool.app',
             '--icon', str(root/'assets'/'studio.icns')]
if sys.platform == 'win32':
    args += ['--additional-hooks-dir', str(root/'scripts'/'pyinstaller_hooks')]
args += [str(root/'scripts'/'gui_entry.py')]
env = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(root/'build'/'pyinstaller-cache'))
if sys.platform == 'win32':
    # Do not collect unrelated DLLs from tools injected into the host PATH.
    # In particular, Qt uses Windows ICU, not Poppler's same-named icuuc.dll.
    windows = Path(os.environ.get('SystemRoot', r'C:\Windows'))
    env['PATH'] = os.pathsep.join(map(str, [
        Path(sys.executable).parent, Path(sys.base_prefix),
        windows/'System32', windows,
    ]))
subprocess.run(args, cwd=root, env=env, check=True)
if sys.platform == 'win32':
    # Widgets uses the Windows raster backend; no software OpenGL renderer is needed.
    software_gl = dist/'omsipmxtool'/'_internal'/'PySide6'/'opengl32sw.dll'
    software_gl.unlink(missing_ok=True)
notice_dir = (dist/'omsipmxtool.app'/'Contents'/'Resources'
              if sys.platform == 'darwin' else dist/'omsipmxtool')
shutil.copy2(root/'MODEL-RIGHTS.txt', notice_dir/'MODEL-RIGHTS.txt')
for name in ('LICENSE', 'THIRD-PARTY-NOTICES.txt', 'README.md', 'README.en.md',
             'BINARY-DISTRIBUTION.txt'):
    shutil.copy2(root/name, notice_dir/name)
shutil.copytree(root/'LICENSES', notice_dir/'LICENSES', dirs_exist_ok=True)
