# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Package a built Windows folder plus verified sources and original notices."""
import hashlib
import argparse
import importlib.metadata
import json
import platform
import shutil
import subprocess
import tarfile
import tomllib
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    from PIL import features
    from PySide6.QtCore import QLibraryInfo
    import ssl
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', type=Path, default=ROOT/'dist/omsipmxtool')
    bundle = parser.parse_args().bundle.resolve()
    if not bundle.is_relative_to((ROOT/'dist').resolve()):
        raise ValueError('Bundle must be inside the project dist directory')
    if not (bundle/'omsipmxtool.exe').is_file():
        raise RuntimeError('Build the Windows application first')
    output = ROOT/'dist/release'
    output.mkdir(parents=True, exist_ok=True)
    entries = json.loads((ROOT/'scripts/release-sources.json').read_text(encoding='utf-8'))
    sources = ROOT/'build/release-sources'
    for entry in entries:
        if digest(sources/entry['file']) != entry['sha256']:
            raise ValueError('Incorrect source archive: '+entry['file'])
    # Read only regular legal/attribution files. Never extract archive paths or links.
    for entry in entries:
        with tarfile.open(sources/entry['file']) as archive:
            for member in archive:
                relative = PurePosixPath(member.name)
                name = relative.name.lower()
                legal = (name.startswith(('license', 'licence', 'copying', 'copyright', 'notice'))
                         or name == 'qt_attribution.json' or 'LICENSES' in relative.parts)
                if not member.isfile() or not legal:
                    continue
                if relative.is_absolute() or '..' in relative.parts or member.size > 2_000_000:
                    raise ValueError('Unsafe notice path or size: '+member.name)
                target = bundle/'LICENSES/upstream'/Path(*relative.parts)
                if not target.resolve().is_relative_to(bundle.resolve()):
                    raise ValueError('Notice outside bundle')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
    for name in ('README.md', 'README.en.md', 'BINARY-DISTRIBUTION.txt',
                 'LICENSE', 'THIRD-PARTY-NOTICES.txt', 'MODEL-RIGHTS.txt'):
        shutil.copy2(ROOT/name, bundle/name)
    shutil.copy2(ROOT/'scripts/release-sources.json', bundle/'sources.json')
    packages = ['Pillow', 'pypinyin', 'PySide6', 'shiboken6', 'PyInstaller',
                'pyinstaller-hooks-contrib', 'setuptools', 'packaging', 'altgraph',
                'pefile', 'pywin32-ctypes']
    info = {
        'version': VERSION,
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'python': platform.python_version(), 'platform': platform.platform(),
        'qt': QLibraryInfo.build(), 'openssl': ssl.OPENSSL_VERSION,
        'packages': {name: importlib.metadata.version(name) for name in packages},
        'pillow_features': features.get_supported(),
        'pillow_libimagequant': features.check_feature('libimagequant'),
        'signed': False,
    }
    (bundle/'BUILD-INFO.json').write_text(json.dumps(info, indent=2)+'\n', encoding='utf-8')
    manifest = bundle/'BINARY-MANIFEST.sha256'
    files = sorted(p for p in bundle.rglob('*') if p.is_file() and p != manifest)
    forbidden = {'.pmx', '.pmd', '.hum', '.o3d', '.log', '.bak'}
    if any(p.is_symlink() or p.suffix.lower() in forbidden for p in files):
        raise ValueError('Unexpected user data or symlink in release')
    manifest.write_text(''.join(digest(p)+'  '+p.relative_to(bundle).as_posix()+'\n'
                                for p in files), encoding='utf-8')
    windows = output/f'omsipmxtool-{VERSION}-windows-x64.zip'
    with ZipFile(windows, 'w', ZIP_DEFLATED) as archive:
        for path in files+[manifest]:
            archive.write(path, 'omsipmxtool/'+path.relative_to(bundle).as_posix())
    dependencies = output/f'omsipmxtool-{VERSION}-dependency-sources.zip'
    with ZipFile(dependencies, 'w', ZIP_STORED) as archive:
        archive.write(ROOT/'scripts/release-sources.json', 'sources.json')
        archive.write(ROOT/'BINARY-DISTRIBUTION.txt', 'BINARY-DISTRIBUTION.txt')
        for entry in entries:
            archive.write(sources/entry['file'], entry['file'])
    subprocess.run([__import__('sys').executable, str(ROOT/'scripts/package_source.py')],
                   cwd=ROOT, check=True)
    source = output/f'omsipmxtool-{VERSION}-source.zip'
    shutil.copy2(ROOT/'dist/omsipmxtool-source-review.zip', source)
    for path in (windows, dependencies, source):
        with ZipFile(path) as archive:
            if archive.testzip():
                raise RuntimeError('Invalid release ZIP: '+path.name)
        print(path.name, path.stat().st_size, flush=True)
    (output/'SHA256SUMS.txt').write_text(''.join(digest(p)+'  '+p.name+'\n'
        for p in (windows, dependencies, source)), encoding='utf-8')


if __name__ == '__main__':
    main()
