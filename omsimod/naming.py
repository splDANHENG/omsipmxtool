# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""ASCII identifiers derived from filenames, without changing the source model."""
import re
from pypinyin import lazy_pinyin
from .export import character_name


def pinyin_name(value):
    text = ''.join(lazy_pinyin(value))
    text = re.sub(r'[^A-Za-z0-9_-]+', '_', text).strip('_')
    return character_name(text)
