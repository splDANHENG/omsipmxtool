# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Synthetic PMX local-axis regressions; no private model data is included."""
import math
import tempfile
import unittest
from pathlib import Path
from test_converter import fixture, txt, p
from omsimod.pmx import load, ConversionError
from omsimod.gui import convert_model


def with_hand_field(*, axes=None, position=(.8, 1.5, 0), ik_angle=None):
    data = fixture()
    prefix = txt('righthand') + txt('')
    old = prefix + p('3fbiH3f', .8, 1.5, 0, 11, 0, 0, 0, 0, 0)
    flags = (0x800 if axes is not None else 0) | (0x20 if ik_angle is not None else 0)
    new = prefix + p('3fbiH3f', *position, 11, 0, flags, 0, 0, 0)
    if axes is not None:
        new += p('6f', *axes)
    if ik_angle is not None:
        new += p('bifi', 0, 1, ik_angle, 0)
    assert data.count(old) == 1
    return data.replace(old, new)


class PmxLocalAxesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def read(self, data, name='model.pmx'):
        source = self.root/name
        source.write_bytes(data)
        return load(source)

    def test_unused_nonfinite_axes_warn_without_altering_geometry_or_bones(self):
        original = self.read(fixture())
        actual = self.read(with_hand_field(axes=(math.nan, math.inf, -math.inf, 0, 0, math.nan)))
        self.assertEqual(actual.vertices, original.vertices)
        self.assertEqual(actual.indices, original.indices)
        self.assertEqual(actual.materials, original.materials)
        self.assertEqual(actual.bones, original.bones)
        self.assertTrue(any('bone-local coordinate axes' in w and 'righthand' in w for w in actual.warnings))

    def test_finite_axes_do_not_create_a_nonfinite_warning(self):
        actual = self.read(with_hand_field(axes=(1, 0, 0, 0, 0, 1)))
        self.assertFalse(any('non-finite' in w for w in actual.warnings))

    def test_nonfinite_bone_position_remains_an_error(self):
        with self.assertRaisesRegex(ConversionError, 'Non-finite'):
            self.read(with_hand_field(axes=(1, 0, 0, 0, 0, 1), position=(math.nan, 1.5, 0)))

    def test_nonfinite_vertex_position_remains_an_error(self):
        data = fixture()
        vertex = p('3f3f2fB', 0, 0, 0, 0, 0, -1, 0, 0, 2)
        bad = p('3f3f2fB', math.inf, 0, 0, 0, 0, -1, 0, 0, 2)
        self.assertEqual(data.count(vertex), 1)
        with self.assertRaisesRegex(ConversionError, 'Non-finite'):
            self.read(data.replace(vertex, bad))

    def test_nonfinite_ik_angle_is_not_accidentally_allowed(self):
        with self.assertRaisesRegex(ConversionError, 'Non-finite'):
            self.read(with_hand_field(axes=(math.nan,)*6, ik_angle=math.nan))

    def test_truncated_local_axes_are_still_rejected(self):
        axes = p('6f', 1, 2, 3, 4, 5, 6)
        data = with_hand_field(axes=(1, 2, 3, 4, 5, 6))
        offset = data.index(axes)
        with self.assertRaisesRegex(ConversionError, 'Truncated'):
            self.read(data[:offset+20])

    def test_gui_conversion_uses_the_same_geometry_and_retains_warning(self):
        good, bad = self.root/'good.pmx', self.root/'bad.pmx'
        good.write_bytes(fixture())
        bad.write_bytes(with_hand_field(axes=(math.nan,)*6))
        expected = convert_model(good, self.root/'good', 'Driver', 2, {})
        actual = convert_model(bad, self.root/'bad', 'Driver', 2, {})
        for relative in ('Humans/Driver/model/body_0000.o3d', 'Humans/Driver/driver.hum'):
            self.assertEqual((self.root/'good'/relative).read_bytes(), (self.root/'bad'/relative).read_bytes())
        self.assertEqual(actual['vertices'], expected['vertices'])
        self.assertTrue(any('non-finite bone-local' in w for w in actual['warnings']))
