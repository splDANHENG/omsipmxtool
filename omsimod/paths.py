# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Writable per-user state, independent of the executable or source directory."""
import os
import shutil
import sys
from pathlib import Path


def data_directory():
    override = os.environ.get('OMSIMOD_DATA_DIR')
    if override:
        return Path(override).expanduser()
    if sys.platform == 'darwin':
        return Path.home()/'Library'/'Application Support'/'OMSI Mod Studio'
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', str(Path.home()/'AppData'/'Local')))/'OMSI Mod Studio'
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local'/'share')))/'omsimod'


def migrate_legacy(source, destination):
    """Only migrate into an absent destination; never overwrite live backups."""
    source, destination = Path(source), Path(destination)
    if not source.is_dir() or destination.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    return True


def prepare_data_directory():
    target = data_directory()
    if not getattr(sys, 'frozen', False) and not os.environ.get('OMSIMOD_DATA_DIR'):
        migrate_legacy(Path(__file__).resolve().parent.parent/'userdata', target)
    return target
