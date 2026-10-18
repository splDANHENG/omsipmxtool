# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Portable O3D v1 writer and staged content-package export."""
import filecmp
import hashlib
import json
import re
import struct
import tempfile
from pathlib import Path, PureWindowsPath
from .pmx import ConversionError
from .rig import SLOTS, prepare, identify


def pack(fmt, *values):
    return struct.pack('<'+fmt, *values)


def string(value):
    data = value.encode('ascii')
    if len(data) > 255:
        raise ConversionError('O3D name too long')
    return pack('B', len(data)) + data


def o3d(vertices, normals, uvs, weights, triangles, diffuse, texture):
    out = bytearray(b'\x84\x19\x01')
    out += b'\x17' + pack('H', len(vertices))
    for p, n, uv in zip(vertices, normals, uvs):
        out += pack('8f', *p, *n, *uv)
    out += b'\x49' + pack('H', len(triangles))
    for triangle in triangles:
        out += pack('4H', *triangle, 0)
    out += b'\x26' + pack('H', 1)
    out += pack('11f', *diffuse, 0, 0, 0, 0, 0, 0, 1) + string(texture)
    out += b'\x79' + pack('16f', *(1.0 if i % 5 == 0 else 0.0 for i in range(16)))
    out += b'\x54' + pack('H', len(SLOTS))
    for slot, name in enumerate(SLOTS):
        entries = [(i, w[slot]) for i, w in enumerate(weights) if w.get(slot, 0) > 0]
        out += string(name) + pack('H', len(entries))
        for i, weight in entries:
            out += pack('Hf', i, weight)
    return out


def bake_texture(source, diffuse, destination):
    try:
        from PIL import Image
    except ImportError as exc:
        raise ConversionError('Pillow is required: python -m pip install Pillow') from exc
    if source is None:
        image = Image.new('RGBA', (1, 1), (255, 255, 255, 255))
    else:
        with Image.open(source) as original:
            image = original.convert('RGBA')
    channels = []
    for channel, factor in zip(image.split(), diffuse):
        factor = max(0.0, min(1.0, factor))
        channels.append(channel.point([round(v*factor) for v in range(256)]))
    image = Image.merge('RGBA', channels)
    alpha = image.getchannel('A')
    histogram = alpha.histogram()
    mode = 2 if any(histogram[1:255]) else (1 if histogram[0] else 0)
    image.save(destination, format='PNG')
    return mode


def texture_source(source, relative):
    rel = relative.replace('\\', '/')
    if PureWindowsPath(relative).drive or rel.startswith('/'):
        raise ConversionError(f'Texture must be inside the PMX folder: {relative}')
    root = source.parent.resolve()
    candidate = (root / rel).resolve()
    if not candidate.is_relative_to(root):
        raise ConversionError(f'Texture escapes the PMX folder: {relative}')
    if not candidate.is_file():
        raise ConversionError(f'Missing texture: {relative}')
    if candidate.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.bmp', '.tga', '.dds'):
        raise ConversionError(f'Unsupported texture extension: {relative}')
    return candidate


class TextureExporter:
    """Share baked textures within one export, retaining tint and alpha changes."""

    def __init__(self, folder):
        self.folder = folder
        self.inputs = {}
        self.contents = {}
        self.count = 0

    def export(self, source, diffuse, name):
        key = (source, tuple(max(0.0, min(1.0, v)) for v in diffuse))
        if key in self.inputs:
            return self.inputs[key]
        destination = self.folder/name
        mode = bake_texture(source, diffuse, destination)
        digest = hashlib.sha256()
        with destination.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024*1024), b''):
                digest.update(chunk)
        candidates = self.contents.setdefault(digest.digest(), [])
        for existing, existing_mode in candidates:
            # Confirm byte equality even in the event of a hash collision.
            if filecmp.cmp(destination, self.folder/existing, shallow=False):
                destination.unlink()
                result = (existing, existing_mode)
                break
        else:
            result = (name, mode)
            candidates.append(result)
            self.count += 1
        self.inputs[key] = result
        return result


def text_file(path, lines):
    path.write_bytes(('\r\n'.join(lines)+'\r\n').encode('utf-8'))


def character_name(value):
    """Keep Unicode model names while producing a portable directory component."""
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', value).strip(' .')[:48].rstrip(' .')
    if not value:
        value = 'CustomDriver'
    if value.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL',
            *(f'COM{i}' for i in range(10)), *(f'LPT{i}' for i in range(10))}:
        value = '_' + value
    return value[:48]


def convert(model, source, output, name, height, overrides):
    if not name or character_name(name) != name:
        raise ConversionError('角色标识须为有效文件夹名称（最多 48 字符，不含路径分隔符或 Windows 保留名称）')
    if not 0.5 <= height <= 3:
        raise ConversionError('--height must be between 0.5 and 3 metres')
    output = output.resolve()
    if output.exists():
        raise ConversionError('Output already exists; choose a new directory (no overwrite)')
    if output == source.resolve() or output in source.resolve().parents:
        raise ConversionError('Output must not contain the source')
    joints = identify(model, overrides)
    positions, normals, weights, jp = prepare(model, joints, height)
    # Check all textures before touching the destination.
    sources = {m.texture: texture_source(source, model.textures[m.texture])
               for m in model.materials if m.texture >= 0 and m.diffuse[3] > 0}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.omsimod-', dir=output.parent) as temp:
        stage = Path(temp)/'package'
        folder = stage/'Humans'/name
        meshes, textures = folder/'model', folder/'texture'
        meshes.mkdir(parents=True)
        textures.mkdir()
        texture_exporter = TextureExporter(textures)
        cfg, offset, mesh_count = [], 0, 0
        for mi, material in enumerate(model.materials):
            faces = model.indices[offset:offset+material.count]
            offset += material.count
            if material.diffuse[3] <= 0:
                model.warnings.append(f'Omitted fully hidden material: {material.name}')
                continue
            if not faces:
                continue
            tex, alpha_mode = texture_exporter.export(
                sources.get(material.texture), material.diffuse, f'mat_{mi:03d}.png')
            # <=8,000 triangles -> <=48,000 vertices when double-sided,
            # safely below all v1/u16 section limits.
            for start in range(0, len(faces), 24000):
                chunk = faces[start:start+24000]
                local, keys, triangles = {}, [], []
                for k in range(0, len(chunk), 3):
                    face = chunk[k:k+3]
                    for back in range(2 if material.double_sided else 1):
                        tri = []
                        for index in (face[::-1] if back else face):
                            key = (index, back)
                            if key not in local:
                                local[key] = len(keys)
                                keys.append(key)
                            tri.append(local[key])
                        triangles.append(tri)
                filename = f'body_{mesh_count:04d}.o3d'
                data = o3d([positions[i] for i, _ in keys],
                           [tuple(-x for x in normals[i]) if back else normals[i] for i, back in keys],
                           [model.vertices[i].uv for i, _ in keys],
                           [weights[i] for i, _ in keys], triangles, (1, 1, 1, 1), tex)
                (meshes/filename).write_bytes(data)
                cfg += ['[mesh]', filename, '[smoothskin]']
                for slot, bone in enumerate(SLOTS):
                    cfg += ['[setbone]', bone, str(-2-slot)]
                cfg += ['[matl]', tex, '0', '[matl_alpha]', str(alpha_mode), '']
                mesh_count += 1
        if not mesh_count:
            raise ConversionError('No visible geometry in the default material state')
        text_file(meshes/'model.cfg', cfg)
        # O3D x/y/z = right/up/forward; .hum = right/forward/up.
        def world(role):
            x, y, z = jp[role]
            return (x, z, y)
        hip, knee = world('right_thigh'), world('right_shin')
        waist, neck = world('torso'), world('neck')
        shoulder, elbow, hand = [world('right_'+r) for r in ('arm', 'elbow', 'hand')]
        finger = (hand[0]+height*0.07, hand[1], hand[2])
        links = (*hip, *knee, *waist[1:], *shoulder, *elbow, *neck[1:], *hand, *finger)
        seat = max(0.01, hip[2]-height*0.057)
        hum = ['[model]', 'model\\model.cfg', '[humangeom]', f'{abs(hip[0])*2:.6f}', f'{height:.6f}',
               '[seatheight]', f'{seat:.6f}', '[links]', *[f'{v:.6f}' for v in links],
               '[walk_param]', '1.4', '66', '1', '1', '0', '[mass]', '75']
        text_file(folder/'driver.hum', hum)
        report = {'format': 1, 'source_name': model.name, 'character': name,
                  'human_path': f'Humans\\{name}\\driver.hum', 'height': height,
                  'vertices': len(model.vertices), 'triangles': len(model.indices)//3,
                  'output_meshes': mesh_count,
                  'output_textures': texture_exporter.count,
                  'weighted_vertices_by_bone': {slot: sum(w.get(i, 0) > 0 for w in weights)
                                                for i, slot in enumerate(SLOTS)},
                  'joints': {role: model.bones[i].name for role, i in joints.items()},
                  'warnings': model.warnings + ['Material tint/alpha rendering and seat fit require in-game verification.'],
                  'game_verified': False}
        (stage/'conversion-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        text_file(stage/'INSTALL.txt', [
            'Experimental package: NOT verified in game.',
            'Copy Humans into an openOMSI content root. Keep the directory structure.',
            'Back up maps/<map>/drivers.txt, then put the following path first:',
            report['human_path'],
            'Keep existing driver entries below it. AI drivers may also select this model.',
            'Restart the game completely; inspect outside view and mirrors.',
            'To undo, restore drivers.txt and remove only this character folder.',
            'No game files have been modified by this converter.'])
        if output.exists():
            raise ConversionError('Output appeared during conversion; refusing overwrite')
        stage.rename(output)
    return report
