# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Conservative static-mesh checks, independent of any game's grip algorithm."""
from .rig import length, sub


def thumb_mesh_quality(model, before, after, forearm_length):
    """Inspect visible triangle edges and coincident vertices touched by a pose.

    Edge changes over 50% and 1% of the forearm length are diagnostic only:
    local stretching is acceptable when the fingers retain their shape.
    Only severe collapse (below 25% length) or opening a seam vetoes a pose.
    This is a regression guard, not visual approval.
    Coincident source vertices (UV/material seams) must stay coincident to
    within 0.1% of the forearm length. Hidden geometry does not veto a pose.
    """
    edges, visible = set(), set()
    offset = 0
    for material in model.materials:
        faces = model.indices[offset:offset + material.count]
        offset += material.count
        if material.diffuse[3] <= 0:
            continue
        visible.update(faces)
        for k in range(0, len(faces) - 2, 3):
            a, b, c = faces[k:k + 3]
            edges.update(tuple(sorted(pair)) for pair in ((a, b), (b, c), (c, a)))
    max_ratio, min_ratio, max_change, distorted, collapsed = 1.0, 1.0, 0.0, 0, 0
    for a, b in edges:
        if before[a] == after[a] and before[b] == after[b]:
            continue
        old, new = length(sub(before[a], before[b])), length(sub(after[a], after[b]))
        if old < 1e-7:
            continue
        ratio, change = new / old, abs(new - old)
        max_ratio, min_ratio = max(max_ratio, ratio), min(min_ratio, ratio)
        max_change = max(max_change, change)
        if (ratio > 1.5 or ratio < 0.5) and change > forearm_length * 0.01:
            distorted += 1
        if ratio < 0.25 and change > forearm_length * 0.01:
            collapsed += 1
    seams = {}
    max_gap = 0.0
    for i in sorted(visible):
        key = tuple(round(v, 7) for v in before[i])
        if key in seams:
            max_gap = max(max_gap, length(sub(after[i], after[seams[key]])))
        else:
            seams[key] = i
    return {'safe': collapsed == 0 and max_gap <= forearm_length * 0.001,
            'distorted_edges': distorted, 'collapsed_edges': collapsed,
            'max_edge_ratio': max_ratio,
            'min_edge_ratio': min_ratio, 'max_edge_change_m': max_change,
            'max_seam_gap_m': max_gap,
            'edge_change_limit_m': forearm_length * 0.01,
            'seam_gap_limit_m': forearm_length * 0.001}
