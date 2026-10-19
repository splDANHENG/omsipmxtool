# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Thumb adaptation tests using constructed geometry, not real model assets."""
import math
from pathlib import Path
import tempfile
import unittest
from test_converter import fixture, read_o3d
from omsimod.pmx import load, Bone, Vertex
from omsimod.rig import identify, prepare
from omsimod.thumb_pose import adapt_thumb_pose
from omsimod.export import convert


class ThumbPoseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'synthetic.pmx'
        self.source.write_bytes(fixture())
        self.model = load(self.source)
        self.joints = identify(self.model, {})

    def thumb(self, side='right', *, mixed=False):
        wrist = self.joints[side + '_hand']
        w = self.model.bones[wrist].position
        sign = 1 if side == 'right' else -1
        root = len(self.model.bones)
        cn = '右' if side == 'right' else '左'
        self.model.bones.extend([
            Bone(cn+'親指０', '', w, wrist),
            Bone(cn+'親指２', '', (w[0]+sign*.06, w[1]-.04, w[2]+.03), root)])
        first = len(self.model.vertices)
        for delta in (0, .002, .004):
            self.model.vertices.append(Vertex((w[0]+sign*(.06+delta), w[1]-.04, w[2]+.03),
                (0, 1, 0), (0, 0), [(root+1, .5), (wrist, .5)] if mixed else [(root+1, 1)]))
        self.model.indices.extend([first, first+1, first+2])
        self.model.materials[0].count = len(self.model.indices)
        return root, first

    def prepared(self):
        return prepare(self.model, self.joints, 2)

    def test_both_hands_rotate_without_reflection(self):
        _, r = self.thumb()
        _, l = self.thumb('left')
        p, n, _, jp = self.prepared()
        q, normals, report = adapt_thumb_pose(self.model, self.joints, p, n, jp)
        for side, start in [('right', r), ('left', l)]:
            wrist = jp[side+'_hand']
            self.assertEqual(report[side]['status'], 'adapted')
            self.assertAlmostEqual(q[start][1], wrist[1])
            self.assertGreater(q[start][2], wrist[2])
            self.assertAlmostEqual(q[start][0], p[start][0])
            self.assertAlmostEqual(math.dist(q[start], wrist), math.dist(p[start], wrist))
            self.assertAlmostEqual(math.dist(q[start], q[start+1]), math.dist(p[start], p[start+1]))
            self.assertAlmostEqual(sum(v*v for v in normals[start]), 1)
        self.assertAlmostEqual(q[r][0], -q[l][0])
        self.assertAlmostEqual(q[r][2], q[l][2])
        self.assertEqual(q[:3], p[:3])
        self.assertEqual(n[:3], normals[:3])
        self.assertIsNot(q, p)

    def test_partial_thumb_weights_blend_at_palm_seam(self):
        _, start = self.thumb(mixed=True)
        p, n, _, jp = self.prepared()
        q, _, _ = adapt_thumb_pose(self.model, self.joints, p, n, jp)
        self.assertAlmostEqual(q[start][1], (p[start][1] + jp['right_hand'][1]) / 2)
        self.assertNotEqual(q[start], p[start])

    def test_missing_or_ambiguous_thumb_is_skipped(self):
        p, n, _, jp = self.prepared()
        q, nn, r = adapt_thumb_pose(self.model, self.joints, p, n, jp)
        self.assertEqual(q, p)
        self.assertEqual(nn, n)
        self.assertTrue(all(s['status']=='skipped' for s in r.values()))
        root, _ = self.thumb()
        self.model.bones.append(Bone('右親指１', '', (1, 1.5, .05), root))
        p, n, _, jp = self.prepared()
        q, _, r = adapt_thumb_pose(self.model, self.joints, p, n, jp)
        self.assertEqual(r['right']['status'], 'skipped')
        self.assertEqual(q, p)

    def test_export_defaults_on_and_can_be_disabled(self):
        self.thumb()
        a, b = Path(self.temp.name)/'unchanged', Path(self.temp.name)/'adapted'
        off = convert(self.model, self.source, a, 'Thumb', 2, {}, adapt_thumbs=False)
        on = convert(self.model, self.source, b, 'Thumb', 2, {})
        self.assertFalse(off['thumb_rest_pose']['enabled'])
        self.assertTrue(on['thumb_rest_pose']['enabled'])
        folder = 'Humans/Thumb/model/body_0000.o3d'
        av, _, _ = read_o3d(a/folder)
        bv, _, _ = read_o3d(b/folder)
        self.assertNotEqual(av, bv)
        self.assertEqual((a/'Humans/Thumb/driver.hum').read_bytes(),
                         (b/'Humans/Thumb/driver.hum').read_bytes())

    def test_gui_conversion_option_reaches_export(self):
        # Verify the GUI helper forwards the default to the exporter.
        from unittest.mock import patch
        from omsimod.gui import convert_model
        with patch('omsimod.gui.convert') as export:
            export.return_value = {}
            convert_model(self.source, Path(self.temp.name)/'gui', 'Thumb', 2, {})
            self.assertTrue(export.call_args.kwargs['adapt_thumbs'])

    def test_cli_defaults_on_and_allows_opt_out(self):
        from unittest.mock import patch
        from omsimod.__main__ import main
        for flags, enabled in [([], True), (['--no-adapt-thumbs'], False),
                               (['--adapt-thumbs'], True)]:
            with self.subTest(flags=flags), patch('sys.argv', [
                    'omsimod', 'convert', str(self.source), '--output',
                    str(Path(self.temp.name)/'cli'), *flags]), \
                    patch('omsimod.__main__.convert', return_value={}) as export, \
                    patch('builtins.print'):
                self.assertEqual(main(), 0)
                self.assertEqual(export.call_args.kwargs['adapt_thumbs'], enabled)
