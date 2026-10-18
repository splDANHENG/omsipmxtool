# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Check standalone O3D material texture references before installing a package."""
import struct
from pathlib import Path, PureWindowsPath


def mesh_textures(path):
    data=path.read_bytes(); offset=0
    def take(size):
        nonlocal offset
        if size < 0 or offset+size > len(data):
            raise ValueError('O3D 文件不完整：'+str(path))
        value=data[offset:offset+size];offset+=size
        return value
    def number(fmt):
        return struct.unpack('<'+fmt,take(struct.calcsize('<'+fmt)))[0]
    if take(2)!=b'\x84\x19':
        raise ValueError('人物网格不是支持的 O3D 文件：'+str(path))
    version=number('B')
    if version not in (1,2,3,4,5,6,7):
        raise ValueError('不支持的 O3D 版本：'+str(version))
    flags=number('B') if version>=3 else 0
    if version>=4:take(4)
    count_format='I' if version>=3 else 'H'
    index_bytes=4 if flags&1 else 2
    while offset<len(data):
        tag=number('B')
        if tag==0x17:take(number(count_format)*32)
        elif tag==0x49:take(number(count_format)*(3*index_bytes+2))
        elif tag==0x26:
            names=[]
            for _ in range(number('H')):
                take(44)
                raw=take(number('B'))
                if raw:
                    try:names.append(raw.decode('utf-8'))
                    except UnicodeDecodeError:
                        # Legacy filenames can be Chinese or Western ANSI.
                        # The resolver tries both without rewriting the names.
                        alternatives=[]
                        for encoding in ('gb18030','cp1252'):
                            try:alternatives.append(raw.decode(encoding))
                            except UnicodeDecodeError:pass
                        names.append(tuple(alternatives))
            return names
        elif tag==0x79:take(64)
        elif tag==0x54:
            for _ in range(number('H')):
                take(number('B'));take(number('H')*(index_bytes+4))
        else:
            raise ValueError('无法校验 O3D 材质区段：'+str(path))
    raise ValueError('O3D 缺少材质区段：'+str(path))


def require_texture(package, mesh_directory, reference):
    alternatives=(reference,) if isinstance(reference,str) else reference
    root=package.resolve()
    for value in alternatives:
        rel=Path(value.replace('\\','/'))
        if rel.is_absolute() or PureWindowsPath(value).drive:
            continue
        for directory in (root/'texture',mesh_directory/'texture',mesh_directory):
            target=(directory/rel).resolve()
            if target.is_relative_to(root) and target.is_file():
                return
    raise ValueError('人物包缺少贴图，或贴图位于人物目录以外：'+str(reference))
