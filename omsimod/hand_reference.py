# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Measure the HUM hand reference from exported, visible middle-finger geometry.

HUM has one right-hand reference for both hands; it cannot retain PMX finger
joints. OpenOMSI uses the wrist-to-finger distance when curling the hands
(v0.3.38, crates/omsi-sim/src/human/skin.rs). This module measures that
distance; it does not implement or copy the runtime curling algorithm.
"""
import re
from .rig import SLOTS, norm


def _middle_name(name, side):
    name = norm(name.rsplit(':', 1)[-1])
    jp = '右' if side == 'right' else '左'
    short = side[0]
    # Exact conventional names, including NFKC-normalized Japanese numerals.
    patterns = (rf'{jp}中指[123]',
                rf'(?:{side}|{short})(?:middlefinger|handmiddle|middle)0?[123]',
                rf'(?:middlefinger|middle)0?[123](?:{side}|{short})')
    return any(re.fullmatch(pattern, name) for pattern in patterns)


def measure_hand_reference(model, joints, positions, weights, joint_positions, height):
    """Return a length and its provenance, with a conservative legacy fallback.

    Positions must be the final scaled T-pose vertices from prepare(). Sample
    only visible, indexed vertices predominantly assigned to a named middle
    finger under the selected wrist. This excludes sleeves, bracelets, hidden
    expression layers, and unrelated bones whose names happen to match.
    """
    visible = set()
    offset = 0
    for material in model.materials:
        if material.diffuse[3] > 0:
            visible.update(model.indices[offset:offset + material.count])
        offset += material.count

    estimates = {}
    for side in ('right', 'left'):
        wrist_index = joints[side + '_hand']
        slot = SLOTS.index(side + '_hand')
        # Parent-first resolution also handles rigs where children precede parents.
        under_wrist = {wrist_index: True, -1: False}

        def descends(index):
            path = []
            while index not in under_wrist:
                path.append(index)
                index = model.bones[index].parent
            result = under_wrist[index]
            for child in path:
                under_wrist[child] = result
            return result

        middle = {i for i, bone in enumerate(model.bones)
                  if (_middle_name(bone.name, side) or _middle_name(bone.english, side))
                  and descends(i)}
        if not middle:
            continue
        wrist = joint_positions[side + '_hand']
        direction = 1.0 if side == 'right' else -1.0
        distances = []
        for i in visible:
            if weights[i].get(slot, 0.0) <= 0.5:
                continue
            if sum(w for bone, w in model.vertices[i].weights if bone in middle) <= 0.5:
                continue
            # prepare() aligns the arm with X; the reference is longitudinal,
            # rather than a diagonal including finger spread or palm thickness.
            distance = direction * (positions[i][0] - wrist[0])
            if distance > 0:
                distances.append(distance)
        if len(distances) < 8:
            continue
        distances.sort()
        # Trim isolated spikes without changing the mesh or its bone weights.
        measured = distances[int(0.98 * (len(distances) - 1))]
        if not height * 0.025 <= measured <= height * 0.2:
            continue
        estimates[side] = {'length_m': measured, 'sample_vertices': len(distances)}

    side = next((s for s in ('right', 'left') if s in estimates), None)
    if side is None:
        return {'method': 'height_ratio_fallback', 'length_m': height * 0.07,
                'measured_sides': {}}
    return {'method': 'middle_finger_vertices', 'length_m': estimates[side]['length_m'],
            'side': side, 'measured_sides': estimates}
