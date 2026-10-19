# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Synthetic hand regressions; no third-party model data is bundled."""
import math
import tempfile
import unittest
from pathlib import Path
from test_converter import fixture
from omsimod.pmx import load, Bone, Vertex, Material
from omsimod.rig import identify, prepare, SLOTS
from omsimod.hand_reference import measure_hand_reference
from omsimod.export import convert


class HandReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'synthetic.pmx'
        self.source.write_bytes(fixture())
        self.model = load(self.source)
        self.joints = identify(self.model, {})

    def add_finger(self, side='right', name=None, parent=None):
        wrist = self.joints[side + '_hand']
        sign = 1 if side == 'right' else -1
        point = self.model.bones[wrist].position
        bone = len(self.model.bones)
        self.model.bones.append(Bone(name or ('右中指３' if side == 'right' else '左中指３'), '',
                                     (point[0] + sign * .17, point[1], point[2]),
                                     wrist if parent is None else parent))
        first = len(self.model.vertices)
        # Several positions along a synthetic fingertip, with a small isolated spike.
        for i in range(101):
            distance = .15 + .05 * i / 100 if i < 100 else .8
            self.model.vertices.append(Vertex((point[0] + sign * distance, point[1], point[2]),
                                              (0, 0, -1), (0, 0), [(bone, 1.0)]))
        self.model.indices.extend(range(first, len(self.model.vertices)))
        self.model.materials[0].count = len(self.model.indices)
        return bone, first

    def measure(self):
        positions, _, weights, jp = prepare(self.model, self.joints, 2.0)
        return measure_hand_reference(self.model, self.joints, positions, weights, jp, 2.0)

    def test_measurement_uses_finger_tip_and_rejects_single_spike(self):
        self.add_finger()
        result = self.measure()
        self.assertEqual(result['method'], 'middle_finger_vertices')
        self.assertEqual(result['side'], 'right')
        self.assertAlmostEqual(result['length_m'], .199)
        self.assertNotAlmostEqual(result['length_m'], 2 * .07)

    def test_named_bones_must_belong_to_the_selected_wrist(self):
        self.add_finger(parent=self.joints['head'])
        self.assertEqual(self.measure()['method'], 'height_ratio_fallback')

    def test_hidden_and_unreferenced_vertices_do_not_change_measurement(self):
        bone, _ = self.add_finger()
        before = self.measure()['length_m']
        start = len(self.model.vertices)
        self.model.vertices.extend([Vertex((1.1, 1.5, 0), (0, 0, -1), (0, 0), [(bone, 1)])] * 300)
        self.assertEqual(self.measure()['length_m'], before)  # Not indexed.
        self.model.indices.extend(range(start, len(self.model.vertices)))
        self.model.materials.append(Material('hidden', (1, 1, 1, 0), -1, 300, False))
        self.assertEqual(self.measure()['length_m'], before)

    def test_bracelet_and_thumb_do_not_set_hand_length(self):
        _, _ = self.add_finger()
        before = self.measure()['length_m']
        wrist = self.joints['right_hand']
        thumb = len(self.model.bones)
        self.model.bones.append(Bone('右親指２', '', (1.3, 1.5, 0), wrist))
        self.model.vertices.extend([Vertex((1.3, 1.5, 0), (0, 0, -1), (0, 0), [(thumb, 1)])] * 100)
        self.model.indices.extend(range(len(self.model.vertices) - 100, len(self.model.vertices)))
        self.model.materials[0].count = len(self.model.indices)
        self.assertEqual(self.measure()['length_m'], before)

    def test_english_names_and_left_only_fallback(self):
        self.add_finger(side='left', name='middle_finger_3.L')
        result = self.measure()
        self.assertEqual(result['side'], 'left')
        self.assertAlmostEqual(result['length_m'], .199)

    def test_namespaced_english_bone_names(self):
        self.add_finger(name='mixamorig:RightHandMiddle3')
        self.assertEqual(self.measure()['method'], 'middle_finger_vertices')

    def test_unrecognized_names_and_sparse_data_use_explicit_fallback(self):
        bone, _ = self.add_finger(name='middle_control_unrelated')
        self.assertEqual(self.measure()['method'], 'height_ratio_fallback')
        self.model.bones[bone].name = 'right_middle_3'
        self.model.indices = self.model.indices[:6]
        self.model.materials[0].count = 6
        result = self.measure()
        self.assertEqual(result['method'], 'height_ratio_fallback')
        self.assertAlmostEqual(result['length_m'], .14)

    def test_both_sides_are_recorded_with_right_reference(self):
        self.add_finger(side='left')
        self.add_finger(side='right')
        result = self.measure()
        self.assertEqual(result['side'], 'right')
        self.assertEqual(set(result['measured_sides']), {'left', 'right'})

    def test_final_t_pose_and_scale_are_used_for_a_pose_model(self):
        _, first = self.add_finger()
        for vertex in self.model.vertices[:first]:
            vertex.weights = [(self.joints['torso'], 1)]
        shoulder = self.model.bones[self.joints['right_arm']].position
        angle = math.radians(-30)

        def turn(p):
            x, y = p[0] - shoulder[0], p[1] - shoulder[1]
            return (shoulder[0] + x * math.cos(angle) - y * math.sin(angle),
                    shoulder[1] + x * math.sin(angle) + y * math.cos(angle), p[2])

        for role in ('elbow', 'hand'):
            b = self.model.bones[self.joints['right_' + role]]
            b.position = turn(b.position)
        for vertex in self.model.vertices[first:]:
            vertex.position = turn(vertex.position)
        positions, _, weights, jp = prepare(self.model, self.joints, 1.0)
        result = measure_hand_reference(self.model, self.joints, positions, weights, jp, 1.0)
        self.assertAlmostEqual(result['length_m'], .199 / 2)

    def test_export_writes_measured_reference_into_hum(self):
        # Use a complete synthetic mesh with triangle counts divisible by three.
        self.add_finger()
        self.model.indices.append(3)
        self.model.materials[0].count = len(self.model.indices)
        output = self.root / 'package'
        report = convert(self.model, self.source, output, 'Hands', 2, {})
        self.assertEqual(report['hand_reference']['method'], 'middle_finger_vertices')
        lines = (output / 'Humans/Hands/driver.hum').read_text().splitlines()
        start = lines.index('[links]') + 1
        actual = float(lines[start + 19]) - float(lines[start + 16])
        self.assertAlmostEqual(actual, report['hand_reference']['length_m'], places=5)

    def test_missing_fingers_warn_without_changing_legacy_reference(self):
        report = convert(self.model, self.source, self.root / 'fallback', 'NoFingers', 2, {})
        self.assertEqual(report['hand_reference']['method'], 'height_ratio_fallback')
        self.assertAlmostEqual(report['hand_reference']['length_m'], .14)
        self.assertTrue(any('Hand reference uses a height-based fallback' in w for w in report['warnings']))
