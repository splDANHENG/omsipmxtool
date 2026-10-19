# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Optional thumb rest-pose adaptation for the target's flat-hand convention.

Uses PMX thumb chains and proper rotations, never a reflection. This is an
asset adaptation, not an implementation of the game's grip-deformation code.
"""
import math
import re
from .rig import norm, unit, sub, dot, cross, rotate, length
from .hand_quality import thumb_mesh_quality


def _thumb_name(name, side):
    name = norm(name.rsplit(':', 1)[-1])
    jp = '右' if side == 'right' else '左'
    return any(re.fullmatch(p, name) for p in (
        rf'{jp}親指[0123]', rf'(?:{side}|{side[0]})(?:hand)?thumb0?[0123]',
        rf'thumb0?[0123](?:{side}|{side[0]})'))


def adapt_thumb_pose(model, joints, positions, normals, joint_positions):
    """Return adapted vertex arrays and per-side results; inputs stay intact.

    Only a single named thumb chain under each selected wrist is accepted.
    Its transverse direction is aligned with +Z in exported O3D coordinates
    (the target's forward/thumb side). Forearm twist is not guessed from a
    character name. Original thumb weights blend the change into the palm.
    """
    out, out_normals = list(positions), list(normals)
    results = {}
    right = model.bones[joints['right_thigh']].position
    left = model.bones[joints['left_thigh']].position
    sign = 1 if right[0] > left[0] else -1
    for side in ('left', 'right'):
        wrist_index = joints[side + '_hand']

        def under_wrist(i):
            while i not in (-1, wrist_index):
                i = model.bones[i].parent
            return i == wrist_index

        thumb = {i for i, b in enumerate(model.bones)
                 if (_thumb_name(b.name, side) or _thumb_name(b.english, side))
                 and under_wrist(i)}
        roots = [i for i in thumb if model.bones[i].parent not in thumb]
        parents = {model.bones[i].parent for i in thumb}
        tips = [i for i in thumb if i not in parents]
        if len(roots) != 1 or len(tips) != 1 or len(thumb) < 2:
            results[side] = {'status': 'skipped', 'reason': 'missing_or_ambiguous_thumb_chain'}
            continue
        source_shoulder = model.bones[joints[side + '_arm']].position
        source_wrist = model.bones[wrist_index].position
        source_direction = sub(source_wrist, source_shoulder)
        target = (1.0 if source_direction[0] > 0 else -1.0, 0.0, 0.0)
        wrist = joint_positions[side + '_hand']
        scale = length(sub(wrist, joint_positions[side + '_arm'])) / length(source_direction)

        def point(i):
            q = rotate(sub(model.bones[i].position, source_wrist), source_direction, target)
            return (wrist[0] + q[0] * sign * scale,
                    wrist[1] + q[1] * scale, wrist[2] + q[2] * sign * scale)

        pivot, tip = point(roots[0]), point(tips[0])
        axis = unit(sub(wrist, joint_positions[side + '_elbow']))
        direction = sub(tip, pivot)
        across = tuple(direction[k] - axis[k] * dot(direction, axis) for k in range(3))
        desired = tuple((1.0 if k == 2 else 0.0) - axis[k] * axis[2] for k in range(3))
        if length(across) < 1e-6 or length(desired) < 1e-6:
            results[side] = {'status': 'skipped', 'reason': 'degenerate_thumb_direction'}
            continue
        across, desired = unit(across), unit(desired)
        angle = math.atan2(dot(axis, cross(across, desired)), dot(across, desired))
        if abs(angle) > math.radians(110):
            results[side] = {'status': 'skipped', 'reason': 'thumb_points_away_from_expected_side'}
            continue
        c, s = math.cos(angle), math.sin(angle)

        def turn(vector):
            v_cross = cross(axis, vector)
            return tuple(vector[k] * c + v_cross[k] * s + axis[k] * dot(axis, vector) * (1 - c)
                         for k in range(3))

        count = 0
        candidate, candidate_normals = list(out), list(out_normals)
        for i, vertex in enumerate(model.vertices):
            total = sum(w for _, w in vertex.weights if w > 0)
            influence = sum(w for b, w in vertex.weights if b in thumb and w > 0) / total
            if influence <= 0:
                continue
            old = positions[i]
            q = turn(sub(old, pivot))
            candidate[i] = tuple(old[k] + influence * (pivot[k] + q[k] - old[k]) for k in range(3))
            n, rotated = normals[i], turn(normals[i])
            blended = tuple(n[k] + influence * (rotated[k] - n[k]) for k in range(3))
            candidate_normals[i] = unit(blended)
            count += 1
        quality = thumb_mesh_quality(model, out, candidate,
                                     length(sub(wrist, joint_positions[side + '_elbow'])))
        result = {'status': 'adapted' if count else 'skipped',
                  'rotation_degrees': math.degrees(angle), 'affected_vertices': count,
                  'static_quality': quality,
                  'bones': [model.bones[i].name for i in sorted(thumb)]}
        if not count:
            result['reason'] = 'no_thumb_vertex_weights'
        elif not quality['safe']:
            result.update(status='skipped', reason='unsafe_static_mesh_deformation',
                          affected_vertices=0, candidate_vertices=count)
        else:
            out, out_normals = candidate, candidate_normals
            if quality['distorted_edges']:
                result['warning'] = 'local_edge_distortion_requires_visual_check'
        results[side] = result
    return out, out_normals, results
