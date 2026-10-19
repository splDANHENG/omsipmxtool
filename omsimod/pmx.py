# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2014 MMD Tools authors (referenced implementation)
# Copyright (c) 2026 omsipmxtool contributors (adaptations)
# PMX reader reference and modifications: see THIRD-PARTY-NOTICES.txt.
"""Read the geometry/material/bone prefix of PMX 2.0/2.1. No MMD runtime."""
import math
import struct
from dataclasses import dataclass
from pathlib import Path


class ConversionError(ValueError):
    pass


def read_metadata(path):
    """Read only the four PMX header strings, without parsing model geometry."""
    with Path(path).open('rb') as stream:
        def take(size):
            data = stream.read(size)
            if len(data) != size:
                raise ConversionError('PMX 文件头不完整，无法读取内嵌说明。')
            return data
        if take(4) != b'PMX ':
            raise ConversionError('Not a PMX file')
        version = struct.unpack('<f', take(4))[0]
        if not any(abs(version - supported) < 1e-5 for supported in (2.0, 2.1)):
            raise ConversionError('Unsupported PMX version')
        header = take(take(1)[0])
        if len(header) < 8 or header[0] not in (0, 1):
            raise ConversionError('Invalid PMX header')
        encoding = 'utf-16-le' if header[0] == 0 else 'utf-8'
        info = {}
        for key in ('name', 'english_name', 'comment', 'english_comment'):
            size = struct.unpack('<i', take(4))[0]
            if not 0 <= size <= 16 * 1024 * 1024:
                raise ConversionError('PMX 内嵌说明长度异常，未显示完整内容，不能继续。')
            try:
                info[key] = take(size).decode(encoding)
            except UnicodeError as exc:
                raise ConversionError('PMX 内嵌说明编码无效，无法完整显示。') from exc
        return info


class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, n):
        if n < 0 or self.pos + n > len(self.data):
            raise ConversionError(f'Truncated PMX at byte {self.pos}')
        result = self.data[self.pos:self.pos+n]
        self.pos += n
        return result

    def read(self, fmt):
        values = struct.unpack('<' + fmt, self.take(struct.calcsize('<' + fmt)))
        if any(isinstance(v, float) and not math.isfinite(v) for v in values):
            raise ConversionError('Non-finite number in PMX')
        return values[0] if len(values) == 1 else values

    def count(self):
        n = self.read('i')
        if not 0 <= n <= min(10_000_000, len(self.data) - self.pos):
            raise ConversionError(f'Invalid PMX count: {n}')
        return n

    def text(self):
        try:
            return self.take(self.count()).decode(self.encoding)
        except UnicodeError as exc:
            raise ConversionError('Invalid PMX text encoding') from exc

    def index(self, kind):
        size = self.sizes[kind]
        fmt = {1: 'b', 2: 'h', 4: 'i'}[size]
        return self.read(fmt.upper() if kind == 0 else fmt)


@dataclass
class Vertex:
    position: tuple
    normal: tuple
    uv: tuple
    weights: list


@dataclass
class Bone:
    name: str
    english: str
    position: tuple
    parent: int


@dataclass
class Material:
    name: str
    diffuse: tuple
    texture: int
    count: int
    double_sided: bool


@dataclass
class Model:
    name: str
    vertices: list
    indices: list
    textures: list
    materials: list
    bones: list
    warnings: list


def load(path):
    r = Reader(Path(path).read_bytes())
    if r.take(4) != b'PMX ':
        raise ConversionError('Not a PMX file')
    version = r.read('f')
    if not (abs(version - 2.0) < 1e-5 or abs(version - 2.1) < 1e-5):
        raise ConversionError(f'Unsupported PMX version: {version}')
    header = r.take(r.read('B'))
    if len(header) < 8 or header[0] not in (0, 1) or header[1] > 4:
        raise ConversionError('Invalid PMX header')
    r.encoding = 'utf-16-le' if header[0] == 0 else 'utf-8'
    r.sizes = header[2:8]
    if any(n not in (1, 2, 4) for n in r.sizes):
        raise ConversionError('Invalid PMX index size')
    name = r.text()
    for _ in range(3):
        r.text()
    vertices, special = [], set()
    for _ in range(r.count()):
        p, n, uv = r.read('3f'), r.read('3f'), r.read('2f')
        r.take(16 * header[1])
        mode = r.read('B')
        if mode == 0:
            weights = [(r.index(3), 1.0)]
        elif mode in (1, 3):
            bones = [r.index(3), r.index(3)]
            w = r.read('f')
            weights = list(zip(bones, (w, 1-w)))
            if mode == 3:
                r.read('9f')
                special.add('SDEF')
        elif mode in (2, 4):
            bones = [r.index(3) for _ in range(4)]
            weights = list(zip(bones, r.read('4f')))
            if mode == 4:
                special.add('QDEF')
        else:
            raise ConversionError(f'Unsupported vertex weight mode: {mode}')
        if any(w < 0 or w > 1.00001 for _, w in weights):
            raise ConversionError('Invalid vertex weight')
        r.read('f')  # edge scale
        vertices.append(Vertex(p, n, uv, weights))
    indices = [r.index(0) for _ in range(r.count())]
    if len(indices) % 3 or any(i >= len(vertices) for i in indices):
        raise ConversionError('Invalid triangle indices')
    textures = [r.text() for _ in range(r.count())]
    materials = []
    for _ in range(r.count()):
        mn = r.text()
        r.text()
        diffuse = r.read('4f')
        r.read('3f'); r.read('f'); r.read('3f')
        flags = r.read('B')
        r.read('4f'); r.read('f')
        texture = r.index(1)
        r.index(1); r.read('B')
        toon = r.read('B')
        if toon == 0:
            r.index(1)
        elif toon == 1:
            r.read('B')
        else:
            raise ConversionError('Invalid toon flag')
        r.text()
        # This is a reference count into the index array already read above,
        # not the length of an array stored after this field.
        count = r.read('i')
        if not 0 <= count <= len(indices):
            raise ConversionError('Invalid material face count')
        if count % 3 or not -1 <= texture < len(textures):
            raise ConversionError('Invalid material indices')
        materials.append(Material(mn, diffuse, texture, count, bool(flags & 1)))
    if sum(m.count for m in materials) != len(indices):
        raise ConversionError('Material face counts do not match geometry')
    bones, ignored_local_axes = [], []
    for _ in range(r.count()):
        bn, en, pos = r.text(), r.text(), r.read('3f')
        parent = r.index(3)
        r.read('i')
        flags = r.read('H')
        if flags & 1:
            r.index(3)
        else:
            r.read('3f')
        if flags & 0x300:
            r.index(3); r.read('f')
        if flags & 0x400:
            r.read('3f')
        if flags & 0x800:
            # These optional MMD bone-local X/Z axes are not stored in Bone
            # or used by rig preparation/export. Some PMXs put NaNs here on
            # terminal finger bones. Consume the field without relaxing the
            # finite checks on positions, normals, weights or other fields.
            axes = struct.unpack('<6f', r.take(24))
            if not all(math.isfinite(value) for value in axes):
                ignored_local_axes.append(bn)
        if flags & 0x2000:
            r.read('i')
        if flags & 0x20:
            r.index(3); r.read('i'); r.read('f')
            for _ in range(r.count()):
                r.index(3)
                limited = r.read('B')
                if limited not in (0, 1):
                    raise ConversionError('Invalid IK limit flag')
                if limited:
                    r.read('6f')
        bones.append(Bone(bn, en, pos, parent))
    if not vertices or not bones or not indices:
        raise ConversionError('Model needs geometry and bones')
    for b in bones:
        if not -1 <= b.parent < len(bones):
            raise ConversionError('Invalid bone parent')
    for i in range(len(bones)):
        seen = set()
        while i != -1:
            if i in seen:
                raise ConversionError('Cyclic bone hierarchy')
            seen.add(i)
            i = bones[i].parent
    for v in vertices:
        if any(w > 0 and not 0 <= b < len(bones) for b, w in v.weights):
            raise ConversionError('Vertex references missing bone')
        if sum(w for _, w in v.weights) <= 0:
            raise ConversionError('Vertex has no usable weights')
    warnings = ['Physics, morphs, IK, append transforms, toon, sphere maps and outlines are not exported.']
    if ignored_local_axes:
        warnings.append('Ignored non-finite bone-local coordinate axes (not exported): ' + ', '.join(ignored_local_axes))
    warnings += [f'{mode} approximated with linear blend skinning.' for mode in sorted(special)]
    return Model(name, vertices, indices, textures, materials, bones, warnings)
