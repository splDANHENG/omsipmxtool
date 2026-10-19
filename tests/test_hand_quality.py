# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Static regressions on constructed triangles and UV seams, without assets."""
import unittest
from types import SimpleNamespace
from omsimod.hand_quality import thumb_mesh_quality


class HandQualityTests(unittest.TestCase):
    def model(self, indices, alpha=1):
        return SimpleNamespace(indices=indices, materials=[
            SimpleNamespace(count=len(indices), diffuse=(1, 1, 1, alpha))])

    def test_local_stretch_is_diagnostic_and_does_not_veto_pose(self):
        p = [(0, 0, 0), (.001, 0, 0), (0, .01, 0)]
        q = [p[0], (.012, 0, 0), p[2]]
        r = thumb_mesh_quality(self.model([0, 1, 2]), p, q, .3)
        self.assertTrue(r['safe'])
        self.assertGreater(r['distorted_edges'], 0)
        self.assertAlmostEqual(r['max_edge_ratio'], 12)

    def test_collapsed_edge_rejected(self):
        p = [(0, 0, 0), (.01, 0, 0), (0, .01, 0)]
        self.assertFalse(thumb_mesh_quality(
            self.model([0, 1, 2]), p, [p[0], (.001, 0, 0), p[2]], .3)['safe'])

    def test_rigid_rotation_and_scale_do_not_fail(self):
        for scale in (.1, 1, 10):
            p = [(0, 0, 0), (.01*scale, 0, 0), (0, .01*scale, 0)]
            q = [(-y, x, z) for x, y, z in p]
            self.assertTrue(thumb_mesh_quality(self.model([0, 1, 2]), p, q, .3*scale)['safe'])

    def test_separate_material_or_uv_vertices_cannot_open_a_crack(self):
        p = [(0, 0, 0), (.02, 0, 0), (0, .02, 0)] * 2
        q = list(p)
        q[3] = (0, 0, .001)
        r = thumb_mesh_quality(self.model([0, 1, 2, 3, 4, 5]), p, q, .3)
        self.assertFalse(r['safe'])
        self.assertEqual(r['collapsed_edges'], 0)
        self.assertAlmostEqual(r['max_seam_gap_m'], .001)

    def test_hidden_and_unindexed_geometry_do_not_veto(self):
        p = [(0, 0, 0), (.01, 0, 0), (0, .01, 0)]
        q = [p[0], (1, 0, 0), p[2]]
        self.assertTrue(thumb_mesh_quality(self.model([0, 1, 2], 0), p, q, .3)['safe'])
        self.assertTrue(thumb_mesh_quality(self.model([]), p, q, .3)['safe'])
