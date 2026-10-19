# SPDX-License-Identifier: AGPL-3.0-only
"""Group converter meshes for runtime body visibility.

Only the converter's unencrypted O3D v1 layout is accepted. Three unreferenced
vertices carry a signature and a group mask in ordinary, normalized weights.
Original rendered vertices, weights, triangles, normals and UVs are preserved.
The runtime adapter hides a whole group if any of its required parts is hidden.
"""
from collections import defaultdict
import math
import struct

SLOTS = ['left_thigh', 'right_thigh', 'left_shin', 'right_shin',
         'left_arm', 'right_arm', 'left_elbow', 'right_elbow',
         'hips', 'torso', 'head', 'left_hand', 'right_hand']


class Reader:
    def __init__(self, data):
        self.data, self.at = bytes(data), 0

    def take(self, n):
        if n < 0 or self.at + n > len(self.data):
            raise ValueError('O3D 文件不完整。')
        out = self.data[self.at:self.at+n]
        self.at += n
        return out

    def number(self, fmt):
        return struct.unpack('<'+fmt, self.take(struct.calcsize('<'+fmt)))

    def expect(self, data):
        if self.take(len(data)) != data:
            raise ValueError('仅支持 omsipmxtool 生成的 O3D v1 人物包。')


def read_mesh(data):
    r = Reader(data)
    r.expect(b'\x84\x19\x01\x17')
    vertices = [r.take(32) for _ in range(r.number('H')[0])]
    r.expect(b'\x49')
    faces = [r.number('4H') for _ in range(r.number('H')[0])]
    if not vertices or not faces or any(max(f[:3]) >= len(vertices) or f[3] for f in faces):
        raise ValueError('O3D 三角面索引或材质无效。')
    start = r.at
    r.expect(b'\x26\x01\x00')
    r.take(44)
    r.take(r.number('B')[0])
    r.expect(b'\x79')
    transform = r.number('16f')
    if transform != tuple(float(i % 5 == 0) for i in range(16)):
        raise ValueError('不支持带额外变换的模型。')
    middle = data[start:r.at]
    r.expect(b'\x54')
    if r.number('H')[0] != 13:
        raise ValueError('需要本转换器的 13 部位骨骼。')
    weights = [{} for _ in vertices]
    for slot, expected in enumerate(SLOTS):
        name = r.take(r.number('B')[0]).decode('ascii')
        if name != expected:
            raise ValueError('模型骨骼顺序不匹配。')
        for _ in range(r.number('H')[0]):
            i, w = r.number('Hf')
            if i >= len(vertices) or slot in weights[i] or not math.isfinite(w) or w <= 0:
                raise ValueError('模型骨骼权重无效。')
            weights[i][slot] = w
    if r.at != len(data) or any(not w or len(w) > 4 for w in weights):
        raise ValueError('模型包含不支持的数据或权重。')
    return vertices, faces, weights, middle


def marker_weights(mask):
    return [{9: .75, 8: .25}, {8: .625, 9: .375},
            {9: .5 + mask / 32768, 8: .5 - mask / 32768}]


def split_mesh(data):
    vertices, faces, weights, middle = read_mesh(data)
    dominant = [max(w, key=w.get) for w in weights]
    groups = defaultdict(list)
    for face in faces:
        mask = 0
        for i in face[:3]:
            mask |= 1 << dominant[i]
        groups[mask].append(face)
    results = []
    for mask, grouped in sorted(groups.items()):
        # Keep all u16 section counts below the format limit, including markers.
        for start in range(0, len(grouped), 20000):
            local, keys, triangles = {}, [], []
            for face in grouped[start:start+20000]:
                tri = []
                for i in face[:3]:
                    if i not in local:
                        local[i] = len(keys) + 3
                        keys.append(i)
                    tri.append(local[i])
                triangles.append((*tri, 0))
            vv = [vertices[keys[0]]] * 3 + [vertices[i] for i in keys]
            ww = marker_weights(mask) + [weights[i] for i in keys]
            out = bytearray(b'\x84\x19\x01\x17' + struct.pack('<H', len(vv)))
            out += b''.join(vv)
            out += b'\x49' + struct.pack('<H', len(triangles))
            out += b''.join(struct.pack('<4H', *f) for f in triangles)
            out += middle + b'\x54\x0d\x00'
            for slot, name in enumerate(SLOTS):
                entries = [(i, w[slot]) for i, w in enumerate(ww) if slot in w]
                encoded = name.encode('ascii')
                out += bytes([len(encoded)]) + encoded + struct.pack('<H', len(entries))
                out += b''.join(struct.pack('<Hf', i, w) for i, w in entries)
            results.append((mask, bytes(out)))
    return results
