# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Repair the missing cabin reference in a supported SXC6120GBEV9 variant.

Default is a read-only check; --apply backs up the original bytes before replacing.
"""
import argparse
import hashlib
import os
from pathlib import Path
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--variant', choices=('sxccd', 'ci-debug'), default='sxccd')
    args = parser.parse_args()
    folder = args.root.resolve()/'Vehicles'/'V_Serises'
    filenames = {
        'sxccd': 'SXC6120GBEV9_TZ405XSD17_2018_SXCCD_10101011.bus',
        'ci-debug': 'SXC6120GBEV9_CI_DEBUG.bus',
    }
    bus = folder/filenames[args.variant]
    old = b'model\\ZZ_Passengercabin_V1200\\00001100.cfg'
    new = b'model\\ZZ_Passengercabin_V1200\\10101011.cfg'
    cabin = folder/new.decode('ascii').replace('\\', '/')
    lines = cabin.read_bytes().splitlines()
    index = lines.index(b'[drivpos]')
    position = [float(value) for value in lines[index+1:index+6]]
    if len(position) != 5:
        raise ValueError('Incomplete driver position')
    data = bus.read_bytes()
    if old not in data and data.count(new) == 1:
        print('Already repaired:', bus)
        return
    if data.count(old) != 1:
        raise ValueError('Unexpected vehicle configuration; refusing to modify')
    before = data.splitlines()
    ref_index = before.index(old)
    if before[ref_index-1].strip() != b'[passengercabin]':
        raise ValueError('Reference is not in the passenger cabin section')
    if (folder/old.decode('ascii').replace('\\', '/')).exists():
        raise ValueError('Old cabin now exists; this repair no longer applies')
    updated = data.replace(old, new, 1)
    print('Vehicle:', bus)
    print('Cabin:', cabin)
    print('Driver position:', position)
    print('Original SHA256:', hashlib.sha256(data).hexdigest())
    if not args.apply:
        print('Read-only check passed; only the passenger cabin path will change.')
        return
    backup = bus.with_name(bus.name+'.omsimod-driver-fix.bak')
    if backup.exists():
        if backup.read_bytes() != data:
            raise ValueError('Existing backup differs; refusing to overwrite')
    else:
        with backup.open('xb') as stream:
            stream.write(data)
    if bus.read_bytes() != data:
        raise ValueError('Vehicle changed during repair; refusing to overwrite')
    with tempfile.NamedTemporaryFile(dir=folder, prefix='.omsimod-repair-', delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(updated)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        temporary.replace(bus)
    finally:
        temporary.unlink(missing_ok=True)
    if bus.read_bytes() != updated or backup.read_bytes() != data:
        raise RuntimeError('Repair verification failed')
    print('Repaired and verified. Original backup:', backup)


if __name__ == '__main__':
    main()
