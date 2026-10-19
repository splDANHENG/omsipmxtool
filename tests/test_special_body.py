# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Special-body behavior on synthetic humanoids with very large accessories."""
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_converter import fixture, p, txt, read_o3d
from omsimod.pmx import load, Bone, Vertex, Material, ConversionError
from omsimod.rig import identify, prepare
from omsimod.special_body import measure_body_reference
from omsimod.gui import convert_model


def special_fixture():
    """A complete tiny PMX, including head/feet and long wings/tails."""
    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp)/'base.pmx'
        source.write_bytes(fixture(scale=12.5))
        model = load(source)
    joints = identify(model, {})
    for v in model.vertices:
        v.weights = [(joints['torso'], 1)]
    def triangle(bone, x, y):
        start = len(model.vertices)
        for position in ((x-.05, y, 0), (x+.05, y, 0), (x, y+.05, .05)):
            model.vertices.append(Vertex(position, (0, 1, 0), (0, 0), [(bone, 1)]))
        model.indices.extend((start, start+1, start+2))
    for side, x in (('left', -1.25), ('right', 1.25)):
        ankle = len(model.bones)
        model.bones.append(Bone(side+'foot', '', (x, 1, 0), joints[side+'_shin']))
        for y in (0, .1, .2):
            triangle(ankle, x, y)
    for y in (24, 24.1, 24.2):
        triangle(joints['head'], 0, y)
    triangle(joints['head'], 0, 60)  # a tall halo/wing, still exported
    triangle(len(model.bones)-2, -1.25, -12)  # low clothing weighted to a foot
    model.materials[0].count = len(model.indices)
    return model


def serialize(model):
    data = b'PMX '+p('fB', 2, 8)+bytes([1, 0, 1, 1, 1, 1, 1, 1])
    data += txt('Synthetic special body')+txt('')*3+p('i', len(model.vertices))
    for v in model.vertices:
        assert v.weights[0][1] == 1 and len(v.weights) == 1
        data += p('3f3f2fBbf', *v.position, *v.normal, *v.uv, 0, v.weights[0][0], 1)
    data += p('i', len(model.indices))+bytes(model.indices)+p('i', 0)
    data += p('i', 1)+txt('body')+txt('')
    data += p('4f3ff3fB4ff', 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    data += p('bbBBB', -1, -1, 0, 1, 0)+txt('')+p('i', len(model.indices))
    data += p('i', len(model.bones))
    for b in model.bones:
        data += txt(b.name)+txt(b.english)+p('3fbiH3f', *b.position, b.parent, 0, 0, 0, 0, 0)
    return data+p('4i', 0, 0, 0, 0)


class SpecialBodyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.model = special_fixture()
        self.source = self.root/'special.pmx'
        self.source.write_bytes(serialize(self.model))
        self.joints = identify(self.model, {})

    def test_default_still_rejects_large_automatic_full_mesh_height(self):
        with self.assertRaisesRegex(ValueError, '手动设置'):
            convert_model(self.source, self.root/'ordinary', 'Driver', None, {})
        self.assertFalse((self.root/'ordinary').exists())

    def test_special_mode_keeps_all_triangles_and_large_accessories(self):
        before = self.source.read_bytes()
        report = convert_model(self.source, self.root/'special', 'Driver', None, {}, special_body=True)
        self.assertEqual(report['height_mode'], 'mmd_body_bounds_0.08')
        self.assertTrue(report['special_body']['enabled'])
        self.assertFalse(report['special_body']['geometry_cropped'])
        self.assertLess(report['height'], 3)
        self.assertGreater(report['special_body']['output_mesh_height_m'], 5)
        vertices, faces = [], []
        for path in (self.root/'special').rglob('*.o3d'):
            v, f, _ = read_o3d(path)
            vertices.extend(v); faces.extend(f)
        self.assertEqual(len(faces), len(self.model.indices)//3)
        self.assertLess(min(v[1] for v in vertices), 0)  # clothing below feet retained
        self.assertGreater(max(v[1] for v in vertices), report['height'])
        self.assertEqual(before, self.source.read_bytes())

    def test_manual_height_is_body_reference_and_scales_uniformly(self):
        reference = measure_body_reference(self.model, self.joints)
        p, _, _, _ = prepare(self.model, self.joints, 1.8,
                            body_bounds=(reference['floor_y'], reference['top_y']))
        foot = 3  # first synthetic foot triangle
        self.assertAlmostEqual(p[foot][1], 0)
        expected_scale = 1.8/reference['height_units']
        for a, b in ((3, 4), (len(p)-3, len(p)-2)):
            self.assertAlmostEqual(math.dist(p[a], p[b]),
                                   math.dist(self.model.vertices[a].position,
                                             self.model.vertices[b].position)*expected_scale)

    def test_hidden_head_geometry_cannot_inflate_reference(self):
        before = measure_body_reference(self.model, self.joints)
        start = len(self.model.vertices)
        self.model.vertices.extend([Vertex((0, 26, 0), (0, 1, 0), (0, 0),
                                           [(self.joints['head'], 1)])]*9)
        self.model.indices.extend(range(start, start+9))
        self.model.materials.append(Material('hidden', (1, 1, 1, 0), -1, 9, False))
        self.assertEqual(measure_body_reference(self.model, self.joints), before)

    def test_missing_or_ambiguous_ankles_fail_instead_of_guessing(self):
        self.model.bones[-2].name = 'unknown ankle'
        with self.assertRaisesRegex(ConversionError, '脚踝'):
            measure_body_reference(self.model, self.joints)
        self.model.bones[-2].name = 'leftfoot'
        self.model.bones.append(Bone('leftfootD', '', (-1.25, 2, 0), self.joints['left_shin']))
        with self.assertRaisesRegex(ConversionError, '歧义'):
            measure_body_reference(self.model, self.joints)

    def test_coincident_d_ankles_are_supported(self):
        before = measure_body_reference(self.model, self.joints)
        foot = self.model.bones[-2]
        self.model.bones.append(Bone('leftfootD', '', foot.position, foot.parent))
        after = measure_body_reference(self.model, self.joints)
        self.assertEqual(after['height_units'], before['height_units'])
        self.assertEqual(after['foot_samples'], before['foot_samples'])

    def test_gui_helper_honors_manual_mapping_in_special_mode(self):
        self.model.bones[self.joints['head']].name = 'custom skull'
        self.source.write_bytes(serialize(self.model))
        report = convert_model(self.source, self.root/'mapped', 'Driver', None,
                               {'head': 'custom skull'}, special_body=True)
        self.assertEqual(report['joints']['head'], 'custom skull')

    def test_cli_forwards_compatibility_option(self):
        from omsimod.__main__ import main
        with patch('sys.argv', ['omsimod', 'convert', str(self.source), '--output',
                               str(self.root/'cli'), '--special-body']), \
                patch('omsimod.__main__.convert', return_value={}) as export, patch('builtins.print'):
            self.assertEqual(main(), 0)
            self.assertTrue(export.call_args.kwargs['special_body'])
