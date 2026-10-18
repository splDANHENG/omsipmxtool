# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
import json
import math
import struct
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from PIL import Image
from omsimod.pmx import load, ConversionError, Bone
from omsimod.rig import identify, prepare, SLOTS
from omsimod.export import convert, bake_texture


def p(fmt, *v):
    return struct.pack('<'+fmt, *v)


def txt(s):
    b = s.encode('utf-8')
    return p('i', len(b))+b


def fixture(scale=1):
    bones = [('hips',(0,1,0),-1), ('spine',(0,1.2,0),0),
             ('head',(0,1.8,0),3), ('neck',(0,1.6,0),1),
             ('leftleg',(-.1,.9,0),0), ('rightleg',(.1,.9,0),0),
             ('leftknee',(-.1,.5,0),4), ('rightknee',(.1,.5,0),5),
             ('leftarm',(-.2,1.5,0),1), ('rightarm',(.2,1.5,0),1),
             ('leftelbow',(-.5,1.5,0),8), ('rightelbow',(.5,1.5,0),9),
             ('lefthand',(-.8,1.5,0),10), ('righthand',(.8,1.5,0),11),
             ('chest',(0,1.4,0),1)]
    data = b'PMX '+p('fB',2,8)+bytes([1,0,1,1,1,1,1,1])
    data += txt('Synthetic test')+txt('')*3+p('i',3)
    for pos in [(0,0,0),(0,2,0),(.1,1,0)]:
        data += p('3f3f2fB', *(v*scale for v in pos), 0,0,-1, 0,0, 2)
        data += p('4b4ff', 1,14,9,-1, .35,.25,.4,0, 1)
    data += p('i3Bi',3,0,1,2,0)  # indices then texture count
    data += p('i',1)+txt('body')+txt('')
    data += p('4f3ff3fB4ff',1,1,1,1, 0,0,0, 0, 0,0,0, 0, 0,0,0,0, 0)
    data += p('bbBBB',-1,-1,0,1,0)+txt('')+p('i',3)
    data += p('i',len(bones))
    for name,pos,parent in bones:
        data += txt(name)+txt('')+p('3fbiH3f',*(v*scale for v in pos),parent,0,0,0,0,0)
    data += p('4i',0,0,0,0) # empty morphs/display/physics (unused prefix)
    return data


def read_o3d(path):
    """Independent sequential validation, including all index/weight boundaries."""
    data = path.read_bytes()
    offset = 0
    def take(fmt):
        nonlocal offset
        result = struct.unpack_from('<'+fmt,data,offset)
        offset += struct.calcsize('<'+fmt)
        return result
    def tag(value):
        assert take('B')[0] == value
    assert take('3B') == (0x84,0x19,1)
    tag(0x17)
    n = take('H')[0]
    vertices = [take('8f') for _ in range(n)]
    assert all(math.isfinite(x) for v in vertices for x in v)
    tag(0x49)
    triangles = [take('4H') for _ in range(take('H')[0])]
    assert all(max(t[:3]) < n and t[3] == 0 for t in triangles)
    tag(0x26)
    assert take('H')[0] == 1
    take('11f')
    size = take('B')[0]
    texture = data[offset:offset+size].decode('ascii'); offset += size
    tag(0x79); take('16f')
    tag(0x54)
    weights = [0.0]*n
    names = []
    for _ in range(take('H')[0]):
        size = take('B')[0]
        names.append(data[offset:offset+size].decode()); offset += size
        for _ in range(take('H')[0]):
            index, weight = take('Hf')
            assert index < n and 0 < weight <= 1
            weights[index] += weight
    assert names == SLOTS
    assert all(abs(w-1) < 1e-5 for w in weights)
    assert offset == len(data)
    return vertices, triangles, texture


class ConverterTests(unittest.TestCase):
    def d_leg_model(self):
        model = load(self.source)
        joints = identify(model, {})
        indices = []
        for role, name in zip(SLOTS[:4], ('左足D', '右足D', '左ひざD', '右ひざD')):
            parent = joints['hips'] if role.endswith('thigh') else indices[0 if role.startswith('left') else 1]
            indices.append(len(model.bones))
            model.bones.append(Bone(name, '', model.bones[joints[role]].position, parent))
        for name in ('右足首D', '右足先EX'):
            parent = indices[-1]
            indices.append(len(model.bones))
            model.bones.append(Bone(name, '', (0.1, 0.1, 0), parent))
        model.vertices = [replace(model.vertices[i % 3], weights=[(index, 1.0)])
                          for i, index in enumerate(indices)]
        model.indices = list(range(6)); model.materials[0].count = 6
        return model, joints, indices

    def test_parallel_d_legs_and_toes_keep_weights(self):
        model, joints, indices = self.d_leg_model()
        # A blended control/deformation weight must merge into the same slot.
        model.vertices[0].weights = [(joints['left_thigh'], .4), (indices[0], .6)]
        _, _, weights, _ = prepare(model, joints, 1.75)
        self.assertEqual(weights, [{0:1.0},{1:1.0},{2:1.0},{3:1.0},{3:1.0},{3:1.0}])
        output = self.root/'d-legs'
        report = convert(model, self.source, output, 'DLegs', 1.75, {})
        self.assertEqual([report['weighted_vertices_by_bone'][s] for s in SLOTS[:4]], [1,1,1,3])
        read_o3d(output/'Humans/DLegs/model/body_0000.o3d')

    def test_d_only_legs_and_unrelated_d_bone(self):
        model, joints, indices = self.d_leg_model()
        for role in SLOTS[:4]:
            model.bones[joints[role]].name = 'unused_' + role
        found = identify(model, {})
        self.assertEqual([found[r] for r in SLOTS[:4]], indices[:4])
        model.bones.append(Bone('HairD', '', (0,2,0), found['head']))
        model.vertices[0].weights = [(len(model.bones)-1,1)]
        weights = prepare(model, found, 1.75)[2]
        self.assertEqual(weights[0], {SLOTS.index('head'):1.0})

    def test_d_leg_pivot_mismatch_is_not_silently_merged(self):
        model, joints, indices = self.d_leg_model()
        model.bones[indices[0]].position = (99,99,99)
        with self.assertRaisesRegex(ConversionError, 'different rest position'):
            prepare(model, joints, 1.75)

    def test_offset_d_legs_are_automatically_selected_and_exported(self):
        model, joints, indices = self.d_leg_model()
        for role, index in zip(SLOTS[:4], indices[:4]):
            x, y, z = model.bones[index].position
            model.bones[index].position = (x, y + .02, z)
        found = identify(model, {})
        self.assertEqual([found[r] for r in SLOTS[:4]], indices[:4])
        self.assertEqual(prepare(model, found, 1.75)[2],
                         [{0:1.0},{1:1.0},{2:1.0},{3:1.0},{3:1.0},{3:1.0}])
        output = self.root/'offset-d-legs'
        report = convert(model, self.source, output, 'OffsetDLegs', 1.75, {})
        self.assertEqual([report['joints'][r] for r in SLOTS[:4]],
                         [model.bones[i].name for i in indices[:4]])
        read_o3d(output/'Humans/OffsetDLegs/model/body_0000.o3d')

    def test_offset_d_legs_respect_explicit_mapping(self):
        model, joints, indices = self.d_leg_model()
        model.bones[indices[0]].position = (-.1, .92, 0)
        role = 'left_thigh'
        found = identify(model, {role: model.bones[joints[role]].name})
        self.assertEqual(found[role], joints[role])
        with self.assertRaisesRegex(ConversionError, 'different rest position'):
            prepare(model, found, 1.75)
        found = identify(model, {role: '左足D'})
        prepare(model, found, 1.75)

    def test_offset_d_selection_preserves_both_leg_chains(self):
        model, joints, indices = self.d_leg_model()
        for role, index in zip(SLOTS[:4], indices[:4]):
            x, y, z = model.bones[index].position
            model.bones[index].position = (x, y + .02, z)
        # Ordinary controls, mixed weights and ordinary ankle descendants.
        model.vertices[0].weights = [(joints['left_thigh'], 1)]
        model.vertices[1].weights = [(joints['right_thigh'], .4), (indices[1], .6)]
        model.vertices[2].weights = [(joints['left_shin'], 1)]
        model.vertices[3].weights = [(joints['right_shin'], 1)]
        model.bones.append(Bone('ordinary_ankle', '', (0.1,.1,0), joints['right_shin']))
        model.vertices[4].weights = [(len(model.bones)-1, 1)]
        for overrides in ({}, {'left_thigh': '左足D'}):
            found = identify(model, overrides)
            self.assertEqual(prepare(model, found, 1.75)[2],
                             [{0:1.0},{1:1.0},{2:1.0},{3:1.0},{3:1.0},{3:1.0}])
        out = self.root/'mixed-offset'
        report = convert(model, self.source, out, 'Mixed', 1.75, {})
        self.assertEqual([report['weighted_vertices_by_bone'][r] for r in SLOTS[:4]], [1,1,1,3])
        read_o3d(out/'Humans/Mixed/model/body_0000.o3d')

    def test_coincident_d_legs_keep_original_selection(self):
        model, joints, _ = self.d_leg_model()
        self.assertEqual(identify(model, {}), joints)

    def test_ambiguous_d_legs_still_fail(self):
        model, _, indices = self.d_leg_model()
        model.bones[indices[0]].position = (-.1, .92, 0)
        model.bones.append(Bone('leftlegD', '', (-.1, .93, 0), 0))
        with self.assertRaisesRegex(ConversionError, 'ambiguous D deformation bones'):
            prepare(model, identify(model, {}), 1.75)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root/'人物.pmx'
        self.source.write_bytes(fixture())

    def tearDown(self):
        self.temp.cleanup()

    def test_parser_and_weight_sum(self):
        m = load(self.source)
        _, _, w, _ = prepare(m, identify(m, {}), 1.75)
        self.assertAlmostEqual(w[0][SLOTS.index('torso')], .6, places=6)
        self.assertAlmostEqual(w[0][SLOTS.index('right_arm')], .4, places=6)

    def test_end_to_end_cli_and_binary(self):
        output = self.root/'package'
        result = subprocess.run([sys.executable,'-m','omsimod','convert',str(self.source),
                                 '--output',str(output),'--name','TestDriver'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report['game_verified'])
        folder = output/'Humans'/'TestDriver'
        vertices, tris, texture = read_o3d(next((folder/'model').glob('*.o3d')))
        self.assertEqual(len(tris),1)
        self.assertAlmostEqual(max(v[1] for v in vertices),1.75)
        self.assertTrue((folder/'texture'/texture).exists())
        hum = (folder/'driver.hum').read_text().splitlines()
        link = hum.index('[links]')+1
        self.assertEqual(len(hum[link:hum.index('[walk_param]')]),22)
        self.assertEqual(self.source.read_bytes(),fixture())

    def test_texture_tint_and_alpha(self):
        src = self.root/'a.png'; dst=self.root/'b.png'
        Image.new('RGBA',(1,1),(200,100,50,128)).save(src)
        self.assertEqual(bake_texture(src,(.5,1,1,.5),dst),2)
        with Image.open(dst) as img:
            self.assertEqual(img.getpixel((0,0)),(100,100,50,64))

    def test_no_overwrite(self):
        out = self.root/'existing'; out.mkdir()
        (out/'keep').write_text('keep')
        with self.assertRaises(ConversionError):
            convert(load(self.source),self.source,out,'Test',1.75,{})
        self.assertEqual((out/'keep').read_text(),'keep')

    def test_texture_escape_and_missing_fail_atomically(self):
        for name in ['../secret.png','C:\\secret.png','missing.png']:
            m=load(self.source);m.textures=[name];m.materials[0].texture=0
            out=self.root/'out'
            with self.assertRaises(ConversionError):
                convert(m,self.source,out,'Test',1.75,{})
            self.assertFalse(out.exists())

    def test_truncated_input(self):
        for size in (0,4,20,len(fixture())-25):
            self.source.write_bytes(fixture()[:size])
            with self.assertRaises(ConversionError): load(self.source)

    def test_ambiguous_bone_needs_override(self):
        m=load(self.source);m.bones[14].english='spine'
        with self.assertRaises(ConversionError): identify(m,{})
        # Exact native name disambiguates an alias collision.
        m.bones[1].name='custom_spine'
        self.assertEqual(identify(m,{'torso':'custom_spine'})['torso'],1)

    def test_bent_arms_rejected(self):
        m=load(self.source);m.bones[12].position=(-.5,1.8,0)
        with self.assertRaises(ConversionError): prepare(m,identify(m,{}),1.75)

    def test_double_sided(self):
        m=load(self.source);m.materials[0].double_sided=True
        out=self.root/'out'
        convert(m,self.source,out,'Test',1.75,{})
        _,tri,_=read_o3d(next(out.rglob('*.o3d')))
        self.assertEqual(len(tri),2)

    def test_hidden_state_not_vendor_or_material_name(self):
        import copy
        m=load(self.source)
        hidden=copy.deepcopy(m.materials[0])
        hidden.name='arbitrary_vendor_layer'
        hidden.diffuse=(1,1,1,0)
        hidden.texture=0
        m.textures=['hidden_texture_not_present.png']
        m.materials[0].name='face_expression_visible'
        m.materials.append(hidden)
        m.indices=m.indices*2
        out=self.root/'hidden'
        report=convert(m,self.source,out,'Test',1.75,{})
        self.assertEqual(report['output_meshes'],1)
        self.assertTrue(any('arbitrary_vendor_layer' in w for w in report['warnings']))
        self.assertFalse(any('face_expression_visible' in w for w in report['warnings']))


if __name__ == '__main__':
    unittest.main()
