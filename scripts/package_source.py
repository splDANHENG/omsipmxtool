# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Create a source-only review archive from an explicit release allowlist."""
import hashlib
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = [ROOT/name for name in (
        '.gitignore', '.gitattributes', 'pyproject.toml', 'README.md', 'README.en.md',
        'LICENSE', 'THIRD-PARTY-NOTICES.txt', 'MODEL-RIGHTS.txt',
        'BINARY-DISTRIBUTION.txt', 'requirements-release.txt', 'scripts/release-sources.json',
        'RELEASE-REVIEW.txt', 'TWO-COMPUTERS.md', 'WINDOWS-HANDOFF.txt',
        'Start-GUI.bat', '启动界面.command', 'assets/studio.png', 'assets/studio.icns')]
    for folder, pattern in (('omsimod', '*.py'), ('tests', '*.py'),
                            ('scripts', '*.py'), ('LICENSES', '*.txt'),
                            ('scripts/pyinstaller_hooks', '*.py'),
                            ('.github/workflows', '*.yml')):
        files.extend((ROOT/folder).glob(pattern))
    files.append(ROOT/'omsimod/MODEL-RIGHTS.txt')
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT) or not path.is_file():
            raise ValueError('Invalid release input: '+str(path))
    if (ROOT/'MODEL-RIGHTS.txt').read_bytes() != (ROOT/'omsimod/MODEL-RIGHTS.txt').read_bytes():
        raise ValueError('Project notice copies differ')
    manifest = []
    destination = ROOT/'dist/omsipmxtool-source-review.zip'
    destination.parent.mkdir(exist_ok=True)
    with ZipFile(destination, 'w', ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            relative = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            manifest.append(hashlib.sha256(data).hexdigest()+'  '+relative)
            archive.writestr('omsipmxtool/'+relative, data)
        archive.writestr('omsipmxtool/SOURCE-MANIFEST.sha256', '\n'.join(manifest)+'\n')
    with ZipFile(destination) as archive:
        if archive.testzip():
            raise RuntimeError('Archive verification failed')
    (ROOT/'build').mkdir(exist_ok=True)
    (ROOT/'build/source-release-files.txt').write_text('\n'.join(manifest)+'\n',encoding='utf-8')
    print(f'{destination.name}: {len(manifest)} source files; verified')
    print('SHA256: '+hashlib.sha256(destination.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
