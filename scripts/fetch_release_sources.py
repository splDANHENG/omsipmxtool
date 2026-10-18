# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Download the pinned upstream sources; reject changed or partial downloads."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT/'build/release-sources'
    destination.mkdir(parents=True, exist_ok=True)
    manifest = ROOT/'scripts/release-sources.json'
    for item in json.loads(manifest.read_text(encoding='utf-8')):
        path = destination/item['file']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            partial = path.with_suffix(path.suffix+'.part')
            with urlopen(item['url'], timeout=120) as response, partial.open('wb') as stream:
                while chunk := response.read(1024*1024):
                    stream.write(chunk)
            if hashlib.sha256(partial.read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('Source checksum mismatch: '+item['file'])
            partial.replace(path)
        print('Verified '+path.name, flush=True)
    (destination/'sources.json').write_bytes(manifest.read_bytes())


if __name__ == '__main__':
    main()
