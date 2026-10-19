# SPDX-License-Identifier: AGPL-3.0-only
"""New PMX exports must work with the existing runtime signature and face masks."""
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from omsimod.body_visibility import marker_weights, read_mesh
from omsimod.export import convert, o3d
from omsimod.library import Library
from omsimod.pmx import load
from omsimod.rig import identify, prepare
from test_converter import fixture


def rendered(data):
    vertices, faces, weights, _ = read_mesh(data)
    return Counter(tuple((vertices[i], tuple(weights[i].items())) for i in face[:3])
                   for face in faces)


class AutomaticBodyVisibilityTests(unittest.TestCase):
    def test_new_pmx_names_and_different_parts_need_no_separate_preparation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, role in [('CharacterA', 'head'), ('CharacterB', 'left_thigh')]:
                source = root / (name + '.pmx')
                source.write_bytes(fixture())
                model = load(source)
                joints = identify(model, {})
                model.vertices = [replace(vertex, weights=[(joints[role], 1)])
                                  for vertex in model.vertices]
                output = root / name
                report = convert(model, source, output, name, 1.75, {}, adapt_thumbs=False)
                folder = output / 'Humans' / name
                manifest = json.loads((folder / 'bodytoggle.json').read_text())
                self.assertTrue(report['body_visibility']['automatic'])
                self.assertEqual(manifest['format'], 2)
                positions, normals, weights, _ = prepare(model, joints, 1.75)
                original = o3d(positions, normals, [v.uv for v in model.vertices], weights,
                               [(0, 1, 2)], (1, 1, 1, 1), 'mat_000.png')
                actual = Counter()
                for mesh in manifest['meshes']:
                    raw = (folder / 'model' / mesh['file']).read_bytes()
                    vertices, faces, mesh_weights, _ = read_mesh(raw)
                    # These exact slots and normalized weights are consumed by filter.asm.
                    self.assertEqual(mesh_weights[:3], marker_weights(mesh['parts']))
                    self.assertTrue(all(min(face[:3]) >= 3 for face in faces))
                    for face in faces:
                        mask = 0
                        for index in face[:3]:
                            mask |= 1 << max(mesh_weights[index], key=mesh_weights[index].get)
                        self.assertEqual(mesh['parts'], mask)
                    self.assertEqual(vertices[:3], [vertices[3]] * 3)
                    actual.update(rendered(raw))
                self.assertEqual(actual, rendered(original))

    def test_automatic_groups_survive_library_install_and_map_activation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'new.pmx'
            source.write_bytes(fixture())
            output = root / 'export'
            convert(load(source), source, output, 'NewDriver', 1.75, {})
            library = Library(root / 'library')
            game = root / 'game'
            map_folder = game / 'maps' / 'Map'
            map_folder.mkdir(parents=True)
            (map_folder / 'global.cfg').write_text('map')
            original = b'old\\driver.hum\r\n'
            (map_folder / 'drivers.txt').write_bytes(original)
            item = library.add(output / 'Humans/NewDriver/driver.hum')
            relative = library.activate(item, game, 'Map')
            installed = game / relative.replace('\\', '/')
            manifest = json.loads((installed.parent / 'bodytoggle.json').read_text())
            self.assertTrue(manifest['automatic'])
            for mesh in manifest['meshes']:
                self.assertEqual((installed.parent / 'model' / mesh['file']).read_bytes(),
                                 (output / 'Humans/NewDriver/model' / mesh['file']).read_bytes())
            library.restore(game, 'Map')
            self.assertEqual((map_folder / 'drivers.txt').read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
