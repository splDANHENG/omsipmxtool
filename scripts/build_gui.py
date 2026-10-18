"""Build locally on each OS/architecture; no user data goes into the bundle."""
import subprocess
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
        '--windowed', '--name', 'OMSI Mod Studio', '--paths', str(root),
        '--distpath', str(root/'dist'), '--workpath', str(root/'build'),
        '--specpath', str(root/'build')]
if sys.platform == 'darwin':
    args += ['--osx-bundle-identifier', 'org.omsimod.studio',
             '--icon', str(root/'assets'/'studio.icns')]
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
