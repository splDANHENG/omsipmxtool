"""Explicit 13-slot rig reduction; PMX model space is kept until O3D export."""
import math
import unicodedata
from .pmx import ConversionError

SLOTS = ['left_thigh', 'right_thigh', 'left_shin', 'right_shin',
         'left_arm', 'right_arm', 'left_elbow', 'right_elbow',
         'hips', 'torso', 'head', 'left_hand', 'right_hand']
ALIASES = {
    'hips': ['下半身', 'hips', 'pelvis', 'lower body'],
    'torso': ['上半身', 'spine', 'upper body'],
    'head': ['頭', 'head'],
    'neck': ['首', 'neck'],
}
for side, jp in [('left', '左'), ('right', '右')]:
    for role, names in {
        'thigh': [jp+'足', side+'leg', side+'thigh', side+'upleg'],
        'shin': [jp+'ひざ', jp+'膝', side+'knee', side+'lowerleg'],
        'arm': [jp+'腕', side+'arm', side+'upperarm'],
        'elbow': [jp+'ひじ', jp+'肘', side+'elbow', side+'forearm'],
        'hand': [jp+'手首', side+'wrist', side+'hand'],
    }.items():
        ALIASES[side+'_'+role] = names


def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKC', s).casefold() if c not in ' _.-')


def identify(model, overrides):
    unknown = set(overrides) - set(ALIASES)
    if unknown:
        raise ConversionError('Unknown mapping roles: ' + ', '.join(sorted(unknown)))
    result = {}
    for role, aliases in ALIASES.items():
        if role in overrides:
            wanted = overrides[role]
            if not isinstance(wanted, str):
                raise ConversionError('Bone mapping values must be exact bone names')
            hits = [i for i, b in enumerate(model.bones) if wanted in (b.name, b.english)]
        else:
            names = {norm(n) for n in aliases}
            hits = [i for i, b in enumerate(model.bones)
                    if norm(b.name) in names or norm(b.english) in names]
        if len(hits) != 1:
            raise ConversionError(f'{role}: expected one bone, found {len(hits)}. Use --mapping JSON; inspect lists names.')
        result[role] = hits[0]
    if len(set(result.values())) != len(result):
        raise ConversionError('Each required joint must refer to a different bone')
    return result


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def length(v):
    return math.sqrt(sum(x*x for x in v))


def unit(v):
    d = length(v)
    if d < 1e-8:
        raise ConversionError('Coincident joints / zero direction')
    return tuple(x/d for x in v)


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def rotate(v, source, target):
    a, b = unit(source), unit(target)
    c = max(-1.0, min(1.0, dot(a, b)))
    axis = cross(a, b)
    s = length(axis)
    if s < 1e-8:
        if c < 0:
            raise ConversionError('Arm points backwards; correct the rest pose before conversion')
        return v
    k = tuple(x/s for x in axis)
    kv = cross(k, v)
    return tuple(v[i]*c + kv[i]*s + k[i]*dot(k, v)*(1-c) for i in range(3))


def prepare(model, joints, height):
    positions = [b.position for b in model.bones]
    direct = {joints[s]: k for k, s in enumerate(SLOTS)}
    # Neck and its descendants follow the head; other extra bones follow nearest
    # mapped ancestor. No physics is retained.
    direct[joints['neck']] = SLOTS.index('head')
    mapping, fallback = [], []
    for i, bone in enumerate(model.bones):
        k = i
        while k != -1 and k not in direct:
            k = model.bones[k].parent
        if k == -1:
            mapping.append(SLOTS.index('torso'))
            fallback.append(bone.name)
        else:
            mapping.append(direct[k])
    if fallback:
        model.warnings.append('Bones without a mapped ancestor follow torso: ' + ', '.join(fallback))
    weights = []
    for v in model.vertices:
        total = {}
        for b, w in v.weights:
            if w > 0:
                slot = mapping[b]
                total[slot] = total.get(slot, 0) + w
        denom = sum(total.values())
        weights.append({k: w/denom for k, w in total.items()})
    verts = [v.position for v in model.vertices]
    normals = [v.normal for v in model.vertices]
    # Bake each arm as a weighted rigid rotation into a horizontal T pose.
    # Bent elbows require a fuller rebind and are deliberately rejected in v0.1.
    for side in ('left', 'right'):
        ids = [joints[side+'_'+r] for r in ('arm', 'elbow', 'hand')]
        sh, el, hand = [positions[i] for i in ids]
        if dot(unit(sub(el, sh)), unit(sub(hand, el))) < 0.97:
            raise ConversionError(f'{side} elbow is bent: supply a straight-arm T/A rest pose')
        direction = sub(hand, sh)
        target = (1.0 if direction[0] > 0 else -1.0, 0, 0)
        if abs(unit(direction)[0]) < 0.4:
            raise ConversionError(f'{side} arm is not a supported T/A pose')
        slots = {SLOTS.index(side+'_'+r) for r in ('arm', 'elbow', 'hand')}
        for i, w in enumerate(weights):
            influence = sum(value for slot, value in w.items() if slot in slots)
            if influence:
                p = verts[i]
                q = rotate(sub(p, sh), direction, target)
                verts[i] = tuple(p[k] + influence*(sh[k]+q[k]-p[k]) for k in range(3))
                n = normals[i]
                rn = rotate(n, direction, target)
                normals[i] = unit(tuple(n[k]+influence*(rn[k]-n[k]) for k in range(3)))
        for i in ids:
            q = rotate(sub(positions[i], sh), direction, target)
            positions[i] = tuple(sh[k]+q[k] for k in range(3))
    # PMX anatomical right may be -X; infer it from paired leg joints.
    right = positions[joints['right_thigh']]
    left = positions[joints['left_thigh']]
    if abs(right[0]-left[0]) < 1e-5:
        raise ConversionError('Cannot establish left/right axis from thighs')
    sign = 1 if right[0] > left[0] else -1
    cx, cz = (right[0]+left[0])/2, (right[2]+left[2])/2
    floor = min(v[1] for v in verts)
    top = max(v[1] for v in verts)
    if top-floor < 1e-6:
        raise ConversionError('Model has no height')
    scale = height/(top-floor)
    # Turn 180 degrees around up if anatomical right is -X. Y remains up in O3D.
    def transform(p):
        return ((p[0]-cx)*sign*scale, (p[1]-floor)*scale, (p[2]-cz)*sign*scale)
    verts = [transform(p) for p in verts]
    normals = [unit((n[0]*sign, n[1], n[2]*sign)) for n in normals]
    jp = {role: transform(positions[i]) for role, i in joints.items()}
    model.warnings.append('Height uses full mesh bounds (including hair/accessories); inspect scale in game.')
    model.warnings.append('Extra bones are collapsed; asymmetry is retained in geometry, not in mirrored joint parameters.')
    return verts, normals, weights, jp
