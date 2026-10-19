# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Estimate a humanoid body reference without distant wings or clothing tails."""
import math
from .pmx import ConversionError
from .rig import ALIASES, norm, length, sub


def measure_body_reference(model, joints):
    """Use visible head/foot geometry near anatomical joints, without cropping.

    The sampling neighborhoods are heuristic: twice the head-to-neck distance
    and three quarters of the knee-to-ankle distance. They locate a scale/floor
    reference, not a canonical human height. All geometry is still exported.
    Ambiguous/missing feet fail explicitly instead of inventing a default size.
    """
    def named(bone, names):
        return any(norm(value.rsplit(':', 1)[-1]) in names
                   for value in (bone.name, bone.english))

    def under(index, roots):
        while index != -1:
            if index in roots:
                return True
            index = model.bones[index].parent
        return False

    visible, offset = set(), 0
    for material in model.materials:
        if material.diffuse[3] > 0:
            visible.update(model.indices[offset:offset + material.count])
        offset += material.count
    head = model.bones[joints['head']].position
    neck = model.bones[joints['neck']].position
    head_radius = 2 * length(sub(head, neck))
    if head_radius < 1e-6:
        raise ConversionError('特殊体型模式无法测量头部：头和颈关节重合。')
    head_bones = {i for i in range(len(model.bones)) if under(i, {joints['head']})}

    def samples(bones, pivot, radius):
        result = []
        for i in visible:
            vertex = model.vertices[i]
            total = sum(w for _, w in vertex.weights if w > 0)
            weight = sum(w for b, w in vertex.weights if b in bones and w > 0)
            if weight > total * .5 and length(sub(vertex.position, pivot)) <= radius:
                result.append(vertex.position[1])
        return result

    head_samples = samples(head_bones, head, head_radius)
    if len(head_samples) < 8:
        raise ConversionError('特殊体型模式缺少可靠的头部网格，请检查头部骨骼映射。')
    feet, ankle_names, radii = {}, {}, {}
    for side, jp in (('left', '左'), ('right', '右')):
        shin_names = {norm(name) for name in ALIASES[side + '_shin']}
        shin_names |= {name + 'd' for name in list(shin_names)}
        shins = {joints[side + '_shin']} | {
            i for i, b in enumerate(model.bones) if named(b, shin_names)}
        foot_names = {norm(name) for name in (
            jp + '足首', jp + '足首D', side + 'foot', side + 'ankle',
            side + 'footD', side + 'ankleD')}
        ankles = [i for i, b in enumerate(model.bones)
                  if named(b, foot_names) and under(i, shins)]
        if not ankles:
            raise ConversionError(f'特殊体型模式无法识别{jp}脚踝，需要标准人体脚部骨骼。')
        pivot = model.bones[ankles[0]].position
        if any(length(sub(model.bones[i].position, pivot)) > 1e-4 for i in ankles):
            raise ConversionError(f'特殊体型模式的{jp}脚踝位置存在歧义，请先检查骨骼。')
        radius = .75 * length(sub(model.bones[joints[side + '_shin']].position, pivot))
        foot_bones = {i for i in range(len(model.bones)) if under(i, set(ankles))}
        feet[side] = samples(foot_bones, pivot, radius)
        if len(feet[side]) < 8:
            raise ConversionError(f'特殊体型模式缺少可靠的{jp}脚部网格，无法确定脚底。')
        ankle_names[side] = [model.bones[i].name for i in ankles]
        radii[side] = radius
    floor, top = min(min(v) for v in feet.values()), max(head_samples)
    if not math.isfinite(top - floor) or top - floor <= 1e-6:
        raise ConversionError('特殊体型模式无法确定有效的主体高度。')
    return {'method': 'visible_mesh_near_head_and_ankles',
            'floor_y': floor, 'top_y': top, 'height_units': top - floor,
            'head_samples': len(head_samples),
            'foot_samples': {side: len(v) for side, v in feet.items()},
            'ankle_bones': ankle_names, 'head_radius_units': head_radius,
            'foot_radius_units': radii, 'estimated': True}
